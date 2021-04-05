# -*- coding: utf-8 -*-

import copy
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from ..exc import SchemaError, UnknownType
from ..lang import ast as _ast, print_ast
from .directives import SPECIFIED_DIRECTIVES
from .introspection import INTROPSPECTION_TYPES
from .resolver_map import Resolver, ResolverMap, TypeResolver
from .scalars import SPECIFIED_SCALAR_TYPES
from .types import (
    Directive,
    GraphQLAbstractType,
    GraphQLType,
    InputObjectType,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    UnionType,
    unwrap_type,
)
from .validation import validate_schema


_SPECIFIED_DIRECTIVE_NAMES = [t.name for t in SPECIFIED_DIRECTIVES]
_PROTECTED_TYPES = SPECIFIED_SCALAR_TYPES + INTROPSPECTION_TYPES


class Schema(ResolverMap):
    """
    A GraphQL schema definition.

    A GraphQL schema definition. This is the main container for a GraphQL
    schema and its related types.

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

        description: Schema description.

        nodes: AST node for the schema if applicable, i.e. when creating
            the schema from a GraphQL (SDL) document.

    Attributes:
        query_type (Optional[ObjectType]):
            The root query type for the schema (required).

        mutation_type (Optional[ObjectType]):
            The root mutation type for the schema (optional).

        subscription_type (Optional[ObjectType]):
            The root subscription type for the schema (optional).

        description (Optional[str]): Schema description.

        nodes (List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]):
            AST node for the schema if applicable, i.e. when creating the schema
            from a GraphQL (SDL) document.

        types (Dict[str, GraphQLType]):
            Mapping ``type name -> Type instance`` of all types used in the
            schema, excluding directives.

        directives (Dict[str, py_gql.schema.Directive]):
            Mapping ``directive name -> Directive instance`` of all directives
            used in the schema.

        implementations (Dict[str, ObjectType]):
            Mapping of ``interface name -> [implementing object types]``.
    """

    __slots__ = (
        "description",
        "query_type",
        "mutation_type",
        "subscription_type",
        "nodes",
        "_possible_types",
        "_is_valid",
        "_literal_types_cache",
        "types",
        "directives",
        "implementations",
        "resolvers",
        "subscriptions",
        "default_resolver",
        "default_resolvers",
    )

    def __init__(
        self,
        query_type: Optional[ObjectType] = None,
        mutation_type: Optional[ObjectType] = None,
        subscription_type: Optional[ObjectType] = None,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[NamedType]] = None,
        description: Optional[str] = None,
        nodes: Optional[
            List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]
        ] = None,
    ):
        super().__init__()
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.subscription_type = subscription_type

        self.description = description

        self.nodes = (
            nodes or []
        )  # type: List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]

        self.directives = _build_directive_map(directives or [])

        self.types = _build_type_map(
            [*(types or []), query_type, mutation_type, subscription_type],
            self.directives.values(),
            _type_map=_default_type_map(),
        )  # type: Dict[str, NamedType]

        self._invalidate_and_rebuild_caches()

    def _invalidate_and_rebuild_caches(self):
        self._is_valid: Optional[bool] = None
        self._literal_types_cache: Dict[_ast.Type, GraphQLType] = {}

        self.implementations: Dict[
            str,
            List[Union[ObjectType, InterfaceType]],
        ] = defaultdict(list)

        for type_ in self.types.values():
            if isinstance(type_, (InterfaceType, ObjectType)):
                for i in type_.interfaces:
                    self.implementations[i.name].append(type_)

    def _replace_types_and_directives(
        self,
        types: Optional[Dict[str, Optional[NamedType]]] = None,
        directives: Optional[Dict[str, Optional[Directive]]] = None,
    ) -> None:
        busted_cache = False

        for type_name, new_type in (types or {}).items():
            try:
                original_type = self.types[type_name]
            except KeyError:
                pass
            else:
                if original_type in _PROTECTED_TYPES:
                    raise SchemaError(
                        f"Cannot replace specified type {original_type}",
                    )

                busted_cache = new_type != original_type

                if new_type is None:
                    del self.types[type_name]
                else:
                    if type(original_type) != type(new_type):
                        raise SchemaError(
                            "Cannot replace type %r with a different kind of type %r."
                            % (original_type, new_type),
                        )
                    self.types[type_name] = new_type

        for directive_name, new_directive in (directives or {}).items():
            try:
                original_directive = self.directives[directive_name]
            except KeyError:
                pass
            else:
                if original_directive in SPECIFIED_DIRECTIVES:
                    raise SchemaError(
                        f"Cannot replace specified directive {original_directive}",
                    )

            if new_directive is None:
                del self.directives[directive_name]
            else:
                self.directives[directive_name] = new_directive

        # We can safely ignore the potential type error given that if the type
        # has been replaced we have checked it matches its old kind above.
        self.query_type = (
            self.types.get(self.query_type.name)  # type: ignore
            if self.query_type
            else None
        )

        self.mutation_type = (
            self.types.get(self.mutation_type.name)  # type: ignore
            if self.mutation_type
            else None
        )

        self.subscription_type = (
            self.types.get(self.subscription_type.name)  # type: ignore
            if self.subscription_type
            else None
        )

        if busted_cache:
            # Circular import
            from .fix_type_references import fix_type_references

            fix_type_references(self)
            self._invalidate_and_rebuild_caches()

    def validate(self):
        """
        Check that the schema is valid.

        Raises:
            :class:`~py_gql.exc.SchemaError` if the schema is invalid.
        """
        if self._is_valid is None:
            validate_schema(self)
            self._is_valid = True

    def get_type(self, name: str) -> NamedType:
        """
        Get a type by name.

        Args:
            name: Requested type name

        Returns:
            py_gql.schema.NamedType: Type instance

        Raises:
            UnknownType: if ``default`` is not set and the type is not found.

        """
        try:
            return self.types[name]
        except KeyError:
            raise UnknownType(name)

    def get_type_from_literal(self, ast_node: _ast.Type) -> GraphQLType:
        """
        Return a :class:`py_gql.schema.Type` instance for an AST type node.

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
        raise TypeError(f"Invalid type node {ast_node!r}")

    def get_possible_types(
        self,
        abstract_type: GraphQLAbstractType,
    ) -> Sequence[Union[InterfaceType, ObjectType]]:
        """
        Get the possible implementations of an abstract type.

        Args:
            abstract_type: Abstract type to check.

        Raises:
            TypeError: when the input type is not an abstract type.

        Returns:
            List of possible types.

        """
        if isinstance(abstract_type, UnionType):
            return abstract_type.types or []
        elif isinstance(abstract_type, InterfaceType):
            return self.implementations.get(abstract_type.name, [])

        raise TypeError(f"Not an abstract type: {abstract_type}")

    def is_possible_type(
        self,
        abstract_type: GraphQLAbstractType,
        type_: GraphQLType,
    ) -> bool:
        """
        Check that ``type_`` is a possible realization of ``abstract_type``.

        Returns: ``True`` if ``type_`` is valid for ``abstract_type``
        """
        if not isinstance(type_, (InterfaceType, ObjectType)):
            return False

        return type_ in self.get_possible_types(abstract_type)

    def is_subtype(self, type_: GraphQLType, super_type: GraphQLType) -> bool:
        """
        Check if a type is either equal or a subset of a super type (covariant).

        Args:
            type_ (py_gql.schema.GraphQLType): Target type.
            super_type (py_gql.schema.GraphQLType): Super type.

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
            isinstance(
                super_type,
                GraphQLAbstractType,
            )
            and self.is_possible_type(super_type, type_)
        )

    def types_overlap(self, rhs: GraphQLType, lhs: GraphQLType) -> bool:
        """
        Determine if two composite types "overlap".

        Two composite types overlap when the Sets of possible concrete types for
        each intersect.

        This is often used to determine if a fragment of a given type could
        possibly be visited in a context of another type. This function is
        commutative.
        """
        if rhs == lhs:
            return True

        if isinstance(rhs, GraphQLAbstractType) and isinstance(
            lhs,
            GraphQLAbstractType,
        ):
            rhs_types = self.get_possible_types(rhs)
            lhs_types = self.get_possible_types(lhs)
            return any((t in lhs_types for t in rhs_types))

        return (
            isinstance(rhs, GraphQLAbstractType)
            and self.is_possible_type(rhs, lhs)
        ) or (
            isinstance(lhs, GraphQLAbstractType)
            and self.is_possible_type(lhs, rhs)
        )

    def to_string(
        self,
        indent: Union[str, int] = 4,
        include_descriptions: bool = True,
        include_introspection: bool = False,
        include_custom_schema_directives: bool = False,
    ) -> str:
        """
        Format the schema as an SDL string.
        """
        from ..sdl import ASTSchemaConverter

        return print_ast(
            ASTSchemaConverter(
                include_introspection=include_introspection,
                include_custom_schema_directives=include_custom_schema_directives,
            )(self),
            indent=indent,
            include_descriptions=include_descriptions,
        )

    def register_default_resolver(
        self,
        typename: str,
        resolver: Resolver,
        *,
        allow_override: bool = False,
    ) -> None:
        super().register_default_resolver(
            typename,
            resolver,
            allow_override=allow_override,
        )

        try:
            object_type = self.types[typename]
        except KeyError:
            raise UnknownType(typename)

        if not isinstance(object_type, ObjectType):
            raise SchemaError(
                'Cannot assign default resolver to %s "%s".'
                % (object_type.__class__.__name__, typename),
            )

        if object_type.default_resolver and not allow_override:
            raise ValueError(
                f'Type "{typename}" already has a default resolver.',
            )

        object_type.default_resolver = resolver
        # Invalidate validation
        self._is_valid = None

    def register_resolver(
        self,
        typename: str,
        fieldname: str,
        resolver: Resolver,
        *,
        allow_override: bool = False,
    ) -> None:
        super().register_resolver(
            typename,
            fieldname,
            resolver,
            allow_override=allow_override,
        )

        try:
            object_type = self.types[typename]
        except KeyError:
            raise UnknownType(typename)

        if not isinstance(object_type, ObjectType):
            raise SchemaError(
                'Cannot assign resolver to %s "%s".'
                % (object_type.__class__.__name__, typename),
            )

        if fieldname == "*":
            return

        try:
            field = object_type.field_map[fieldname]
        except KeyError:
            raise SchemaError(
                f'Cannot assign resolver to unknown field "{typename}.{fieldname}".',
            )

        if (
            field.resolver is not None
            and not allow_override
            and field.resolver is not resolver
        ):
            raise ValueError(
                f'Field "{fieldname}" of type "{typename}" already has a resolver.',
            )

        field.resolver = resolver
        # Invalidate validation
        self._is_valid = None

    def register_subscription(
        self,
        typename: str,
        fieldname: str,
        resolver: Resolver,
        *,
        allow_override: bool = False,
    ) -> None:
        super().register_subscription(
            typename,
            fieldname,
            resolver,
            allow_override=allow_override,
        )

        try:
            object_type = self.types[typename]
        except KeyError:
            raise UnknownType(typename)

        if not isinstance(object_type, ObjectType):
            raise SchemaError(
                "Cannot assign subscription to "
                f'{object_type.__class__.__name__} "{typename}".',
            )

        try:
            field = object_type.field_map[fieldname]
        except KeyError:
            raise SchemaError(
                "Cannot assign subscription to unknown field"
                f'"{typename}.{fieldname}".',
            )

        if (
            field.subscription_resolver is not None
            and not allow_override
            and field.subscription_resolver is not resolver
        ):
            raise ValueError(
                f'Field "{fieldname}" of type "{typename}" already has a subscription.',
            )

        field.subscription_resolver = resolver
        # Invalidate validation
        self._is_valid = None

    def register_type_resolver(
        self,
        typename: str,
        resolver: TypeResolver,
        *,
        allow_override: bool = False,
    ) -> None:
        super().register_type_resolver(
            typename,
            resolver,
            allow_override=allow_override,
        )

        try:
            abstract_type = self.types[typename]
        except KeyError:
            raise UnknownType(typename)

        if not isinstance(abstract_type, GraphQLAbstractType):
            raise SchemaError(
                'Cannot assign type resolver to %s "%s".'
                % (abstract_type.__class__.__name__, typename),
            )

        abstract_type.resolve_type = resolver

    def clone(self) -> "Schema":
        cloned = Schema(
            query_type=self.query_type,
            mutation_type=self.mutation_type,
            subscription_type=self.subscription_type,
            nodes=self.nodes,
        )

        cloned._replace_types_and_directives(
            types={
                t.name: copy.copy(t)
                for t in self.types.values()
                if (
                    t not in SPECIFIED_SCALAR_TYPES
                    and t not in INTROPSPECTION_TYPES
                )
            },
            directives={
                d.name: copy.copy(d)
                for d in self.directives.values()
                if d not in SPECIFIED_DIRECTIVES
            },
        )

        cloned.merge_resolvers(self)

        return cloned


