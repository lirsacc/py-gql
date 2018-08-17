# -*- coding: utf-8 -*-
"""
"""

import functools as ft

from .. import types as _types
from ..._utils import lazy
from ...exc import ExtensionError, SDLError
from ...lang import ast as _ast
from ...utilities import directive_arguments, value_from_ast
from ..directives import SPECIFIED_DIRECTIVES, DeprecatedDirective
from ..introspection import INTROPSPECTION_TYPES
from ..scalars import SPECIFIED_SCALAR_TYPES, default_scalar


def _deprecation_reason(node):
    # type: (Union[_ast.FieldDefinition, _ast.EnumTypeDefinition]) -> Optional[str]
    args = directive_arguments(DeprecatedDirective, node, {})
    return args.get("reason", None) if args else None


def _desc(node):
    # type: (Union[_ast.TypeDefinition, _ast.FieldDefinition, \
    # _ast.EnumValueDefinition, _ast.DirectiveDefinition]) -> Optional[str]
    return node.description.value if node.description else None


_DEFAULT_TYPES_MAP = {
    t.name: t for t in (SPECIFIED_SCALAR_TYPES + INTROPSPECTION_TYPES)
}


_EXPECTED_EXTENSIONS = {
    _types.ObjectType: _ast.ObjectTypeExtension,
    _types.InterfaceType: _ast.InterfaceTypeExtension,
    _types.EnumType: _ast.EnumTypeExtension,
    _types.UnionType: _ast.UnionTypeExtension,
    _types.InputObjectType: _ast.InputObjectTypeExtension,
    _types.ScalarType: _ast.ScalarTypeExtension,
}


def _assert_correct_extension(type_cls, extension_node):
    try:
        expected_node_cls = _EXPECTED_EXTENSIONS[type_cls]
    except KeyError:
        pass
    else:
        if not isinstance(extension_node, expected_node_cls):
            raise ExtensionError(
                "Expected %s when extending %s but got %s"
                % (
                    expected_node_cls.__name__,
                    type_cls.__name__,
                    type(extension_node).__name__,
                ),
                [extension_node],
            )


