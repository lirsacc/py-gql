# -*- coding: utf-8 -*-
""" Implement the evaluating requests section of the
GraphQL specification. """
# REVIEW: The resolver interface is mirrored on graphql-js but that might change

import functools as ft

import six

from . import _concurrency
from .._utils import OrderedDict, find_one, flatten, is_iterable
from .._string_utils import stringify_path
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
from ._utils import ExecutionContext, GraphQLResult, ResolveInfo
from .executors import DefaultExecutor, Executor
from .middleware import apply_middlewares


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

    :type schema: py_gql.schema.Schema
    :param schema: Schema to execute the query against

    :type ast: py_gql.lang.ast.Document
    :param ast: The parsed query AST containing all operations, fragments, etc

    :type executor: py_gql.execution.executors.Executor
    :param executor: Custom executor to process resolver functions

    :type variables: Optional[dict]
    :param variables: Raw, JSON decoded variables parsed from the request

    :type operation_name: Optional[str]
    :param operation_name: Operation to execute
        If specified, the operation with the given name will be executed. If
        not; this executes the single operation without disambiguation.

    :type initial_value: any
    :param initial_value: Root resolution value
        Will be passed to all top-level resolvers.

    :type context_value: any
    :param context_value:
        Custom application-specific execution context. Use this to pass in
        anything your resolvers require like database connection, user
        information, etc.
        Limits on the type(s) used here will depend on your own resolver
        implementations and the executor you use. Most thread safe
        data-structures should work.

    :type middlewares: Optional[List[callable]]
    :param middlewares:
        List of middleware callable to consume when resolving fields.
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
        if d.is_(_ast.FragmentDefinition)
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

    return _concurrency.chain(deferred_result, _on_end)


def get_operation(document, operation_name):
    """ Extract relevant operation from a parsed document

    :type document: py_gql.lang.ast.Document
    :param document: Parsed document

    :type operation_name: Optional[str]
    :param operation_name: Operation name to extract

    :rtype: py_gql.lang.ast.OperationDefinition
    """
    operations = [
        definition
        for definition in document.definitions
        if definition.is_(_ast.OperationDefinition)
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
    ctx, object_type, selections, visited_fragments=None
):  # noqa : C901
    """ Collect all fields in a selection set, recursively traversing fragments
    in one single map and conserving definitino order.

    :type ctx: ExecutionContext
    :param ctx:
        Current execution context

    :type object_type: py_gql.schema.Type
    :param object_type:
        Current object type

    :type selections: List[py_gql.lang.ast.Selection]
    :param selections:
        Selections from the SelectionSet node(s) to gather fields from

    :type visited_fragments: Optional[Set[str]]
    :param visited_fragments:
        List of already visited fragment spreads

    :rtype: OrderedDict
    """
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

        if selection.is_(_ast.Field):
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

        elif selection.is_(_ast.InlineFragment):
            if not _include_selection(selection, ctx.variables):
                continue

            if not fragment_type_applies(ctx.schema, selection, object_type):
                continue

            _collect_fragment_fields(selection.selection_set.selections)

        elif selection.is_(_ast.FragmentSpread):
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

    return grouped_fields


