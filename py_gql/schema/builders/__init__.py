# -*- coding: utf-8 -*-
"""
If you have an SDL-based schema definition, then you can create an executable
schema out of it.
"""

import copy
import functools as ft

import six

from .. import types as _types
from ..._utils import DefaultOrderedDict, OrderedDict, lazy, nested_key
from ...exc import SDLError, TypeExtensionError
from ...lang import ast as _ast, parse
from ...schema import DeprecatedDirective
from ...utilities import default_resolver, directive_arguments, value_from_ast
from .._validation import RESERVED_NAMES
from ..scalars import SPECIFIED_SCALAR_TYPES, DefaultScalarType
from ..schema import Schema
from .visitors import (
    HealSchemaVisitor,
    SchemaDirective,
    SchemaVisitor,
    _SchemaDirectivesApplicator,
    visit_schema,
)


def build_schema_from_ast(
    document,
    resolvers=None,
    additional_types=None,
    schema_directives=None,
    _raise_on_unknown_extension=False,
    _raise_on_missing_directive=False,
):
    """ Build an executable schema from an SDL-based schema definition.

    The schema is validated at the end to ensure no invalid schema gets created.

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

        schema_directives (dict):

        _raise_on_unknown_extension (bool):
            If ``True`` will raise if an extension nodes refers to an unknown
            type, else will discard the extension.

        _raise_on_missing_directive (bool):
            If ``True`` will raise if a directive nodes refers to an unknown
            schema directive, else will ignore the directive.

    Raises:
        py_gql.exc.SDLError:
    """
    if isinstance(document, six.string_types):
        ast = parse(document, allow_type_system=True)
    elif isinstance(document, _ast.Document):
        ast = document
    else:
        TypeError("Invalid document provided %s" % type(document))

    (
        schema_definition,
        schema_extensions,
        type_nodes,
        extension_nodes,
        directive_nodes,
    ) = _split_definitions(ast.definitions)

    type_names = set(type_nodes.keys())
    if additional_types:
        type_names |= set((t.name for t in additional_types))

    for type_name, ext_nodes in extension_nodes.items():
        if _raise_on_unknown_extension and type_name not in type_names:
            raise TypeExtensionError(
                'Cannot extend unknown type "%s"' % type_name, ext_nodes
            )
        if type_name in RESERVED_NAMES:
            raise TypeExtensionError(
                'Cannot extend specified type "%s"' % type_name, ext_nodes
            )

    types, directives = _types_and_directives_from_ast_nodes(
        type_nodes,
        directive_nodes,
        extension_nodes,
        additional_types=additional_types,
    )

    for schema_type in types.values():
        if isinstance(schema_type, _types.ObjectType):
            for field in schema_type.fields:
                field.resolve = _infer_resolver(
                    resolvers, schema_type.name, field.name
                )

    operation_types = _operation_types(
        schema_definition, schema_extensions, types
    )

    schema = Schema(
        query_type=operation_types.get("query"),
        mutation_type=operation_types.get("mutation"),
        subscription_type=operation_types.get("subscription"),
        types=types.values(),
        directives=directives.values(),
        nodes=(
            ([schema_definition] if schema_definition else [])
            + schema_extensions
        ),
    )

    schema.validate()
    schema = heal_schema(
        apply_schema_directives(
            schema, schema_directives or {}, strict=_raise_on_missing_directive
        )
    )
    schema.validate()

    return schema


def _operation_types(schema_definition, schema_extensions, type_map):
    """ Extract operation types from a schema_definiton and a type map.
    """

    def _extract(def_or_ext):
        operation_types = {}
        for opdef in def_or_ext.operation_types:
            type_name = opdef.type.name.value
            op = opdef.operation
            if op in operation_types:
                raise SDLError(
                    "Can only define one %s in schema" % op, [def_or_ext, opdef]
                )
            if type_name not in type_map:
                raise SDLError(
                    "%s type %s not found in document" % (op, type_name),
                    [def_or_ext, opdef],
                )
            operation_types[op] = type_map[type_name]
        return operation_types

    if schema_definition is None:
        base_schema = {
            k: type_map.get(k.capitalize(), None)
            for k in ("query", "mutation", "subscription")
        }
    else:
        base_schema = _extract(schema_definition)

    for ext in schema_extensions:
        base_schema.update(_extract(ext))

    return base_schema