class TypesBuilder(object):
    """ Build and extend type definitions from AST nodes.

    Warning:
        Specified types (scalars, introspection and directives) will not be
        built or extended.

    Args:
        type_defs (Mapping[str, _ast.TypeDefinition]):
            Type definitions by name
        directive_defs (Mapping[str, _ast.DirectiveDefinition]):
            Directive definitions by name
        type_extensions (Mapping[str, List[_ast.TypeExtensions]]):
            Type extensions by extend type name
        additional_types (Mapping[str, _types.NamedType]):
            Known type that should not be built when referenced
    """

    __slots__ = (
        "_type_defs",
        "_directive_defs",
        "_extensions",
        "_cache",
        "_extended_cache",
    )

    def __init__(
        self,
        type_defs,
        directive_defs,
        type_extensions=None,
        additional_types=None,
    ):
        self._type_defs = type_defs
        self._directive_defs = directive_defs
        self._extensions = type_extensions or {}

        self._cache = dict(_DEFAULT_TYPES_MAP)
        self._extended_cache = {}

        if additional_types:
            self._cache.update(additional_types)

    def build_type(self, type_node):
        # type: (Union[_ast.Type, _ast.TypeSystemDefinition]) -> _types.Type
        if isinstance(type_node, _ast.NonNullType):
            return _types.NonNullType(
                self.build_type(type_node.type), node=type_node
            )

        if isinstance(type_node, _ast.ListType):
            return _types.ListType(
                self.build_type(type_node.type), node=type_node
            )

        type_name = type_node.name.value

        try:
            return self._cache[type_name]
        except KeyError:
            if isinstance(type_node, _ast.NamedType):
                type_def = self._type_defs.get(type_name, None)
                if type_def is None:
                    raise SDLError(
                        "Type %s not found in document" % type_name, [type_node]
                    )
            else:
                type_def = type_node

            self._cache[type_name] = built = self._type_from_definition(
                type_def
            )
            return built

    def build_directive(self, directive_def):
        # type: (_ast.DirectiveDefinition) -> _types.Directive
        return _types.Directive(
            name=directive_def.name.value,
            description=_desc(directive_def),
            locations=[loc.value for loc in directive_def.locations],
            args=(
                [
                    self._build_input_value(arg, _types.Argument)
                    for arg in directive_def.arguments
                ]
                if directive_def.arguments
                else None
            ),
            node=directive_def,
        )

    def _type_from_definition(self, type_def):
        # type: (_ast.TypeSystemDefinition) -> _types.Type
        if isinstance(type_def, _ast.ObjectTypeDefinition):
            return self._build_object_type(type_def)
        if isinstance(type_def, _ast.InterfaceTypeDefinition):
            return self._build_interface_type(type_def)
        if isinstance(type_def, _ast.EnumTypeDefinition):
            return self._build_enum_type(type_def)
        if isinstance(type_def, _ast.UnionTypeDefinition):
            return self._build_union_type(type_def)
        if isinstance(type_def, _ast.ScalarTypeDefinition):
            return self._build_scalar_type(type_def)
        if isinstance(type_def, _ast.InputObjectTypeDefinition):
            return self._build_input_object_type(type_def)
        raise TypeError(type(type_def))

    def _build_object_type(self, type_def):
        # type: (_ast.ObjectTypeDefinition) -> _types.ObjectType
        return _types.ObjectType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_field(field_node) for field_node in type_def.fields
            ],
            interfaces=(
                [self.build_type(iface) for iface in type_def.interfaces]
                if type_def.interfaces
                else None
            ),
            nodes=[type_def],
        )

    def _build_interface_type(self, type_def):
        # type: (_ast.InterfaceTypeDefinition) -> _types.InterfaceType
        return _types.InterfaceType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_field(field_node) for field_node in type_def.fields
            ],
            nodes=[type_def],
        )

    def _build_field(self, field_def):
        # type: (_ast.FieldDefinition) -> _types.Field
        return _types.Field(
            field_def.name.value,
            # has to be lazy to support cyclic definition
            ft.partial(self.build_type, field_def.type),
            description=_desc(field_def),
            args=(
                [
                    self._build_input_value(arg, _types.Argument)
                    for arg in field_def.arguments
                ]
                if field_def.arguments
                else None
            ),
            deprecation_reason=_deprecation_reason(field_def),
            node=field_def,
        )

    def _build_enum_type(self, type_def):
        # type: (_ast.EnumTypeDefinition) -> _types.EnumType
        return _types.EnumType(
            name=type_def.name.value,
            description=_desc(type_def),
            values=[self._build_enum_value(v) for v in type_def.values],
            nodes=[type_def],
        )

    def _build_enum_value(self, node):
        # type: (_ast.EnumValueDefinition) -> _types.EnumValue
        return _types.EnumValue(
            name=node.name.value,
            description=_desc(node),
            value=node.name.value,
            deprecation_reason=_deprecation_reason(node),
            node=node,
        )

    def _build_union_type(self, type_def):
        # type: (_ast.UnionTypeDefinition) -> _types.UnionType
        return _types.UnionType(
            name=type_def.name.value,
            description=_desc(type_def),
            types=[self.build_type(type_) for type_ in type_def.types],
            nodes=[type_def],
        )

    def _build_scalar_type(self, type_def):
        # type: (_ast.ScalarTypeDefinition) -> _types.ScalarType
        return default_scalar(
            name=type_def.name.value,
            description=_desc(type_def),
            nodes=[type_def],
        )

    def _build_input_object_type(self, type_def):
        # type: (_ast.InputObjectTypeDefinition) -> _types.InputObjectType
        return _types.InputObjectType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_input_value(field_node, _types.InputField)
                for field_node in type_def.fields
            ],
            nodes=[type_def],
        )

    def _build_input_value(
        self,
        input_value_def,  # type: _ast.InputValueDefinition
        input_value_cls,  # type: Type
    ):
        # type: (...) -> Union[_types.Argument, _types.InputField]
        type_ = self.build_type(input_value_def.type)
        kwargs = dict(description=_desc(input_value_def), node=input_value_def)
        if input_value_def.default_value is not None:
            kwargs["default_value"] = value_from_ast(
                input_value_def.default_value, lazy(type_)
            )
        return input_value_cls(input_value_def.name.value, type_, **kwargs)

    def extend_type(self, type_):
        # type: (_types.Type) -> _types.Type
        cache = self._extended_cache

        if isinstance(type_, _types.ListType):
            return _types.ListType(self.extend_type(type_.type))

        if isinstance(type_, _types.NonNullType):
            return _types.NonNullType(self.extend_type(type_.type))

        name = type_.name

        if name in _DEFAULT_TYPES_MAP:
            return type_

        try:
            return cache[name]
        except KeyError:
            if isinstance(type_, _types.ObjectType):
                cache[name] = extended = self._extend_object_type(type_)
            elif isinstance(type_, _types.InterfaceType):
                cache[name] = extended = self._extend_interface_type(type_)
            elif isinstance(type_, _types.EnumType):
                cache[name] = extended = self._extend_enum_type(type_)
            elif isinstance(type_, _types.UnionType):
                cache[name] = extended = self._extend_union_type(type_)
            elif isinstance(type_, _types.InputObjectType):
                cache[name] = extended = self._extend_input_object_type(type_)
            elif isinstance(type_, _types.ScalarType):
                cache[name] = extended = self._extend_scalar_type(type_)
            else:
                raise TypeError(type(type_))

            return extended

    def extend_directive(self, directive):
        # type: (_types.Directive) -> _types.Directive
        if directive in SPECIFIED_DIRECTIVES:
            return directive

        return _types.Directive(
            directive.name,
            description=directive.description,
            locations=directive.locations,
            args=[self._extend_argument(a) for a in directive.args],
            node=directive.node,
        )

    def _extend_object_type(self, object_type):
        # type: (_types.ObjectType) -> _types.ObjectType
        name = object_type.name
        extensions = self._extensions.get(name, [])

        for extension_node in extensions:
            _assert_correct_extension(_types.ObjectType, extension_node)

        return _types.ObjectType(
            name,
            description=object_type.description,
            fields=self._extend_object_fields(object_type),
            interfaces=self._extend_object_interfaces(object_type),
            nodes=object_type.nodes + extensions,
        )

    def _extend_object_interfaces(self, object_type):
        # type: (_types.ObjectType) -> List[_types.NamedType]
        iface_names = set(i.name for i in object_type.interfaces)
        ifaces = [self.extend_type(iface) for iface in object_type.interfaces]

        for extension in self._extensions.get(object_type.name, []):
            for ext_iface in extension.interfaces:
                if ext_iface.name.value in iface_names:
                    raise ExtensionError(
                        'Interface "%s" already implemented for type "%s"'
                        % (ext_iface.name.value, object_type.name),
                        [ext_iface],
                    )
                iface_names.add(ext_iface.name.value)
                ifaces.append(self.extend_type(self.build_type(ext_iface)))

        return ifaces

    def _extend_field(self, field_def):
        # type: (_types.Field) -> _types.Field
        return _types.Field(
            field_def.name,
            self.extend_type(field_def.type),
            description=field_def.description,
            deprecation_reason=field_def.deprecation_reason,
            args=[self._extend_argument(a) for a in field_def.args],
            resolve=field_def.resolve,
            node=field_def.node,
        )

    def _extend_object_fields(self, composite_type):
        # type: (Union[_types.ObjectType, _types.InterfaceType]) -> List[_types.Field]
        field_names = set(f.name for f in composite_type.fields)

        fields = [self._extend_field(f) for f in composite_type.fields]

        for extension in self._extensions.get(composite_type.name, []):
            for ext_field in extension.fields:
                if ext_field.name.value in field_names:
                    raise ExtensionError(
                        'Found duplicate field "%s" when extending %s "%s"'
                        % (
                            ext_field.name.value,
                            "type"
                            if isinstance(composite_type, _types.ObjectType)
                            else "interface",
                            composite_type.name,
                        ),
                        [ext_field],
                    )
                field_names.add(ext_field.name.value)
                fields.append(self._extend_field(self._build_field(ext_field)))

        return fields

    def _extend_interface_type(self, interface_type):
        # type: (_types.InterfaceType) -> _types.InterfaceType
        name = interface_type.name
        extensions = self._extensions.get(name, [])

        for extension_node in extensions:
            _assert_correct_extension(_types.InterfaceType, extension_node)

        return _types.InterfaceType(
            name,
            description=interface_type.description,
            fields=self._extend_object_fields(interface_type),
            nodes=interface_type.nodes + extensions,
        )

    def _extend_enum_type(self, enum_type):
        # type: (_types.EnumType) -> EnumType
        name = enum_type.name
        extensions = self._extensions.get(name, [])

        values = enum_type.values[:]
        value_names = set(ev.name for ev in values)

        for extension_node in extensions:
            _assert_correct_extension(_types.EnumType, extension_node)
            for value in extension_node.values:
                if value.name.value in value_names:
                    raise ExtensionError(
                        'Found duplicate enum value "%s" when extending EnumType "%s"'
                        % (value.name.value, name),
                        [value],
                    )
                values.append(self._build_enum_value(value))
                value_names.add(value.name.value)

        return _types.EnumType(
            name,
            description=enum_type.description,
            values=values,
            nodes=enum_type.nodes + extensions,
        )

    def _extend_union_type(self, union_type):
        # type: (_types.UnionType) -> UnionType
        name = union_type.name
        extensions = self._extensions.get(name, [])

        member_names = set(t.name for t in union_type.types)
        member_types = [self.extend_type(t) for t in union_type.types]

        for extension_node in extensions:
            _assert_correct_extension(_types.UnionType, extension_node)
            for type_def in extension_node.types:
                if type_def.name.value in member_names:
                    raise ExtensionError(
                        'Found duplicate member type "%s" when extending UnionType "%s"'
                        % (type_def.name.value, name),
                        [type_def],
                    )
                member_types.append(self.extend_type(self.build_type(type_def)))
                member_names.add(type_def.name.value)

        return _types.UnionType(
            name, types=member_types, nodes=union_type.nodes + extensions
        )

    def _extend_input_object_type(self, input_object_type):
        # type: (_types.InputObjectType) -> InputObjectType
        name = input_object_type.name
        extensions = self._extensions.get(name, [])

        field_names = set(f.name for f in input_object_type.fields)
        fields = [
            _types.InputField(
                f.name,
                self.extend_type(f.type),
                default_value=f._default_value,
                description=f.description,
                node=f.node,
            )
            for f in input_object_type.fields
        ]

        for extension_node in extensions:
            _assert_correct_extension(_types.InputObjectType, extension_node)
            for ext_field in extension_node.fields:
                if ext_field.name.value in field_names:
                    raise ExtensionError(
                        'Found duplicate field "%s" when extending input object "%s"'
                        % (ext_field.name.value, name),
                        [ext_field],
                    )
                field_names.add(ext_field.name.value)
                fields.append(
                    self._build_input_value(ext_field, _types.InputField)
                )

        return _types.InputObjectType(
            name,
            description=input_object_type.description,
            fields=fields,
            nodes=input_object_type.nodes + extensions,
        )

    def _extend_scalar_type(self, scalar_type):
        # type: (_types.ScalarType) -> ScalarType
        name = scalar_type.name
        extensions = self._extensions.get(name, [])

        for extension_node in extensions:
            _assert_correct_extension(_types.ScalarType, extension_node)

        return _types.ScalarType(
            name,
            description=scalar_type.description,
            serialize=scalar_type._serialize,
            parse=scalar_type._parse,
            parse_literal=scalar_type._parse_literal,
            nodes=scalar_type.nodes + extensions,
        )

    def _extend_argument(self, argument):
        # type: (_types.Argument) -> Argument
        return _types.Argument(
            argument.name,
            self.extend_type(argument.type),
            default_value=argument._default_value,
            description=argument.description,
            node=argument.node,
        )
