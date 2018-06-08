# -*- coding: utf-8 -*-
""" Implement the evaluating requests section of the
GraphQL specification.

See: http://facebook.github.io/graphql/October2016/#sec-Execution

NOTE: The current version of this code was focused on passing the test suite
and does not provide any custom executors (just a placeholder for now) or
middleware capability. As such resolution is purely synchronous.

NOTE: The resolver interface is mirrored on graphql-js but that might change
"""

import json
import functools as ft

import six

from .._utils import (
    find_one, OrderedDict, DefaultOrderedDict, flatten, is_iterable, Path)
from ..exc import (InvalidValue, CoercionError, ScalarSerializationError,
                   UnknownEnumValue, ExecutionError, DocumentValidationError,
                   VariableCoercionError, ResolverError)
from ..lang import ast as _ast, print_ast
from ..schema import (NonNullType, SkipDirective, IncludeDirective,
                      is_abstract_type, ListType, ScalarType, EnumType,
                      ObjectType, InterfaceType, UnionType, Schema)
from ..schema.introspection import schema_field, type_field, type_name_field
from ..utilities import (typed_value_from_ast, coerce_value,
                         coerce_argument_values)
from ..validation import validate_ast
from ._utils import ExecutionContext, ResolutionContext, directive_arguments
from .executors import DefaultExecutor, Executor
from . import _concurrency


def execute(schema, ast, executor=None, variables=None, operation_name=None,
            initial_value=None, validators=None, context=None,
            _skip_validation=False):
    """
    :type schema: py_gql.schema.Schema
    :param schema: Schema to execute the query against

    :type ast: py_gql.lang.ast.Document
    :param ast:

    :type executor:
    :param executor:

    :type variables:
    :param variables:

    :type operation_name: str
    :param operation_name:

    :type initial_value:
    :param initial_value:

    :type context: any
    :param context:
        Custom application-specific execution context. Use this to pass in
        anything your resolver require.
        Limits on the type(s) used here will depend on your own resolver
        implementations and the executor you use.

    :type validators: List[py_gql.validation.ValidationVisitor]
    :param validators:
        List of custom validators to use **instead** of the specified ones.

    :type _skip_validation: bool
    :param _skip_validation:
        Set to `True` to skip document validation.
    """
    # This can raise and should as it is a §ogrammer error that
    # should not be exposed
    assert isinstance(schema, Schema) and schema.validate(), 'Invalid schema'
    assert isinstance(ast, _ast.Document), 'Expected document'
    assert variables is None or isinstance(variables, dict), \
        'Variables must be a dictionnary'
    assert executor is None or isinstance(executor, Executor)

    executor = executor or DefaultExecutor()

    variables = variables or dict()

    # REVIEW: Should this be part of the execution code ? It makes a few tests
    # awkward and could very well be part of another entry point.
    if not _skip_validation:
        validation_result = validate_ast(schema, ast, validators=validators)
        if not validation_result:
            raise DocumentValidationError(validation_result.errors)

    operation = get_operation(ast, operation_name)

    fragments = {
        d.name.value: d
        for d in ast.definitions
        if isinstance(d, _ast.FragmentDefinition)
    }

    coerced_variables = coerce_variable_values(schema, operation, variables)

    object_type = {
        'query': schema.query_type,
        'mutation': schema.mutation_type,
        'subscription': schema.subscription_type,
    }[operation.operation]

    if object_type is None:
        raise ExecutionError(
            "Schema doesn't support %s operation" % operation.operation)

    ctx = ExecutionContext(
        schema, ast, coerced_variables, fragments, executor, operation, context)

    # While it would be more python-ic to raise in case of validation error,
    # the natural flow would be to interrupt processing but the spec
    # (http://facebook.github.io/graphql/October2016/#sec-Errors-and-Non-Nullability)
    # says that we should null field and return all errors. Maybe we can
    # re-evaluate the interpretation later.
    result = _execute(ctx, operation, object_type, initial_value).result()
    return result, ctx.errors


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
        if isinstance(definition, _ast.OperationDefinition)
    ]

    if not operations:
        raise ExecutionError('Must provide an operation')

    if not operation_name:
        if len(operations) == 1:
            return operations[0]
        else:
            raise ExecutionError('Operation name is required when document '
                                 'contains multiple operation definitions')

    operation = find_one(operations, lambda o: o.name.value == operation_name)
    if operation is not None:
        return operation
    else:
        raise ExecutionError('No operation "%s" found in document'
                             % operation_name)


