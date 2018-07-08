# -*- coding: utf-8 -*-
""" Utilitiy classes to define custom types.

All types used in a schema should be instances of
:class:`py_gql.schema.types.Type`.
"""

import six

from .._utils import OrderedDict, cached_property, lazy
from ..exc import ScalarParsingError, ScalarSerializationError, UnknownEnumValue
from ..lang.parser import DIRECTIVE_LOCATIONS


def _evaluate_lazy_list(entries):
    _entries = lazy(entries)
    if not _entries:
        return []
    elif isinstance(_entries, (list, tuple)):
        return [lazy(entry) for entry in _entries]
    elif isinstance(_entries, dict):
        return [lazy(entry) for entry in _entries.values()]
    else:
        raise TypeError("Expected list or dict of items")


_UNDEF = object()


class Type(object):
    def __repr__(self):
        return str(self)

    def __eq__(self, lhs):
        return self is lhs or (
            isinstance(self, WrappingType)
            and self.__class__ == lhs.__class__
            and self.type == lhs.type
        )

    def __hash__(self):
        return id(self)


class NamedType(Type):
    """
    :vartype name: py_gql.schema.types.Type
    :ivar name:
        Name of the type, must be unique across a single
        :class:`py_gql.schema.Schema` instance
    """

    def __str__(self):
        return self.name


class WrappingType(Type):
    """ Types wrapping other types.

    :vartype node: Optional[py_gql.lang.ast.NonNullType]
    :ivar node: Source node when building type from the SDL
    """

    def __init__(self, type_, node=None):
        """
        :type type_: Union[py_gql.schema.types.Type, Callable[[], py_gql.schema.types.Type]]
        :param type_: Wrapped type.
            Can be a callable for lazy definitions.

        :type node: Optional[py_gql.lang.ast.NonNullType]
        :param node: Source node when building type from the SDL
        """
        self._type = type_
        self.node = node

    @cached_property
    def type(self):
        """
        :rtype: py_gql.schema.types.Type
        """
        return lazy(self._type)


class NonNullType(WrappingType):
    """ Non nullable wrapping type.

    A non-null is a wrapping type which points to another type.
    Non-null types enforce that their values are never null and can ensure
    an error is raised if this ever occurs during a request. It is useful for
    fields which you can make a strong guarantee on non-nullability, for example
    usually the id field of a database row will never be null.

    :vartype node: Optional[py_gql.lang.ast.NonNullType]
    :ivar node: Source node when building type from the SDL
    """

    def __init__(self, type_, node=None):
        """
        :type type_: Union[py_gql.schema.types.Type, Callable[[], py_gql.schema.types.Type]]
        :param type_: Wrapped type.
            Can be a callable for lazy definitions.

        :type node: Optional[py_gql.lang.ast.NonNullType]
        :param node: Source node when building type from the SDL
        """
        assert not isinstance(type_, NonNullType)
        self._type = type_
        self.node = node

    def __str__(self):
        return "%s!" % self.type


class ListType(WrappingType):
    """ List wrapping type.

    A list is a wrapping type which points to another type.
    Lists are often created within the context of defining the fields of
    an object type.

    :vartype node: Optional[py_gql.lang.ast.NonNullType]
    :ivar node: Source node when building type from the SDL
    """

    def __str__(self):
        return "[%s]" % self.type


class InputField(object):
    """ Field definitions for of an :class:`InputType`

    :vartype name: str
    :ivar name: Fieldname

    :vartype default_value: any
    :ivar default_value: Default value

    :vartype has_default_value: bool
    :ivar has_default_value: Whether the default value is set or not.
        You should only use the :attr:`default_value` attribute if this
        attribute is ``True``.

    :vartype description: Optional[str]
    :ivar description: Field description.

    :vartype node: Optional[py_gql.lang.ast.InputValueDefinition]
    :ivar node: Source node when building type from the SDL
    """

    # Yikes! Didn't find a better way to differentiate None as value and no
    # value in arguments... at least it's not exposed to callers.
    # Maybe we could wrap default value in a singleton type ?
    def __init__(
        self, name, type_, default_value=_UNDEF, description=None, node=None
    ):
        """
        :type name: str
        :param name: Fieldname

        :type type_: Union[py_gql.schema.types.Type, Callable[[], py_gql.schema.types.Type]]
        :param type_: Field type.
            Can be a callable for lazy definitions.
            Must result in a input type.

        :type default_value: Optional[any]
        :param default_value: Default value for this field.
            As `None` is a valid value, you must omit this argument if you want
            to have no default value.

        :type description: Optional[str]
        :param description: Field description

        :type node: Optional[py_gql.lang.ast.InputValueDefinition]
        :ivar node: Source node when building type from the SDL
        """
        self.name = name
        self._type = type_
        self.default_value = default_value
        self.description = description
        self.has_default_value = self.default_value is not _UNDEF
        self.node = node

    @cached_property
    def type(self):
        """ Field type

        :rtype: py_gql.schema.types.Type
        """
        return lazy(self._type)

    @cached_property
    def required(self):
        """ Whether that field is required or not.

        A field is required if it's type is :class:`NonNullType` and it has no
        default value.

        :rtype: bool
        """
        return (
            isinstance(self.type, NonNullType) and self.default_value is _UNDEF
        )

    def __str__(self):
        return "InputField(%s: %s)" % (self.name, self.type)


