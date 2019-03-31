# -*- coding: utf-8 -*-
"""
Since the June 2018 version of the specification, SDL documents are officially
supported and provide with a language agnostic way of defining schemas. The
:mod:`py_gql.schema.build` module exposes the related utilities.
"""

import collections
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from ..._utils import nested_key
from ...exc import ExtensionError, SDLError
from ...lang import ast as _ast, parse
from .. import types as _types
from ..schema import GraphQLType, NamedType, ObjectType, Schema
from .type_builder import TypesBuilder
from .visitors import (
    HealSchemaVisitor,
    SchemaDirective,
    SchemaDirectivesApplicationVisitor,
)

__all__ = (
    "build_schema_from_ast",
    "extend_schema",
    "build_schema",
    "SchemaDirective",
)

ResolverMap = Union[
    Mapping[str, Callable[..., Any]],
    Mapping[str, Mapping[str, Callable[..., Any]]],
    Callable[[str, str], Callable[..., Any]],
]


def build_schema(
    document: Union[_ast.Document, str],
    resolvers: Optional[ResolverMap] = None,
    additional_types: Optional[List[NamedType]] = None,
    schema_directives: Optional[Mapping[str, Type[SchemaDirective]]] = None,
    assume_valid: bool = False,
) -> Schema:
    """ Build an executable schema from a GraphQL document.

    This includes:

        - Generating types from their definitions
        - Applying schema and type extensions
        - Applying schema directives

    Args:
        document (Union[str, py_gql.lang.ast.Document]): SDL document

        resolvers: Field resolvers
            If a `dict` is provided, this looks for the resolver at key
            `{type_name}.{field_name}`. If a callable is provided, this calls
            it with the `{type_name}.{field_name}` argument and use the return
            value if it is itself a callable.

        additional_types: User supplied list of types
            Use this to specify some custom implementation for scalar, enums,
            etc.
            - In case of object types, interfaces, etc. the supplied type will
            override the extracted type without checking for compatibility.
            - Extension will be applied to these types. As a result, the
            resulting types may not be the same objects that were provided,
            so users should not rely on type identity.

        schema_directives: Schema directive classes
            - Members must be subclasses of :class:`SchemaDirective`
            - Members must define a non-null ``definition`` attribute or the
            corresponding definition must be present in the document

        assume_valid: Do not validate intermediate schemas

    Returns:
        Executable schema

    Raises:
        py_gql.exc.SDLError:
    """
    ast = _document_ast(document)
    schema = build_schema_from_ast(
        ast, resolvers=resolvers, additional_types=additional_types
    )

    if not assume_valid:
        schema.validate()

    schema = extend_schema(
        schema,
        ast,
        resolvers=resolvers,
        additional_types=additional_types,
        strict=False,
    )

    if not assume_valid:
        schema.validate()

    if schema_directives:

        schema = HealSchemaVisitor(
            SchemaDirectivesApplicationVisitor(
                dict(schema.directives), schema_directives, strict=True
            ).visit_schema(schema)
        )()

        if not assume_valid:
            schema.validate()

    return schema


def build_schema_from_ast(
    document: Union[_ast.Document, str],
    resolvers: Optional[ResolverMap] = None,
    additional_types: Optional[List[NamedType]] = None,
) -> Schema:
    """ Build an executable schema from an SDL-based schema definition ignoring
    extensions.

    Args:
        document: SDL document

        resolvers: Field resolvers
            If a `dict` is provided, this looks for the resolver at key
            `{type_name}.{field_name}`. If a callable is provided, this calls
            it with the `{type_name}.{field_name}` argument and use the return
            value if it is itself a callable.

        additional_types: User supplied list of types
            Use this to specify some custom implementation for scalar, enums,
            etc.
            - In case of object types, interfaces, etc. the supplied type will
            override the extracted type without checking for compatibility.
            - Extension will be applied to these types. As a result, the
            resulting types may not be the same objects that were provided,
            so users should not rely on type identity.

    Returns:
        Executable schema

    Raises:
        py_gql.exc.SDLError:
    """
    ast = _document_ast(document)
    schema_def, type_defs, directive_defs = _collect_definitions(ast)

    builder = TypesBuilder(
        type_defs,
        directive_defs,
        {},
        additional_types=(
            _merge_type_maps(additional_types) if additional_types else None
        ),
    )

    directives = [
        builder.build_directive(directive_def)
        for directive_def in directive_defs.values()
    ]

    types = [builder.build_type(type_def) for type_def in type_defs.values()]

    if resolvers is not None:
        _assign_resolvers(types, resolvers)

    if schema_def is None:
        operations = {
            t.name.lower(): t
            for t in types
            if (
                isinstance(t, ObjectType)
                and t.name in ("Query", "Mutation", "Subscription")
            )
        }
    else:
        operations = {}
        for op_def in schema_def.operation_types:
            op = op_def.operation
            if op in operations:
                raise SDLError(
                    "Schema must only define a single %s operation" % op,
                    [schema_def, op_def],
                )
            operations[op] = cast(ObjectType, builder.build_type(op_def.type))

    return Schema(
        query_type=operations.get("query"),
        mutation_type=operations.get("mutation"),
        subscription_type=operations.get("subscription"),
        types=types,
        directives=directives,
        nodes=[schema_def] if schema_def else None,
    )