def coerce_variable_values(schema, operation, variables=None):
    """ Prepares an object map of variable values of the correct type based on
    the provided operation definition and arbitrary JSON input. If the input
    cannot be parsed to match the variable definitions, an ExecutionError will
    be thrown.

    The returned value is a plain dict since it is exposed to user code.

    Extra variables are ignored and filtered out.

    :type schema: py_gql.schema.Schema

    :type operation: py_gql.lang.ast.OperationDefinition

    :type variables: Optional[dict]

    :rtype: dict
    """
    variables = dict() if variables is None else variables
    coerced, errors = {}, []

    for var_def in operation.variable_definitions:
        name = var_def.variable.name.value
        var_type = schema.get_type_from_literal(var_def.type)
        if name not in variables:
            if var_def.default_value is not None:
                try:
                    coerced[name] = typed_value_from_ast(
                        var_def.default_value,
                        var_type,
                    )
                except InvalidValue as err:
                    errors.append(
                        'Variable "$%s" got invalid default value %s (%s)'
                        % (name, print_ast(var_def.default_value), err)
                    )
            elif isinstance(var_type, NonNullType):
                errors.append(
                    'Variable "$%s" of required type "%s" was not provided.'
                    % (name, var_type)
                )
        else:
            try:
                coerced[name] = coerce_value(variables[name], var_type)
            except (InvalidValue, CoercionError) as err:
                errors.append(
                    'Variable "$%s" got invalid value %s (%s)'
                    % (name, json.dumps(variables[name], sort_keys=True), err)
                )

    if errors:
        raise VariableCoercionError(errors)

    return coerced


def collect_fields(ctx, object_type, selections, visited_fragments=None):
    """ Collect all fields in a selection set, recursively traversing fragments
    in one single map.

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

    :rtype: bool
    """
    visited_fragments = visited_fragments or set()
    grouped_fields = DefaultOrderedDict(list)

    def _collect_fragment_fields(fragment_selections):
        fragment_grouped_fields = collect_fields(
            ctx,
            object_type,
            fragment_selections,
            visited_fragments
        )
        for key, gf in fragment_grouped_fields.items():
            grouped_fields[key].extend(gf)

    for selection in selections:
        if isinstance(selection, _ast.Field):
            if not _include_selection(selection, ctx.variables):
                continue

            key = (selection.alias.value
                   if selection.alias
                   else selection.name.value)
            grouped_fields[key].append(selection)

        elif isinstance(selection, _ast.InlineFragment):
            if not _include_selection(selection, ctx.variables):
                continue

            if not fragment_type_applies(ctx.schema, selection, object_type):
                continue

            _collect_fragment_fields(selection.selection_set.selections)

        elif isinstance(selection, _ast.FragmentSpread):
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
    skipped = skip is not None and skip['if']
    included = include is None or include['if']
    return (not skipped) and included


def _field_def(schema, parent_type, name):
    if name in ('__schema', '__type', '__typename'):
        if name == '__schema' and schema.query_type == parent_type:
            return schema_field
        elif name == '__type' and schema.query_type == parent_type:
            return type_field
        elif name == '__typename':
            return type_name_field
    return parent_type.field_map.get(name, None)


def _resolve_type(value, context, schema, abstract_type):
    if callable(getattr(abstract_type, 'resolve_type', None)):
        return abstract_type.resolve_type(value, context=context, schema=schema)
    elif hasattr(value, '__graphql_type__') and value.__graphql_type__:
        return value.__graphql_type__
    else:
        possible_types = schema.get_possible_types(abstract_type)
        for typ in possible_types:
            if callable(getattr(typ, 'is_type_of', None)):
                if typ.is_type_of(value, context=context, schema=schema):
                    return typ
        return None


