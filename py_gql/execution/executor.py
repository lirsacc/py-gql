# -*- coding: utf-8 -*-

import functools
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
    Type,
    TypeVar,
    Union,
)

from .._string_utils import stringify_path
from .._utils import OrderedDict, is_iterable
from ..exc import (
    CoercionError,
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
from ..utilities import coerce_argument_values, directive_arguments
from .default_resolver import default_resolver as _default_resolver
from .tracer import NullTracer, Tracer
from .wrappers import GroupedFields, ResolveInfo, ResponsePath

Resolver = Callable[..., Any]

T = TypeVar("T")
G = TypeVar("G")
E = TypeVar("E", bound=Exception)


class Executor:
    """
    Default executor class (synchronous).
    """

    # These static methods should likely be re-implemented in order to build
    # custom executors. See to AsyncExecutor and ThreadPoolExecutor for
    # reference.
    @staticmethod
    def gather_values(values: Iterable[Any]) -> Any:
        return values

    @staticmethod
    def map_value(
        value: Any,
        then: Callable[[Any], Any],
        else_: Optional[
            Tuple[Union[Type[E], Tuple[Type[E], ...]], Callable[[E], Any]]
        ] = None,
    ) -> Any:
        try:
            return then(value)
        except Exception as err:
            if else_ and isinstance(err, else_[0]):
                return else_[1](err)  # type: ignore
            raise

    @staticmethod
    def unwrap_value(value):
        return value

    def wrap_field_resolver(self, resolver: Resolver) -> Resolver:
        return resolver

    # -------------------------------------------------------------------------

    __slots__ = (
        "schema",
        "document",
        "variables",
        "fragments",
        "operation",
        "context_value",
        "_grouped_fields",
        "_fragment_type_applies",
        "_field_defs",
        "_argument_values",
        "_resolver_cache",
        "_errors",
        "_default_resolver",
        "_middlewares",
        "_tracer",
    )

    def __init__(
        # fmt: off
        self,
        schema: Schema,
        document: _ast.Document,
        variables: Dict[str, Any],
        context_value: Any,
        default_resolver: Optional[Resolver] = None,
        middlewares: Optional[Sequence[Callable[..., Any]]] = None,
        tracer: Optional[Tracer] = None,
        **_: Any
        # fmt: on
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

        self._default_resolver = default_resolver or _default_resolver

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
        self._middlewares = middlewares or []
        self._tracer = tracer or NullTracer()

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
                if not err.nodes:
                    err.nodes = [node]
            err.path = path if path is not None else err.path
        self._errors.append(err)

    @property
    def errors(self) -> List[GraphQLResponseError]:
        """ All field errors collected during query execution. """
        return self._errors[:]

    def fragment_type_applies(
        self,
        object_type: ObjectType,
        fragment: Union[_ast.InlineFragment, _ast.FragmentDefinition],
    ) -> bool:
        """ Determine if a fragment is applicable to the given type. """
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

            # TODO: Is this point technically possible given a valid document.
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
        """
        Collect all fields in a selection set, recursively traversing
        fragments in one single map and conserving definitino order.
        """
        cache_key = parent_type.name, tuple(selections)
        try:
            return self._grouped_fields[cache_key]
        except KeyError:
            visited_fragments = visited_fragments or set()
            grouped_fields = OrderedDict()  # type: GroupedFields

            for selection in selections:
                if isinstance(selection, _ast.Field):
                    if _skip_selection(selection, self.variables):
                        continue

                    key = selection.response_name
                    if key not in grouped_fields:
                        grouped_fields[key] = []
                    grouped_fields[key].append(selection)

                elif isinstance(selection, _ast.InlineFragment):
                    if _skip_selection(selection, self.variables):
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
                    if _skip_selection(selection, self.variables):
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
                    raise RuntimeError(
                        "Invalid state: introspection type in the wrong position."
                    )
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

    # REVIEW: This seems too involved, I'd rather have one single way to do this
    # at the cost of diverging from the various methods seen in graphql-js.
    def resolve_type(
        self, value: Any, t: Union[InterfaceType, UnionType]
    ) -> Optional[ObjectType]:
        if t.resolve_type is not None:
            maybe_type = t.resolve_type(value)
            if isinstance(maybe_type, str):
                return self.schema.get_type(maybe_type)  # type: ignore
            else:
                return maybe_type
        elif isinstance(value, dict) and value.get("__typename__"):
            return self.schema.get_type(value["__typename__"])  # type: ignore
        elif hasattr(value, "__typename__") and value.__typename__:
            return self.schema.get_type(value.__typename__)  # type: ignore
        else:
            possible_types = self.schema.get_possible_types(t)
            for pt in possible_types:
                if pt.is_type_of is not None:
                    if pt.is_type_of(value):
                        return pt
            return None

    def _get_field_resolver(self, base: Resolver) -> Resolver:
        try:
            return self._resolver_cache[base]
        except KeyError:
            wrapped = self.wrap_field_resolver(base)
            if self._middlewares:
                wrapped = _apply_middlewares(wrapped, self._middlewares)
            self._resolver_cache[base] = wrapped
            return wrapped

    def resolve_field(
        self,
        parent_type: ObjectType,
        parent_value: Any,
        field_definition: Field,
        nodes: List[_ast.Field],
        path: ResponsePath,
    ) -> Any:
        resolver = self._get_field_resolver(
            field_definition.resolver or self._default_resolver
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

        def fail(err):
            self.add_error(err, path, node)
            self._tracer.on_field_end(info)
            return None

        def complete(res):
            self._tracer.on_field_end(info)
            return self.complete_value(field_definition.type, nodes, path, res)

        self._tracer.on_field_start(info)

        try:
            coerced_args = self.argument_values(field_definition, node)
            resolved = resolver(
                parent_value, self.context_value, info, **coerced_args
            )
        except (CoercionError, ResolverError) as err:
            return fail(err)
        else:
            return self.map_value(
                resolved, complete, else_=(ResolverError, fail)
            )

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
            resolved = self.unwrap_value(
                self.resolve_field(
                    parent_type, root, field_def, nodes, path + [key]
                )
            )

            keys.append(key)
            pending.append(resolved)

        def _collect(done):
            return OrderedDict(zip(keys, done))

        return self.map_value(self.gather_values(pending), _collect)

    def execute_fields_serially(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Any:
        args = []
        done = []  # type: List[Tuple[str, Any]]

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            # Needed because closures. Might be a better way to do this without
            # resorting to inlining deferred_serial.
            args.append((key, field_def, nodes, path + [key]))

        def _next():
            try:
                k, f, n, p = args.pop(0)
            except IndexError:
                return OrderedDict(done)
            else:

                def cb(value):
                    done.append((k, value))
                    return _next()

                return self.map_value(
                    self.unwrap_value(
                        self.resolve_field(parent_type, root, f, n, p)
                    ),
                    cb,
                )

        return _next()

    def complete_value(  # noqa: C901
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> Any:
        if isinstance(field_type, NonNullType):
            return self.map_value(
                self.complete_value(
                    field_type.type, nodes, path, resolved_value
                ),
                lambda r: self._handle_non_nullable_value(nodes, path, r),
            )

        if resolved_value is None:
            return None

        if isinstance(field_type, ListType):
            if not is_iterable(resolved_value, False):
                raise RuntimeError(
                    'Field "%s" is a list type and resolved value should be '
                    "iterable" % stringify_path(path)
                )
            return self.gather_values(
                [
                    self.complete_value(
                        field_type.type, nodes, path + [index], entry
                    )
                    for index, entry in enumerate(resolved_value)
                ]
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


def _subselections(nodes: Iterable[_ast.Field]) -> Iterator[_ast.Selection]:
    for field in nodes:
        # TODO: Can this happen provided query document has been validated?
        if field.selection_set:
            for selection in field.selection_set.selections:
                yield selection


def _skip_selection(
    node: Union[_ast.Field, _ast.InlineFragment, _ast.FragmentSpread],
    variables: Mapping[str, Any],
) -> bool:
    skip = directive_arguments(SkipDirective, node, variables=variables)
    include = directive_arguments(IncludeDirective, node, variables=variables)
    skipped = skip is not None and skip["if"]
    included = include is None or include["if"]
    return skipped or (not included)


def _apply_middlewares(
    func: Callable[..., Any], middlewares: Sequence[Callable[..., Any]]
) -> Callable[..., Any]:
    tail = func
    for mw in reversed(middlewares):
        if not callable(mw):
            raise TypeError("Middleware should be a callable")

        tail = functools.partial(mw, tail)

    return tail
