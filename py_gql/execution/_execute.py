# -*- coding: utf-8 -*-
""" Implement the evaluating requests section of the
GraphQL specification. """

# REVIEW: The resolver interface is mirrored on graphql-js but that might change

# REVIEW: The Future based interface can be awkward especially when checking
# for Future instances in order to gain performance.

import functools as ft

import six

from . import _concurrency
from .._string_utils import stringify_path
from .._utils import OrderedDict, find_one, is_iterable, lazy
from ..exc import (
    CoercionError,
    ExecutionError,
    ResolverError,
    ScalarSerializationError,
    UnknownEnumValue,
)
from ..lang import ast as _ast
from ..schema import (
    EnumType,
    IncludeDirective,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    SkipDirective,
    UnionType,
    is_abstract_type,
)
from ..schema.introspection import schema_field, type_field, type_name_field
from ..utilities import (
    coerce_argument_values,
    coerce_variable_values,
    default_resolver,
    directive_arguments,
)
from .executors import DefaultExecutor, Executor
from .middleware import apply_middlewares
from .wrappers import ExecutionContext, GraphQLResult, ResolveInfo


def execute(  # flake8: noqa : C901
    schema,
    ast,
    executor=None,
    variables=None,
    operation_name=None,
    initial_value=None,
    context_value=None,
    middlewares=None,
):
    """ Execute a graphql query against a schema.

    Args:
        schema (py_gql.schema.Schema): Schema to execute the query against

        ast (py_gql.lang.ast.Document): The parsed query

        executor (Optional[py_gql.execution.Executor]): Executor instance

        variables (Optional[dict]):
            Raw, JSON decoded variables parsed from the request

        operation_name (Optional[str]): Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value (Any): Root resolution value passed to all top-level
            resolvers

        context_value (Any): Custom application-specific execution context
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

        middlewares (Optional[List[Callable]]):
            List of middleware callable to use when resolving fields
    """
    # Programmer errors
    assert isinstance(schema, Schema), "Expected Schema object"
    assert isinstance(ast, _ast.Document), "Expected document"
    assert variables is None or isinstance(
        variables, dict
    ), "Variables must be a dictionnary"
    assert executor is None or isinstance(executor, Executor)
    assert not middlewares or all(callable(mw) for mw in middlewares)

    executor = executor or DefaultExecutor()
    variables = variables or dict()

    operation = get_operation(ast, operation_name)
    object_type = {
        "query": schema.query_type,
        "mutation": schema.mutation_type,
        "subscription": schema.subscription_type,
    }[operation.operation]

    if object_type is None:
        raise ExecutionError(
            "Schema doesn't support %s operation" % operation.operation
        )

    fragments = {
        d.name.value: d
        for d in ast.definitions
        if d.__class__ is _ast.FragmentDefinition
    }

    coerced_variables = coerce_variable_values(schema, operation, variables)

    ctx = ExecutionContext(
        schema,
        ast,
        coerced_variables,
        fragments,
        executor,
        operation,
        middlewares,
        context_value,
    )

    if operation.operation == "query":
        deferred_result = _execute_selections(
            ctx, operation.selection_set.selections, object_type, initial_value
        )
    elif operation.operation == "mutation":
        deferred_result = _execute_selections_serially(
            ctx, operation.selection_set.selections, object_type, initial_value
        )
    else:
        raise NotImplementedError("%s not supported" % operation.operation)

    def _on_end(data):
        return GraphQLResult(
            data=data, errors=[err for err, _, _ in ctx.errors]
        )

    if _concurrency.is_deferred(deferred_result):
        return _concurrency.chain(deferred_result, _on_end, cls=ctx.future_cls)
    return _concurrency.deferred(_on_end(deferred_result), cls=ctx.future_cls)