def extend_schema(
    schema: Schema,
    document: Union[_ast.Document, str],
    resolvers: Optional[ResolverMap] = None,
    additional_types: Optional[List[NamedType]] = None,
    strict: bool = True,
) -> Schema:
    """ Extend an existing Schema according to a GraphQL document (adding new
    types and directives + extending known types).

    Warning:

        Specified types cannot be replace or extended.

    Args:
        schema (py_gql.schema.Schema): Executable schema

        document (Union[str, _ast.Document]): SDL document

        resolvers (Union[dict, callable]): Field resolvers
            If a `dict` is provided, this looks for the resolver at key
            `{type_name}.{field_name}`. If a callable is provided, this calls
            it with the `{type_name}.{field_name}` argument and use the return
            value if it is itself a callable.

        additional_types (List[py_gql.schema.Type]): User supplied list of types
            Use this to specify some custom implementation for scalar, enums,
            etc.
            - In case of object types, interfaces, etc. the supplied type will
            override the extracted type without checking for compatibility.
            - Extension will be applied to these types. As a result, the
            resulting types may not be the same objects that were provided,
            so users should not rely on type identity.

        strict (bool): Enable strict mode.
            In strict mode, unknown extension targets, overriding type and
            overriding the schema definition will raise an
            :class:`ExtensionError`. Disable strict mode will silently ignore
            such errors.

    Returns:
        py_gql.schema.Schema: Executable schema

    Raises:
        py_gql.exc.SDLError:

    """
    ast = _document_ast(document)

    schema_exts, type_defs, directive_defs, type_exts = _collect_extensions(
        schema, ast, strict=strict
    )

    if not (
        schema_exts
        or (set(type_defs.keys()) - set(schema.types.keys()))
        or type_exts
        or (set(directive_defs.keys()) - set(schema.directives.keys()))
    ):
        return schema

    builder = TypesBuilder(
        type_defs,
        directive_defs,
        type_exts,
        additional_types=_merge_type_maps(schema.types, additional_types or []),
    )

    directives = [
        builder.extend_directive(d) for d in schema.directives.values()
    ] + [
        builder.extend_directive(builder.build_directive(d))
        for d in directive_defs.values()
    ]

    types = [
        builder.extend_type(t)
        for t in schema.types.values()
        if t.name in type_exts
    ] + [
        builder.extend_type(builder.build_type(t))
        for t in type_defs.values()
        if t.name.value not in schema.types
    ]

    if resolvers:
        _assign_resolvers(types, resolvers)

    def _extend_or(maybe_type):
        return builder.extend_type(maybe_type) if maybe_type else None

    operation_types = dict(
        query=_extend_or(schema.query_type),
        mutation=_extend_or(schema.mutation_type),
        subscription=_extend_or(schema.subscription_type),
    )

    for ext in schema_exts:
        for op_def in ext.operation_types:
            op = op_def.operation
            if operation_types.get(op) is not None:
                raise ExtensionError(
                    "Schema must only define a single %s operation" % op,
                    [ext, op_def],
                )
            operation_types[op] = builder.extend_type(
                builder.build_type(op_def.type)
            )

    return Schema(
        query_type=operation_types["query"],
        mutation_type=operation_types["mutation"],
        subscription_type=operation_types["subscription"],
        types=types,
        directives=directives,
        nodes=(schema.nodes or []) + (schema_exts or []),  # type: ignore
    )


