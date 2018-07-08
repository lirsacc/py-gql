# -*- coding: utf-8 -*-
""" Build an executable schema from an parsed SDL file. """

import collections
import copy

import six

from . import types as _schema
from .._utils import is_iterable, nested_key
from ..exc import SDLError, TypeExtensionError
from ..lang import ast as _ast, parse
from ..utilities import directive_arguments, value_from_ast
from .directives import DeprecatedDirective
from .scalars import SPECIFIED_SCALAR_TYPES
from .schema import Schema
from .schema_directive import apply_schema_directives
from .validation import RESERVED_NAMES


def _ident(value):
    return value


def schema_from_ast(
    document,
    resolvers=None,
    known_types=None,
    schema_directives=None,
    _raise_on_unknown_extension=False,
    _raise_on_missing_directive=False,
):
    """ Build a valid schema from a schema definition.

    The schema is validate at the end to ensure not invalid schema gets created.

    :type document: Union[py_gql.lang.ast.Document, str, List[str]]
    :param document: Schema definition AST(s)
        A document will be used as is while a string or multiple string will
        be parsed first (potentially raising appropriate exceptions). List of
        strings will be combined as a single SDL.

    :type resolvers: Union[dict, callable]
    :param resolvers: Used to infer field resolvers
        If a `dict` is provided, this looks for the resolver at key
        `{type_name}.{field_name}`. If a callable is provided, this calls
        it with the `{type_name}.{field_name}` argument and use the return value
        if it is callable.

    :type known_types: List[py_gql.schema.Type]
    :param known_types: User supplied list of known types
        Use this to specify some custom implementation for scalar, enums, etc.
        In case of object types, interfaces, etc. the supplied type will
        override the extracted type without checking.

    :type _raise_on_unknown_extension: bool
    :param _raise_on_unknown_extension:

    :type _raise_on_missing_directive: bool
    :param _raise_on_missing_directive:

    """

    if isinstance(document, six.string_types):
        ast = parse(document, allow_type_system=True)
    elif isinstance(document, _ast.Document):
        ast = document
    elif is_iterable(document, False):
        document = parse("\n".join(document), allow_type_system=True)
    else:
        raise TypeError(type(document))

    # First pass = parse and extract relevant informaton
    (
        schema_definition,
        type_nodes,
        extension_nodes,
        directive_nodes,
    ) = _extract_types(ast.definitions)

    if _raise_on_unknown_extension:
        type_names = set(type_nodes.keys())
        if known_types:
            type_names |= set((t.name for t in known_types))

        for type_name, ext_nodes in extension_nodes.items():
            if type_name not in type_names:
                raise SDLError(
                    'Cannot extend unknown type "%s"' % type_name, ext_nodes
                )

    # Second pass = translate types in schema object and apply extensions
    types, directives = _build_types_and_directives(
        type_nodes, directive_nodes, extension_nodes, known_types=known_types
    )

    # TODO: Should we do the same for resolve_type on Union and Interface ?
    # Third pass associate resolvers
    for schema_type in types.values():
        if isinstance(schema_type, _schema.ObjectType):
            for field in schema_type.fields:
                field.resolve = _infer_resolver(
                    resolvers, schema_type.name, field.name
                )

    operation_types = _operation_types(schema_definition, types)

    schema = Schema(
        query_type=operation_types.get("query"),
        mutation_type=operation_types.get("mutation"),
        subscription_type=operation_types.get("subscription"),
        types=types.values(),
        directives=directives.values(),
        node=schema_definition,
    )

    # Schema must be valid before applying directives
    schema.validate()
    apply_schema_directives(
        schema, schema_directives or {}, strict=_raise_on_missing_directive
    )
    schema.validate()

    return schema


def _deprecation_reason(node):
    args = directive_arguments(DeprecatedDirective, node, {})
    return args.get("reason") if args else None


def _infer_resolver(resolvers, type_name, field_name):
    if callable(resolvers):
        return resolvers(type_name, field_name)
    elif isinstance(resolvers, dict):
        flat_key = "%s.%s" % (type_name, field_name)
        if flat_key in resolvers:
            return resolvers[flat_key]
        return nested_key(resolvers, type_name, field_name, default=None)
    return None