class InputObjectType(NamedType):
    """ Input Object Type Definition

    An input object defines a structured collection of fields which may be
    supplied to a field argument.

    Using `NonNullType` will ensure that a value must be provided by the query.

    When two types need to refer to each other, or a type needs to refer to
    itself in a field, you can use a lambda expression to supply the
    fields lazily.
    """

    def __init__(self, name, fields, description=None, nodes=None):
        """
        :type name: str
        :type fields: dict(str, InputField)|[InputField]|callable
        :type description: str
        """
        self.name = name
        self.description = description
        self._fields = fields
        self.nodes = [] if nodes is None else nodes

    @cached_property
    def fields(self):
        return _evaluate_lazy_list(self._fields)

    @cached_property
    def field_map(self):
        return {f.name: f for f in self.fields}


class EnumValue(object):
    """ Enum value definition
    """

    @classmethod
    def from_def(cls, definition):
        if isinstance(definition, cls):
            return definition
        elif isinstance(definition, str):
            return cls(definition, definition)
        elif isinstance(definition, tuple):
            name, value = definition
            return cls(name, value)
        elif isinstance(definition, dict):
            return cls(**definition)
        else:
            raise TypeError("Invalid enum value definition %r" % definition)

    def __init__(
        self,
        name,
        value=_UNDEF,
        deprecation_reason=None,
        description=None,
        node=None,
    ):
        """
        :type name: str
        :type value: Hashable
        :type deprecation_reason: str
        :type description: str
        """
        assert name not in ("true", "false", "null")
        self.name = name
        self.value = value if value is not _UNDEF else name
        self.description = description
        self.deprecated = bool(deprecation_reason)
        self.deprecation_reason = deprecation_reason
        self.node = node

    def __str__(self):
        return self.name


class EnumType(NamedType):
    """ Enum Type Definition

    Some leaf values of requests and input values are Enums. GraphQL serializes
    Enum values as strings, however internally Enums can be represented by any
    kind of type, often integers.

    .. warning::

        Enum values must be hashable to provide revere-lookup
        capabilities when coercing python values into enum values.
    """

    def __init__(self, name, values, description=None, nodes=None):
        """
        :type name: str
        :type values: [EnumValue|str|Tuple[str, Hashable]|dict]
        :type description: str
        """
        self.name = name
        self.description = description
        self.nodes = [] if nodes is None else nodes
        self.values = OrderedDict()
        self.reverse_values = OrderedDict()
        for v in values:
            ev = EnumValue.from_def(v)
            assert ev.name not in self.values, (
                "Duplicate enum value %s" % ev.name
            )
            self.reverse_values[ev.value] = self.values[ev.name] = ev

    def get_value(self, name):
        """ Extract the value for a given name.

        :type name: str
        :param name:
            Name of the value to extract.

        :rtype: EnumValue
        :returns:
            The corresponding EnumValue
        """
        try:
            return self.values[name].value
        except KeyError:
            raise UnknownEnumValue(
                "Invalid name %s for enum %s" % (name, self.name)
            )

    def get_name(self, value):
        """ Extract the name for a given value.

        :type name: Hashable
        :param name:
            Value for the name to extract.

        :rtype: EnumValue
        :returns:
            The corresponding EnumValue
        """
        try:
            return self.reverse_values[value].name
        except KeyError:
            raise UnknownEnumValue(
                "Invalid value %r for enum %s" % (value, self.name)
            )