def _build_directive_map(maybe_directives: List[Any]) -> Dict[str, Directive]:
    directives = {
        d.name: d for d in SPECIFIED_DIRECTIVES
    }  # Dict[str, Directive]

    for value in maybe_directives:
        if not isinstance(value, Directive):
            raise SchemaError(
                f'Expected directive but got "{value!r}" of type "{type(value)}"',
            )

        name = value.name

        if name in _SPECIFIED_DIRECTIVE_NAMES:
            if value is not directives[name]:
                raise SchemaError(
                    f'Cannot override specified directive "{name}"',
                )
            continue

        if name in directives:
            if value is not directives[name]:
                raise SchemaError(f'Duplicate directive "{name}"')
            continue

        directives[name] = value

    return directives


def _default_type_map() -> Dict[str, NamedType]:
    types = {}  # type: Dict[str, NamedType]
    types.update({t.name: t for t in SPECIFIED_SCALAR_TYPES})
    types.update({t.name: t for t in INTROPSPECTION_TYPES})
    return types


def _build_type_map(
    types: Iterable[Optional[GraphQLType]],
    directives: Optional[Iterable[Directive]] = None,
    _type_map: Optional[Dict[str, NamedType]] = None,
) -> Dict[str, NamedType]:
    type_map = (
        _type_map if _type_map is not None else {}
    )  # type: Dict[str, NamedType]

    for type_ in types:

        if type_ is None:
            continue

        child_types = []  # type: List[GraphQLType]

        inner_type = unwrap_type(type_)

        if not isinstance(inner_type, NamedType):
            raise SchemaError(
                f'Expected NamedType but got "{inner_type}" of type {type(inner_type)}',
            )

        name = inner_type.name

        if name in type_map:
            if inner_type is not type_map[name]:
                raise SchemaError(f'Duplicate type "{name}"')
            continue

        type_map[name] = inner_type

        if isinstance(inner_type, UnionType):
            child_types.extend(inner_type.types)

        if isinstance(inner_type, ObjectType):
            child_types.extend(inner_type.interfaces)

        if isinstance(inner_type, (ObjectType, InterfaceType)):
            for field in inner_type.fields:
                child_types.append(field.type)
                child_types.extend([arg.type for arg in field.arguments or []])

        if isinstance(inner_type, InputObjectType):
            for input_field in inner_type.fields:
                child_types.append(input_field.type)

        type_map.update(_build_type_map(child_types, _type_map=type_map))

    if directives:
        directive_types = []  # type: List[GraphQLType]
        for directive in directives:
            directive_types.extend(
                [arg.type for arg in directive.arguments or []],
            )

        type_map.update(_build_type_map(directive_types, _type_map=type_map))

    return type_map
