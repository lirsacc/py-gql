# -*- coding: utf-8 -*-

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from .._utils import Lazy, lazy
from ..exc import ScalarParsingError, ScalarSerializationError, UnknownEnumValue
from ..lang import ast as _ast
from ..lang.parser import (
    DIRECTIVE_LOCATIONS,
    RUNTIME_DIRECTIVE_LOCATIONS,
    SCHEMA_DIRECTIVE_LOCATONS,
)
from ._types import GraphQLType, ListType, NamedType, NonNullType  # noqa: F401


if TYPE_CHECKING:
    from ..execution import ResolveInfo  # noqa: F401


Resolver = Callable[..., Any]
TResolver = TypeVar("TResolver", bound=Resolver)

TypeResolver = Callable[
    [Any, Any, "ResolveInfo"],
    Optional[Union["ObjectType", str]],
]
TTypeResolver = TypeVar("TTypeResolver", bound=TypeResolver)


# TODO: Encode as much of the rules for validate_schema in the type system such
# as making sure only output types can be used in `Field`. This most likely
# requires making some types generic, such as `NonNullType`.

# TODO: Multiple objects expose both a X and X_map method which could be
# standardised under either of these.

T = TypeVar("T")

LazySeq = Lazy[Sequence[T]]

_UNSET = object()


class GraphQLAbstractType(NamedType):
    """
    Abstract types.

    These types may describe the parent context of a selection set and indicate
    that the value will be of a concrete ObjectType.
    """

    resolve_type = NotImplemented  # type: Optional[TypeResolver]


class GraphQLLeafType(NamedType):
    """
    Lead types.

    These types may describe types which may be leaf values.
    """


class GraphQLCompositeType(NamedType):
    """
    Composite types.

    These types may describe the parent context of a selection set.
    """