def _extract_types(definitions):
    """ Extract types, directives and extensions from a list of definition nodes

    :type definitions: List[py_gql.lang.ast.Definition]
    :param definitions: AST nodes

    :rtype: Tuple[
        Optional[py_gql.lang.ast.SchemaDefinition],
        Mapping[str, py_gql.lang.ast.TypeDefinition],
        Mapping[str, py_gql.lang.ast.TypeExtension],
        Mapping[str, py_gql.lang.ast.DirectiveDefinition],
    ]
    :returns: (
        schema_definition,
        type_definitions,
        type_extensions,
        directive_definitions
    )
    """
    schema_definition = None
    types = {}
    extensions = collections.defaultdict(list)
    directives = {}

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

        elif isinstance(definition, _ast.TypeExtension):
            extensions[definition.name.value].append(definition)

        elif isinstance(definition, _ast.DirectiveDefinition):
            if definition.name.value in directives:
                raise SDLError(
                    "Duplicate directive @%s" % definition.name.value,
                    [definition],
                )
            directives[definition.name.value] = definition

    return schema_definition, types, extensions, directives


def _operation_types(schema_definition, type_map):
    """ Extract operation types from a schema_definiton and a type map.
    """
    if schema_definition is None:
        return {
            k: type_map.get(k.capitalize(), None)
            for k in ("query", "mutation", "subscription")
        }
    else:
        operation_types = {}
        for opdef in schema_definition.operation_types:
            type_name = opdef.type.name.value
            op = opdef.operation
            if op in operation_types:
                raise SDLError(
                    "Can only define one %s in schema" % op,
                    [schema_definition, opdef],
                )
            if type_name not in type_map:
                raise SDLError(
                    "%s type %s not found in document" % (op, type_name),
                    [schema_definition, opdef],
                )
            operation_types[op] = type_map[type_name]
        return operation_types


class Ref(object):
    def __init__(self, type_name, cache):
        self._type_name = type_name
        self._cache = cache

    def __str__(self):
        return "Ref(%s)" % self._type_name

    def __call__(self):
        return self._cache[self._type_name]