def get_operation(document, operation_name=None):
    """ Extract relevant operation from a parsed document.

    In case the ``operation_name`` argument is null, the document is
    expected to contain only one operation which will be extracted.

    Args:
        document (py_gql.lang.ast.Document): Parsed document
        opeation_name (Optional[str]): Operation to extract

    Returns:
        py_gql.lang.ast.OperationDefinition: Relevant operation

    Raises:
        ExecutionError: No relevant operation can be found.
    """
    operations = [
        definition
        for definition in document.definitions
        if definition.__class__ is _ast.OperationDefinition
    ]

    if not operations:
        raise ExecutionError("Expected at least one operation")

    if not operation_name:
        if len(operations) == 1:
            return operations[0]
        else:
            raise ExecutionError(
                "Operation name is required when document "
                "contains multiple operation definitions"
            )

    operation = find_one(operations, lambda o: o.name.value == operation_name)
    if operation is not None:
        return operation
    else:
        raise ExecutionError(
            'No operation "%s" found in document' % operation_name
        )


def collect_fields(
    ctx,  # type: ExecutionContext
    object_type,  # type: py_gql.schema.ObjectType
    selections,  # type: List[py_gql.lang.ast.Selection]
    visited_fragments=None,  # type: Optional[Set[str]]
):
    # noqa: C901
    # type: (...) -> OrderedDict
    """ Collect all fields in a selection set, recursively traversing fragments
    in one single map and conserving definitino order.

    Args:
        ctx: Current execution context
        object_type: Current object type
        selections: Selections from the SelectionSet(s) to gather fields from
        visited_fragments: List of already visited fragment spreads

    Returns:
        Ordered map of fieldnames to relevant nodes
    """

    cache_key = object_type.name, tuple(selections)
    if cache_key in ctx.grouped_fields:
        return ctx.grouped_fields[cache_key]

    visited_fragments = visited_fragments or set()
    grouped_fields = OrderedDict()

    def _collect_fragment_fields(fragment_selections):
        fragment_grouped_fields = collect_fields(
            ctx, object_type, fragment_selections, visited_fragments
        )
        for key, gf in fragment_grouped_fields.items():
            if key not in grouped_fields:
                grouped_fields[key] = []
            grouped_fields[key].extend(gf)

    for selection in selections:
        kind = selection.__class__

        if kind is _ast.Field:
            if not _include_selection(selection, ctx.variables):
                continue

            key = (
                selection.alias.value
                if selection.alias
                else selection.name.value
            )
            if key not in grouped_fields:
                grouped_fields[key] = []
            grouped_fields[key].append(selection)

        elif kind is _ast.InlineFragment:
            if not _include_selection(selection, ctx.variables):
                continue

            if not fragment_type_applies(ctx.schema, selection, object_type):
                continue

            _collect_fragment_fields(selection.selection_set.selections)

        elif kind is _ast.FragmentSpread:
            if not _include_selection(selection, ctx.variables):
                continue

            name = selection.name.value
            if name in visited_fragments:
                continue

            fragment = ctx.fragments.get(name)

            if not fragment_type_applies(ctx.schema, fragment, object_type):
                continue

            _collect_fragment_fields(fragment.selection_set.selections)
            visited_fragments.add(name)

    ctx.grouped_fields[cache_key] = grouped_fields
    return grouped_fields


def fragment_type_applies(
    schema,  # type: py_gql.schema.Schema
    fragment,  # type: Union[py_gql.lang.ast.InlineFragment, py_gql.lang.ast.FragmentDefinition]
    object_type,  # type: py_gql.schema.ObjectType
):
    # type: (...) -> bool
    """ Determines if a fragment is applicable to the given type.

    Args:
        schema: Current schema
        fragment: Fragment node
        object_type: Current object type

    Returns:
        ``True`` if the fragment node is applicable to the object type
    """
    type_condition = fragment.type_condition
    if not type_condition:
        return True

    fragment_type = schema.get_type_from_literal(type_condition)
    if fragment_type == object_type:
        return True

    if is_abstract_type(fragment_type):
        return schema.is_possible_type(fragment_type, object_type)

    return False