# TODO: The default value handling is really weird. Should be reviewed.
class InputValue:
    NO_DEFAULT_VALUE = _UNSET

    def __init__(
        self,
        name: str,
        type_: Lazy[GraphQLType],
        default_value: Lazy[Any] = _UNSET,
        description: Optional[str] = None,
        node: Optional[_ast.InputValueDefinition] = None,
        python_name: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.node = node
        self._ldefault_value = default_value
        self._ltype = type_
        self._type = None  # type: Optional[GraphQLType]
        self.python_name = python_name or name

    @property
    def has_default_value(self) -> bool:
        return self._default_value is not _UNSET

    @property
    def _default_value(self) -> Any:
        if not hasattr(self, "_cdefault_value"):
            self._cdefault_value = lazy(self._ldefault_value)
        return self._cdefault_value

    @property
    def default_value(self) -> Any:
        if self._default_value is _UNSET:
            raise AttributeError("No default value")
        return self._default_value

    @default_value.setter
    def default_value(self, value: Any) -> None:
        self._cdefault_value = value

    @default_value.deleter
    def default_value(self) -> None:
        self._cdefault_value = _UNSET

    @property
    def type(self) -> GraphQLType:
        if self._type is None:
            self._type = lazy(self._ltype)
        return self._type

    @type.setter
    def type(self, type_: GraphQLType) -> None:
        self._type = self._ltype = type_

    @property
    def required(self) -> bool:
        return (
            isinstance(self.type, NonNullType) and self._default_value is _UNSET
        )


class InputField(InputValue):
    """
    Member of an :class:`py_gql.schema.InputObjectType`.

    Warning:
        As ``None`` is a valid default value, in order to define an argument
        without any default value, the ``default_value`` argument **must** be
        omitted.

    Args:
        name: Field name

        type_: Field type (must be input type)

        default_value: Default value

        description: Field description

        node: Source node used when building type from the SDL

    Attributes:
        name (str): Field name

        description (Optional[str]): Field description

        has_default_value (bool): ``True`` if default value is set

        default_value (Any):
            Default value if it was set. Accessing this attribute raises an
            :py:class:`AttributeError` if default value wasn't set.

        type (GraphQLType): Value type.

        required (bool):
            Whether this field is required (non nullable and does not have
            any default value)

        node (Optional[py_gql.lang.ast.InputValueDefinition]):
            Source node used when building type from the SDL
    """

    def __str__(self) -> str:
        return f"InputField({self.name}: {self.type})"

    def __repr__(self) -> str:
        return f"InputField({self.name}: {self.type})"


class InputObjectType(NamedType):
    """
    Input Object Type Definition

    An input object defines a structured collection of fields which can be
    supplied as a field or directive argument.

    Args:
        name: Type name

        fields: Fields

        description: Type description

        nodes: Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name

        description (Optional[str]): Type description

        nodes (List[\
            Union[\
                py_gql.lang.ast.InputObjectTypeDefinition,\
                py_gql.lang.ast.InputObjectTypeExtension,\
            ]\
        ]): Source nodes used when building type from the SDL

        fields (Sequence[InputField]): Object fields.

        field_map (Dict[str, InputField]): Object fields as a map.
    """

    def __init__(
        self,
        name: str,
        fields: LazySeq[InputField],
        description: Optional[str] = None,
        nodes: Optional[
            List[
                Union[
                    _ast.InputObjectTypeDefinition,
                    _ast.InputObjectTypeExtension,
                ]
            ]
        ] = None,
    ):
        self.name = name
        self.description = description
        self._source_fields = fields
        self._fields = None  # type: Optional[Sequence[InputField]]
        self.nodes = (
            [] if nodes is None else nodes
        )  # noqa: B950, type: List[Union[_ast.InputObjectTypeDefinition, _ast.InputObjectTypeExtension]]

    @property
    def fields(self) -> Sequence[InputField]:
        if self._fields is None:
            self._fields = lazy(self._source_fields) or []
        return self._fields

    @fields.setter
    def fields(self, fields: List[InputField]) -> None:
        self._fields = self._source_fields = fields

    @property
    def field_map(self) -> Dict[str, InputField]:
        return {f.name: f for f in self.fields}


_EV = TypeVar("_EV", bound="EnumValue")


class EnumValue:
    """

    Enum value definition.

    Args:
        name: Name of the value

        value: Python value.
            Defaults to ``name`` if omitted.

            Warning:
                Must be hashable to support reverse lookups when coercing python
                values into enum values

        deprecation_reason:
            If set, the value will be marked as deprecated and the introspection
            layer will expose this to consumers.

        description: Enum value description

        node: Source node used when building type from the SDL

    Attributes:
        name (str): Enum value name

        value (str): Enum value value

        description (Optional[str]): Enum value description

        deprecation_reason (Optional[str]):
            If set, the value will be marked as deprecated and the introspection
            layer will expose this to consumers.

        deprecated: ``True`` if :attr:`deprecation_reason` is set.

        node (Optional[py_gql.lang.ast.EnumValueDefinition]):
            Source node used when building type from the SDL
    """

    __slots__ = (
        "deprecated",
        "deprecation_reason",
        "description",
        "name",
        "node",
        "value",
    )

    @classmethod
    def from_def(
        cls: Type[_EV],
        definition: Union[_EV, str, Tuple[str, Any]],
    ) -> _EV:
        """
        Create an enum value from various source objects.

        This supports existing `EnumValue` instances, strings,
        ``(name, value)`` tuples and dictionaries matching the signature of
        `EnumValue.__init__`.
        """
        if isinstance(definition, cls):
            return definition
        elif isinstance(definition, str):
            return cls(definition, definition)
        elif isinstance(definition, tuple):
            name, value = definition
            return cls(name, value)
        else:
            raise TypeError(f"Invalid enum value definition {definition}")

    def __init__(
        self,
        name: str,
        value: Any = _UNSET,
        deprecation_reason: Optional[str] = None,
        description: Optional[str] = None,
        node: Optional[_ast.EnumValueDefinition] = None,
    ):
        if name in ("true", "false", "null"):
            raise ValueError(f'Invalid name "{name}" for enum value')

        self.name = name
        self.value = value if value is not _UNSET else name
        self.description = description
        self.deprecated = deprecation_reason is not None
        self.deprecation_reason = deprecation_reason
        self.node = node

    def __str__(self) -> str:
        return self.name


class EnumType(GraphQLLeafType, NamedType):
    """
    Enum Type Definition

    Some leaf values of requests and input values are Enums. GraphQL serializes
    Enum values as strings, however internally Enums can be represented by any
    kind of Python type.

    Args:
        name: Enum name

        values: List of enum value definition supported by `EnumValue.from_def`

        description: Enum description

        nodes: Source nodes used when building type from the SDL

    Attributes:
        name (str): Enum name

        values (Dict[str, py_gql.schema.EnumValue]): Values by name

        reverse_values: (Dict[H, EnumValue]): Values by value

        description (Optional[str]): Enum description

        nodes (List[Union[\
            py_gql.lang.ast.EnumTypeDefinition, \
            py_gql.lang.ast.EnumTypeExtension,\
        ]]):
            Source nodes used when building type from the SDL
    """

    @classmethod
    def from_python_enum(cls, enum, description=None, nodes=None):
        """
        Create a GraphQL Enum type from a Python enum
        """
        return cls(
            enum.__name__,
            [(v.name, v) for v in enum],
            description=description,
            nodes=nodes,
        )

    def __init__(
        self,
        name: str,
        values: Iterable[Union[EnumValue, str, Tuple[str, Any]]],
        description: Optional[str] = None,
        nodes: Optional[
            List[Union[_ast.EnumTypeDefinition, _ast.EnumTypeExtension]]
        ] = None,
    ):
        self.name = name
        self.description = description
        self.nodes = (
            [] if nodes is None else nodes
        )  # type: List[Union[_ast.EnumTypeDefinition, _ast.EnumTypeExtension]]

        self._set_values(values)

    def _set_values(
        self,
        values: Iterable[Union[EnumValue, str, Tuple[str, Any]]],
    ) -> None:
        self.values = []  # type: List[EnumValue]
        self._values = {}  # type: Dict[str, EnumValue]
        self._reverse_values = {}  # type: Dict[Any, EnumValue]

        for v in values:
            v = EnumValue.from_def(v)

            if v.name in self._values:
                raise ValueError(f"Duplicate enum value {v.name}")

            self.values.append(v)
            self._reverse_values[v.value] = self._values[v.name] = v

    def get_value(self, name: str) -> Any:
        """
        Extract the value for a given name.

        Args:
            name: Name of the value to extract

        Returns:
            :class:`py_gql.schema.EnumValue`: The corresponding EnumValue.

        Raises:
            UnknownEnumValue: when the name is unknown.
        """
        try:
            return self._values[name].value
        except KeyError:
            raise UnknownEnumValue(f"Invalid name {name} for enum {self.name}")

    def get_name(self, value: Any) -> str:
        """
        Extract the name for a given value.

        Args:
            value: Value of the value to extract, must be hashable

        Returns:
            :class:`py_gql.schema.EnumValue`: The corresponding EnumValue

        Raises:
            UnknownEnumValue: when the value is unknown
        """
        try:
            return self._reverse_values[value].name
        except KeyError:
            raise UnknownEnumValue(
                f"Invalid value {value!r} for enum {self.name}",
            )


_ScalarValueNode = Union[
    _ast.IntValue,
    _ast.FloatValue,
    _ast.StringValue,
    _ast.BooleanValue,
]

_ScalarValue = Union[str, int, float, bool, None]


class ScalarType(GraphQLLeafType, NamedType):
    """
    Scalar Type Definition

    The leaf values of any request and input values to arguments are
    Scalars (or Enums) and are defined with a name and a series of functions
    used to parse input from ast or variables and to ensure validity.

    To define custom scalars, you can either instantiate this class with the
    corresponding arguments (that is how `Int`, `Float`, etc. are implemented)
    or subclass this class and implement :meth:`serialize`, :meth:`parse` and
    :meth:`parse_literal` (this is how `RegexType` is implemented).

    Args:
        name: Type name

        serialize: Type serializer.

            This function will receive a Python value and must output JSON
            serializable scalars.

            Raise :class:`~py_gql.exc.ScalarSerializationError`,
            :py:class:`ValueError` or :py:class:`TypeError` to signify that the
            value cannot be serialized.

        parse: Type de-serializer.

            This function will receive JSON scalars and can outputs any Python
            value.

            Raise :class:`~py_gql.exc.ScalarParsingError`, :py:class:`ValueError`
            or :py:class:`TypeError` to signify that the value cannot be parsed.

        parse_literal: Type de-serializer for value nodes.

            This function receives a :class:`py_gql.lang.ast.Value`
            and can outputs any Python value.

            Raise :class:`~py_gql.exc.ScalarParsingError`, :py:class:`ValueError`
            or :py:class:`TypeError` to signify that the value cannot be parsed.

            If not provided, the execution layer will extract the node's value
            as a string and pass it to `parse`.

        description: Type description

        nodes: Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name

        description (Optional[str]): Type description

        nodes (List[Union[\
            py_gql.lang.ast.ScalarTypeDefinition, \
            py_gql.lang.ast.ScalarTypeExtension\
        ]]):
            Source nodes used when building type from the SDL

    """

    def __init__(
        self,
        name: str,
        serialize: Callable[[Any], _ScalarValue],
        parse: Callable[[_ScalarValue], Any],
        parse_literal: Optional[
            Callable[[_ScalarValueNode, Mapping[str, Any]], Any]
        ] = None,
        description: Optional[str] = None,
        nodes: Optional[
            List[Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension]]
        ] = None,
    ):
        self.name = name
        self.description = description
        self._serialize = serialize
        self._parse = parse
        self._parse_literal = parse_literal
        self.nodes = (
            [] if nodes is None else nodes
        )  # type: List[Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension]]

    def serialize(self, value: Any) -> _ScalarValue:
        """
        Transform a Python value in a JSON serializable one.

        Args:
            value: Python level value

        Returns:
            JSON scalar

        Raises:
            ScalarSerializationError: when the type's serializer fail with
                ValueError or TypeError (other exceptions bubble up).
        """
        try:
            return self._serialize(value)
        except (ValueError, TypeError) as err:
            raise ScalarSerializationError(str(err)) from err

    def parse(self, value: _ScalarValue) -> Any:
        """
        Transform a GraphQL value in a valid Python value

        Args:
            value: JSON scalar

        Returns:
            Python level value

        Raises:
            ScalarParsingError: when the type's parser fail with
                ValueError or TypeError (other exceptions bubble up).
        """
        try:
            return self._parse(value)
        except (ValueError, TypeError) as err:
            raise ScalarParsingError(str(err)) from err

    def parse_literal(
        self,
        node: _ScalarValueNode,
        variables: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """
        Transform an AST node in a valid Python value

        Args:
            node: Parse node
            variables: Raw, JSON decoded variables parsed from the request

        Returns:
            Python level value

        Raises:
            ScalarParsingError: when the type's parser fail with
                ValueError or TypeError (other exceptions bubble up).
        """
        try:
            try:
                if self._parse_literal is not None:
                    return self._parse_literal(node, variables or {})
                return self.parse(node.value)
            except AttributeError:
                return self.parse(node.value)
        except (ValueError, TypeError) as err:
            raise ScalarParsingError(str(err), [node]) from err


class Argument(InputValue):
    """
    Argument definition for use in field or directives.

    Warning:
        As ``None`` is a valid default value, in order to define an argument
        without any default value, the ``default_value`` argument **must** be
        omitted.

    Args:
        name: Argument name

        type_: Argument type (must be input type)

        default_value: Default value

        description: Argument description

        node: Source node used when building type from the SDL

    Attributes:
        name (str): Argument name

        description (Optional[str]): Argument description

        has_default_value (bool): ``True`` if default value is set

        default_value (Any):
            Default value if it was set. Accessing this attribute raises an
            :py:class:`AttributeError` if default value wasn't set.

        type (GraphQLType): Value type.

        required (bool):
            Whether this argument is required (non nullable and does not have
            any default value)

        node (Optional[py_gql.lang.ast.InputValueDefinition]):
            Source node used when building type from the SDL
    """

    def __str__(self) -> str:
        return f"Argument({self.name}: {self.type})"

    def __repr__(self) -> str:
        return f"Argument({self.name}: {self.type})"


class Field:
    """
    Member of a composite type.

    Args:
        name: Field name

        type_: Field type (must be output type)

        args: Field arguments

        description: Field description

        deprecation_reason:
            If set, the field will be marked as deprecated and the introspection
            layer will expose this to consumers.

        resolver: Resolver function.

        node: Source node used when building type from the SDL

    Attributes:
        name (str): Field name

        description (Optional[str]): Field description

        deprecation_reason (Optional[str]):
            If set, the field will be marked as deprecated and the introspection
            layer will expose this to consumers.

        deprecated: ``True`` if :attr:`deprecation_reason` is set.

        type (GraphQLType): Field type.

        arguments (List[py_gql.schema.Argument]): Field arguments.

        argument_map (Dict[str, py_gql.schema.Argument]):
            Field arguments in indexed form.

        resolver (callable): Field resolver.
        subscription_resolver (callable): Field resolver for subscriptions.

        node (Optional[py_gql.lang.ast.FieldDefinition]):
            Source node used when building type from the SDL

    """

    def __init__(
        self,
        name: str,
        type_: Lazy[GraphQLType],
        args: Optional[LazySeq[Argument]] = None,
        description: Optional[str] = None,
        deprecation_reason: Optional[str] = None,
        resolver: Optional["Resolver"] = None,
        subscription_resolver: Optional["Resolver"] = None,
        node: Optional[_ast.FieldDefinition] = None,
        python_name: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.deprecated = bool(deprecation_reason)
        self.deprecation_reason = deprecation_reason
        self.resolver = resolver
        self.subscription_resolver = subscription_resolver
        self._source_args = args
        self._args = None  # type: Optional[Sequence[Argument]]
        self.node = node
        self._ltype = type_
        self._type = None  # type: Optional[GraphQLType]
        self.python_name = python_name or name

    @property
    def type(self) -> GraphQLType:
        if self._type is None:
            self._type = lazy(self._ltype)
        return self._type

    @type.setter
    def type(self, type_: GraphQLType) -> None:
        self._type = self._ltype = type_

    @property
    def arguments(self) -> Sequence[Argument]:
        if self._args is None:
            self._args = lazy(self._source_args) or []
        return self._args

    @arguments.setter
    def arguments(self, args: List[Argument]) -> None:
        self._args = self._source_args = args

    @property
    def argument_map(self) -> Dict[str, Argument]:
        return {arg.name: arg for arg in self.arguments}

    def __str__(self) -> str:
        return f"Field({self.name}: {self.type})"

    def __repr__(self) -> str:
        return f"Field({self.name}: {self.type})"


class InterfaceType(GraphQLCompositeType, GraphQLAbstractType, NamedType):
    """
    Interface Type Definition.

    When a field can return one of a heterogeneous set of types, a Interface
    type is used to describe what types are possible, what fields are in
    common across all types, as well as a function to determine which type
    is actually used when the field is resolved.

    Args:
        name: Type name

        fields: Fields

        interfaces: Implemented interfaces

        interfaces (LazySeq[InterfaceType]):
            Implemented interfaces.

        resolve_type: Type resolver

        description: Type description

        nodes: Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name

        description (Optional[str]): Type description

        fields (Sequence[py_gql.schema.Field]): Object fields.

        field_map (Dict[str, py_gql.schema.Field]):
            Object fields as a map.

        resolve_type (Optional[callable]): Type resolver

        nodes (List[Union[\
            py_gql.lang.ast.InterfaceTypeDefinition,\
            py_gql.lang.ast.InterfaceTypeExtension,\
        ]]):
            Source nodes used when building type from the SDL
    """

    def __init__(
        self,
        name: str,
        fields: LazySeq[Field],
        interfaces: Optional[LazySeq["InterfaceType"]] = None,
        resolve_type: Optional["TypeResolver"] = None,
        description: Optional[str] = None,
        nodes: Optional[
            List[
                Union[_ast.InterfaceTypeDefinition, _ast.InterfaceTypeExtension]
            ]
        ] = None,
    ):
        self.name = name
        self.description = description
        self._source_fields = fields
        self._fields = None  # type: Optional[Sequence[Field]]
        self._source_interfaces = interfaces
        self._interfaces = None  # type: Optional[Sequence[InterfaceType]]
        self.nodes = (
            [] if nodes is None else nodes
        )  # noqa: B950, type: List[Union[_ast.InterfaceTypeDefinition, _ast.InterfaceTypeExtension]]
        self.resolve_type = resolve_type

    @property
    def fields(self) -> Sequence["Field"]:
        if self._fields is None:
            self._fields = lazy(self._source_fields) or []
        return self._fields

    @fields.setter
    def fields(self, fields: List["Field"]) -> None:
        self._fields = self._source_fields = fields

    @property
    def field_map(self) -> Dict[str, "Field"]:
        return {f.name: f for f in self.fields}

    @property
    def interfaces(self) -> Sequence["InterfaceType"]:
        if self._interfaces is None:
            self._interfaces = lazy(self._source_interfaces) or []
        return self._interfaces

    @interfaces.setter
    def interfaces(self, interfaces: List["InterfaceType"]) -> None:
        self._interfaces = self._source_interfaces = interfaces


class ObjectType(GraphQLCompositeType, NamedType):
    """
    Object Type Definition

    Almost all of the GraphQL types you define will be object types. Object
    types have a name, but most importantly describe their fields.

    Args:
        name: Type name

        fields: Fields

        interfaces: Implemented interfaces

        default_resolver:

        description: Type description

        nodes: Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name

        description (Optional[str]): Type description

        interfaces (Sequence[InterfaceType]):
            Implemented interfaces.

        fields (Sequence[py_gql.schema.Field]): Object fields.

        field_map (Dict[str, py_gql.schema.Field]):
            Object fields as a map.

        default_resolver (Optional[Callable[..., Any]]):

        nodes (List[Union[\
            py_gql.lang.ast.ObjectTypeDefinition,\
            py_gql.lang.ast.ObjectTypeExtension,\
        ]]):
            Source nodes used when building type from the SDL
    """

    def __init__(
        self,
        name: str,
        fields: LazySeq[Field],
        interfaces: Optional[LazySeq[InterfaceType]] = None,
        default_resolver: Optional["Resolver"] = None,
        description: Optional[str] = None,
        nodes: Optional[
            List[Union[_ast.ObjectTypeDefinition, _ast.ObjectTypeExtension]]
        ] = None,
    ):
        self.name = name
        self.description = description
        self._source_fields = fields
        self._source_fields = fields
        self.default_resolver = default_resolver
        self._fields = None  # type: Optional[Sequence[Field]]
        self._source_interfaces = interfaces
        self._interfaces = None  # type: Optional[Sequence[InterfaceType]]
        self.nodes = (
            [] if nodes is None else nodes
        )  # type: List[Union[_ast.ObjectTypeDefinition, _ast.ObjectTypeExtension]]

    @property
    def fields(self) -> Sequence["Field"]:
        if self._fields is None:
            self._fields = lazy(self._source_fields) or []
        return self._fields

    @fields.setter
    def fields(self, fields: List["Field"]) -> None:
        self._fields = self._source_fields = fields

    @property
    def field_map(self) -> Dict[str, "Field"]:
        return {f.name: f for f in self.fields}

    @property
    def interfaces(self) -> Sequence["InterfaceType"]:
        if self._interfaces is None:
            self._interfaces = lazy(self._source_interfaces) or []
        return self._interfaces

    @interfaces.setter
    def interfaces(self, interfaces: List["InterfaceType"]) -> None:
        self._interfaces = self._source_interfaces = interfaces


class UnionType(GraphQLCompositeType, GraphQLAbstractType, NamedType):
    """
    Union Type Definition

    When a field can return one of a heterogeneous set of types, a Union type
    is used to describe what types are possible as well as providing a function
    to determine which type is actually used when the field is resolved.

    Args:
        name: Type name

        types: Member types

        resolve_type: Type resolver

        description: Type description

        nodes: Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name

        description (Optional[str]): Type description

        resolve_type (Optional[callable]): Type resolver

        types (Sequence[ObjectType]): Member types.

        nodes (List[Union[\
            py_gql.lang.ast.UnionTypeDefinition,\
            py_gql.lang.ast.UnionTypeExtension,\
        ]]):
            Source nodes used when building type from the SDL

    """

    def __init__(
        self,
        name: str,
        types: LazySeq[ObjectType],
        resolve_type: Optional["TypeResolver"] = None,
        description: Optional[str] = None,
        nodes: Optional[
            List[Union[_ast.UnionTypeDefinition, _ast.UnionTypeExtension]]
        ] = None,
    ):
        self.name = name
        self.description = description
        self._source_types = types
        self._types = None  # type: Optional[Sequence[ObjectType]]
        self.nodes = (
            [] if nodes is None else nodes
        )  # type: List[Union[_ast.UnionTypeDefinition, _ast.UnionTypeExtension]]
        self.resolve_type = resolve_type

    @property
    def types(self) -> Sequence[ObjectType]:
        if self._types is None:
            self._types = lazy(self._source_types) or []
        return self._types

    @types.setter
    def types(self, types: List[ObjectType]) -> None:
        self._types = self._source_types = types


class Directive:
    """
    Directive definition

    `Directives
    <https://graphql.github.io/graphql-spec/June2018/#sec-Type-System.Directives>`_
    are used by the GraphQL runtime as a way of modifying execution behavior.
    Type system creators will usually not create these directly.

    Args:
        name: Directive name.

        locations: Possible locations for that directive.

        args: Argument definitions.

        repeatable: Specify that the directive can be applied multiple times to
            the same target. Repeatable directives are often useful when the
            same directive should be used with different arguments at a single
            location, especially in cases where additional information needs to
            be provided to a type or schema extension via a directive.

        description: Directive description.

        node: Source node used when building type from the SDL.

    Attributes:
        name (str): Directive name.

        description (Optional[str]): Directive description.

        locations (List[str]): Possible locations for that directive.

        arguments (List[py_gql.schema.Argument]): Directive arguments.

        argument_map (Dict[str, py_gql.schema.Argument]):
            Directive arguments in indexed form.

        repeatable: Specify that the directive can be applied multiple times to
            the same target. Repeatable directives are often useful when the
            same directive should be used with different arguments at a single
            location, especially in cases where additional information needs to
            be provided to a type or schema extension via a directive.

        node (Optional[py_gql.lang.ast.DirectiveDefinition]):
            Source node used when building type from the SDL.
    """

    ALL_LOCATIONS = DIRECTIVE_LOCATIONS
    RUNTIME_LOCATIONS = RUNTIME_DIRECTIVE_LOCATIONS
    SCHEMA_LOCATONS = SCHEMA_DIRECTIVE_LOCATONS

    def __init__(
        self,
        name: str,
        locations: Sequence[str],
        args: Optional[List[Argument]] = None,
        repeatable: bool = False,
        description: Optional[str] = None,
        node: Optional[_ast.DirectiveDefinition] = None,
    ):
        if not locations:
            raise ValueError("Expected at least one location")

        if any(x not in DIRECTIVE_LOCATIONS for x in locations):
            raise ValueError(
                "Locations must be one of %s but received %r"
                % (DIRECTIVE_LOCATIONS, locations),
            )

        self.name = name
        self.description = description
        self.locations = locations
        self.repeatable = repeatable
        self.arguments = args if args is not None else []
        self.argument_map = {arg.name: arg for arg in self.arguments}
        self.node = node


def is_input_type(type_: GraphQLType) -> bool:
    """
    Check if a type is an input type.

    These types may be used as input types for arguments and directives.
    """
    return isinstance(
        unwrap_type(type_),
        (ScalarType, EnumType, InputObjectType),
    )


def is_output_type(type_: GraphQLType) -> bool:
    """
    Check if a type is an output type.

    These types may be used as output types as the result of fields.
    """
    return isinstance(
        unwrap_type(type_),
        (ScalarType, EnumType, ObjectType, InterfaceType, UnionType),
    )


def unwrap_type(type_: GraphQLType) -> NamedType:
    """
    Recursively extract inner type from a potentially wrapping type like
    `ListType` or `NonNullType`.
    """
    cur = type_
    while isinstance(cur, (ListType, NonNullType)):
        cur = cur.type
    return cast(NamedType, cur)
