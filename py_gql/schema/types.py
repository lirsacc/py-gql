# -*- coding: utf-8 -*-
""" Utilitiy classes to define custom types.
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
    """ Base type class, all types used in a :class:`py_gql.schema.Schema`
    should be instances of this (or a subclass). """

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
    """ Named type. The name **must be unique** across a single
    :class:`py_gql.schema.Schema` instance.

    Attributes:
        name (str): Type name.
    """

    def __str__(self):
        return self.name


class WrappingType(Type):
    """ Types wrapping other types.

    Attributes:
        node (:class:`py_gql.lang.ast.Type`):
            Source node used when building type from the SDL

    Args:
        type_ (Lazy[py_gql.schema.Type]): Wrapped type.
        node (Optional[py_gql.lang.ast.Type]):
            Source node used when building type from the SDL
    """

    def __init__(self, type_, node=None):
        self._type = type_
        self.node = node

    @cached_property
    def type(self):
        """ :class:`py_gql.schema.Type`: Wrapped type """
        return lazy(self._type)


class NonNullType(WrappingType):
    """ Non nullable wrapping type.

    A non-null is a wrapping type which points to another type.
    Non-null types enforce that their values are never null and can ensure
    an error is raised if this ever occurs during a request. It is useful for
    fields which you can make a strong guarantee on non-nullability, for example
    usually the id field of a database row will never be null.

    Attributes:
        node (:class:`py_gql.lang.ast.NonNullType`):
            Source node used when building type from the SDL

    Args:
        type_ (Lazy[py_gql.schema.Type]): Wrapped type.
        node (Optional[py_gql.lang.ast.NonNullType]):
            Source node used when building type from the SDL
    """

    def __init__(self, type_, node=None):
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

    Attributes:
        node (:class:`py_gql.lang.ast.ListType`):
            Source node used when building type from the SDL

    Args:
        type_ (Lazy[py_gql.schema.Type]):
            Type or callable returning the type (lazy / cyclic definitions).

        node (Optional[py_gql.lang.ast.ListType]):
            Source node used when building type from the SDL
    """

    def __str__(self):
        return "[%s]" % self.type


class InputField(object):
    """ Member of an :class:`py_gql.schema.InputObjectType`

    Args:
        name (str): Field name
        type_ (Lazy[py_gql.schema.Type]): Field type (must be input type)
        default_value (Optional[any]): Default value
        description (Optional[str]): Field description
        node (Optional[py_gql.lang.ast.InputValueDefinition]):
            Source node used when building type from the SDL

    Attributes:
        name (str): Field name
        description (Optional[str]): Field description
        has_default_value (bool): ``True`` if default value is set
        node (Optional[py_gql.lang.ast.InputValueDefinition]):
            Source node used when building type from the SDL
    """

    # Yikes! Didn't find a better way to differentiate None as value and no
    # value in arguments... at least it's not exposed to callers.
    # Maybe we could wrap default value in a singleton type ?
    def __init__(
        self, name, type_, default_value=_UNDEF, description=None, node=None
    ):
        self.name = name
        self._type = type_
        self._default_value = default_value
        self.description = description
        self.has_default_value = self._default_value is not _UNDEF
        self.node = node

    @property
    def default_value(self):
        """ Default value if it was set """
        if self._default_value is _UNDEF:
            raise AttributeError("No default value")
        return self._default_value

    @cached_property
    def type(self):
        """ py_gql.schema.Type: Field type """
        return lazy(self._type)

    @cached_property
    def required(self):
        """ bool: Whether this field is required (non nullable and does
        not have a default value) """
        return (
            isinstance(self.type, NonNullType) and self._default_value is _UNDEF
        )

    def __str__(self):
        return "InputField(%s: %s)" % (self.name, self.type)


class InputObjectType(NamedType):
    """ Input Object Type Definition

    An input object defines a structured collection of fields which may be
    supplied to a field argument or a directive.

    Args:
        name (str): Type name
        fields (Lazy[List[py_gql.schema.InputField]]): Fields
        description (Optional[str]): Type description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name
        description (Optional[str]): Directive description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    """

    def __init__(self, name, fields, description=None, nodes=None):
        self.name = name
        self.description = description
        self._fields = fields
        self.nodes = [] if nodes is None else nodes

    @cached_property
    def fields(self):
        """ List[py_gql.schema.InputField]: Object fields """
        return _evaluate_lazy_list(self._fields)

    @cached_property
    def field_map(self):
        """ Dict[str, py_gql.schema.InputField]: Object fields map """
        return {f.name: f for f in self.fields}


