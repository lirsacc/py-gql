# -*- coding: utf-8 -*-

from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from .._string_utils import stringify_path
from .._utils import OrderedDict, apply_middlewares, is_iterable
from ..exc import (
    CoercionError,
    ResolverError,
    ScalarSerializationError,
    UnknownEnumValue,
)
from ..lang import ast as _ast
from ..schema import (
    EnumType,
    Field,
    GraphQLAbstractType,
    GraphQLCompositeType,
    GraphQLType,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    UnionType,
)
from .instrumentation import Instrumentation
from .runtime import BlockingRuntime, Runtime
from .wrappers import (
    GroupedFields,
    ResolutionContext,
    ResolveInfo,
    ResponsePath,
)

Resolver = Callable[..., Any]

T = TypeVar("T")
G = TypeVar("G")
E = TypeVar("E", bound=Exception)


class Executor(ResolutionContext):
    """Core executor class.

    This is the core executor class implementing all of the operations necessary
    to fulfill a GraphQL query or mutation as defined [in the spec](
    https://spec.graphql.org/June2018/#sec-Execution).
    """

    __slots__ = ResolutionContext.__slots__ + ("instrumentation", "runtime",)

    def __init__(
        self,
        schema: Schema,
        document: _ast.Document,
        variables: Dict[str, Any],
        context_value: Any,
        *,
        middlewares: Optional[Sequence[Callable[..., Any]]] = None,
        instrumentation: Optional[Instrumentation] = None,
        disable_introspection: bool = False,
        default_resolver: Optional[Resolver] = None,
        runtime: Optional[Runtime] = None
    ):
        super().__init__(
            schema,
            document,
            variables,
            context_value,
            disable_introspection=disable_introspection,
            default_resolver=default_resolver,
            middlewares=middlewares,
        )
        self.instrumentation = instrumentation or Instrumentation()
        self.runtime = runtime or BlockingRuntime()

    def field_resolver(
        self, parent_type: ObjectType, field_definition: Field
    ) -> Resolver:
        base = (
            field_definition.resolver
            or parent_type.default_resolver
            or self._default_resolver
        )
        try:
            return self._resolver_cache[base]
        except KeyError:
            wrapped = (
                self.runtime.wrap_callable(base)
                if base is not self._default_resolver
                else base
            )
            if self._middlewares:
                wrapped = apply_middlewares(wrapped, self._middlewares)
            self._resolver_cache[base] = wrapped
            return wrapped

    def resolve_type(
        self,
        value: Any,
        info: ResolveInfo,
        abstract_type: Union[InterfaceType, UnionType],
    ) -> Optional[ObjectType]:

        maybe_type = None  # type: Optional[Union[ObjectType, str]]

        if abstract_type.resolve_type is not None:
            maybe_type = abstract_type.resolve_type(
                value, self.context_value, info
            )
        else:
            # Default type resolution
            maybe_type = (
                value.get("__typename__", None)
                if isinstance(value, dict)
                else getattr(value, "__typename__", None)
            )

        if maybe_type is None:
            maybe_type = type(value).__name__

        if isinstance(maybe_type, str):
            return self.schema.get_type(maybe_type)  # type: ignore
        else:
            return maybe_type

    def resolve_field(
        self,
        parent_type: ObjectType,
        parent_value: Any,
        field_definition: Field,
        nodes: List[_ast.Field],
        path: ResponsePath,
    ) -> Any:
        resolver = self.field_resolver(parent_type, field_definition)
        node = nodes[0]
        info = ResolveInfo(
            field_definition, path, parent_type, nodes, self.runtime, self
        )

        self.instrumentation.on_field_start(
            parent_value, self.context_value, info
        )

        def fail(err):
            self.add_error(err, path, node)
            self.instrumentation.on_field_end(
                parent_value, self.context_value, info
            )
            return None

        def complete(res):
            self.instrumentation.on_field_end(
                parent_value, self.context_value, info
            )
            return self.complete_value(
                field_definition.type, nodes, path, info, res
            )

        try:
            coerced_args = self.argument_values(field_definition, node)
        except CoercionError as err:
            return fail(err)

        try:
            return self.runtime.unwrap_value(
                self.runtime.map_value(
                    self.runtime.unwrap_value(
                        resolver(
                            parent_value,
                            self.context_value,
                            info,
                            **coerced_args,
                        )
                    ),
                    complete,
                    else_=(ResolverError, fail),
                )
            )
        except ResolverError as err:
            return fail(err)

    def _iterate_fields(
        self, parent_type: ObjectType, fields: GroupedFields
    ) -> Iterator[Tuple[str, Field, List[_ast.Field]]]:
        for key, nodes in fields.items():
            field_def = self.field_definition(parent_type, nodes[0].name.value)
            if field_def is None:
                continue

            yield key, field_def, nodes

    def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Any:
        keys = []
        pending = []

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            resolved = self.resolve_field(
                parent_type, root, field_def, nodes, path + [key]
            )

            keys.append(key)
            pending.append(resolved)

        def _collect(done):
            return OrderedDict(zip(keys, done))

        return self.runtime.map_value(
            self.runtime.gather_values(pending), _collect
        )

    def execute_fields_serially(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Any:
        resolved_fields = OrderedDict()  # type: Dict[str, Any]

        args = list(self._iterate_fields(parent_type, fields))

        def _next():
            try:
                k, f, n = args.pop(0)
            except IndexError:
                return resolved_fields
            else:

                def cb(value):
                    resolved_fields[k] = value
                    return _next()

                return self.runtime.map_value(
                    self.resolve_field(parent_type, root, f, n, path + [k]), cb
                )

        return _next()

    def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        info: ResolveInfo,
        resolved_value: Any,
    ) -> Any:
        return self.runtime.gather_values(
            self.complete_value(inner_type, nodes, path + [index], info, entry)
            for index, entry in enumerate(resolved_value)
        )

    def complete_non_nullable_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        info: ResolveInfo,
        resolved_value: Any,
    ) -> Any:
        return self.runtime.map_value(
            self.complete_value(inner_type, nodes, path, info, resolved_value),
            lambda r: self._handle_non_nullable_value(nodes, path, r),
        )

    def complete_value(  # noqa: C901
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        info: ResolveInfo,
        resolved_value: Any,
    ) -> Any:

        if isinstance(field_type, NonNullType):
            return self.complete_non_nullable_value(
                field_type.type, nodes, path, info, resolved_value
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
                field_type.type, nodes, path, info, resolved_value
            )

        if isinstance(field_type, ScalarType):
            try:
                return field_type.serialize(resolved_value)
            except ScalarSerializationError as err:
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

        if isinstance(field_type, GraphQLCompositeType):
            if isinstance(field_type, GraphQLAbstractType):
                runtime_type = self.resolve_type(
                    resolved_value, info, field_type
                )

                if not isinstance(runtime_type, ObjectType):
                    raise RuntimeError(
                        'Abstract type "%s" must resolve to an ObjectType at '
                        'runtime for field "%s". Received "%s"'
                        % (field_type, stringify_path(path), runtime_type)
                    )

                # Backup check in case of badly implemented `resolve_type`
                if not self.schema.is_possible_type(field_type, runtime_type):
                    raise RuntimeError(
                        'Runtime ObjectType "%s" is not a possible type for '
                        'field "%s" of type "%s".'
                        % (runtime_type, stringify_path(path), field_type)
                    )
            else:
                runtime_type = cast(ObjectType, field_type)

            return self.execute_fields(
                runtime_type,
                resolved_value,
                path,
                self.collect_fields(
                    runtime_type,
                    [
                        selection
                        for field in nodes
                        if field.selection_set
                        for selection in field.selection_set.selections
                    ],
                ),
            )

        raise TypeError(
            "Invalid field type %s at %s" % (field_type, stringify_path(path))
        )

    def _handle_non_nullable_value(
        self, nodes: List[_ast.Field], path: ResponsePath, resolved_value: Any
    ) -> Any:
        if resolved_value is None:
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
        return resolved_value