def _collect_definitions(
    document: _ast.Document
) -> Tuple[
    Optional[_ast.SchemaDefinition],
    Dict[str, _ast.TypeDefinition],
    Dict[str, _ast.DirectiveDefinition],
]:
    schema_definition = None
    types = {}  # type: Dict[str, _ast.TypeDefinition]
    directives = {}  # type: Dict[str, _ast.DirectiveDefinition]

    for node in document.definitions:
        if isinstance(node, _ast.SchemaDefinition):
            if schema_definition is not None:
                raise SDLError(
                    "More than one schema definition in document", [node]
                )
            schema_definition = node

        elif isinstance(node, _ast.TypeDefinition):
            name = node.name.value
            if name in types:
                raise SDLError("Duplicate type %s" % name, [node])
            types[name] = node

        elif isinstance(node, _ast.DirectiveDefinition):
            name = node.name.value
            if name in directives:
                raise SDLError("Duplicate directive @%s" % name, [node])
            directives[name] = node

    return schema_definition, types, directives


def _assign_resolvers(types: List[GraphQLType], resolvers: ResolverMap) -> None:

    if callable(resolvers):
        infer = lambda parent, field: resolvers(parent.name, field.name)
    elif isinstance(resolvers, dict):
        infer = lambda parent, field: (
            cast(Dict[str, Any], resolvers).get(
                "%s.%s" % (parent.name, field.name), None
            )
            or nested_key(
                cast(Dict[str, Any], resolvers),
                parent.name,
                field.name,
                default=None,
            )
        )

    for type_ in types:
        if isinstance(type_, _types.ObjectType):
            for field in type_.fields:
                field.resolver = infer(type_, field) or field.resolver


def _document_ast(document: Union[str, _ast.Document]) -> _ast.Document:
    if isinstance(document, str):
        return parse(document, allow_type_system=True)
    elif isinstance(document, _ast.Document):
        return document
    else:
        TypeError("Expected Document but got %s" % type(document))


def _collect_extensions(  # noqa: C901
    schema: Schema, document: _ast.Document, strict: bool = True
) -> Tuple[
    List[_ast.SchemaExtension],
    Dict[str, _ast.TypeDefinition],
    Dict[str, _ast.DirectiveDefinition],
    Dict[str, List[_ast.TypeExtension]],
]:
    schema_exts = []  # type: List[_ast.SchemaExtension]
    type_defs = {}  # type: Dict[str, _ast.TypeDefinition]
    _type_exts = []  # type: List[_ast.TypeExtension]
    type_exts = collections.defaultdict(
        list
    )  # type: Dict[str, List[_ast.TypeExtension]]
    directive_defs = {}  # type: Dict[str, _ast.DirectiveDefinition]

    for definition in document.definitions:
        if strict and isinstance(definition, _ast.SchemaDefinition):
            raise ExtensionError(
                "Cannot redefine schema in strict schema extension",
                [definition],
            )

        elif isinstance(definition, _ast.SchemaExtension):
            schema_exts.append(definition)

        elif isinstance(definition, _ast.TypeDefinition):
            name = definition.name.value
            if name in schema.types:
                if strict:
                    raise ExtensionError(
                        'Type "%s" is already defined in the schema.' % name,
                        [definition],
                    )
                else:
                    continue
            else:
                type_defs[name] = definition

        elif isinstance(definition, _ast.DirectiveDefinition):
            name = definition.name.value
            if name in schema.directives:
                if strict:
                    raise ExtensionError(
                        'Directive "@%s" is already defined in the schema.'
                        % name,
                        [definition],
                    )
                else:
                    continue
            else:
                directive_defs[name] = definition

        elif isinstance(definition, _ast.TypeExtension):
            _type_exts.append(definition)

    for ext in _type_exts:
        target = ext.name.value
        if not ((target in type_defs) or schema.has_type(target)):
            if strict:
                raise ExtensionError(
                    'Cannot extend undefined type "%s".' % target, [ext]
                )
            else:
                continue
        else:
            type_exts[target].append(ext)

    return schema_exts, type_defs, directive_defs, dict(type_exts)


def _merge_type_maps(
    *type_maps: Union[Mapping[str, NamedType], List[NamedType]]
) -> Dict[str, NamedType]:
    type_map = {}  # type: Dict[str, NamedType]
    for tm in type_maps:
        if isinstance(tm, list):
            type_map.update({type_.name: type_ for type_ in tm})
        elif isinstance(tm, dict):
            type_map.update(tm)
    return type_map
