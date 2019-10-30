# -*- coding: utf-8 -*-

import collections
from typing import (
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..exc import ExtensionError, SDLError
from ..lang import ast as _ast, parse
from ..schema import NamedType, ObjectType, Schema
from .ast_type_builder import ASTTypeBuilder
from .schema_directives import SchemaDirective, apply_schema_directives

TTypeExtension = TypeVar("TTypeExtension", bound=Type[_ast.TypeExtension])


__all__ = ("build_schema", "extend_schema")


def build_schema(
    document: Union[_ast.Document, str],
    *,
    ignore_extensions: bool = False,
    additional_types: Optional[List[NamedType]] = None,
    schema_directives: Optional[Mapping[str, Type[SchemaDirective]]] = None
) -> Schema:
    """ Build an executable schema from a GraphQL document.

    This includes:

        - Generating types from their definitions
        - Applying schema and type extensions
        - Applying schema directives

    Args:
        document: SDL document

        ignore_extensions: Whether to apply schema and type extensions or not.

        additional_types: User supplied list of types
            Use this to specify some custom implementation for scalar, enums, etc.
            - In case of object types, interfaces, etc. the supplied type will
            override the extracted type without checking for compatibility.
            - Extension will be applied to these types. As a result, the
            resulting types may not be the same objects that were provided,
            so users should not rely on type identity.

        schema_directives: Schema directive classes.
            Members must be subclasses of :class:`py_gql.schema.SchemaDirective`
            and must either  define a non-null ``definition`` attribute or the
            corresponding definition must be present in the document. See
            :func:`~py_gql.schema.apply_schema_directives` for more details.

            Note:
                Specified directives such as ``@deperecated`` do not need to be
                specified this way and are always processed internally to ensure
                compliance with the specification.

    Returns:
        Executable schema

    Raises:
        py_gql.exc.SDLError:
        py_gql.exc.ExtensionError:
    """
    ast = _document_ast(document)
    schema = build_schema_ignoring_extensions(
        ast, additional_types=additional_types
    )

    if not ignore_extensions:
        schema = extend_schema(
            schema, ast, additional_types=additional_types, strict=False
        )

    if schema_directives is not None:
        schema = apply_schema_directives(schema, schema_directives)

    schema.validate()

    return schema


def build_schema_ignoring_extensions(
    document: Union[_ast.Document, str],
    *,
    additional_types: Optional[List[NamedType]] = None
) -> Schema:
    """ Build an executable schema from an SDL-based schema definition ignoring
    extensions. """
    ast = _document_ast(document)
    schema_def, type_defs, directive_defs = _collect_definitions(ast)

    builder = ASTTypeBuilder(
        type_defs,
        directive_defs,
        {},
        additional_types=(
            {t.name: t for t in additional_types} if additional_types else {}
        ),
    )

    directives = [
        builder.build_directive(directive_def)
        for directive_def in directive_defs.values()
    ]

    # Cast is safe as type defs will always lead to named types and not wrapped types
    types = [
        cast(NamedType, builder.build_type(type_def))
        for type_def in type_defs.values()
    ]

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
    *,
    additional_types: Optional[List[NamedType]] = None,
    strict: bool = True,
    schema_directives: Optional[Mapping[str, Type[SchemaDirective]]] = None
) -> Schema:
    """ Extend an existing Schema according to a GraphQL document (adding new
    types and directives + extending known types).

    Warning:
        Specified types (scalars, introspection) cannot be replace or extended.

    Args:
        schema: Executable schema

        document: SDL document

        additional_types: User supplied list of types
            Use this to specify some custom implementation for scalar, enums,
            etc.
            - In case of object types, interfaces, etc. the supplied type will
            override the extracted type without checking for compatibility.
            - Extension will be applied to these types. As a result, the
            resulting types may not be the same objects that were provided,
            so users should not rely on type identity.

        strict: Enable strict mode.
            In strict mode, unknown extension targets, overriding type and
            overriding the schema definition will raise an
            :class:`ExtensionError`. Disable strict mode will silently ignore
            such errors.

        schema_directives: Schema directive classes.
            Members must be subclasses of :class:`py_gql.schema.SchemaDirective`
            and must either  define a non-null ``definition`` attribute or the
            corresponding definition must be present in the document. See
            :func:`~py_gql.schema.apply_schema_directives` for more details.

            Note:
                Specified directives such as ``@deperecated`` do not need to be
                specified this way and are always processed internally to ensure
                compliance with the specification.

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

    builder = ASTTypeBuilder(
        type_defs,
        directive_defs,
        type_exts,
        additional_types={
            **schema.types,
            **{t.name: t for t in additional_types or []},
        },
    )

    directives = [
        builder.extend_directive(d) for d in schema.directives.values()
    ] + [
        builder.extend_directive(builder.build_directive(d))
        for d in directive_defs.values()
    ]

    # Cast is safe as type defs will always lead to named types and not wrapped types
    types = [
        cast(NamedType, builder.extend_type(t))
        for t in schema.types.values()
        if t.name in type_exts
    ] + [
        cast(NamedType, builder.extend_type(builder.build_type(t)))
        for t in type_defs.values()
        if t.name.value not in schema.types
    ]

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

    schema = Schema(
        query_type=operation_types["query"],
        mutation_type=operation_types["mutation"],
        subscription_type=operation_types["subscription"],
        types=types,
        directives=directives,
        nodes=(schema.nodes or []) + (schema_exts or []),  # type: ignore
    )

    if schema_directives is not None:
        schema = apply_schema_directives(schema, schema_directives)

    schema.validate()
    return schema


def _collect_definitions(
    document: _ast.Document,
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