class ScalarType(NamedType):
    """ Scalar Type Definition

    The leaf values of any request and input values to arguments are
    Scalars (or Enums) and are defined with a name and a series of functions
    used to parse input from ast or variables and to ensure validity.

    - To raise an error on serialization (output), raise a
    ``ScalarSerializationError``, ``ValueError`` or ``TypeError``
    in ``serialize``.

    - To raise an error on parsing (input), raise a ``ScalarParsingError``,
    ``ValueError``, or ``TypeError`` in ``parse`` or ``parse_literal``.
    """

    def __init__(
        self,
        name,
        serialize,
        parse,
        parse_literal=None,
        description=None,
        nodes=None,
    ):
        """
        :type name: str
        :type serialize: callable
        :type parse: callable
        :type parse_literal: callable
        :type description: str
        """
        self.name = name
        self.description = description
        self._serialize = serialize
        self._parse = parse
        self._parse_literal = parse_literal
        self.nodes = [] if nodes is None else nodes

    def serialize(self, value):
        """ Transform a Python value in a JSON serializable one """
        try:
            return self._serialize(value)
        except (ValueError, TypeError) as err:
            six.raise_from(ScalarSerializationError(str(err)), err)

    def parse(self, value):
        """ Transform a GraphQL value in a valid Python value """
        try:
            return self._parse(value)
        except (ValueError, TypeError) as err:
            six.raise_from(ScalarParsingError(str(err)), err)

    def parse_literal(self, node, variables=None):
        """ Transform an AST node in a valid Python value """
        try:
            if (
                hasattr(self, "_parse_literal")
                and self._parse_literal is not None
            ):
                return self._parse_literal(node, variables or {})
            else:
                return self.parse(node.value)
        except (ValueError, TypeError) as err:
            six.raise_from(ScalarParsingError(str(err), [node]), err)


class Argument(object):
    """ Field or Directive argument definition
    """

    # Yikes! Didn't find a better way to differentiate None as value and no
    # value in arguments... at least it's not exposed to callers.
    # Maybe we could wrap default value in a singleton type ?
    def __init__(
        self, name, type_, default_value=_UNDEF, description=None, node=None
    ):
        """
        :type name: str
        :type type_: Type
        :type default_value: any
        :type description: str
        """
        self.name = name
        self._type = type_
        self.default_value = default_value
        self.description = description
        self.has_default_value = self.default_value is not _UNDEF
        self.node = node

    @cached_property
    def type(self):
        return lazy(self._type)

    @cached_property
    def required(self):
        return (
            isinstance(self.type, NonNullType) and self.default_value is _UNDEF
        )

    def __str__(self):
        return "Argument(%s: %s)" % (self.name, self.type)


Arg = Argument


class Field(object):
    """ Member of an ``ObjectType``
    """

    def __init__(
        self,
        name,
        type_,
        args=None,
        description=None,
        deprecation_reason=None,
        resolve=None,
        subscribe=None,
        node=None,
    ):
        """
        :type name: str
        :type type_: Type
        :type args: callable|[Argument]|dict(str, Argument)
        :type fields: [Field]|dict(str, Field)
        :type resolve: callable
        :type deprecation_reason: str
        :type description: str
        """
        assert resolve is None or callable(resolve)
        assert subscribe is None or callable(subscribe)

        self.name = name
        self._type = type_
        self.description = description
        self.deprecated = bool(deprecation_reason)
        self.deprecation_reason = deprecation_reason
        self.resolve = resolve
        self.subscribe = subscribe
        self._args = args
        self.node = node

    @cached_property
    def type(self):
        return lazy(self._type)

    @cached_property
    def args(self):
        return _evaluate_lazy_list(self._args)

    arguments = args

    @cached_property
    def arg_map(self):
        return {arg.name: arg for arg in self.args}

    def __str__(self):
        return "Field(%s: %s)" % (self.name, self.type)


class ObjectType(NamedType):
    """ Object Type Definition

    Almost all of the GraphQL types you define will be object types. Object
    types have a name, but most importantly describe their fields.

    When two types need to refer to each other, or a type needs to refer to
    itself in a field, you can use a lambda expression to supply the
    fields lazily.
    """

    def __init__(
        self,
        name,
        fields,
        interfaces=None,
        is_type_of=None,
        description=None,
        nodes=None,
    ):
        """
        :type name: str
        :type fields: callable|dict(str, InputField)|[InputField]
        :type interfaces: callable|[InterfaceType]|dict(str, InterfaceType)
        :type is_type_of: callable|type
        :type description: str
        """
        self.name = name
        self.description = description
        self._fields = fields
        self._interfaces = interfaces
        self.nodes = [] if nodes is None else nodes

        assert is_type_of is None or callable(is_type_of)
        if isinstance(is_type_of, type):
            self.is_type_of = lambda v, **_: isinstance(v, is_type_of)
        else:
            self.is_type_of = is_type_of

    @cached_property
    def interfaces(self):
        return _evaluate_lazy_list(self._interfaces)

    @cached_property
    def fields(self):
        return _evaluate_lazy_list(self._fields)

    @cached_property
    def field_map(self):
        return {f.name: f for f in self.fields}