def _include_selection(node, variables=None):
    skip = directive_arguments(SkipDirective, node, variables=variables)
    include = directive_arguments(IncludeDirective, node, variables=variables)
    skipped = skip is not None and skip["if"]
    included = include is None or include["if"]
    return (not skipped) and included


def _field_def(ctx, parent_type, name):

    cache_key = parent_type.name, name

    if cache_key not in ctx.field_defs:
        if name in ("__schema", "__type", "__typename"):
            if name == "__schema" and ctx.schema.query_type == parent_type:
                ctx.field_defs[cache_key] = schema_field
            elif name == "__type" and ctx.schema.query_type == parent_type:
                ctx.field_defs[cache_key] = type_field
            elif name == "__typename":
                ctx.field_defs[cache_key] = type_name_field
            else:
                ctx.field_defs[cache_key] = parent_type.field_map.get(
                    name, None
                )
        else:
            ctx.field_defs[cache_key] = parent_type.field_map.get(name, None)

    return ctx.field_defs[cache_key]


def _resolve_type(value, context, schema, abstract_type):
    if callable(getattr(abstract_type, "resolve_type", None)):
        return abstract_type.resolve_type(value, context=context, schema=schema)
    if isinstance(value, dict) and value.get("__typename__"):
        return value["__typename__"]
    elif hasattr(value, "__typename__") and value.__typename__:
        return value.__typename__
    else:
        possible_types = schema.get_possible_types(abstract_type)
        for type_ in possible_types:
            if callable(getattr(type_, "is_type_of", None)):
                if type_.is_type_of(value, context=context, schema=schema):
                    return type_
        return None


def _execute_selections(ctx, selections, object_type, object_value, path=None):
    fields = collect_fields(ctx, object_type, selections)
    deferred_fields = []
    path = path or []

    for key, nodes in fields.items():
        field_def = _field_def(ctx, object_type, nodes[0].name.value)
        if field_def is None:
            continue

        deferred_fields.append(
            resolve_field(
                ctx,
                object_type,
                object_value,
                field_def,
                nodes,
                path + [key],
                lambda x: x,
            )
        )

    return _concurrency.chain(
        _concurrency.all_(deferred_fields, cls=ctx.future_cls),
        OrderedDict,
        cls=ctx.future_cls,
    )


def _execute_selections_serially(
    ctx, selections, object_type, object_value, path=None
):
    fields = collect_fields(ctx, object_type, selections)
    resolved_fields = []
    steps = []
    path = path or []

    for key, nodes in fields.items():
        field_def = _field_def(ctx, object_type, nodes[0].name.value)
        if field_def is None:
            continue

        steps.append(
            ft.partial(
                resolve_field,
                ctx,
                object_type,
                object_value,
                field_def,
                nodes,
                path + [key],
                resolved_fields.append,
            )
        )

    steps.append(lambda: OrderedDict(resolved_fields))
    return _concurrency.serial(steps, cls=ctx.future_cls)


def resolve_field(
    ctx, parent_type, parent_value, field_def, nodes, path, on_success
):
    """ Execute a field resolver in the current executor and expose
    result as a Future. """

    key = path[-1]
    info = ResolveInfo(
        field_def,
        parent_type,
        path,
        ctx.schema,
        ctx.variables,
        ctx.fragments,
        ctx.operation,
        nodes,
        ctx.executor,
    )

    resolver = field_def.resolve or default_resolver

    def _unwrap(value):
        value = lazy(value)
        if _concurrency.is_deferred(value):
            return _concurrency.unwrap(value, cls=ctx.future_cls)
        return value

    def resolve(root, args, context, info):
        resolved = _unwrap(
            ctx.executor.submit(resolver, root, args, context, info)
        )
        if _concurrency.is_deferred(resolved):
            complete = ft.partial(
                complete_value, ctx, field_def.type, nodes, info.path
            )
            return _concurrency.chain(
                resolved, lazy, complete, cls=ctx.future_cls
            )
        return complete_value(ctx, field_def.type, nodes, info.path, resolved)

    resolve = apply_middlewares(resolve, ctx.middlewares)

    def _on_success(field_value):
        return on_success((key, field_value))

    def _on_error(err):
        ctx.add_error(err, nodes[0], path)
        return on_success((key, None))

    try:
        args = _argument_values(ctx, field_def, nodes)
    except CoercionError as err:
        return _on_error(err)

    try:
        resolved_or_deferred = resolve(parent_value, args, ctx.context, info)
    except (CoercionError, ResolverError) as err:
        return _on_error(err)
    else:
        if _concurrency.is_deferred(resolved_or_deferred):
            return _concurrency.except_(
                _concurrency.chain(
                    resolved_or_deferred, _on_success, cls=ctx.future_cls
                ),
                (CoercionError, ResolverError),
                _on_error,
                cls=ctx.future_cls,
            )
        return _on_success(resolved_or_deferred)