class EnumValue(object):
    """ Enum value definition.

    Args:
        name (str): Name of the value
        value (Optional[any]): Python value.
            Defaults to ``name`` if unset, must be hashable to support reverse
            lookups
        deprecation_reason (Optional[str]):
            If set, the field will be marked as deprecated and include this as
            the reason
        description (Optional[str]): Enum value description
        node (Optional[py_gql.lang.ast.EnumValueDefinition]):
            Source node used when building type from the SDL

    Attributes:
        name (str): Enum value name
        value: Enum value value
        description (Optional[str]): Enum value description
        deprecation_reason (Optional[str]):
        deprecated (bool):
        node (Optional[py_gql.lang.ast.FieldDefinition]):
            Source node used when building type from the SDL
    """

    @classmethod
    def from_def(cls, definition):
        """ Create an enum value from various source objects.

        This supports existing `EnumValue` instances, strings,
        (name, value) tuples and dictionnaries matching the signature of
        `EnumValue.__init__`.
        """
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

    Warning:
        Enum values must be hashable to provide reverse lookup
        capabilities when coercing python values into enum values.

    Args:
        name (str): Enum name
        values (list): List of enum value definition support by
            `EnumValue.from_def`
        description (Optional[str]): Enum description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    Attributes:
        name (str): Enum name
        values (Dict[str, py_gql.schema.EnumValue]):
            Values by name
        reverse_values (Dict[any, py_gql.schema.EnumValue]):
            Values by value
        description (Optional[str]): Enum description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    """

    def __init__(self, name, values, description=None, nodes=None):
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

        Args:
            name (str): Name of the value to extract

        Returns:
            :class:`py_gql.schema.EnumValue`: The corresponding EnumValue

        Raises:
            :class:`~py_gql.exc.UnknownEnumValue` when the name is unknown
        """
        try:
            return self.values[name].value
        except KeyError:
            raise UnknownEnumValue(
                "Invalid name %s for enum %s" % (name, self.name)
            )

    def get_name(self, value):
        """ Extract the name for a given value.

        Args:
            value (any): Value of the value to extract, must be hashable

        Returns:
            :class:`py_gql.schema.EnumValue`: The corresponding EnumValue

        Raises:
            :class:`~py_gql.exc.UnknownEnumValue` when the value is unknown
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

    Args:
        name (str): Type name

        serialize (callable): Type serializer
            This function receives Python value and must output JSON scalars
            (that is string, number, boolean and null).
            Raise :class:`~py_gql.exc.ScalarSerializationError`,
            :py:class:`ValueError` or :py:class:`TypeError` to signify that the
            value cannot be serialized.

        parse (callable): Type de-serializer
            This function receives JSON scalars and outputs Python values.
            Raise :class:`~py_gql.exc.ScalarParsingError`, :py:class:`ValueError`
            or :py:class:`TypeError` to signify that the value cannot be parsed.

        parse_literal (Optional[callable]): Type de-serializer for value nodes
            This function receives a :class:`py_gql.lang.ast.Value`
            and outputs Python values.
            Raise :class:`~py_gql.exc.ScalarParsingError`, :py:class:`ValueError`
            or :py:class:`TypeError` to signify that the value cannot be parsed.
            If unset, the ``parse`` argument is used and gets passed the
            ``value`` attribute of the node.

        description (Optional[str]): Type description

        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name
        description (Optional[str]): Type description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

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
        self.name = name
        self.description = description
        assert callable(serialize)
        self._serialize = serialize
        assert callable(parse)
        self._parse = parse
        assert parse_literal is None or callable(parse_literal)
        self._parse_literal = parse_literal
        self.nodes = [] if nodes is None else nodes

    def serialize(self, value):
        """ Transform a Python value in a JSON serializable one.

        Args:
            value: Python level value

        Returns:
            JSON scalar
        """
        try:
            return self._serialize(value)
        except (ValueError, TypeError) as err:
            six.raise_from(ScalarSerializationError(str(err)), err)

    def parse(self, value):
        """ Transform a GraphQL value in a valid Python value

        Args:
            value: JSON scalar

        Returns:
            Python level value
        """
        try:
            return self._parse(value)
        except (ValueError, TypeError) as err:
            six.raise_from(ScalarParsingError(str(err)), err)

    def parse_literal(self, node, variables=None):
        """ Transform an AST node in a valid Python value

        Args:
            value (py_gql.lang.ast.Value): Parse node

        Returns:
            Python level value
        """
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
    """ Field or Directive argument definition.

    Warning:
        As ``None`` is a valid default value, in order to define an
        argument wihtout any default value, the ``default_value`` argument
        must be omitted.

    Args:
        name (str): Argument name
        type_ (Lazy[py_gql.schema.Type]): Argument type (must be input type)
        default_value (Optional[any]): Default value
        description (Optional[str]): Argument description
        node (Optional[py_gql.lang.ast.InputValueDefinition]):
            Source node used when building type from the SDL

    Attributes:
        name (str): Argument name
        description (Optional[str]): Argument description
        has_default_value (bool): ``True`` if default value is set
        node (Optional[py_gql.lang.ast.InputValueDefinition]):
            Source node used when building type from the SDL
    """

    # Yikes! Didn't find a better way to differentiate None as value and no
    # value in arguments... at least it's not exposed to callers.
    # Maybe we could wrap default value in a singleton type ?
    def __init__(
        self, name, type_, default_value=_UNDEF, description=None, node=None
    ):
        self.name = name
        self._type = type_
        self._default_value = default_value
        self.description = description
        self.has_default_value = self._default_value is not _UNDEF
        self.node = node

    @property
    def default_value(self):
        """ Default value if it was set """
        if self._default_value is _UNDEF:
            raise AttributeError("No default value")
        return self._default_value

    @cached_property
    def type(self):
        """ py_gql.schema.Type: Argument type """
        return lazy(self._type)

    @cached_property
    def required(self):
        """ bool: Whether this argument is required (non nullable and does
        not have a default value) """
        return (
            isinstance(self.type, NonNullType) and self._default_value is _UNDEF
        )

    def __str__(self):
        return "Argument(%s: %s)" % (self.name, self.type)


class Field(object):
    """ Member of an :class:`py_gql.schema.ObjectType`.

    Args:
        name (str): Field name
        type_ (Lazy[py_gql.schema.Type]): Field type (must be output type)
        args (Lazy[List[py_gql.schema.Argument]]): Field arguments
        description (Optional[str]): Field description
        deprecation_reason (Optional[str]):
            If set, the field will be marked as deprecated and include this as
            the reason
        resolve (callable):
            Resolver function. If not set, :func:`py_gql.utilities.default_resolver`
            will be used during execution
        node (Optional[py_gql.lang.ast.FieldDefinition]):
            Source node used when building type from the SDL

    Attributes:
        name (str): Field name
        description (Optional[str]): Field description
        deprecation_reason (Optional[str]):
        deprecated (bool):
        resolve (Optional[callable]): Resolver function
        node (Optional[py_gql.lang.ast.FieldDefinition]):
            Source node used when building type from the SDL
    """

    def __init__(
        self,
        name,
        type_,
        args=None,
        description=None,
        deprecation_reason=None,
        resolve=None,
        node=None,
    ):
        assert resolve is None or callable(resolve)

        self.name = name
        self._type = type_
        self.description = description
        self.deprecated = bool(deprecation_reason)
        self.deprecation_reason = deprecation_reason
        self.resolve = resolve
        self._args = args
        self.node = node

    @cached_property
    def type(self):
        """ py_gql.schema.Type: Field type """
        return lazy(self._type)

    @cached_property
    def args(self):
        """ List[py_gql.schema.Argument]: Field arguments """
        return _evaluate_lazy_list(self._args)

    arguments = args

    @cached_property
    def arg_map(self):
        """ Dict[str, py_gql.schema.Argument]: Field arguments map """
        return {arg.name: arg for arg in self.args}

    def __str__(self):
        return "Field(%s: %s)" % (self.name, self.type)


class ObjectType(NamedType):
    """ Object Type Definition

    Almost all of the GraphQL types you define will be object types. Object
    types have a name, but most importantly describe their fields.

    Args:
        name (str): Type name
        fields (Lazy[List[py_gql.schema.Field]]): Fields
        interfaces (Lazy[List[py_gql.schema.InterfaceType]]):
            Implemented interfaces
        is_type_of:
            Either ``None``, a callable or a class used to identify an
            object's interface.
        description (Optional[str]): Type description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name
        is_type_of (Optional[callable]): Type resolver
        description (Optional[str]): Directive description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL
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
        """ List[py_gql.schema.InterfaceType]: Implemented interfaces """
        return _evaluate_lazy_list(self._interfaces)

    @cached_property
    def fields(self):
        """ List[py_gql.schema.Field]: Object fields """
        return _evaluate_lazy_list(self._fields)

    @cached_property
    def field_map(self):
        """ Dict[str, py_gql.schema.Field]: Object fields map """
        return {f.name: f for f in self.fields}