def _build_types_and_directives(  # noqa
    type_nodes, directive_nodes, extension_nodes, known_types=None
):
    """ Build types from source nodes:

    - Build type map
    - Build directive map
    - Associate reference node to types
    - Apply type extensions

    :type type_nodes: Mapping[str, py_gql.lang.ast.TypeDefinition]
    :param type_nodes: Type definitions

    :type directive_nodes: Mapping[str, py_gql.lang.ast.DirectiveDefinition]
    :param directive_nodes: Directive definitions

    :type extension_nodes: Mapping[str, py_gql.lang.ast.TypeExtension]
    :param extension_nodes: Directive definitions

    :type known_types: List[py_gql.schema.Type]
    :param known_types: List of known type implementations to inject
        Most useful for scalars and enums but can be used for
        Extensions will be applied to these types as well and the
        resulting types may not be the same objects that were provided.
        Do not rely on type identity.

    :rtype: Tuple[
        Mapping[str, py_gql.schema.Type],
        Mapping[str, py_gql.schema.Directive]
    ]
    :returns: (type_map, directive_map)
    """
    _cache = {}
    _known_types = {t.name: copy.copy(t) for t in (known_types or [])}

    for _type in SPECIFIED_SCALAR_TYPES:
        _cache[_type.name] = _type

    def build_directive(node):
        """
        :type node: py_gql.lang.ast.DirectiveDefinition
        :param node:

        :rtype: py_gql.schema.Directive
        """
        return _schema.Directive(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            locations=[loc.value for loc in node.locations],
            args=(
                [input_value(arg, _schema.Argument) for arg in node.arguments]
                if node.arguments
                else None
            ),
            node=node,
        )

    def build_type(type_node):
        """
        :type type_node: py_gql.lang.ast.TypeSystemDefinition
        :param type_node:

        :rtype: py_gql.schema.Type|Ref
        """
        if isinstance(type_node, _ast.ListType):
            return _schema.ListType(build_type(type_node.type), node=type_node)

        if isinstance(type_node, _ast.NonNullType):
            return _schema.NonNullType(
                build_type(type_node.type), node=type_node
            )

        type_name = type_node.name.value

        if type_name in _cache:
            return _cache[type_name]

            return _cache[type_name]

        if isinstance(type_node, _ast.NamedType):
            type_def = type_nodes.get(type_name) or _known_types.get(type_name)
            if type_def is None:
                raise SDLError(
                    "Type %s not found in document" % type_name, [type_node]
                )
            # Leverage the ususal lazy evaluation of fields and types
            # to prevent recursion issues
            return Ref(type_name, _cache)
        elif isinstance(type_node, _ast.TypeDefinition):
            if type_name in _known_types:
                _cache[type_name] = _known_types[type_name]
            else:
                _cache[type_name] = type_from_definition(type_node)
        else:
            raise TypeError(type(type_node))

        return _cache[type_name]

    def type_from_definition(type_def):
        """
        :type type_node: py_gql.lang.ast.TypeDefinition
        :param type_node:

        :rtype: py_gql.schema.Type
        """
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
        """
        :type type_node: py_gql.lang.ast.ObjectTypeDefinition
        :param type_node:

        :rtype: py_gql.schema.ObjectType
        """
        return _schema.ObjectType(
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
        """
        :type type_node: py_gql.lang.ast.InterfaceTypeDefinition
        :param type_node:

        :rtype: py_gql.schema.InterfaceType
        """
        return _schema.InterfaceType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[object_field(field_node) for field_node in node.fields],
            nodes=[node],
        )

    def object_field(node):
        """
        :type type_node: py_gql.lang.ast.FieldDefinition
        :param type_node:

        :rtype: py_gql.schema.Field
        """
        return _schema.Field(
            node.name.value,
            build_type(node.type),
            description=(node.description.value if node.description else None),
            args=(
                [input_value(arg, _schema.Argument) for arg in node.arguments]
                if node.arguments
                else None
            ),
            deprecation_reason=_deprecation_reason(node),
            node=node,
        )

    def enum_type(node):
        """
        :type type_node: py_gql.lang.ast.EnumTypeDefinition
        :param type_node:

        :rtype: py_gql.schema.EnumType
        """
        return _schema.EnumType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            values=[enum_value(v) for v in node.values],
            nodes=[node],
        )

    def enum_value(node):
        """
        :type type_node: py_gql.lang.ast.EnumValueDefinition
        :param type_node:

        :rtype: py_gql.schema.EnumValue
        """
        return _schema.EnumValue(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            value=node.name.value,
            deprecation_reason=_deprecation_reason(node),
            node=node,
        )

    def union_type(node):
        """
        :type type_node: py_gql.lang.ast.UnionTypeDefinition
        :param type_node:

        :rtype: py_gql.schema.UnionType
        """
        return _schema.UnionType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            types=[build_type(type) for type in node.types],
            nodes=[node],
        )

    def scalar_type(node):
        """
        :type type_node: py_gql.lang.ast.ScalarypeDefinition
        :param type_node:

        :rtype: py_gql.schema.Scalarype
        """
        return _schema.ScalarType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            nodes=[node],
            serialize=_ident,
            parse=_ident,
        )

    def input_object_type(node):
        """
        :type type_node: py_gql.lang.ast.InputObjectTypeDefinition
        :param type_node:

        :rtype: py_gql.schema.InputObjectType
        """
        return _schema.InputObjectType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[
                input_value(field_node, _schema.InputField)
                for field_node in node.fields
            ],
            nodes=[node],
        )

    def input_value(node, cls):
        """
        :type type_node: py_gql.lang.ast.InputValueDefinition
        :param type_node:

        :type cls: type
        :param cls: Argument or InputField

        :rtype: py_gql.schema.Argument|py_gql.schema.InputField
        """
        type = build_type(node.type)
        kwargs = dict(
            description=(node.description.value if node.description else None),
            node=node,
        )
        if node.default_value is not None:
            kwargs["default_value"] = value_from_ast(node.default_value, type)

        return cls(node.name.value, type, **kwargs)

    def extend(schema_type, extension_node):
        """
        :type schema_type: py_gql.schema.Type
        :param schema_type:

        :type extension_node: py_gql.lang.ast.TypeExtension
        :param extension_node:

        :rtype: py_gql.schema.Type
        :returns: Extended type
        """
        if isinstance(schema_type, _schema.ObjectType):
            return extend_object(schema_type, extension_node)
        if isinstance(schema_type, _schema.InterfaceType):
            return extend_interface(schema_type, extension_node)
        if isinstance(schema_type, _schema.EnumType):
            return extend_enum(schema_type, extension_node)
        if isinstance(schema_type, _schema.UnionType):
            return extend_union(schema_type, extension_node)
        if isinstance(schema_type, _schema.InputObjectType):
            return extend_input_object(schema_type, extension_node)
        if isinstance(schema_type, _schema.ScalarType):
            return extend_scalar(schema_type, extension_node)
        raise TypeError(type(schema_type))

    def extend_object(source_type, extension_node):
        """
        :type schema_type: py_gql.schema.ObjectType
        :param schema_type:

        :type extension_node: py_gql.lang.ast.ObjectTypeExtension
        :param extension_node:

        :rtype: py_gql.schema.ObjectType
        """
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

        return _schema.ObjectType(
            name=source_type.name,
            description=source_type.description,
            fields=fields,
            interfaces=ifaces if ifaces else None,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_interface(source_type, extension_node):
        """
        :type schema_type: py_gql.schema.InterfaceType
        :param schema_type:

        :type extension_node: py_gql.lang.ast.InterfaceTypeExtension
        :param extension_node:

        :rtype: py_gql.schema.InterfaceType
        """
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

        return _schema.InterfaceType(
            name=source_type.name,
            description=source_type.description,
            fields=fields,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_enum(source_type, extension_node):
        """
        :type schema_type: py_gql.schema.EnumType
        :param schema_type:

        :type extension_node: py_gql.lang.ast.EnumTypeExtension
        :param extension_node:

        :rtype: py_gql.schema.EnumType
        """
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

        return _schema.EnumType(
            source_type.name,
            values=values,
            description=source_type.description,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_union(source_type, extension_node):
        """
        :type schema_type: py_gql.schema.UnionType
        :param schema_type:

        :type extension_node: py_gql.lang.ast.UnionTypeExtension
        :param extension_node:

        :rtype: py_gql.schema.UnionType
        """
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

        return _schema.UnionType(
            source_type.name,
            types=types,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_input_object(source_type, extension_node):
        """
        :type schema_type: py_gql.schema.InputObjectType
        :param schema_type:

        :type extension_node: py_gql.lang.ast.InputObjectTypeExtension
        :param extension_node:

        :rtype: py_gql.schema.InputObjectType
        """
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
            fields.append(input_value(ext_field, _schema.InputField))

        return _schema.InputObjectType(
            name=source_type.name,
            description=source_type.description,
            fields=fields,
            nodes=source_type.nodes + [extension_node],
        )

    def extend_scalar(source_type, extension_node):
        """
        :type schema_type: py_gql.schema.ScalarType
        :param schema_type:

        :type extension_node: py_gql.lang.ast.ScalarTypeExtension
        :param extension_node:

        :rtype: py_gql.schema.ScalarType
        """
        if not isinstance(extension_node, _ast.ScalarTypeExtension):
            raise TypeExtensionError(
                'Expected ScalarTypeExtension for ScalarType "%s" but got %s'
                % (source_type.name, type(extension_node).__name__),
                [extension_node],
            )

        if source_type.name in RESERVED_NAMES:
            raise TypeExtensionError(
                "Cannot extend specified scalar %s" % (source_type.name),
                [extension_node],
            )

        return _schema.ScalarType(
            source_type.name,
            source_type._serialize,
            source_type._parse,
            source_type._parse_literal,
            description=source_type.description,
            nodes=source_type.nodes + [extension_node],
        )

    types = {
        type_node.name.value: build_type(type_node)
        for type_node in type_nodes.values()
    }

    for schema_type in known_types or []:
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