def _infer_resolver(resolvers, type_name, field_name):
    if callable(resolvers):
        return resolvers(type_name, field_name)
    elif isinstance(resolvers, dict):
        flat_key = "%s.%s" % (type_name, field_name)
        if flat_key in resolvers:
            return resolvers[flat_key]
        return nested_key(resolvers, type_name, field_name, default=None)
    return None


def _deprecation_reason(node):
    args = directive_arguments(DeprecatedDirective, node, {})
    return args.get("reason", None) if args else None


def _split_definitions(definitions):
    """ Extract types, directives and extension definitions from a list
    of definition nodes.

    Args:
        definitions (List[py_gql.lang.ast.SchemaDefinition]): AST nodes

    Returns:
        Tuple[Optional[py_gql.lang.ast.SchemaDefinition],
              List[py_gql.lang.ast.SchemaExtension],
              Mapping[str, py_gql.lang.ast.TypeDefinition],
              Mapping[str, py_gql.lang.ast.TypeExtension],
              Mapping[str, py_gql.lang.ast.DirectiveDefinition]]:

    Raises:
        py_gql.exc.SDLError:
    """
    schema_definition = None
    types = OrderedDict()
    directives = OrderedDict()
    extensions = DefaultOrderedDict(list)
    schema_extensions = []

    for definition in definitions:
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

        elif isinstance(definition, _ast.SchemaExtension):
            schema_extensions.append(definition)

        elif isinstance(definition, _ast.TypeExtension):
            extensions[definition.name.value].append(definition)

        elif isinstance(definition, _ast.DirectiveDefinition):
            if definition.name.value in directives:
                raise SDLError(
                    "Duplicate directive @%s" % definition.name.value,
                    [definition],
                )
            directives[definition.name.value] = definition

    return schema_definition, schema_extensions, types, extensions, directives


class Ref(object):
    def __init__(self, type_name, cache):
        self._type_name = type_name
        self._cache = cache

    def __str__(self):
        return "Ref(%s)" % self._type_name

    def __call__(self):
        return self._cache[self._type_name]


def _input_value(node, type_, cls):
    # type: (
    #   py_gql.lang.ast.InputValueDefinition,
    #   py_gql.schema.Type,
    #   Type,
    # ) -> Union[py_gql.schema.Argument, py_gql.schema.InputField]
    desc = node.description.value if node.description else None
    kwargs = dict(description=desc, node=node)
    if node.default_value is not None:
        kwargs["default_value"] = value_from_ast(
            node.default_value, lazy(type_)
        )
    return cls(node.name.value, type_, **kwargs)