class InterfaceType(NamedType):
    """ Interface Type Definition

    When a field can return one of a heterogeneous set of types, a Interface
    type is used to describe what types are possible, what fields are in
    common across all types, as well as a function to determine which type
    is actually used when the field is resolved.
    """

    def __init__(
        self, name, fields, resolve_type=None, description=None, nodes=None
    ):
        """
        :type name: str
        :type fields: callable|dict(str, InputField)|[InputField]
        :type description: str
        """
        self.name = name
        self.description = description
        self._fields = fields
        self.nodes = [] if nodes is None else nodes

        assert resolve_type is None or callable(resolve_type)
        self.resolve_type = resolve_type

    @cached_property
    def fields(self):
        return _evaluate_lazy_list(self._fields)

    @cached_property
    def field_map(self):
        return {f.name: f for f in self.fields}


class UnionType(NamedType):
    """ Union Type Definition

    When a field can return one of a heterogeneous set of types, a Union type
    is used to describe what types are possible as well as providing a function
    to determine which type is actually used when the field is resolved.
    """

    def __init__(
        self, name, types, resolve_type=None, description=None, nodes=None
    ):
        """
        :type name: str
        :type types: callable|[Type]|dict(str, Type)
        :type description: str
        """
        self.name = name
        self.description = description
        self._types = types
        self.nodes = [] if nodes is None else nodes

        assert resolve_type is None or callable(resolve_type)
        self.resolve_type = resolve_type

    @cached_property
    def types(self):
        return _evaluate_lazy_list(self._types)


class Directive(Type):
    """ Directive definition

    Directives are used by the GraphQL runtime as a way of modifying
    execution behavior. Type system creators will usually not create
    these directly.
    """

    def __init__(self, name, locations, args=None, description=None, node=None):
        """
        :type name: str
        :type locations: [str]
        :type args: callable|[Argument]|dict(str, Argument)
        :type description: str
        """
        assert locations and all(
            [loc in DIRECTIVE_LOCATIONS for loc in locations]
        )
        self.name = name
        self.description = description
        self.locations = locations
        self._args = args
        self.node = node

    @cached_property
    def args(self):
        return _evaluate_lazy_list(self._args)

    arguments = args

    @cached_property
    def arg_map(self):
        return {arg.name: arg for arg in self.args}

    def __str__(self):
        return "@%s" % self.name


def is_input_type(type_):
    """ These types may be used as input types for arguments and directives.

    :type type_: py_gql.schema.types.Type
    :param type_:

    :rtype: bool
    """
    return isinstance(
        unwrap_type(type_), (ScalarType, EnumType, InputObjectType)
    )


def is_output_type(type_):
    """ These types may be used as output types as the result of fields.

    :type type_: py_gql.schema.types.Type
    :param type_:

    :rtype: bool
    """
    return isinstance(
        unwrap_type(type_),
        (ScalarType, EnumType, ObjectType, InterfaceType, UnionType),
    )


def is_leaf_type(type_):
    """  These types may describe types which may be leaf values.

    :type type_: py_gql.schema.types.Type
    :param type_:

    :rtype: bool
    """
    return isinstance(type_, (ScalarType, EnumType))


def is_composite_type(type_):
    """ These types may describe the parent context of a selection set.

    :type type_: py_gql.schema.types.Type
    :param type_:

    :rtype: bool
    """
    return isinstance(type_, (ObjectType, InterfaceType, UnionType))


def is_abstract_type(type_):
    """ These types may describe the parent context of a selection set.

    :type type_: py_gql.schema.types.Type
    :param type_:

    :rtype: bool
    """
    return isinstance(type_, (InterfaceType, UnionType))


def unwrap_type(type_):
    """ Recursively extract type for a potentially wrapping type like
    :class:`ListType` or :class:`NonNullType`.

    :type type_: py_gql.schema.types.Type
    :rtype: py_gql.schema.types.Type

    >>> from py_gql.schema.scalars import Int
    >>> unwrap_type(NonNullType(ListType(NonNullType(Int)))) is Int
    True
    """
    if isinstance(type_, WrappingType):
        return unwrap_type(type_.type)
    return type_


def nullable_type(type_):
    """ Extract nullable type from a potentially non nulllable one.

    :type type_: py_gql.schema.types.Type
    :param type_: Potentially non-nullable type

    :rtype: py_gql.schema.types.Type
    :returns: Nullable type

    >>> from py_gql.schema.scalars import Int
    >>> unwrap_type(NonNullType(Int)) is Int
    True
    """
    if isinstance(type_, NonNullType):
        return type_.type
    return type_
