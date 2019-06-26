# -*- coding: utf-8 -*-
""" Schema definition. """

from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast

from ..exc import SchemaError, UnknownType
from ..lang import ast as _ast
from .build_type_map import build_type_map
from .directives import SPECIFIED_DIRECTIVES
from .introspection import INTROPSPECTION_TYPES
from .scalars import SPECIFIED_SCALAR_TYPES
from .types import (
    Directive,
    GraphQLAbstractType,
    GraphQLType,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    UnionType,
)
from .validation import validate_schema

_SPECIFIED_DIRECTIVE_NAMES = [t.name for t in SPECIFIED_DIRECTIVES]


Resolver = Callable[..., Any]


class Schema:
    """ A GraphQL schema definition.

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

        nodes: AST node for the schema if applicable, i.e. when creating
            the schema from a GraphQL (SDL) document.

    Attributes:
        query_type (Optional[ObjectType]):
            The root query type for the schema (required).

        mutation_type (Optional[ObjectType]):
            The root mutation type for the schema (optional).

        subscription_type (Optional[ObjectType]):
            The root subscription type for the schema (optional).

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
    )

    def __init__(
        self,
        query_type: Optional[ObjectType] = None,
        mutation_type: Optional[ObjectType] = None,
        subscription_type: Optional[ObjectType] = None,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[NamedType]] = None,
        nodes: Optional[
            List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]
        ] = None,
    ):
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.subscription_type = subscription_type

        self.nodes = (
            nodes or []
        )  # type: List[Union[_ast.SchemaDefinition, _ast.SchemaExtension]]

        self.directives = _build_directive_map(directives or [])

        self.types = build_type_map(
            [query_type, mutation_type, subscription_type, *(types or [])],
            self.directives.values(),
            _type_map=_default_type_map(),
        )

        self._invalidate_and_rebuild_caches()

    def _invalidate_and_rebuild_caches(self):
        self._possible_types = (
            {}
        )  # type: Dict[GraphQLAbstractType, Sequence[ObjectType]]
        self._is_valid = None  # type: Optional[bool]
        self._literal_types_cache = {}  # type: Dict[_ast.Type, GraphQLType]

        self.implementations = defaultdict(
            list
        )  # type: Dict[str, List[ObjectType]]

        for type_ in self.types.values():
            if isinstance(type_, ObjectType):
                for i in type_.interfaces:
                    self.implementations[i.name].append(type_)

    def _replace_types_and_directives(
        self,
        types: Optional[Sequence[NamedType]] = None,
        directives: Optional[Sequence[Directive]] = None,
    ) -> None:
        busted_cache = False

        for new_type in types or ():
            try:
                original_type = self.types[new_type.name]
            except KeyError:
                pass
            else:
                if original_type in SPECIFIED_SCALAR_TYPES:
                    raise SchemaError(
                        "Cannot replace specified type %s" % original_type
                    )
                if type(original_type) != type(new_type):
                    raise SchemaError(
                        "Cannot replace type %r with a different kind of type %r."
                        % (original_type, new_type)
                    )

            busted_cache = new_type != original_type
            self.types[new_type.name] = new_type

        for new_directive in directives or ():
            try:
                original_directive = self.directives[new_directive.name]
            except KeyError:
                pass
            else:
                if original_directive in SPECIFIED_DIRECTIVES:
                    raise SchemaError(
                        "Cannot replace specified directive %s"
                        % original_directive
                    )

            self.directives[new_directive.name] = new_directive

        if busted_cache:
            # Circular import
            from .fix_type_references import fix_type_references

            self._invalidate_and_rebuild_caches()
            fix_type_references(self)

    def validate(self):
        """ Check that the schema is valid.

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
            py_gql.schema.Type: Type instance

        Raises:
            :class:`~py_gql.exc.UnknownType`:
                if ``default`` is not set and the type is not found

        """
        try:
            return self.types[name]
        except KeyError:
            raise UnknownType(name)

    def has_type(self, name: str) -> bool:
        """
        Check if the schema contains a type with the given name.
        """
        return name in self.types

    def get_type_from_literal(self, ast_node: _ast.Type) -> GraphQLType:
        """
        Given an AST node describing a type, return a corresponding
        :class:`py_gql.schema.Type` instance.

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
        self, abstract_type: GraphQLAbstractType
    ) -> Sequence[ObjectType]:
        """
        Get the possible implementations of an abstract type.

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
        self, abstract_type: GraphQLAbstractType, type_: GraphQLType
    ) -> bool:
        """
        Check that ``type_`` is a possible realization of ``abstract_type``.

        Returns: ``True`` if ``type_`` is valid for ``abstract_type``
        """
        if not isinstance(type_, ObjectType):
            return False

        return type_ in self.get_possible_types(abstract_type)

    def is_subtype(self, type_, super_type):
        """
        Provided a type and a super type, return true if the first type is
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
            isinstance(super_type, GraphQLAbstractType)
            and isinstance(type_, ObjectType)
            and self.is_possible_type(super_type, type_)
        )

    def types_overlap(self, rhs: GraphQLType, lhs: GraphQLType) -> bool:
        """
        Provided two composite types, determine if they "overlap". Two
        composite types overlap when the Sets of possible concrete types for
        each intersect.

        This is often used to determine if a fragment of a given type could
        possibly be visited in a context of another type. This function is
        commutative.
        """
        if rhs == lhs:
            return True

        if isinstance(rhs, GraphQLAbstractType) and isinstance(
            lhs, GraphQLAbstractType
        ):
            rhs_types = self.get_possible_types(cast(GraphQLAbstractType, rhs))
            lhs_types = self.get_possible_types(cast(GraphQLAbstractType, lhs))
            return any((t in lhs_types for t in rhs_types))

        return (
            isinstance(rhs, GraphQLAbstractType)
            and self.is_possible_type(cast(GraphQLAbstractType, rhs), lhs)
        ) or (
            isinstance(lhs, GraphQLAbstractType)
            and self.is_possible_type(cast(GraphQLAbstractType, lhs), rhs)
        )

    def to_string(
        self,
        indent: Union[str, int] = 4,
        include_descriptions: bool = True,
        include_introspection: bool = False,
        use_legacy_comment_descriptions: bool = False,
        include_custom_directives: bool = False,
    ) -> str:
        """
        Format the schema as an SDL string.

        Refer to :class:`py_gql.utilities.ASTSchemaPrinter` for details.
        """
        from ..utilities.ast_schema_printer import ASTSchemaPrinter

        return ASTSchemaPrinter(
            indent=indent,
            include_descriptions=include_descriptions,
            include_introspection=include_introspection,
            use_legacy_comment_descriptions=use_legacy_comment_descriptions,
            include_custom_directives=include_custom_directives,
        )(self)

    def assign_resolver(
        self, fieldpath: str, func: Resolver, allow_override: bool = False
    ) -> "Schema":
        """
        Register a resolver against a type in the schema.

        Args:
            fieldpath: Field path in the form ``{Typename}.{Fieldname}``.
            func: The resolver function.
            allow_override:
                By default this function will raise :py:class:`ValueError` if
                the field already has a resolver defined. Set this to ``True``
                to allow overriding.

        Raises:
            :py:class:`ValueError`:

        Warning:
            This will update the type inline and as such is expected to be used
            after having used `py_gql.build_schema`.
        """

        try:
            typename, fieldname = fieldpath.split(".")[:2]
        except ValueError:
            raise ValueError(
                'Invalid field path "%s". Field path must of the form '
                '"{Typename}.{Fieldname}"' % fieldpath
            )

        object_type = self.get_type(typename)

        if not isinstance(object_type, ObjectType):
            raise ValueError(
                'Expected "%s" to be ObjectTye but got %s.'
                % (typename, object_type.__class__.__name__)
            )

        object_type.assign_resolver(
            fieldname, func, allow_override=allow_override
        )

        return self

    def resolver(self, fieldpath: str) -> Callable[[Resolver], Resolver]:
        """
        Decorator version of :meth:`assign_resolver`.

        .. code-block:: python

            schema = ...

            @schema.resolver("Query.foo")
            def resolve_foo(obj, ctx, info):
                return "foo"

        Args:
            fieldpath: Field path in the form ``{Typename}.{Fieldname}``.
        """

        def decorator(func: Resolver) -> Resolver:
            self.assign_resolver(fieldpath, func)
            return func

        return decorator


def _build_directive_map(maybe_directives: List[Any]) -> Dict[str, Directive]:
    directives = {
        d.name: d for d in SPECIFIED_DIRECTIVES
    }  # Dict[str, Directive]

    for value in maybe_directives:
        if not isinstance(value, Directive):
            raise SchemaError(
                'Expected directive but got "%r" of type "%s"'
                % (value, type(value))
            )

        name = value.name

        if name in _SPECIFIED_DIRECTIVE_NAMES:
            if value is not directives[name]:
                raise SchemaError(
                    'Cannot override specified directive "%s"' % name
                )
            continue

        if name in directives:
            if value is not directives[name]:
                raise SchemaError('Duplicate directive "%s"' % name)
            continue

        directives[name] = value

    return directives


def _default_type_map() -> Dict[str, NamedType]:
    types = {}  # type: Dict[str, NamedType]
    types.update({t.name: t for t in SPECIFIED_SCALAR_TYPES})
    types.update({t.name: t for t in INTROPSPECTION_TYPES})
    return types
