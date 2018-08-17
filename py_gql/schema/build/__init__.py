# -*- coding: utf-8 -*-
"""
Since the June 2018 version of the specification, SDL documents are officially
supported and provide with a language agnostic way of defining schemas. The
:mod:`py_gql.schema.build` module exposes the related utilities.
"""

import collections

import six

from .. import types as _types
from ..._utils import OrderedDict, nested_key
from ...exc import ExtensionError, SDLError
from ...lang import ast as _ast, parse
from ..schema import Schema
from .type_builder import TypesBuilder
from .visitors import (
    HealSchemaVisitor,
    SchemaDirective,
    _SchemaDirectivesApplicator,
    visit_schema,
)

__all__ = (
    "build_schema_from_ast",
    "extend_schema",
    "make_executable_schema",
    "SchemaDirective",
)


def make_executable_schema(
    document,
    resolvers=None,
    additional_types=None,
    schema_directives=None,
    assume_valid=False,
):
    """ Build an executable schema from a GraphQL document.

    This includes:

    - Generating types from their definitions
    - Applying schema and type extensions
    - Applying schema directives

    Args:
        document (Union[str, py_gql.lang.ast.Document]): SDL document

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

        schema_directives (dict): Schema directive classes
            - Members must be subclasses of :class:`SchemaDirective`
            - Members must define a non-null ``definition`` attribute or the
            corresponding definition must be present in the document

        assume_valid (bool): Do not validate intermediate schemas

    Returns:
        py_gql.schema.Schema: Executable schema

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
        schema = heal_schema(
            apply_schema_directives(schema, schema_directives, strict=True)
        )

        if not assume_valid:
            schema.validate()

    return schema


def build_schema_from_ast(document, resolvers=None, additional_types=None):
    """ Build an executable schema from an SDL-based schema definition ignoring
    extensions.

    Args:
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

    Returns:
        py_gql.schema.Schema: Executable schema

    Raises:
        py_gql.exc.SDLError:
    """
    ast = _document_ast(document)
    schema_def, type_defs, directive_defs = _collect_definitions(ast)

    builder = TypesBuilder(
        type_defs,
        directive_defs,
        additional_types=_merge_type_maps(additional_types),
    )

    directives = [
        builder.build_directive(directive_def)
        for directive_def in directive_defs.values()
    ]

    types = [builder.build_type(type_def) for type_def in type_defs.values()]

    _assign_resolvers(types, resolvers)

    if schema_def is None:
        operations = {
            t.name.lower(): t
            for t in types
            if t.name in ("Query", "Mutation", "Subscription")
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
            operations[op] = builder.build_type(op_def.type)

    return Schema(
        query_type=operations.get("query"),
        mutation_type=operations.get("mutation"),
        subscription_type=operations.get("subscription"),
        types=types,
        directives=directives,
        nodes=[schema_def] if schema_def else None,
    )


def extend_schema(
    schema, document, resolvers=None, additional_types=None, strict=True
):
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
    assert isinstance(schema, Schema)

    schema_exts, type_defs, directive_defs, type_exts = _collect_extensions(
        schema, ast, strict=strict
    )

    if not (schema_exts or type_defs or directive_defs or type_exts):
        return schema

    if additional_types is None:
        additional_types = {}

    builder = TypesBuilder(
        type_defs,
        directive_defs,
        type_exts,
        additional_types=_merge_type_maps(schema.types, additional_types),
    )

    directives = [
        builder.extend_directive(d) for d in schema.directives.values()
    ]
    directives += [
        builder.extend_directive(builder.build_directive(d))
        for d in directive_defs.values()
    ]

    types = [builder.extend_type(t) for t in schema.types.values()]
    types += [
        builder.extend_type(builder.build_type(t)) for t in type_defs.values()
    ]

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
        query_type=operation_types.get("query", None),
        mutation_type=operation_types.get("mutation", None),
        subscription_type=operation_types.get("subscription", None),
        types=types,
        directives=directives,
        nodes=(schema.nodes or []) + (schema_exts or []),
    )


def _collect_definitions(document):
    schema_definition = None
    types = OrderedDict()
    directives = OrderedDict()

    for definition in document.definitions:
        if isinstance(definition, _ast.SchemaDefinition):
            if schema_definition is not None:
                raise SDLError(
                    "Must provide only one schema definition", [definition]
                )
            schema_definition = definition

        elif isinstance(definition, _ast.TypeDefinition):
            if definition.name.value in types:
                raise SDLError(
                    "Duplicate type %s" % definition.name.value, [definition]
                )
            types[definition.name.value] = definition

        elif isinstance(definition, _ast.DirectiveDefinition):
            if definition.name.value in directives:
                raise SDLError(
                    "Duplicate directive @%s" % definition.name.value,
                    [definition],
                )
            directives[definition.name.value] = definition

    return schema_definition, types, directives


def _assign_resolvers(types, resolvers):

    if callable(resolvers):
        infer = lambda parent, field: resolvers(parent.name, field.name)
    elif isinstance(resolvers, dict):
        infer = lambda parent, field: (
            resolvers.get("%s.%s" % (parent.name, field.name), None)
            or nested_key(resolvers, parent.name, field.name, default=None)
        )
    elif not resolvers:
        return

    for type_ in types:
        if isinstance(type_, _types.ObjectType):
            for field in type_.fields:
                field.resolve = infer(type_, field) or field.resolve


def _document_ast(document):
    # type: (Union[_ast.Document, str]) -> _ast.Document
    if isinstance(document, six.string_types):
        return parse(document, allow_type_system=True)
    elif isinstance(document, _ast.Document):
        return document
    else:
        TypeError("Expected Document but got %s" % type(document))


def _collect_extensions(schema, document, strict=True):
    schema_exts = []
    type_defs = OrderedDict()
    _type_exts = []
    type_exts = collections.defaultdict(list)
    directive_defs = OrderedDict()

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
            existing = schema.get_type(name, None)
            if existing is not None:
                if strict:
                    raise ExtensionError(
                        'Type "%s" is already defined in the schema.' % name,
                        [definition],
                    )
                else:
                    continue
            type_defs[name] = definition

        elif isinstance(definition, _ast.DirectiveDefinition):
            name = definition.name.value
            existing = schema.directives.get(name, None)
            if existing is not None:
                if strict:
                    raise ExtensionError(
                        'Directive "@%s" is already defined in the schema.'
                        % name,
                        [definition],
                    )
                else:
                    continue
            directive_defs[name] = definition

        elif isinstance(definition, _ast.TypeExtension):
            _type_exts.append(definition)

    for ext in _type_exts:
        target = ext.name.value
        target_exists = schema.get_type(target, None) or (target in type_defs)
        if not target_exists:
            if strict:
                raise ExtensionError(
                    'Cannot extend undefined type "%s".' % target, [ext]
                )
            else:
                continue

        type_exts[target].append(ext)

    return schema_exts, type_defs, directive_defs, type_exts


def _merge_type_maps(*type_maps):
    type_map = {}
    for tm in type_maps:
        if isinstance(tm, list):
            type_map.update({type_.name: type_ for type_ in tm})
        elif isinstance(tm, dict):
            type_map.update(tm)
    return type_map


def heal_schema(schema):
    """ Fix type reference in a schema after modifying them inline.

    This ensures that all nested references to a certain type match the top
    level reference the schema has.

    Args:
        schema (py_gql.schema.Schema): Schema to fix

    Returns:
        py_gql.schema.Schema: Fixed schema

    Warning:
        This can modify the types inline and is expected to be used after
        buiding a schema, do not use this if your types are globally defined.
    """
    return visit_schema(HealSchemaVisitor(schema), schema)


def apply_schema_directives(schema, schema_directives, strict=False):
    """ Apply schema directives to a schema.

    Args:
        schema (py_gql.schema.Schema): Schema to modify
        schema_directives (Mapping[str, type]): ``{ name -> SchemaDirective subclass }``
            Schema directives are instantiated and provided the arguments
            for each occurence so user need to provide classes.
        strict (bool):
            If ``True`` will raise on missing implementation, otherwise silently
            ignores such directivess

    Returns:
        py_gql.schema.Schema: Updated schema
    """
    return visit_schema(
        _SchemaDirectivesApplicator(schema, schema_directives, strict=strict),
        schema,
    )
