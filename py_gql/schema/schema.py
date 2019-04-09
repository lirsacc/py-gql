# -*- coding: utf-8 -*-
""" Schema definition. """

import itertools as it
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from ..exc import SchemaError, UnknownType
from ..lang import ast as _ast
from .directives import SPECIFIED_DIRECTIVES
from .introspection import __Schema__
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
        types: Optional[List[GraphQLType]] = None,
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

        _types = [
            x
            for x in (query_type, mutation_type, subscription_type)
            if x is not None
        ]  # type: List[GraphQLType]

        _types.append(__Schema__)
        _types.extend(list(SPECIFIED_SCALAR_TYPES))

        if types:
            _types.extend(types)

        _directives = []  # type: List[Directive]
        if directives:
            _directives.extend(directives)

        _directive_names = set(
            d.name for d in _directives if isinstance(d, Directive)
        )

        for d in SPECIFIED_DIRECTIVES:
            if d.name not in _directive_names:
                _directives.append(d)

        self._possible_types = (
            {}
        )  # type: Dict[Union[UnionType, InterfaceType], List[ObjectType]]
        self._is_valid = None  # type: Optional[bool]
        self._literal_types_cache = {}  # type: Dict[_ast.Type, GraphQLType]

        self.types, self.directives = _build_type_maps(_types, _directives)
        self._invalidate_and_rebuild_caches()

    def _invalidate_and_rebuild_caches(self):
        self.implementations = defaultdict(
            list
        )  # type: Dict[str, List[ObjectType]]

        for type_ in self.types.values():
            if isinstance(type_, ObjectType):
                for i in type_.interfaces:
                    self.implementations[i.name].append(type_)

        self._is_valid = None

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
        self, abstract_type: Union[UnionType, InterfaceType]
    ) -> List[ObjectType]:
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
        self, abstract_type: Union[UnionType, InterfaceType], type_: GraphQLType
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
            is_abstract_type(super_type)
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

    def to_string(
        self,
        indent: Union[str, int] = 4,
        include_descriptions: bool = True,
        include_introspection: bool = False,
        use_legacy_comment_descriptions: bool = False,
    ) -> str:
        """
        Format the schema as an SDL string.

        Args:
            indent:
                Indent character or number of spaces

            include_descriptions:
                If ``True`` include descriptions in the output

            use_legacy_comment_descriptions:
                Control how descriptions are formatted.

                Set to ``True`` for the old standard (use comments) which will be
                compatible with most GraphQL parsers while the default settings is
                to use block strings and is part of the most recent specification.

            include_introspection:
                If ``True``, include introspection types in the output
        """
        from ..utilities.ast_schema_printer import ASTSchemaPrinter

        return ASTSchemaPrinter(
            indent=indent,
            include_descriptions=include_descriptions,
            include_introspection=include_introspection,
            use_legacy_comment_descriptions=use_legacy_comment_descriptions,
        )(self)

    def assign_resolver(
        self,
        fieldpath: str,
        func: Callable[..., Any],
        allow_override: bool = False,
    ) -> None:
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

        def decorator(func):
            self.assign_resolver(fieldpath, func)
            return func

        return decorator


def _build_type_maps(
    # fmt: off
    *types: Sequence[GraphQLType],
    _type_map: Optional[Dict[str, NamedType]] = None
    # fmt: on
) -> Tuple[Dict[str, NamedType], Dict[str, Directive]]:
    """
    Recursively build a mapping name <> Type from a list of types to include
    all referenced types.

    Warning:
        This will flatten all lazy type definitions and attributes.

    Args:
        types: List of types
        _type_map: Pre-built type map (used for recursive calls)
    """
    type_map = (
        _type_map if _type_map is not None else {}
    )  # type: Dict[str, NamedType]

    directive_map = {}  # type: Dict[str, Directive]

    for type_ in it.chain(*types):
        if not type_:
            continue

        child_types = []  # type: List[GraphQLType]

        if isinstance(type_, Directive):
            # Directives cannot be referenced outside of the first call in the
            # recursion.
            child_types.extend([arg.type for arg in type_.arguments or []])
            directive_map[type_.name] = type_
        else:
            type_ = cast(NamedType, unwrap_type(type_))

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

            if isinstance(type_, UnionType):
                child_types.extend(type_.types)

            if isinstance(type_, ObjectType):
                child_types.extend(type_.interfaces)

            if isinstance(type_, (ObjectType, InterfaceType)):
                for field in type_.fields:
                    child_types.append(field.type)
                    child_types.extend(
                        [arg.type for arg in field.arguments or []]
                    )

            if isinstance(type_, InputObjectType):
                for input_field in type_.fields:
                    child_types.append(input_field.type)

        type_map.update(_build_type_maps(child_types, _type_map=type_map)[0])

    return type_map, directive_map