def complete_value(ctx, field_type, nodes, path, resolved_value):
    kind = field_type.__class__
    if kind is NonNullType:
        # REVIEW:
        # - Error is different than ref implementation
        # - Shouldn't this be a RuntimeError ? As in the developer should
        # never return a null non nullable field and instead reais
        # explicitely if the query lead to this behaviour ?
        def _handle_null(value):
            if value is None:
                ctx.add_error(
                    'Field "%s" is not nullable' % stringify_path(path),
                    nodes[0],
                    path,
                )
            return value

        return _concurrency.chain(
            complete_value(ctx, field_type.type, nodes, path, resolved_value),
            _handle_null,
            cls=ctx.future_cls,
        )

    if resolved_value is None:
        return None

    if kind is ListType:
        if not is_iterable(resolved_value, False):
            raise RuntimeError(
                'Field "%s" is a list type and resolved value '
                "should be iterable" % stringify_path(path)
            )

        return _concurrency.all_(
            [
                complete_value(ctx, field_type.type, nodes, path + [i], entry)
                for i, entry in enumerate(resolved_value)
            ],
            cls=ctx.future_cls,
        )

    # Need to handle custom scalar types
    if issubclass(kind, ScalarType):
        try:
            serialized = field_type.serialize(resolved_value)
        except ScalarSerializationError as err:
            raise RuntimeError(
                'Field "%s" cannot be serialized as "%s": %s'
                % (path, field_type, err)
            )
        else:
            return serialized

    if kind is EnumType:
        try:
            serialized = field_type.get_name(resolved_value)
        except UnknownEnumValue as err:
            raise RuntimeError(
                'Field "%s" cannot be serialized as "%s": %s'
                % (path, field_type, err)
            )
        else:
            return serialized

    if kind in (ObjectType, InterfaceType, UnionType):
        if kind in (InterfaceType, UnionType):
            runtime_type = _resolve_type(
                resolved_value, ctx.context, ctx.schema, field_type
            )

            if isinstance(runtime_type, six.string_types):
                runtime_type = ctx.schema.get_type(runtime_type, None)

            if not isinstance(runtime_type, ObjectType):
                raise RuntimeError(
                    'Abstract type "%s" must resolve to an ObjectType at runtime '
                    'for field "%s". Received "%s".'
                    % (field_type, path, runtime_type)
                )
            # Backup check in case of badly implemented `resolve_type`,
            # `is_type_of`
            if not ctx.schema.is_possible_type(field_type, runtime_type):
                raise RuntimeError(
                    'Runtime ObjectType "%s" is not a possible type for '
                    'field "%s" of type "%s".'
                    % (runtime_type, stringify_path(path), field_type)
                )
        else:
            runtime_type = field_type

        return _execute_selections(
            ctx, list(_subselections(nodes)), runtime_type, resolved_value, path
        )


def _subselections(nodes):
    for field in nodes:
        for selection in field.selection_set.selections:
            yield selection


def _argument_values(ctx, field_def, nodes):
    cache_key = (field_def, nodes[0])
    if cache_key not in ctx.argument_values:
        ctx.argument_values[cache_key] = coerce_argument_values(
            field_def, nodes[0], ctx.variables
        )
    return ctx.argument_values[cache_key]