def _types_and_directives_from_ast_nodes(  # noqa
    type_nodes, directive_nodes, extension_nodes, additional_types=None
):
    """ Build types and directives from source nodes, including applying
    extension nodes.

    Args:
        type_nodes (Mapping[str, py_gql.lang.ast.TypeDefinition]):
            Type definitions

        type_directive (Mapping[str, py_gql.lang.ast.DirectiveDefinition]):
            Directive definitions

        extension_nodes (Mapping[str, py_gql.lang.ast.TypeExtension]):
            Type extensions

        additional_types (List[py_gql.schema.Type]): User supplied list of known types
            Use this to specify some custom implementation for scalar, enums, etc.
            In case of object types, interfaces, etc. the supplied type will
            override the extracted type without checking for compatibility.

    Returns:
        Tuple[Mapping[str, py_gql.schema.Type],
              Mapping[str, py_gql.schema.Directive]]: (type_map, directive_map)

    Raises:
        py_gql.exc.SDLError:
    """
    _cache = {}
    _additional_types = {t.name: copy.copy(t) for t in (additional_types or [])}

    for _type in SPECIFIED_SCALAR_TYPES:
        _cache[_type.name] = _type

    def build_directive(node):
        # type: (py_gql.lang.ast.DirectiveDefinition) -> py_gql.schema.Directive
        return _types.Directive(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            locations=[loc.value for loc in node.locations],
            args=(
                [input_value(arg, _types.Argument) for arg in node.arguments]
                if node.arguments
                else None
            ),
            node=node,
        )

    def build_type(type_node):
        # type: (py_gql.lang.ast.TypeSystemDefinition) -> py_gql.schema.Type
        if isinstance(type_node, _ast.ListType):
            return _types.ListType(build_type(type_node.type), node=type_node)

        if isinstance(type_node, _ast.NonNullType):
            return _types.NonNullType(
                build_type(type_node.type), node=type_node
            )

        type_name = type_node.name.value

        if type_name in _cache:
            return _cache[type_name]

        if isinstance(type_node, _ast.NamedType):
            type_def = type_nodes.get(type_name) or _additional_types.get(
                type_name
            )
            if type_def is None:
                raise SDLError(
                    "Type %s not found in document" % type_name, [type_node]
                )
            # Leverage the ususal lazy evaluation of fields and types
            # to prevent recursion issues
            return Ref(type_name, _cache)
        elif isinstance(type_node, _ast.TypeDefinition):
            if type_name in _additional_types:
                _cache[type_name] = _additional_types[type_name]
            else:
                _cache[type_name] = type_from_definition(type_node)
        else:
            raise TypeError(type(type_node))

        return _cache[type_name]

    def type_from_definition(type_def):
        # type: (py_gql.lang.ast.TypeSystemDefinition) -> py_gql.schema.Type
        if isinstance(type_def, _ast.ObjectTypeDefinition):
            return object_type(type_def)
        if isinstance(type_def, _ast.InterfaceTypeDefinition):
            return interface_type(type_def)
        if isinstance(type_def, _ast.EnumTypeDefinition):
            return enum_type(type_def)
        if isinstance(type_def, _ast.UnionTypeDefinition):
            return union_type(type_def)
        if isinstance(type_def, _ast.ScalarTypeDefinition):
            return scalar_type(type_def)
        if isinstance(type_def, _ast.InputObjectTypeDefinition):
            return input_object_type(type_def)
        raise TypeError(type(type_def))

    def object_type(node):
        # type: (py_gql.lang.ast.ObjectTypeDefinition) -> py_gql.schema.ObjectType
        return _types.ObjectType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[object_field(field_node) for field_node in node.fields],
            interfaces=(
                [build_type(iface) for iface in node.interfaces]
                if node.interfaces
                else None
            ),
            nodes=[node],
        )

    def interface_type(node):
        # type: (py_gql.lang.ast.InterfaceTypeDefinition) -> py_gql.schema.InterfaceType
        return _types.InterfaceType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[object_field(field_node) for field_node in node.fields],
            nodes=[node],
        )

    def object_field(node):
        # type: (py_gql.lang.ast.FieldDefinition) -> py_gql.schema.Field
        return _types.Field(
            node.name.value,
            build_type(node.type),
            description=(node.description.value if node.description else None),
            args=(
                [input_value(arg, _types.Argument) for arg in node.arguments]
                if node.arguments
                else None
            ),
            deprecation_reason=_deprecation_reason(node),
            node=node,
        )

    def enum_type(node):
        # type: (py_gql.lang.ast.EnumTypeDefinition) -> py_gql.schema.EnumType
        return _types.EnumType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            values=[enum_value(v) for v in node.values],
            nodes=[node],
        )

    def enum_value(node):
        # type: (py_gql.lang.ast.EnumValueDefinition) -> py_gql.schema.EnumValue
        return _types.EnumValue(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            value=node.name.value,
            deprecation_reason=_deprecation_reason(node),
            node=node,
        )

    def union_type(node):
        # type: (py_gql.lang.ast.UnionTypeDefinition) -> py_gql.schema.UnionType
        return _types.UnionType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            types=[build_type(type_) for type_ in node.types],
            nodes=[node],
        )

    def scalar_type(node):
        # type: (py_gql.lang.ast.ScalarTypeDefinition) -> py_gql.schema.ScalarType
        return DefaultScalarType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            nodes=[node],
        )

    def input_object_type(node):
        # type: (
        #   py_gql.lang.ast.InputObjectTypeDefinition
        # ) -> py_gql.schema.InputObjectType
        return _types.InputObjectType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[
                input_value(field_node, _types.InputField)
                for field_node in node.fields
            ],
            nodes=[node],
        )

    def input_value(node, cls):
        # type: (
        #   py_gql.lang.ast.InputValueDefinition,
        #   Type
        # ) -> Union[py_gql.schema.Argument, py_gql.schema.InputField]
        type_ = build_type(node.type)
        kwargs = dict(
            description=(node.description.value if node.description else None),
            node=node,
        )
        if node.default_value is not None:
            kwargs["default_value"] = value_from_ast(
                node.default_value, lazy(type_)
            )

        return cls(node.name.value, type_, **kwargs)

    def extend(schema_type, extension_node):
        # type: (
        #   py_gql.schema.Type,
        #   py_gql.lang.ast.TypeExtension
        # ) -> py_gql.schema.Type
        if isinstance(schema_type, _types.ObjectType):
            return extend_object(schema_type, extension_node)
        if isinstance(schema_type, _types.InterfaceType):
            return extend_interface(schema_type, extension_node)
        if isinstance(schema_type, _types.EnumType):
            return extend_enum(schema_type, extension_node)
        if isinstance(schema_type, _types.UnionType):
            return extend_union(schema_type, extension_node)
        if isinstance(schema_type, _types.InputObjectType):
            return extend_input_object(schema_type, extension_node)
        if isinstance(schema_type, _types.ScalarType):
            return extend_scalar(schema_type, extension_node)
        raise TypeError(type(schema_type))

    def extend_object(source_type, extension_node):
        # type: (
        #   py_gql.schema.ObjectType,
        #   py_gql.lang.ast.ObjectTypeExtension
        # ) -> py_gql.schema.ObjectType
        if not isinstance(extension_node, _ast.ObjectTypeExtension):
            raise TypeExtensionError(
                'Expected ObjectTypeExtension for ObjectType "%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        field_names = set(f.name for f in source_type.fields)
        fields = source_type.fields[:]
        iface_names = set(i.name for i in source_type.interfaces)
        ifaces = source_type.interfaces[:] if source_type.interfaces else []

        for ext_field in extension_node.fields:
            if ext_field.name.value in field_names:
                raise TypeExtensionError(
                    'Duplicate field "%s" when extending type "%s"'
                    % (ext_field.name.value, source_type.name),
                    [ext_field],
                )
            field_names.add(ext_field.name.value)
            fields.append(object_field(ext_field))

        for ext_iface in extension_node.interfaces:
            if ext_iface.name.value in iface_names:
                raise TypeExtensionError(
                    'Interface "%s" already implemented for type "%s"'
                    % (ext_iface.name.value, source_type.name),
                    [ext_iface],
                )
            iface_names.add(ext_iface.name.value)
            ifaces.append(build_type(ext_iface))

        return _types.ObjectType(
            name=source_type.name,
            description=source_type.description,
            fields=fields,
            interfaces=ifaces if ifaces else None,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_interface(source_type, extension_node):
        # type: (
        #   py_gql.schema.InterfaceType,
        #   py_gql.lang.ast.InterfaceTypeExtension
        # ) -> py_gql.schema.InterfaceType
        if not isinstance(extension_node, _ast.InterfaceTypeExtension):
            raise TypeExtensionError(
                "Expected InterfaceTypeExtension for InterfaceType "
                '"%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        field_names = set(f.name for f in source_type.fields)
        fields = source_type.fields[:]

        for ext_field in extension_node.fields:
            if ext_field.name.value in field_names:
                raise TypeExtensionError(
                    'Duplicate field "%s" when extending interface "%s"'
                    % (ext_field.name.value, source_type.name),
                    [ext_field],
                )
            field_names.add(ext_field.name.value)
            fields.append(object_field(ext_field))

        return _types.InterfaceType(
            name=source_type.name,
            description=source_type.description,
            fields=fields,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_enum(source_type, extension_node):
        # type: (
        #   py_gql.schema.EnumType,
        #   py_gql.lang.ast.EnumTypeExtension
        # ) -> py_gql.schema.EnumType
        if not isinstance(extension_node, _ast.EnumTypeExtension):
            raise TypeExtensionError(
                'Expected EnumTypeExtension for EnumType "%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        values = list(source_type.values.values())
        known_values = set(ev.name for ev in values)

        for value in extension_node.values:
            if value.name.value in known_values:
                raise TypeExtensionError(
                    'Duplicate enum value "%s" when extending EnumType "%s"'
                    % (value.name.value, source_type.name),
                    [value],
                )
            values.append(enum_value(value))
            known_values.add(value.name.value)

        return _types.EnumType(
            source_type.name,
            values=values,
            description=source_type.description,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_union(source_type, extension_node):
        # type: (
        #   py_gql.schema.UnionType,
        #   py_gql.lang.ast.UnionTypeExtension
        # ) -> py_gql.schema.UnionType
        if not isinstance(extension_node, _ast.UnionTypeExtension):
            raise TypeExtensionError(
                'Expected UnionTypeExtension for UnionType "%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        type_names = set(t.name for t in source_type.types)
        types = list(source_type.types)

        for new_type in extension_node.types:
            if new_type.name.value in type_names:
                raise TypeExtensionError(
                    'Duplicate type "%s" when extending EnumType "%s"'
                    % (new_type.name.value, source_type.name),
                    [new_type],
                )
            types.append(build_type(new_type))

        return _types.UnionType(
            source_type.name,
            types=types,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_input_object(source_type, extension_node):
        # type: (
        #   py_gql.schema.InputObjectType,
        #   py_gql.lang.ast.InputObjectTypeExtension
        # ) -> py_gql.schema.InputObjectType
        if not isinstance(extension_node, _ast.InputObjectTypeExtension):
            raise TypeExtensionError(
                "Expected InputObjectTypeExtension for InputObjectType "
                '"%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        field_names = set(f.name for f in source_type.fields)
        fields = source_type.fields[:]

        for ext_field in extension_node.fields:
            if ext_field.name.value in field_names:
                raise TypeExtensionError(
                    'Duplicate field "%s" when extending input object "%s"'
                    % (ext_field.name.value, source_type.name),
                    [ext_field],
                )
            field_names.add(ext_field.name.value)
            fields.append(input_value(ext_field, _types.InputField))

        return _types.InputObjectType(
            name=source_type.name,
            description=source_type.description,
            fields=fields,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_scalar(source_type, extension_node):
        # type: (
        #   py_gql.schema.ScalarType,
        #   py_gql.lang.ast.ScalarTypeExtension
        # ) -> py_gql.schema.ScalarType
        if not isinstance(extension_node, _ast.ScalarTypeExtension):
            raise TypeExtensionError(
                'Expected ScalarTypeExtension for ScalarType "%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        return DefaultScalarType(
            source_type.name,
            description=source_type.description,
            nodes=source_type.nodes + [extension_node],
        )

    types = {
        type_node.name.value: build_type(type_node)
        for type_node in type_nodes.values()
    }

    for schema_type in additional_types or []:
        if schema_type.name not in types:
            _cache[schema_type.name] = types[schema_type.name] = schema_type

    for type_name, exts in extension_nodes.items():
        if type_name not in types:
            continue

        for extension_node in exts:
            _cache[type_name] = types[type_name] = extend(
                _cache[type_name], extension_node
            )

    directives = {
        directive_def.name.value: build_directive(directive_def)
        for directive_def in directive_nodes.values()
    }

    return types, directives


def wrap_resolver(field_def, func):
    """ Apply a modificator function on the resolver of a given field
    definition. If no original resolver is set, this use the default resolver.

    Args:
        field_def (py_gql.schema.Field): Field defnition to modify
        func (Callable): Function to chain to the resolver
            Will be passed the result of the original resolve function.

    Returns:
        py_gql.schema.Field: Modified field defnition
    """
    source_resolver = field_def.resolve or default_resolver

    @ft.wraps(source_resolver)
    def wrapped(parent_value, args, context, info):
        value = source_resolver(parent_value, args, context, info)
        if value is None:
            return value
        return func(value)

    field_def = copy.copy(field_def)
    field_def.resolve = wrapped
    return field_def


def heal_schema(schema):
    """ Fix type reference in a schema.

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


__all__ = (
    "build_schema_from_ast",
    "wrap_resolver",
    "SchemaVisitor",
    "SchemaDirective",
    "visit_schema",
    "heal_schema",
)