class InterfaceType(NamedType):
    """ Interface Type Definition

    When a field can return one of a heterogeneous set of types, a Interface
    type is used to describe what types are possible, what fields are in
    common across all types, as well as a function to determine which type
    is actually used when the field is resolved.

    Args:
        name (str): Type name
        fields (Lazy[List[py_gql.schema.Field]]): Fields
        resolve_type (Optional[callable]): Type resolver
        description (Optional[str]): Type description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name
        resolve_type (Optional[callable]): Type resolver
        description (Optional[str]): Directive description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL
    """

    def __init__(
        self, name, fields, resolve_type=None, description=None, nodes=None
    ):
        self.name = name
        self.description = description
        self._fields = fields
        self.nodes = [] if nodes is None else nodes

        assert resolve_type is None or callable(resolve_type)
        self.resolve_type = resolve_type

    @cached_property
    def fields(self):
        """ List[py_gql.schema.Field]: Interface fields """
        return _evaluate_lazy_list(self._fields)

    @cached_property
    def field_map(self):
        """ Dict[str, py_gql.schema.Field]: Interface fields map """
        return {f.name: f for f in self.fields}


class UnionType(NamedType):
    """ Union Type Definition

    When a field can return one of a heterogeneous set of types, a Union type
    is used to describe what types are possible as well as providing a function
    to determine which type is actually used when the field is resolved.

    Args:
        name (str): Type name
        types (Lazy[List[py_gql.schema.ObjectType]]): Member types
        resolve_type (Optional[callable]): Type resolver
        description (Optional[str]): Type description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

    Attributes:
        name (str): Type name
        resolve_type (Optional[callable]): Type resolver
        description (Optional[str]): Directive description
        nodes (Optional[List[py_gql.lang.ast.Node]]):
            Source nodes used when building type from the SDL

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
        """ List[py_gql.schema.ObjectType]: Member types """
        return _evaluate_lazy_list(self._types)


class Directive(Type):
    """ Directive definition

    Directives are used by the GraphQL runtime as a way of modifying
    execution behavior. Type system creators will usually not create
    these directly.

    Args:
        name (str): Directive name
        locations (List[str]): Possible locations for that directive
        args (List[py_gql.schena.Argument]): Argument definitions
        description (Optional[str]): Directive description
        node (Optional[py_gql.lang.ast.DirectiveDefinition]):
            Source node used when building type from the SDL.

    Attributes:
        name (str): Directive name
        locations (List[str]): Possible locations for that directive
        args (List[py_gql.schena.Argument]): Argument definitions
        arguments (List[py_gql.schena.Argument]): Argument definitions
        arg_map: (Dict[str, py_gql.schena.Argument]): ``arg name -> arg definition``
        description (Optional[str]): Directive description
        node (Optional[py_gql.lang.ast.DirectiveDefinition]):
            Source node used when building type from the SDL.
    """

    def __init__(self, name, locations, args=None, description=None, node=None):
        assert locations and all(
            [loc in DIRECTIVE_LOCATIONS for loc in locations]
        )
        self.name = name
        self.description = description
        self.locations = locations
        self.arguments = self.args = args or []
        self.arg_map = {arg.name: arg for arg in self.args}
        self.node = node

    def __str__(self):
        return "@%s" % self.name


def is_input_type(type_):
    """ These types may be used as input types for arguments and directives.

    Args:
        type_ (py_gql.schema.Type): Type under test

    Returns:
        bool:
    """
    return isinstance(
        unwrap_type(type_), (ScalarType, EnumType, InputObjectType)
    )


def is_output_type(type_):
    """ These types may be used as output types as the result of fields.

    Args:
        type_ (py_gql.schema.Type): Type under test

    Returns:
        bool:
    """
    return isinstance(
        unwrap_type(type_),
        (ScalarType, EnumType, ObjectType, InterfaceType, UnionType),
    )


def is_leaf_type(type_):
    """  These types may describe types which may be leaf values.

    Args:
        type_ (py_gql.schema.Type): Type under test

    Returns:
        bool:
    """
    return isinstance(type_, (ScalarType, EnumType))


def is_composite_type(type_):
    """ These types may describe the parent context of a selection set.

    Args:
        type_ (py_gql.schema.Type): Type under test

    Returns:
        bool:
    """
    return isinstance(type_, (ObjectType, InterfaceType, UnionType))


def is_abstract_type(type_):
    """ These types may describe the parent context of a selection set.

    Args:
        type_ (py_gql.schema.Type): Type under test

    Returns:
        bool:
    """
    return isinstance(type_, (InterfaceType, UnionType))


def unwrap_type(type_):
    """ Recursively extract type for a potentially wrapping type like
    :class:`ListType` or :class:`NonNullType`.

    Args:
        type_ (py_gql.schema.Type): Potentially wrapped type

    Returns:
        Unwrapped type

    >>> from py_gql.schema import Int, NonNullType, ListType
    >>> unwrap_type(NonNullType(ListType(NonNullType(Int)))) is Int
    True
    """
    if isinstance(type_, WrappingType):
        return unwrap_type(type_.type)
    return type_


def nullable_type(type_):
    """ Extract nullable type from a potentially non nulllable one.

    Args:
        type_ (py_gql.schema.Type): Potentially non-nullable type

    Returns:
        py_gql.schema.Type:  Nullable type

    >>> from py_gql.schema import Int, NonNullType
    >>> unwrap_type(NonNullType(Int)) is Int
    True
    """
    if isinstance(type_, NonNullType):
        return type_.type
    return type_
