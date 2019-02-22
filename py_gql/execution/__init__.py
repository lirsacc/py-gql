# -*- coding: utf-8 -*-
"""
"""

# REVIEW: The Async and Sync executors have a bunc of duplicate code which
# allows us to make assumptions and not support mixed cases, which removes
# a large chunk of isawaitable checks that would be made inline otherwise.
# There might be ways to rewrite this in a more readable way.

import asyncio
import functools as ft
from inspect import isawaitable, iscoroutinefunction
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)

from .._string_utils import stringify_path
from .._utils import MaybeAwaitable, deferred_apply, find_one, is_iterable
from ..exc import (
    CoercionError,
    ExecutionError,
    GraphQLResponseError,
    MultiCoercionError,
    ResolverError,
    ScalarSerializationError,
    UnknownEnumValue,
)
from ..lang import ast as _ast
from ..schema import (
    AbstractTypes,
    CompositeTypes,
    EnumType,
    Field,
    GraphQLType,
    IncludeDirective,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    SkipDirective,
    UnionType,
    introspection as _introspection,
)
from ..utilities import (
    coerce_argument_values,
    coerce_variable_values,
    default_resolver,
    directive_arguments,
)
from .middleware import apply_middlewares
from .wrappers import (  # noqa: F401
    GraphQLExtension,
    GraphQLResult,
    GroupedFields,
    ResolveInfo,
    ResponsePath,
)

__all__ = (
    "Executor",
    "SyncExecutor",
    "AsyncExecutor",
    "GraphQLExtension",
    "GraphQLResult",
    "ResolveInfo",
    "ResponsePath",
)

_UNSET = object()

Resolver = Callable[..., Any]