def fragment_type_applies(schema, fragment, object_type):
    """ Determines if a fragment is applicable to the given type.

    :type schema: py_gql.schema.Schema
    :param schema:
        Current schema

    :type fragment: py_gql.lang.ast.InlineFragment|\
        py_gql.lang.ast.FragmentDefinition
    :param fragment:
        Fragment node

    :type object_type: py_gql.schema.Type
    :param object_type:
        Current object type

    :rtype: bool
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


def _field_def(schema, parent_type, name):
    if name in ("__schema", "__type", "__typename"):
        if name == "__schema" and schema.query_type == parent_type:
            return schema_field
        elif name == "__type" and schema.query_type == parent_type:
            return type_field
        elif name == "__typename":
            return type_name_field
    return parent_type.field_map.get(name, None)


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

    def _handlers(key, nodes, field_path):
        def _handle_error(err):
            ctx.add_error(err, nodes[0], field_path)
            return (key, None)

        def _handle_success(completed):
            return (key, completed)

        return _handle_success, _handle_error

    for key, nodes in fields.items():
        field_def = _field_def(ctx.schema, object_type, nodes[0].name.value)
        if field_def is None:
            continue

        field_path = path + [key]
        _handle_success, _handle_error = _handlers(key, nodes, field_path)

        deferred_fields.append(
            resolve_field(
                ctx,
                object_type,
                object_value,
                field_def,
                nodes,
                field_path,
                _handle_success,
                _handle_error,
            )
        )

    return _concurrency.chain(_concurrency.all_(deferred_fields), OrderedDict)


def _execute_selections_serially(
    ctx, selections, object_type, object_value, path=None
):
    fields = collect_fields(ctx, object_type, selections)
    resolved_fields = []
    steps = []
    path = path or []

    def _handlers(key, nodes, field_path):
        def _handle_error(err):
            ctx.add_error(err, nodes[0], field_path)
            resolved_fields.append((key, None))

        def _handle_success(completed):
            resolved_fields.append((key, completed))

        return _handle_success, _handle_error

    for key, nodes in fields.items():
        field_def = _field_def(ctx.schema, object_type, nodes[0].name.value)
        if field_def is None:
            continue

        field_path = path + [key]
        _handle_success, _handle_error = _handlers(key, nodes, field_path)

        steps.append(
            ft.partial(
                resolve_field,
                ctx,
                object_type,
                object_value,
                field_def,
                nodes,
                field_path,
                _handle_success,
                _handle_error,
            )
        )

    steps.append(lambda: OrderedDict(resolved_fields))
    return _concurrency.serial(steps)


def _unwrap_resolved_value(value):
    value = value() if callable(value) else value
    if _concurrency.is_deferred(value):
        return _concurrency.unwrap(value)
    return value


def resolve_field(
    ctx, parent_type, parent_value, field_def, nodes, path, on_success, on_error
):
    """ Execute a field resolver in the current executor and expose
    result as a Future. """

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

    def resolve(root, args, context, info):
        return _concurrency.chain(
            ctx.executor.submit(resolver, root, args, context, info),
            _unwrap_resolved_value,
            ft.partial(complete_value, ctx, field_def.type, nodes, path),
        )

    if ctx.middlewares:
        resolve = apply_middlewares(resolve, ctx.middlewares)

    try:
        args = coerce_argument_values(field_def, nodes[0], ctx.variables)
    except CoercionError as err:
        return on_error(err)

    return _concurrency.except_(
        _concurrency.chain(
            resolve(parent_value, args, ctx.context, info), on_success
        ),
        (CoercionError, ResolverError),
        on_error,
    )


def complete_value(ctx, field_type, nodes, path, resolved_value):
    field_type_type = type(field_type)
    if field_type_type is NonNullType:
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
        )

    if resolved_value is None:
        return None

    if field_type_type is ListType:
        return _complete_list_value(
            ctx, field_type.type, nodes, resolved_value, path
        )

    if field_type_type is ScalarType:
        try:
            serialized = field_type.serialize(resolved_value)
        except ScalarSerializationError as err:
            raise RuntimeError(
                'Field "%s" cannot be serialized as "%s": %s'
                % (path, field_type, err)
            )
        else:
            return serialized

    if field_type_type is EnumType:
        try:
            serialized = field_type.get_name(resolved_value)
        except UnknownEnumValue as err:
            raise RuntimeError(
                'Field "%s" cannot be serialized as "%s": %s'
                % (path, field_type, err)
            )
        else:
            return serialized

    if field_type_type in (ObjectType, InterfaceType, UnionType):
        return _complete_object_value(
            ctx, field_type, nodes, resolved_value, path
        )


def _complete_list_value(ctx, item_type, nodes, list_value, path):
    if not is_iterable(list_value, False):
        raise RuntimeError(
            'Field "%s" is a list type and resolved value '
            "should be iterable" % stringify_path(path)
        )

    return _concurrency.all_(
        [
            complete_value(ctx, item_type, nodes, path + [i], entry)
            for i, entry in enumerate(list_value)
        ]
    )


def _complete_object_value(ctx, field_type, nodes, object_value, path):
    field_type_type = type(field_type)
    if field_type_type in (InterfaceType, UnionType):
        runtime_type = _resolve_type(
            object_value, ctx.context, ctx.schema, field_type
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

    selections = list(flatten(f.selection_set.selections for f in nodes))
    return _execute_selections(
        ctx, selections, runtime_type, object_value, path
    )
