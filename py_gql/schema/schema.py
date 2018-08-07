# -*- coding: utf-8 -*-
""" Schema definition. """

from collections import defaultdict

from ..exc import SchemaError, UnknownType
from ..lang import ast as _ast
from ._validation import validate_schema
from .directives import SPECIFIED_DIRECTIVES
from .introspection import __Schema__
from .printer import SchemaPrinter
from .scalars import SPECIFIED_SCALAR_TYPES
from .types import (
    Directive,
    InputObjectType,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    Type,
    UnionType,
    WrappingType,
    is_abstract_type,
    unwrap_type,
)

_unset = object()


class Schema(object):
    """ A GraphQL schema definition.

    This is the main container for a GraphQL schema and its related types.

    Args:
        query_type (py_gql.schema.ObjectType):
            The root query type for the schema

        mutation_type (py_gql.schema.ObjectType):
            The root mutation type for the schema

        subscription_type (py_gql.schema.ObjectType):
            The root subscription type for the schema

        directives (List[py_gql.schema.Directive]):
            List of possible directives to use.
            The default, specified directives (``@include``, ``@skip``) will
            always be included.

        types (List[py_gql.schema.Type]):
            List of additional types on top of the types that would be infered
            from the root types.

        node (List[Union[py_gql.lang.ast.SchemaDefinition, \
                         py_gql.lang.ast.SchemaExtension]]):
            AST node for the schema if applicable, i.e. when creating the schema
            from a GraphQL (SDL) document.

    Attributes:
        query_type (py_gql.schema.ObjectType):
            The root query type for the schema (required)

        mutation_type (py_gql.schema.ObjectType):
            The root mutation type for the schema (optional)

        subscription_type (py_gql.schema.ObjectType):
            The root subscription type for the schema (optional)

        node (List[Union[py_gql.lang.ast.SchemaDefinition, \
                         py_gql.lang.ast.SchemaExtension]]):
            AST node for the schema if applicable, i.e. when creating the schema
            from a GraphQL (SDL) document.

        type_map (Dict[str, py_gql.schema.Type]):
            Mapping ``type name -> Type instance`` of all types used in the
            schema, including directives.

        types (Dict[str, py_gql.schema.Type]):
            Mapping ``type name -> Type instance`` of all types used in the
            schema, excluding directives.

        directives (Dict[str, py_gql.schema.Directive]):
            Mapping ``directive name -> Directive instance`` of all directives
            used in the schema.

        implementations (Dict[str, List[py_gql.schema.Directive]]):
            Mapping of ``interface name -> [implementing object types]``.
    """

    def __init__(
        self,
        query_type=None,
        mutation_type=None,
        subscription_type=None,
        directives=None,
        types=None,
        nodes=None,
    ):
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.subscription_type = subscription_type

        self._types = [query_type, mutation_type, subscription_type]
        self._types.append(__Schema__)
        self.nodes = nodes or []

        # NOTE: This is the notion of the specified types being always
        # available. As a result of this line, intropection queries will always
        # include thes types even if they are not actively used in the schema.
        # I am not totally sure if this is the right behaviour and it may
        # change in the future.
        self._types.extend(list(SPECIFIED_SCALAR_TYPES))

        if types:
            self._types.extend(types)

        self._directives = []
        if directives:
            self._directives.extend(directives)
        _directive_names = set(
            (d.name for d in self._directives if isinstance(d, Directive))
        )
        for d in SPECIFIED_DIRECTIVES:
            if d.name not in _directive_names:
                self._directives.append(d)

        self._possible_types = {}
        self._is_valid = None
        self._literal_types_cache = {}

        self.type_map = _build_type_map(self._types + self._directives)
        self._rebuild_caches()

    def _rebuild_caches(self):
        self.types = {
            name: t
            for name, t in self.type_map.items()
            if not isinstance(t, Directive)
        }
        self.directives = {
            name: t
            for name, t in self.type_map.items()
            if isinstance(t, Directive)
        }
        self.implementations = defaultdict(list)
        for type_ in self.types.values():
            if isinstance(type_, ObjectType):
                for iface in type_.interfaces:
                    self.implementations[iface.name].append(type_)
        self._is_valid = None

    def validate(self):
        """ Check that the schema is valid and cache the result.

        Returns:
            bool: ``True`` if the schema is valid

        Raises:
            :class:`~py_gql.exc.SchemaError` if the schema is invalid.
        """
        if self._is_valid is None:
            self._is_valid = validate_schema(self)
        return self._is_valid

    def get_type(self, name, default=_unset):
        """ Get a type by name.

        Args:
            name (str): Requested type name
            default: If set, will be returned in case there is no matching type

        Returns:
            py_gql.schema.Type: Type instance

        Raises:
            :class:`~py_gql.exc.UnknownType`:
                if ``default`` is not set and the type is not found

        """
        try:
            return self.types[name]
        except KeyError:
            if default is not _unset:
                return default
            raise UnknownType(name)

    def get_type_from_literal(self, ast_node):
        """ Given an AST node describing a type, return a
        corresponding :class:`py_gql.schema.Type` instance.

        For example, if provided the parsed AST node for ``[User]``,
        a :class:`py_gql.schema.ListType` instance will be returned, containing
        the type called ``User`` found in the schema.
        If a type called ``User`` is not found in the schema, then
        :class:`~py_gql.exc.UnknownType` will be raised.

        Args:
            ast_node (py_gql.lang.ast.Type)

        Returns:
            py_gql.schema.Type: Corresponding type instance

        Raises:
            :class:`~py_gql.exc.UnknownType`: if  any named type is not found
        """
        if ast_node in self._literal_types_cache:
            return self._literal_types_cache[ast_node]

        if isinstance(ast_node, _ast.ListType):
            t = ListType(self.get_type_from_literal(ast_node.type))
            self._literal_types_cache[ast_node] = t
            return t
        elif isinstance(ast_node, _ast.NonNullType):
            t = NonNullType(self.get_type_from_literal(ast_node.type))
            self._literal_types_cache[ast_node] = t
            return t
        elif isinstance(ast_node, _ast.NamedType):
            t = self.get_type(ast_node.name.value)
            self._literal_types_cache[ast_node] = t
            return t
        raise TypeError("Invalid type node %r" % ast_node)

    def get_possible_types(self, type_):
        """ Get the possible implementations of an abstract type.

        Args:
            type_ (Union[py_gql.schema.types.UnionType, \
py_gql.schema.types.InterfaceType]):
                Abstract type to check.

        Returns:
            List[py_gql.schema.types.ObjectType]: List of possible implementations.
        """
        if type_ in self._possible_types:
            return self._possible_types[type_]

        if isinstance(type_, UnionType):
            self._possible_types[type_] = type_.types or []
            return self._possible_types[type_]
        elif isinstance(type_, InterfaceType):
            self._possible_types[type_] = self.implementations.get(
                type_.name, []
            )
            return self._possible_types[type_]

        raise TypeError("Not an abstract type: %s" % type_)

    def is_possible_type(self, abstract_type, type_):
        """ Check that ``type_`` is a possible realization of ``abstract_type``.

        Args:
            abstract_type (Union[py_gql.schema.types.UnionType, \
py_gql.schema.types.InterfaceType]):
            type_ (py_gql.schema.Type): Concrete type to check

        Returns:
            bool: ``True`` if ``type_`` is valid for ``abstract_type``
        """
        return type_ in self.get_possible_types(abstract_type)

    def is_subtype(self, type_, super_type):
        """ Provided a type and a super type, return true if the first type is
        either equal or a subset of the second super type (covariant).

        Args:
            type_ (py_gql.schema.Type):
            super_type (py_gql.schema.Type):

        Returns:
            bool:

        """
        if type_ == super_type:
            return True

        if (
            isinstance(type_, WrappingType)
            and isinstance(super_type, WrappingType)
            and type(type_) == type(super_type)
        ):
            return self.is_subtype(type_.type, super_type.type)

        if isinstance(type_, NonNullType):
            return self.is_subtype(type_.type, super_type)

        if isinstance(type_, ListType):
            return False

        return (
            is_abstract_type(super_type)
            and isinstance(type_, ObjectType)
            and self.is_possible_type(super_type, type_)
        )

    def types_overlap(self, rhs, lhs):
        """ Provided two composite types, determine if they "overlap". Two
        composite types overlap when the Sets of possible concrete types for
        each intersect.

        This is often used to determine if a fragment of a given type could
        possibly be visited in a context of another type. This function is
        commutative.

        Args:
            rhs (py_gql.schema.Type):
            lhs (py_gql.schema.Type):

        Returns:
            bool:
        """
        if rhs == lhs:
            return True

        if is_abstract_type(rhs) and is_abstract_type(lhs):
            rhs_types = self.get_possible_types(rhs)
            lhs_types = self.get_possible_types(lhs)
            return any((t in lhs_types for t in rhs_types))

        return (is_abstract_type(rhs) and self.is_possible_type(rhs, lhs)) or (
            is_abstract_type(lhs) and self.is_possible_type(lhs, rhs)
        )

    def to_string(
        self,
        indent=4,
        include_descriptions=True,
        description_format="block",
        include_introspection=False,
        cls=SchemaPrinter,
    ):
        """ Format the schema as a string

        Args:
            indent (Union[str, int]): Indent character or number of spaces

            include_descriptions (bool):
                If ``True`` include descriptions in the output

            description_format ("comments"|"block"):
                Control how descriptions are formatted. ``"comments"`` is the
                old standard and will be compatible with most GraphQL parsers
                while ``"block"`` is part of the most recent specification and
                includes descriptions as block strings that can be extracted
                according to the specification.

            include_introspection (bool):
                If ``True``, include introspection types in the output

            cls (callable): Custom formatter
                Use this to customize the behaviour, by default this uses
                :class:`py_gql.schema.printer.SchemaPrinter`.

        Returns:
            str: Formatted GraphQL schema
        """
        return cls(
            indent=indent,
            include_descriptions=include_descriptions,
            description_format=description_format,
            include_introspection=include_introspection,
        )(self)