class Executor(object):

    __slots__ = (
        "schema",
        "document",
        "variables",
        "fragments",
        "operation",
        "context_value",
        "_middlewares",
        "_grouped_fields",
        "_fragment_type_applies",
        "_field_defs",
        "_argument_values",
        "_resolver_cache",
        "_errors",
    )

    @classmethod
    def execute_request(
        cls,
        schema: Schema,
        document: _ast.Document,
        operation_name: Optional[str] = None,
        variables: Optional[Mapping[str, Any]] = None,
        initial_value: Optional[Any] = None,
        context_value: Optional[Any] = None,
        middlewares: Optional[Sequence[Resolver]] = None,
    ) -> MaybeAwaitable[GraphQLResult]:
        operation = get_operation(document, operation_name)

        root_type = {
            "query": schema.query_type,
            "mutation": schema.mutation_type,
            "subscription": schema.subscription_type,
        }[operation.operation]

        if root_type is None:
            raise ExecutionError(
                "Schema doesn't support %s operation" % operation.operation
            )

        coerced_variables = coerce_variable_values(
            schema, operation, variables or {}
        )

        executor = cls(
            schema,
            document,
            coerced_variables,
            context_value,
            middlewares or [],
        )

        if operation.operation == "query":
            exe_fn = executor.execute_fields
        elif operation.operation == "mutation":
            exe_fn = executor.execute_fields_serially
        else:
            raise NotImplementedError("%s not supported" % operation.operation)

        fields = executor.collect_fields(
            root_type, operation.selection_set.selections
        )

        data = exe_fn(root_type, initial_value, [], fields)
        return deferred_apply(
            data,
            lambda d: GraphQLResult(
                data=d, errors=[err for err in executor.errors]
            ),
        )

    def __init__(
        self,
        schema: Schema,
        document: _ast.Document,
        variables: Dict[str, Any],
        context_value: Any,
        middlewares: Sequence[Resolver],
    ):
        self.schema = schema
        self.document = document
        self.variables = variables
        self.fragments = {
            f.name.value: f
            for f in document.definitions
            if isinstance(f, _ast.FragmentDefinition)
        }
        self.context_value = context_value

        self._middlewares = middlewares

        self._errors = []  # type: List[GraphQLResponseError]

        # Caches
        self._grouped_fields = (
            {}
        )  # type: Dict[Tuple[str, Tuple[_ast.Selection, ...]], GroupedFields]
        self._fragment_type_applies = (
            {}
        )  # type: Dict[Tuple[str, _ast.Type], bool]
        self._field_defs = {}  # type: Dict[Tuple[str, str], Optional[Field]]
        self._argument_values = (
            {}
        )  # type: Dict[Tuple[Field, _ast.Field], Dict[str, Any]]
        self._resolver_cache = {}  # type: Dict[Resolver, Resolver]

    def add_error(
        self,
        err: Union[CoercionError, ResolverError],
        path: Optional[ResponsePath] = None,
        node: Optional[_ast.Node] = None,
    ) -> None:
        if isinstance(err, MultiCoercionError):
            for child_err in err.errors:
                self.add_error(child_err)
        else:
            if node:
                if err.nodes and node not in err.nodes:
                    err.nodes.append(node)
                elif not err.nodes:
                    err.nodes = [node]
            err.path = path if path is not None else err.path
        self._errors.append(err)

    @property
    def errors(self) -> List[GraphQLResponseError]:
        """ All field errors collected during query execution. """
        return self._errors[:]

    def skip_selection(
        self, node: Union[_ast.Field, _ast.InlineFragment, _ast.FragmentSpread]
    ) -> bool:
        skip = directive_arguments(
            SkipDirective, node, variables=self.variables
        )
        include = directive_arguments(
            IncludeDirective, node, variables=self.variables
        )
        skipped = skip is not None and skip["if"]
        included = include is None or include["if"]
        return skipped or (not included)

    def fragment_type_applies(
        self,
        object_type: ObjectType,
        fragment: Union[_ast.InlineFragment, _ast.FragmentDefinition],
    ) -> bool:
        """ Determines if a fragment is applicable to the given type. """
        type_condition = fragment.type_condition
        if not type_condition:
            return True

        cache_key = (object_type.name, type_condition)
        try:
            return self._fragment_type_applies[cache_key]
        except KeyError:
            fragment_type = self.schema.get_type_from_literal(type_condition)
            if fragment_type == object_type:
                self._fragment_type_applies[cache_key] = True
                return True

            if isinstance(object_type, AbstractTypes):
                if self.schema.is_possible_type(object_type, fragment_type):
                    self._fragment_type_applies[cache_key] = True
                    return True

            self._fragment_type_applies[cache_key] = False
            return False

    def _collect_fragment_fields(
        self,
        parent_type: ObjectType,
        fragment: Union[_ast.FragmentDefinition, _ast.InlineFragment],
        visited_fragments: Set[str],
        grouped_fields: GroupedFields,
    ) -> None:
        fragment_grouped_fields = self.collect_fields(
            parent_type, fragment.selection_set.selections, visited_fragments
        )
        for key, collected in fragment_grouped_fields.items():
            if key not in grouped_fields:
                grouped_fields[key] = []
            grouped_fields[key].extend(collected)

    def collect_fields(
        self,
        parent_type: ObjectType,
        selections: Sequence[_ast.Selection],
        visited_fragments: Optional[Set[str]] = None,
    ) -> GroupedFields:
        """ Collect all fields in a selection set, recursively traversing
        fragments in one single map and conserving definitino order. """
        cache_key = parent_type.name, tuple(selections)
        try:
            return self._grouped_fields[cache_key]
        except KeyError:
            visited_fragments = visited_fragments or set()
            grouped_fields = {}  # type: GroupedFields

            for selection in selections:
                if isinstance(selection, _ast.Field):
                    if self.skip_selection(selection):
                        continue

                    key = selection.response_name
                    if key not in grouped_fields:
                        grouped_fields[key] = []
                    grouped_fields[key].append(selection)

                elif isinstance(selection, _ast.InlineFragment):
                    if self.skip_selection(selection):
                        continue

                    if not self.fragment_type_applies(parent_type, selection):
                        continue

                    self._collect_fragment_fields(
                        parent_type,
                        selection,
                        visited_fragments,
                        grouped_fields,
                    )

                elif isinstance(selection, _ast.FragmentSpread):
                    if self.skip_selection(selection):
                        continue

                    name = selection.name.value
                    if name in visited_fragments:
                        continue

                    fragment = self.fragments[name]
                    if not self.fragment_type_applies(parent_type, fragment):
                        continue

                    self._collect_fragment_fields(
                        parent_type, fragment, visited_fragments, grouped_fields
                    )
                    visited_fragments.add(name)

            self._grouped_fields[cache_key] = grouped_fields
            return grouped_fields

    def field_definition(
        self, parent_type: ObjectType, name: str
    ) -> Optional[Field]:
        """ """
        key = parent_type.name, name
        cache = self._field_defs
        is_query_type = self.schema.query_type == parent_type

        try:
            return cache[key]
        except KeyError:
            if name in ("__schema", "__type", "__typename"):
                if name == "__schema" and is_query_type:
                    cache[key] = _introspection.schema_field
                elif name == "__type" and is_query_type:
                    cache[key] = _introspection.type_field
                elif name == "__typename":
                    cache[key] = _introspection.type_name_field
                else:
                    cache[key] = parent_type.field_map.get(name, None)
            else:
                cache[key] = parent_type.field_map.get(name, None)

            return cache[key]

    def argument_values(
        self, field_definition: Field, node: _ast.Field
    ) -> Dict[str, Any]:
        cache_key = field_definition, node
        try:
            return self._argument_values[cache_key]
        except KeyError:
            self._argument_values[cache_key] = coerce_argument_values(
                field_definition, node, self.variables
            )
        return self._argument_values[cache_key]

    # REVIEW: This seems to involved, I'd rather have one single way to do this
    # at the cose of diverging from the various methods seen in graphql-js.
    def resolve_type(
        self, value: Any, t: Union[InterfaceType, UnionType]
    ) -> Optional[ObjectType]:
        if t.resolve_type is not None:
            maybe_type = t.resolve_type(value, self.context_value, self.schema)
            if isinstance(maybe_type, str):
                return self.schema.get_type(maybe_type, None)  # type: ignore
            else:
                return maybe_type
        elif isinstance(value, dict) and value.get("__typename__"):
            return self.schema.get_type(  # type: ignore
                value["__typename__"], None
            )
        elif hasattr(value, "__typename__") and value.__typename__:
            return self.schema.get_type(  # type: ignore
                value.__typename__, None
            )
        else:
            possible_types = self.schema.get_possible_types(t)
            for pt in possible_types:
                if pt.is_type_of is not None:
                    if pt.is_type_of(value, self.context_value, self.schema):
                        return pt
            return None

    def resolve_field(
        self,
        parent_type: ObjectType,
        parent_value: Any,
        field_definition: Field,
        nodes: List[_ast.Field],
        path: ResponsePath,
    ) -> MaybeAwaitable[Any]:
        resolver = self.get_field_resolver(
            field_definition.resolve or default_resolver
        )
        node = nodes[0]
        info = ResolveInfo(
            field_definition,
            path,
            parent_type,
            self.schema,
            self.variables,
            self.fragments,
            nodes,
        )

        try:
            coerced_args = self.argument_values(field_definition, node)
            resolved = resolver(
                parent_value, self.context_value, info, **coerced_args
            )
        except (CoercionError, ResolverError) as err:
            self.add_error(err, path, node)
            return None
        else:
            return self.complete_value(
                field_definition.type, nodes, path, resolved
            )

    def get_field_resolver(self, base: Resolver) -> Resolver:
        try:
            return self._resolver_cache[base]
        except KeyError:
            resolver = apply_middlewares(base, self._middlewares)
            self._resolver_cache[base] = resolver
            return resolver

    def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> MaybeAwaitable[Dict[str, Any]]:
        raise NotImplementedError()

    def execute_fields_serially(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> MaybeAwaitable[Dict[str, Any]]:
        raise NotImplementedError()

    def complete_value(  # noqa: C901
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> MaybeAwaitable[Any]:
        if isinstance(field_type, NonNullType):
            return self.complete_non_nullable_value(
                field_type.type, nodes, path, resolved_value
            )

        if resolved_value is None:
            return None

        if isinstance(field_type, ListType):
            if not is_iterable(resolved_value, False):
                raise RuntimeError(
                    'Field "%s" is a list type and resolved value should be '
                    "iterable" % stringify_path(path)
                )
            return self.complete_list_value(
                field_type.type, nodes, path, resolved_value
            )

        if isinstance(field_type, ScalarType):
            try:
                return field_type.serialize(resolved_value)
            except ScalarSerializationError as err:
                assert False
                raise RuntimeError(
                    'Field "%s" cannot be serialized as "%s": %s'
                    % (stringify_path(path), field_type, err)
                ) from err

        if isinstance(field_type, EnumType):
            try:
                return field_type.get_name(resolved_value)
            except UnknownEnumValue as err:
                raise RuntimeError(
                    'Field "%s" cannot be serialized as "%s": %s'
                    % (stringify_path(path), field_type, err)
                ) from err

        if isinstance(field_type, CompositeTypes):
            if isinstance(field_type, AbstractTypes):
                runtime_type = self.resolve_type(resolved_value, field_type)

                if not isinstance(runtime_type, ObjectType):
                    raise RuntimeError(
                        'Abstract type "%s" must resolve to an ObjectType at '
                        'runtime for field "%s". Received "%s"'
                        % (field_type, stringify_path(path), runtime_type)
                    )

                # Backup check in case of badly implemented `resolve_type` or
                # `is_type_of`
                if not self.schema.is_possible_type(field_type, runtime_type):
                    raise RuntimeError(
                        'Runtime ObjectType "%s" is not a possible type for '
                        'field "%s" of type "%s".'
                        % (runtime_type, stringify_path(path), field_type)
                    )
            else:
                runtime_type = field_type

            return self.execute_fields(
                runtime_type,
                resolved_value,
                path,
                self.collect_fields(field_type, tuple(_subselections(nodes))),
            )

        raise TypeError(
            "Invalid field type %s at %s" % (field_type, stringify_path(path))
        )

    def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        iterable: Any,
    ) -> MaybeAwaitable[List[Any]]:
        raise NotImplementedError()

    def complete_non_nullable_value(
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> MaybeAwaitable[Any]:
        raise NotImplementedError()


def _subselections(nodes: Iterable[_ast.Field]) -> Iterator[_ast.Selection]:
    for field in nodes:
        if field.selection_set:
            for selection in field.selection_set.selections:
                yield selection


def get_operation(
    document: _ast.Document, operation_name: Optional[str] = None
) -> _ast.OperationDefinition:
    """ Extract relevant operation from a parsed document.

    In case the ``operation_name`` argument is null, the document is
    expected to contain only one operation which will be extracted.

    Args:
        document: Parsed document
        opeation_name: Operation to extract

    Returns: Relevant operation definition

    Raises:
        ExecutionError: No relevant operation can be found.
    """
    operations = [
        definition
        for definition in document.definitions
        if isinstance(definition, _ast.OperationDefinition)
    ]

    if not operations:
        raise ExecutionError("Expected at least one operation definition")

    if not operation_name:
        if len(operations) == 1:
            return operations[0]
        raise ExecutionError(
            "Operation name is required when document "
            "contains multiple operation definitions"
        )

    operation = find_one(
        operations, lambda o: o.name and o.name.value == operation_name
    )
    if operation is not None:
        return operation
    else:
        raise ExecutionError('No operation "%s" in document' % operation_name)


class SyncExecutor(Executor):
    def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Dict[str, Any]:
        result = {}
        for key, nodes in fields.items():
            field_def = self.field_definition(parent_type, nodes[0].name.value)
            if field_def is None:
                continue  # REVIEW: Should this happen at all? Raise?

            result[key] = self.resolve_field(
                parent_type, root, field_def, nodes, path + [key]
            )

        return result

    execute_fields_serially = execute_fields

    def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        iterable: Any,
    ) -> List[Any]:
        return [
            self.complete_value(inner_type, nodes, path + [index], entry)
            for index, entry in enumerate(iterable)
        ]

    def complete_non_nullable_value(
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> Any:
        unwrapped = self.complete_value(field_type, nodes, path, resolved_value)
        if unwrapped is None:
            # REVIEW: Shouldn't this be a RuntimeError? As in the developer
            # should never return a null non nullable field, raising explicitely
            # if the query lead to this behaviour could be valid outcome.
            self.add_error(
                ResolverError(
                    'Field "%s" is not nullable' % stringify_path(path),
                    nodes=nodes,
                    path=path,
                )
            )
        return unwrapped


class AsyncExecutor(Executor):
    async def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Dict[str, Any]:

        keys = []
        pending = []

        for key, nodes in fields.items():
            field_def = self.field_definition(parent_type, nodes[0].name.value)
            if field_def is None:
                continue  # REVIEW: Should this happen at all? Raise?

            field_path = path + [key]
            resolved = self.resolve_field(
                parent_type, root, field_def, nodes, field_path
            )

            keys.append(key)
            pending.append(resolved)

        return dict(zip(keys, await asyncio.gather(*pending)))

    async def execute_fields_serially(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Dict[str, Any]:
        args = []
        done = []  # type: List[Tuple[str, Any]]

        for key, nodes in fields.items():
            field_def = self.field_definition(parent_type, nodes[0].name.value)
            if field_def is None:
                continue  # REVIEW: Should this happen at all? Raise?

            # Needed because closures. Might be a better way to do this without
            # resorting to inlining deferred_serial.
            args.append((key, field_def, nodes, path + [key]))

        async def _next() -> Dict[str, Any]:
            try:
                k, f, n, p = args.pop(0)
            except IndexError:
                return dict(done)
            else:
                resolved = await self.resolve_field(parent_type, root, f, n, p)
                done.append((k, resolved))
                return await _next()

        return await _next()

    async def resolve_field(
        self,
        parent_type: ObjectType,
        parent_value: Any,
        field_definition: Field,
        nodes: List[_ast.Field],
        path: ResponsePath,
    ) -> Any:
        resolver = self.get_field_resolver(
            field_definition.resolve or default_resolver
        )
        node = nodes[0]
        info = ResolveInfo(
            field_definition,
            path,
            parent_type,
            self.schema,
            self.variables,
            self.fragments,
            nodes,
        )

        try:
            coerced_args = self.argument_values(field_definition, node)
            resolved = await resolver(
                parent_value, self.context_value, info, **coerced_args
            )
        except (CoercionError, ResolverError) as err:
            self.add_error(err, path, node)
            return None
        else:
            return await self.complete_value(
                field_definition.type, nodes, path, resolved
            )

    async def complete_value(
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> Any:
        value = super().complete_value(field_type, nodes, path, resolved_value)
        if isawaitable(value):
            return await value
        return value

    async def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        iterable: Any,
    ) -> List[Any]:
        return cast(
            List[Any],
            await asyncio.gather(
                *(
                    self.complete_value(
                        inner_type, nodes, path + [index], entry
                    )
                    for index, entry in enumerate(iterable)
                )
            ),
        )

    async def complete_non_nullable_value(
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> Any:
        # REVIEW: Shouldn't this be a RuntimeError? As in the developer
        # should never return a null non nullable field, raising explicitely
        # if the query lead to this behaviour could be valid outcome.
        unwrapped = await self.complete_value(
            field_type, nodes, path, resolved_value
        )
        if unwrapped is None:
            self.add_error(
                ResolverError(
                    'Field "%s" is not nullable' % stringify_path(path),
                    nodes=nodes,
                    path=path,
                )
            )
        return unwrapped

    def get_field_resolver(self, base: Resolver) -> Resolver:
        try:
            return self._resolver_cache[base]
        except KeyError:
            if not iscoroutinefunction(base):

                async def resolver(*args, **kwargs):
                    return await asyncio.get_event_loop().run_in_executor(
                        None, ft.partial(base, *args, **kwargs)
                    )

            else:
                resolver = base

            resolver = apply_middlewares(resolver, self._middlewares)
            self._resolver_cache[base] = resolver
            return resolver