def _defer_field(ctx, object_type, object_value, field_def, nodes, path,
                 on_success, on_error):

    # REVIEW: Should this still happen ?
    def _evaluate_lazy_resolver(value):
        if callable(value):
            return _concurrency.deferred(value())
        return _concurrency.deferred(value)

    return _concurrency.except_(
        _concurrency.chain(
            _concurrency.deferred(None),
            lambda _: resolve_field(
                ctx,
                object_type,
                object_value,
                field_def,
                nodes,
                path
            ),
            _evaluate_lazy_resolver,
            lambda resolved_value: complete_value(
                ctx,
                field_def.type,
                nodes,
                resolved_value,
                path
            ),
            on_success,
        ),
        (CoercionError, ResolverError),
        on_error,
    )


def execute_selections(ctx, selections, object_type, object_value, path=None):
    """
    """
    try:
        fields = collect_fields(ctx, object_type, selections)
    except (InvalidValue, CoercionError) as err:
        raise ExecutionError.new(err)

    deferred_fields = []
    path = path or Path()

    def _handlers(key, nodes, field_path):
        def _handle_error(err):
            ctx.add_error(err, nodes[0], field_path)
            return (key, None)

        def _handle_success(completed):
            return _concurrency.deferred((key, completed))

        return _handle_success, _handle_error

    for key, nodes in fields.items():
        field_def = _field_def(ctx.schema, object_type, nodes[0].name.value)
        if field_def is None:
            continue

        field_path = path + key
        _handle_success, _handle_error = _handlers(key, nodes, field_path)

        deferred_fields.append(_defer_field(
            ctx, object_type, object_value, field_def, nodes, field_path,
            _handle_success, _handle_error
        ))

    return _concurrency.chain(_concurrency.all_(deferred_fields), OrderedDict)


def execute_selections_serially(ctx, selections, object_type, object_value,
                                path=None):
    """
    """
    try:
        fields = collect_fields(ctx, object_type, selections)
    except (InvalidValue, CoercionError) as err:
        raise ExecutionError.new(err)

    resolved_fields = []
    steps = []

    path = path or Path()

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

        field_path = path + key
        _handle_success, _handle_error = _handlers(key, nodes, field_path)

        steps.append(
            ft.partial(
                _defer_field,
                ctx, object_type, object_value, field_def, nodes, field_path,
                _handle_success, _handle_error
            )
        )

    return _concurrency.chain(
        _concurrency.serial(steps),
        lambda _: OrderedDict(resolved_fields)
    )


def resolve_field(ctx, parent_type, parent_value, field_def, nodes, path):
    """ Execute a field resolver in the current executor and expose
    result as a Future.

    Lookup of order for the resolver function is:

        1. field definition
        2. item in the root value, executed in the executor if callable
           returned as is otherwise
        3. attribute of the root value, executed in the executor if callable
           (method, parent value is not passed) returned as is otherwise
    """
    field_name = nodes[0].name.value

    info = ResolutionContext(
        field_def, parent_type, path, ctx.schema, ctx.variables, ctx.fragments,
        ctx.operation, nodes, ctx.executor)

    args = coerce_argument_values(field_def, nodes[0], ctx.variables)

    if field_def.resolve is None:
        if isinstance(parent_value, dict):
            field_value = parent_value.get(field_name, None)
            if callable(field_value):
                return ctx.executor.submit(
                    field_value,
                    parent_value,
                    args,
                    ctx.context,
                    info
                )
            return _concurrency.deferred(field_value)
        else:
            attr_value = getattr(parent_value, field_name, None)
            # Call methods / support lazy evaluation
            if callable(attr_value):
                return ctx.executor.submit(
                    attr_value,
                    args,
                    ctx.context,
                    info
                )
            return _concurrency.deferred(attr_value)
    else:
        return ctx.executor.submit(
            field_def.resolve,
            parent_value,
            args,
            ctx.context,
            info
        )


