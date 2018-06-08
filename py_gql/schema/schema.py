# -*- coding: utf-8 -*-
""" Schema definition. """

from .._utils import cached_property
from ..exc import SchemaError, UnknownType
from ..lang import ast as _ast
from .directives import SPECIFIED_DIRECTIVES
from .introspection import __Schema__
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
from .validation import validate_schema

_unset = object()


class Schema(object):
    """ Schema definition.

    A Schema is created by supplying the root types of each type of operation,
    query and mutation (optional). A schema definition is then supplied to the
    validator and executor. """

    def __init__(
        self,
        query_type=None,
        mutation_type=None,
        subscription_type=None,
        directives=None,
        types=None,
    ):
        """
        :type query_type: py_gql.schema.types.ObjectType
        :param query_type:
            The root query type for the schema (required)

        :type mutation_type: py_gql.schema.types.ObjectType
        :param mutation_type:
            The root mutation type for the schema (optional)

        :type subscription_type: py_gql.schema.types.ObjectType
        :param subscription_type:
            The root subscription type for the schema (optional)

        :type directives: [py_gql.schema.types.Directive]
        :param directives:
            List of possible directives to use. The default specified
            directives will always be added.

        :type types:
        :param types:
            List of additional types on top of the types infered from the
            root types.
        """
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.subscription_type = subscription_type

        self._types = [query_type, mutation_type, subscription_type]
        self._types.append(__Schema__)

        # NOTE: This is the notion of the specified types being always
        # available. As a result of this line, intropection queries will always
        # include thes types even if they are not actively used in the schema.
        # I am not totally sure if this is the right behaviour and it may
        # change in the future.
        self._types.extend(list(SPECIFIED_SCALAR_TYPES))

        if types:
            self._types.extend(types)

        self._directives = list(SPECIFIED_DIRECTIVES)
        if directives:
            self._directives.extend(directives)

        self._possible_types = {}
        self._is_valid = None
        self._literal_types_cache = {}

    @cached_property
    def _type_map(self):
        return _build_type_map(self._types + self._directives)

    @cached_property
    def types(self):
        return {
            name: t
            for name, t in self._type_map.items()
            if not isinstance(t, Directive)
        }

    @cached_property
    def directives(self):
        return {
            name: t for name, t in self._type_map.items() if isinstance(t, Directive)
        }

    @cached_property
    def implementations(self):
        impls = {}
        for typ in self.types.values():
            if isinstance(typ, ObjectType):
                for iface in typ.interfaces:
                    impls[iface.name] = impls.get(iface.name, []) + [typ]
        return impls

    def validate(self):
        if self._is_valid is None:
            self._is_valid = validate_schema(self)
        return self._is_valid

    def get_type(self, type_name, default=_unset):
        """ Get a type by name.

        :type type_name: str
        :rtype: py_gql.schema.types.Type
        """
        try:
            return self.types[type_name]
        except KeyError:
            if default is not _unset:
                return default
            raise UnknownType(type_name)

    def get_type_from_literal(self, ast_node):
        """ Given a Schema and an AST node describing a type, return a
        `Type` definition which applies to that type.
        For example, if provided the parsed AST node for `[User]`,
        a `ListType` instance will be returned, containing the type called
        "User" found in the schema. If a type called "User" is not found in
        the schema, then `UnknownType` will be raised.

        This is the equivalent of ``type_from_ast`` in the reference JS
        implementation.

        :type ast_node: py_gql.lang.ast.Type
        :rtype: py_gql.schema.types.Type
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

    def get_possible_types(self, typ):
        """ Get the possible implementations of an abstract type.

        :type typ: py_gql.schema.types.UnionType|\
            py_gql.schema.types.InterfaceType
        :param typ:
            Abstract type to check.

        :rtype: [py_gql.schema.types.Type]
        :return:
            List of possible implementations.
        """
        if typ in self._possible_types:
            return self._possible_types[typ]

        if isinstance(typ, UnionType):
            self._possible_types[typ] = typ.types or []
            return self._possible_types[typ]
        elif isinstance(typ, InterfaceType):
            self._possible_types[typ] = self.implementations.get(typ.name, [])
            return self._possible_types[typ]

        raise TypeError("Not an abstract type: %s" % typ)

    def is_possible_type(self, abstract_type, possible_type):
        """ Check that ``possible_type`` is a possible realization of
        ``abstract_type``.

        :type typ: py_gql.schema.types.UnionType|\
            py_gql.schema.types.InterfaceType
        :param typ:
            Abstract type to check against.

        :type possible_type: py_gql.schema.types.Type
        :param possible_type:
            Realization type to check.

        :rtype: bool
        """
        return possible_type in self.get_possible_types(abstract_type)

    def is_subtype(self, typ, super_type):
        """ Provided a type and a super type, return true if the first type is
        either equal or a subset of the second super type (covariant).

        :type typ: py_gql.schema.types.Type
        :type super_type: py_gql.schema.types.Type
        :rtype: bool
        """
        if typ == super_type:
            return True

        if (
            isinstance(typ, WrappingType)
            and isinstance(super_type, WrappingType)
            and type(typ) == type(super_type)
        ):
            return self.is_subtype(typ.type, super_type.type)

        if isinstance(typ, NonNullType):
            return self.is_subtype(typ.type, super_type)

        if isinstance(typ, ListType):
            return False

        return (
            is_abstract_type(super_type)
            and isinstance(typ, ObjectType)
            and self.is_possible_type(super_type, typ)
        )

    def overlap(self, rhs, lhs):
        """ Provided two composite types, determine if they "overlap". Two
        composite types overlap when the Sets of possible concrete types for
        each intersect.

        This is often used to determine if a fragment of a given type could
        possibly be visited in a context of another type. This function is
        commutative.

        :type rhs: py_gql.schema.types.Type
        :type lhs: py_gql.schema.types.Type
        :rtype: bool
        """
        if rhs == lhs:
            return True

        if is_abstract_type(rhs) and is_abstract_type(lhs):
            rhs_types = self.get_possible_types(rhs)
            lhs_types = self.get_possible_types(lhs)
            return any((typ in lhs_types for typ in rhs_types))

        return (is_abstract_type(rhs) and self.is_possible_type(rhs, lhs)) or (
            is_abstract_type(lhs) and self.is_possible_type(lhs, rhs)
        )


def _build_type_map(types, _type_map=None):
    """ Recursively build a mapping name <> Type from a list of types to include
    all referenced types.

    :type types: List[py_gql.schema.Type]
    :rtype: dict[str, py_gql.schema.Type]
    """
    type_map = _type_map or {}
    for typ in types or []:
        if not typ:
            continue

        typ = unwrap_type(typ)

        if not (isinstance(typ, Type) and hasattr(typ, "name")):
            raise SchemaError(
                'Expected named types but got "%s" of type %s' % (typ, type(typ))
            )

        name = typ.name
        if name in type_map:
            if typ is not type_map[name]:
                raise SchemaError('Duplicate type "%s"' % name)
            continue

        type_map[name] = typ
        child_types = []

        if isinstance(typ, UnionType):
            child_types.extend(typ.types)

        if isinstance(typ, ObjectType):
            child_types.extend(typ.interfaces)

        if isinstance(typ, (ObjectType, InterfaceType)):
            for field in typ.fields:
                child_types.append(field.type)
                child_types.extend([arg.type for arg in field.args or []])

        if isinstance(typ, InputObjectType):
            for field in typ.fields:
                child_types.append(field.type)

        if isinstance(typ, Directive):
            child_types.extend([arg.type for arg in typ.args or []])

        type_map.update(_build_type_map(child_types, _type_map=type_map))

    return type_map
