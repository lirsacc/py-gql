# -*- coding: utf-8 -*-
""" Schema definition. """

from collections import defaultdict

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
        node=None,
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

        :type node: py_gql.lang.ast.Node
        :param node: AST node for the schema if applicable
        """
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.subscription_type = subscription_type

        self._types = [query_type, mutation_type, subscription_type]
        self._types.append(__Schema__)
        self.node = node

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

    def get_possible_types(self, type_):
        """ Get the possible implementations of an abstract type.

        :type type_: py_gql.schema.types.UnionType|\
            py_gql.schema.types.InterfaceType
        :param type_:
            Abstract type to check.

        :rtype: [py_gql.schema.types.Type]
        :return:
            List of possible implementations.
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
        """ Check that ``possible_type`` is a possible realization of
        ``abstract_type``.

        :type type_: py_gql.schema.types.UnionType|\
            py_gql.schema.types.InterfaceType
        :param type_:
            Abstract type to check against.

        :type possible_type: py_gql.schema.types.Type
        :param possible_type:
            Realization type to check.

        :rtype: bool
        """
        return type_ in self.get_possible_types(abstract_type)

    def is_subtype(self, type_, super_type):
        """ Provided a type and a super type, return true if the first type is
        either equal or a subset of the second super type (covariant).

        :type type_: py_gql.schema.types.Type
        :type super_type: py_gql.schema.types.Type
        :rtype: bool
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
            return any((t in lhs_types for t in rhs_types))

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