def complete_value(ctx, field_type, nodes, resolved_value, path, serial=False):
    """
    """
    if isinstance(field_type, NonNullType):
        # REVIEW:
        # - Error is different than ref implementation
        # - Shouldn't this be a RuntimeError ? As in the developer should
        # never return a null non nullable field and instead reais
        # explicitely if the query lead to this behaviour ?
        def _handle_null(value):
            if value is None:
                ctx.add_error(
                    'Field "%s" is not nullable' % path, nodes[0], path
                )
            return _concurrency.deferred(value)

        return _concurrency.chain(
            complete_value(
                ctx, field_type.type, nodes, resolved_value, path, serial
            ),
            _handle_null
        )

    if resolved_value is None:
        return _concurrency.deferred(None)

    if isinstance(field_type, ListType):
        return _complete_list_value(
            ctx, field_type.type, nodes, resolved_value, path, serial
        )

    if isinstance(field_type, ScalarType):
        try:
            serialized = field_type.serialize(resolved_value)
        except ScalarSerializationError as err:
            raise RuntimeError(
                'Field "%s" cannot be serialized as "%s": %s'
                % (path, field_type, err))
        else:
            return _concurrency.deferred(serialized)

    if isinstance(field_type, EnumType):
        try:
            serialized = field_type.get_name(resolved_value)
        except UnknownEnumValue as err:
            raise RuntimeError(
                'Field "%s" cannot be serialized as "%s": %s'
                % (path, field_type, err))
        else:
            return _concurrency.deferred(serialized)

    if isinstance(field_type, (ObjectType, InterfaceType, UnionType)):
        return _complete_object_value(
            ctx, field_type, nodes, resolved_value, path, serial
        )


def _complete_list_value(ctx, item_type, nodes, list_value, path, serial):
    # Compared to ref implementation, this does not support lazy evaluation
    # of list entries. Maybe once the Future based interface is done.
    if not is_iterable(list_value, False):
        raise RuntimeError('Field "%s" is a list type and resolved value '
                           'should be iterable' % path)

    if not serial:
        return _concurrency.all_([
            complete_value(ctx, item_type, nodes, entry, path + i)
            for i, entry in enumerate(list_value)
        ])
    else:
        results = []
        steps = [
            lambda: _concurrency.chain(
                complete_value(ctx, item_type, nodes, entry, path + i, serial),
                results.append
            )
            for i, entry in enumerate(list_value)
        ]
        return _concurrency.chain(
            _concurrency.serial(steps),
            lambda _: _concurrency.deferred(results)
        )


def _complete_object_value(ctx, field_type, nodes, object_value, path, serial):
    if isinstance(field_type, (InterfaceType, UnionType)):
        runtime_type = _resolve_type(
            object_value, ctx.context, ctx.schema, field_type)

        if isinstance(runtime_type, six.string_types):
            runtime_type = ctx.schema.get_type(runtime_type, None)

        if not isinstance(runtime_type, ObjectType):
            raise RuntimeError(
                'Abstract type "%s" must resolve to an ObjectType at runtime '
                'for field "%s". Received "%s".'
                % (field_type, path, runtime_type))

        # Backup check in case of badly implemented `resolve_type`,
        # `is_type_of`
        if not ctx.schema.is_possible_type(field_type, runtime_type):
            raise RuntimeError(
                'Runtime ObjectType "%s" is not a possible type for '
                'field "%s" of type "%s".' % (runtime_type, path, field_type))

    else:
        runtime_type = field_type

    selections = list(flatten((f.selection_set.selections for f in nodes)))
    if serial:
        return execute_selections_serially(
            ctx, selections, runtime_type, object_value, path
        )
    return execute_selections(ctx, selections, runtime_type, object_value, path)


def _execute(ctx, operation, object_type, initial_value):
    if operation.operation == 'query':
        return execute_selections(
            ctx,
            operation.selection_set.selections,
            object_type,
            initial_value,
        )
    elif operation.operation == 'mutation':
        return execute_selections_serially(
            ctx,
            operation.selection_set.selections,
            object_type,
            initial_value,
        )
    else:
        raise NotImplementedError('%s not supported' % operation.operation)
