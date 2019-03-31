# -*- coding: utf-8 -*-
""" Schema definition. """

import itertools as it
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast

from ..exc import SchemaError, UnknownType
from ..lang import ast as _ast
from .directives import SPECIFIED_DIRECTIVES
from .introspection import __Schema__
from .printer import SchemaPrinter
from .scalars import SPECIFIED_SCALAR_TYPES
from .types import (
    Directive,
    GraphQLType,
    InputObjectType,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    UnionType,
    is_abstract_type,
    unwrap_type,
)
from .validation import validate_schema

_UNSET_NAMED_TYPE = NamedType()


class Schema(object):
    """ A GraphQL schema definition.

    This is the main container for a GraphQL schema and its related types.

    Args:
        query_type: The root query type for the schema
        mutation_type: The root mutation type for the schema
        subscription_type: The root subscription type for the schema

        directives: List of possible directives to use.
            The default, specified directives (``@include``, ``@skip``) will
            **always** be included.

        types: List of additional supported types.
            This only necessary for types that cannot be inferred by traversing
            the root types.

        nodes: AST node for the schema if applicable, i.e. when creating
            the schema from a GraphQL (SDL) document.

    Attributes:
        query_type: The root query type for the schema (required)

        mutation_type: The root mutation type for the schema (optional)

        subscription_type: The root subscription type for the schema (optional)

        node: AST node for the schema if applicable, i.e. when creating the
            schema from a GraphQL (SDL) document.

        type_map: Mapping ``type name -> Type instance`` of all types used in
            the schema, including directives.

        types: Mapping ``type name -> Type instance`` of all types used in the
            schema, excluding directives.

        directives: Mapping ``directive name -> Directive instance`` of all
            directives used in the schema.

        implementations: Mapping of ``interface name -> [implementing object types]``.
    """

    def __init__(
        self,
        query_type: Optional[ObjectType] = None,
        mutation_type: Optional[ObjectType] = None,
        subscription_type: Optional[ObjectType] = None,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[GraphQLType]] = None,
        nodes: Optional[
            List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]
        ] = None,
    ):
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.subscription_type = subscription_type

        self._types = [
            x
            for x in (query_type, mutation_type, subscription_type)
            if x is not None
        ]  # type: List[GraphQLType]
        self._types.append(__Schema__)
        self.nodes = (
            nodes or []
        )  # type: List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]

        # NOTE: This is the notion of the specified types being always
        # available. As a result of this line, intropection queries will always
        # include thes types even if they are not actively used in the schema.
        # I am not totally sure if this is the right behaviour and it may
        # change in the future.
        self._types.extend(list(SPECIFIED_SCALAR_TYPES))

        if types:
            self._types.extend(types)

        self._directives = []  # type: List[Directive]
        if directives:
            self._directives.extend(directives)

        _directive_names = set(
            d.name for d in self._directives if isinstance(d, Directive)
        )

        for d in SPECIFIED_DIRECTIVES:
            if d.name not in _directive_names:
                self._directives.append(d)

        self._possible_types = (
            {}
        )  # type: Dict[Union[UnionType, InterfaceType], List[ObjectType]]
        self._is_valid = None  # type: Optional[bool]
        self._literal_types_cache = {}  # type: Dict[_ast.Type, GraphQLType]

        self.type_map = _build_type_map(self._types, self._directives)
        self._rebuild_caches()

    def _rebuild_caches(self):
        self.types = {
            name: t
            for name, t in self.type_map.items()
            if not isinstance(t, Directive)
        }  # type: Dict[str, NamedType]

        self.directives = {
            name: t
            for name, t in self.type_map.items()
            if isinstance(t, Directive)
        }

        self.implementations = defaultdict(
            list
        )  # type: Dict[str, List[ObjectType]]

        for type_ in self.types.values():
            if isinstance(type_, ObjectType):
                for i in type_.interfaces:
                    self.implementations[i.name].append(type_)

        self._is_valid = None

    def validate(self):
        """ Check that the schema is valid and cache the result.

        Raises:
            :class:`~py_gql.exc.SchemaError` if the schema is invalid.
        """
        validate_schema(self)

    @property
    def is_valid(self) -> bool:
        if self._is_valid is None:
            try:
                self.validate()
            except SchemaError:
                self._is_valid = False
            else:
                self._is_valid = True
        return self._is_valid

    def get_type(
        self, name: str, default: NamedType = _UNSET_NAMED_TYPE
    ) -> GraphQLType:
        """ Get a type by name.

        Args:
            name: Requested type name
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
            if default is not _UNSET_NAMED_TYPE:
                return default
            raise UnknownType(name)

    def has_type(self, name: str) -> bool:
        try:
            self.types[name]
        except KeyError:
            return False
        else:
            return True

    def get_type_from_literal(self, ast_node: _ast.Type) -> GraphQLType:
        """ Given an AST node describing a type, return a
        corresponding :class:`py_gql.schema.Type` instance.

        For example, if provided the parsed AST node for ``[User]``,
        a :class:`py_gql.schema.ListType` instance will be returned, containing
        the type called ``User`` found in the schema.
        If a type called ``User`` is not found in the schema, then
        :class:`~py_gql.exc.UnknownType` will be raised.

        Raises:
            :class:`~py_gql.exc.UnknownType`: if  any named type is not found
        """
        if ast_node in self._literal_types_cache:
            return self._literal_types_cache[ast_node]

        if isinstance(ast_node, _ast.ListType):
            t1 = ListType(self.get_type_from_literal(ast_node.type))
            self._literal_types_cache[ast_node] = t1
            return t1
        elif isinstance(ast_node, _ast.NonNullType):
            t2 = NonNullType(self.get_type_from_literal(ast_node.type))
            self._literal_types_cache[ast_node] = t2
            return t2
        elif isinstance(ast_node, _ast.NamedType):
            t3 = self.get_type(ast_node.name.value)
            self._literal_types_cache[ast_node] = t3
            return t3
        raise TypeError("Invalid type node %r" % ast_node)

    def get_possible_types(
        self, abstract_type: Union[UnionType, InterfaceType]
    ) -> List[ObjectType]:
        """ Get the possible implementations of an abstract type.

        Args:
            type_: Abstract type to check.

        Returns: List of possible implementations.
        """
        if abstract_type in self._possible_types:
            return self._possible_types[abstract_type]

        if isinstance(abstract_type, UnionType):
            self._possible_types[abstract_type] = abstract_type.types or []
            return self._possible_types[abstract_type]
        elif isinstance(abstract_type, InterfaceType):
            self._possible_types[abstract_type] = self.implementations.get(
                abstract_type.name, []
            )
            return self._possible_types[abstract_type]

        raise TypeError("Not an abstract type: %s" % abstract_type)

    def is_possible_type(
        self, abstract_type: Union[UnionType, InterfaceType], type_: GraphQLType
    ) -> bool:
        """ Check that ``type_`` is a possible realization of ``abstract_type``.

        Returns: ``True`` if ``type_`` is valid for ``abstract_type``
        """
        if not isinstance(type_, ObjectType):
            return False
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
            isinstance(type_, (ListType, NonNullType))
            and isinstance(super_type, (ListType, NonNullType))
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

    def types_overlap(self, rhs: GraphQLType, lhs: GraphQLType) -> bool:
        """ Provided two composite types, determine if they "overlap". Two
        composite types overlap when the Sets of possible concrete types for
        each intersect.

        This is often used to determine if a fragment of a given type could
        possibly be visited in a context of another type. This function is
        commutative.
        """
        if rhs == lhs:
            return True

        if is_abstract_type(rhs) and is_abstract_type(lhs):
            rhs_types = self.get_possible_types(
                cast(Union[UnionType, InterfaceType], rhs)
            )
            lhs_types = self.get_possible_types(
                cast(Union[UnionType, InterfaceType], lhs)
            )
            return any((t in lhs_types for t in rhs_types))

        return (
            is_abstract_type(rhs)
            and self.is_possible_type(
                cast(Union[UnionType, InterfaceType], rhs), lhs
            )
        ) or (
            is_abstract_type(lhs)
            and self.is_possible_type(
                cast(Union[UnionType, InterfaceType], lhs), rhs
            )
        )

    def to_string(self, **kwargs: Any) -> str:
        """ Format the schema as an SDL string.

        All arguments are forwarded to :cls:`SchemaPrinter`.
        """
        return SchemaPrinter(**kwargs)(self)

    def assign_resolver(
        self,
        fieldpath: str,
        func: Callable[..., Any],
        allow_override: bool = False,
    ) -> None:
        """ Register a resolver against a type in the schema

        Warning:
            This will update the type inline and as such is expected to be used
            after having used `py_gql.build_schema`.
        """

        try:
            typename, fieldname = fieldpath.split(".")[:2]
        except ValueError:
            raise ValueError(
                'Invalid field path "%s". Field path must of the form "Typename.Fieldname"'
                % fieldpath
            )

        object_type = self.get_type(typename)

        if not isinstance(object_type, ObjectType):
            raise ValueError(
                'Expected "%s" to be ObjectTye but got %s.'
                % (typename, object_type.__class__.__name__)
            )

        try:
            field = object_type.field_map[fieldname]
        except KeyError:
            raise ValueError(
                'Unknown field "%s" for type "%s".' % (fieldname, typename)
            )
        else:
            if (not allow_override) and field.resolver is not None:
                raise ValueError(
                    'Field "%s" of type "%s" already has a resolver.'
                    % (fieldname, typename)
                )

            field.resolver = func or field.resolver

    def resolver(self, fieldpath):
        """ Decorator version of `assign_resolver`. """

        def decorator(func):
            self.assign_resolver(fieldpath, func)
            return func

        return decorator


def _build_type_map(
    *types: Sequence[GraphQLType],
    _type_map: Optional[Dict[str, GraphQLType]] = None
) -> Dict[str, GraphQLType]:
    """ Recursively build a mapping name <> Type from a list of types to include
    all referenced types.

    Warning:
        This will flatten all lazy type definitions and attributes.

    Args:
        types: List of types
        _type_map: Pre-built type map (used for recursive calls)
    """
    type_map = (
        _type_map if _type_map is not None else {}
    )  # type: Dict[str, GraphQLType]

    for type_ in it.chain(*types):
        if not type_:
            continue

        type_ = unwrap_type(type_)

        if not isinstance(type_, NamedType):
            raise SchemaError(
                'Expected NamedType but got "%s" of type %s'
                % (type_, type(type_))
            )

        name = type_.name
        if name in type_map:
            if type_ is not type_map[name]:
                raise SchemaError('Duplicate type "%s"' % name)
            continue

        type_map[name] = type_
        child_types = []  # type: List[GraphQLType]

        if isinstance(type_, UnionType):
            child_types.extend(type_.types)

        if isinstance(type_, ObjectType):
            child_types.extend(type_.interfaces)

        if isinstance(type_, (ObjectType, InterfaceType)):
            for field in type_.fields:
                child_types.append(field.type)
                child_types.extend([arg.type for arg in field.arguments or []])

        if isinstance(type_, InputObjectType):
            for input_field in type_.fields:
                child_types.append(input_field.type)

        if isinstance(type_, Directive):
            child_types.extend([arg.type for arg in type_.arguments or []])

        type_map.update(_build_type_map(child_types, _type_map=type_map))

    return type_map