def _build_type_map(types, _type_map=None):
    """ Recursively build a mapping name <> Type from a list of types to include
    all referenced types.

    Warning:
        This will flatten all lazy type definitions and attributes.

    Args:
        types (List[py_gql.schema.Type]): List of types
        _type_map (Dict[str, py_gql.schema.Type]):
            Pre-built type map ( recursive calls)

    Returns:
        Dict[str, py_gql.schema.Type]
    """
    type_map = _type_map or {}
    for type_ in types or []:
        if not type_:
            continue

        type_ = unwrap_type(type_)

        if not (isinstance(type_, Type) and hasattr(type_, "name")):
            raise SchemaError(
                'Expected named types but got "%s" of type %s'
                % (type_, type(type_))
            )

        name = type_.name
        if name in type_map:
            if type_ is not type_map[name]:
                raise SchemaError('Duplicate type "%s"' % name)
            continue

        type_map[name] = type_
        child_types = []

        if isinstance(type_, UnionType):
            child_types.extend(type_.types)

        if isinstance(type_, ObjectType):
            child_types.extend(type_.interfaces)

        if isinstance(type_, (ObjectType, InterfaceType)):
            for field in type_.fields:
                child_types.append(field.type)
                child_types.extend([arg.type for arg in field.args or []])

        if isinstance(type_, InputObjectType):
            for field in type_.fields:
                child_types.append(field.type)

        if isinstance(type_, Directive):
            child_types.extend([arg.type for arg in type_.args or []])

        type_map.update(_build_type_map(child_types, _type_map=type_map))

    return type_map
