# -*- coding: utf-8 -*-

import functools as ft
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from .._utils import Lazy, lazy
from ..exc import ExtensionError, SDLError
from ..lang import ast as _ast
from ..schema import (
    SPECIFIED_DIRECTIVES,
    SPECIFIED_SCALAR_TYPES,
    Argument,
    DeprecatedDirective,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputField,
    InputObjectType,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    ScalarType,
    UnionType,
)
from ..schema.introspection import INTROPSPECTION_TYPES
from ..schema.scalars import default_scalar
from ..utilities import directive_arguments, value_from_ast


TTypeExtension = TypeVar("TTypeExtension", bound=Type[_ast.TypeExtension])
T = TypeVar("T")


def _default_type_map() -> Dict[str, NamedType]:
    types = {}  # type: Dict[str, NamedType]
    types.update({t.name: t for t in SPECIFIED_SCALAR_TYPES})
    types.update({t.name: t for t in INTROPSPECTION_TYPES})
    return types


_DEFAULT_TYPES_MAP = _default_type_map()


class _DelayedObject:

    UNSET = object()

    def __init__(self, fn: Callable[[], Any]):
        self.fn = fn
        self.value = self.UNSET

    def __call__(self) -> Any:
        if self.value is self.UNSET:
            self.value = self.fn()
        return self.value


class ASTTypeBuilder:
    """
    Build and extend type definitions from AST nodes.

    Warning:
        Specified types (scalars, introspection and directives) will not be
        built or extended in order to prevent exposing non standard GraphQL
        servers.

    Args:
        type_defs: Type definitions by name

        directive_defs: Directive definitions by name
        type_extensions: Type extensions by extend type name
        additional_types: Known type that should not be built when referenced
    """

    __slots__ = (
        "_type_defs",
        "_directive_defs",
        "_cache",
        "_extended_cache",
        "_extensions",
        "_delayed",
    )

    def __init__(
        self,
        type_defs: Mapping[str, _ast.TypeDefinition],
        directive_defs: Mapping[str, _ast.DirectiveDefinition],
        type_extensions: Mapping[str, List[_ast.TypeExtension]],
        additional_types: Mapping[str, NamedType],
    ):
        self._type_defs = type_defs
        self._directive_defs = directive_defs

        self._cache = dict(_DEFAULT_TYPES_MAP)  # type: Dict[str, GraphQLType]
        self._extended_cache = {}  # type: Dict[str, GraphQLType]
        self._extensions = type_extensions
        self._cache.update(additional_types)
        self._delayed = []  # type: List[_DelayedObject]

    # To support recursive types and random ordering between types, we use a lot
    # of lazy objects throughout the builder. Some of them are guaranteed to be
    # called during the build, but other may well only be needed later, which
    # could lead to things exploding later. By collecting them and caching
    # result, we can call them directly from the build context.
    def delay(self, fn: Callable[[], T]) -> Callable[[], T]:
        delayed_obj = _DelayedObject(fn)
        self._delayed.append(delayed_obj)
        return cast(Callable[[], T], delayed_obj)

    def flush_delayed(self):
        for x in self._delayed:
            x()
        self._delayed[:] = []

    def _collect_extensions(
        self,
        target_name: str,
        ext_type: TTypeExtension,
    ) -> List[TTypeExtension]:
        res = []
        for ext in self._extensions.get(target_name) or []:
            if not isinstance(ext, ext_type):
                raise ExtensionError(
                    "Expected %s when extending %s but got %s"
                    % (
                        ext_type.__name__,
                        ext_type.__name__.replace("Extension", ""),
                        type(ext).__name__,
                    ),
                    [ext],
                )

            res.append(cast(TTypeExtension, ext))

        return res

    def build_type(
        self,
        type_node: Union[_ast.Type, _ast.TypeDefinition],
    ) -> GraphQLType:
        if isinstance(type_node, _ast.NonNullType):
            return NonNullType(self.build_type(type_node.type), node=type_node)
        elif isinstance(type_node, _ast.ListType):
            return ListType(self.build_type(type_node.type), node=type_node)
        else:
            type_name = type_node.name.value  # type: ignore

            try:
                return self._cache[type_name]
            except KeyError:
                if isinstance(type_node, _ast.NamedType):
                    try:
                        type_def = self._type_defs[type_name]
                    except KeyError:
                        raise SDLError(
                            f"Type {type_name} not found in document",
                            [type_node],
                        )
                else:
                    type_def = cast(_ast.TypeDefinition, type_node)

                if isinstance(type_def, _ast.ObjectTypeDefinition):
                    built = self._build_object_type(
                        type_def,
                    )  # type: GraphQLType
                elif isinstance(type_def, _ast.InterfaceTypeDefinition):
                    built = self._build_interface_type(type_def)
                elif isinstance(type_def, _ast.EnumTypeDefinition):
                    built = self._build_enum_type(type_def)
                elif isinstance(type_def, _ast.UnionTypeDefinition):
                    built = self._build_union_type(type_def)
                elif isinstance(type_def, _ast.ScalarTypeDefinition):
                    built = self._build_scalar_type(type_def)
                elif isinstance(type_def, _ast.InputObjectTypeDefinition):
                    built = self._build_input_object_type(type_def)
                else:
                    raise TypeError(type(type_def))

                self._cache[type_name] = built
                return built

    def build_directive(
        self,
        directive_def: _ast.DirectiveDefinition,
    ) -> Directive:
        return Directive(
            name=directive_def.name.value,
            description=_desc(directive_def),
            repeatable=directive_def.repeatable,
            locations=[loc.value for loc in directive_def.locations],
            args=(
                [self._build_argument(arg) for arg in directive_def.arguments]
                if directive_def.arguments
                else None
            ),
            node=directive_def,
        )

    def extend_type(self, type_: GraphQLType) -> GraphQLType:

        if isinstance(type_, ListType):
            return ListType(self.extend_type(type_.type))

        if isinstance(type_, NonNullType):
            return NonNullType(self.extend_type(type_.type))

        name = cast(NamedType, type_).name
        if name in _DEFAULT_TYPES_MAP:
            return type_

        try:
            return self._extended_cache[name]
        except KeyError:
            if isinstance(type_, ObjectType):
                extended = self._extend_object_type(type_)  # type: GraphQLType
            elif isinstance(type_, InterfaceType):
                extended = self._extend_interface_type(type_)
            elif isinstance(type_, EnumType):
                extended = self._extend_enum_type(type_)
            elif isinstance(type_, UnionType):
                extended = self._extend_union_type(type_)
            elif isinstance(type_, InputObjectType):
                extended = self._extend_input_object_type(type_)
            elif isinstance(type_, ScalarType):
                extended = self._extend_scalar_type(type_)
            else:
                raise TypeError(type(type_))

            self._extended_cache[name] = extended
            return extended

    def extend_directive(self, directive: Directive) -> Directive:
        if directive in SPECIFIED_DIRECTIVES:
            return directive

        return Directive(
            directive.name,
            description=directive.description,
            repeatable=directive.repeatable,
            locations=directive.locations,
            args=[self._extend_argument(a) for a in directive.arguments],
            node=directive.node,
        )

    def _build_object_type(
        self,
        type_def: _ast.ObjectTypeDefinition,
    ) -> ObjectType:
        return ObjectType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_field(field_node) for field_node in type_def.fields
            ],
            interfaces=(
                [
                    cast(InterfaceType, self.build_type(interface))
                    for interface in type_def.interfaces
                ]
                if type_def.interfaces
                else None
            ),
            nodes=[type_def],
        )

    def _build_interface_type(
        self,
        type_def: _ast.InterfaceTypeDefinition,
    ) -> InterfaceType:
        return InterfaceType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_field(field_node) for field_node in type_def.fields
            ],
            interfaces=(
                # Interface types can be recursive. Cycles should be caught by
                # schema validation.
                self.delay(
                    lambda: [
                        cast(
                            InterfaceType,
                            self.build_type(interface),
                        )
                        for interface in type_def.interfaces
                    ],
                )
                if type_def.interfaces
                else None
            ),
            nodes=[type_def],
        )

    def _build_field(self, field_def: _ast.FieldDefinition) -> Field:
        return Field(
            field_def.name.value,
            # Object types can be recursive.
            self.delay(ft.partial(self.build_type, field_def.type)),
            description=_desc(field_def),
            args=(
                [self._build_argument(arg) for arg in field_def.arguments]
                if field_def.arguments
                else None
            ),
            deprecation_reason=_deprecation_reason(field_def),
            node=field_def,
        )

    def _build_enum_type(self, type_def: _ast.EnumTypeDefinition) -> EnumType:
        return EnumType(
            name=type_def.name.value,
            description=_desc(type_def),
            values=[self._build_enum_value(v) for v in type_def.values],
            nodes=[type_def],
        )

    def _build_enum_value(self, node: _ast.EnumValueDefinition) -> EnumValue:
        return EnumValue(
            name=node.name.value,
            description=_desc(node),
            value=node.name.value,
            deprecation_reason=_deprecation_reason(node),
            node=node,
        )

    def _build_union_type(
        self,
        type_def: _ast.UnionTypeDefinition,
    ) -> UnionType:
        return UnionType(
            name=type_def.name.value,
            description=_desc(type_def),
            types=[
                cast(ObjectType, self.build_type(type_))
                for type_ in type_def.types
            ],
            nodes=[type_def],
        )

    def _build_scalar_type(
        self,
        type_def: _ast.ScalarTypeDefinition,
    ) -> ScalarType:
        return default_scalar(
            name=type_def.name.value,
            description=_desc(type_def),
            nodes=[type_def],
        )

    def _build_input_object_type(
        self,
        type_def: _ast.InputObjectTypeDefinition,
    ) -> InputObjectType:
        return InputObjectType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_input_field(field_node)
                for field_node in type_def.fields
            ],
            nodes=[type_def],
        )

    def _build_argument(self, node: _ast.InputValueDefinition) -> Argument:
        type_ = self.build_type(node.type)
        default_value = InputField.NO_DEFAULT_VALUE  # type: Any
        if node.default_value is not None:
            default_value = value_from_ast(node.default_value, lazy(type_))

        return Argument(
            node.name.value,
            type_,
            default_value=default_value,
            description=_desc(node),
            node=node,
        )

    def _build_input_field(self, node: _ast.InputValueDefinition) -> InputField:
        default_value = InputField.NO_DEFAULT_VALUE  # type: Any
        if node.default_value is not None:
            # We need to support recursive input types, including recursive
            # default values. This should be possible as infinite cycles are not
            # possible in a valid SDL document (by virtue of it being a finite
            # string), which means any input cycle in the default value will be
            # broken, so this should not lead to recursion errors.
            default_value = self.delay(
                lambda: value_from_ast(
                    cast(_ast.Value, node.default_value),
                    lazy(self.build_type(node.type)),
                ),
            )

        return InputField(
            node.name.value,
            # Input object types can be recursive. Cycles should be caught by
            # schema validation.
            self.delay(ft.partial(self.build_type, node.type)),
            default_value=default_value,
            description=_desc(node),
            node=node,
        )

    def _extend_object_type(self, object_type: ObjectType) -> ObjectType:
        name = object_type.name
        extensions = self._collect_extensions(name, _ast.ObjectTypeExtension)

        field_names = set(f.name for f in object_type.fields)
        fields = [self._extend_field(f) for f in object_type.fields]

        for extension in extensions:
            for ext_field in extension.fields:
                if ext_field.name.value in field_names:
                    raise ExtensionError(
                        'Found duplicate field "%s" when extending type "%s"'
                        % (ext_field.name.value, object_type.name),
                        [ext_field],
                    )
                field_names.add(ext_field.name.value)
                fields.append(self._extend_field(self._build_field(ext_field)))

        interface_names = set(i.name for i in object_type.interfaces)
        interfaces = [
            cast(InterfaceType, self.extend_type(interface))
            for interface in object_type.interfaces
        ]

        for extension in extensions:
            for ext_interface in extension.interfaces:
                if ext_interface.name.value in interface_names:
                    raise ExtensionError(
                        'Interface "%s" already implemented for type "%s"'
                        % (ext_interface.name.value, object_type.name),
                        [ext_interface],
                    )
                interface_names.add(ext_interface.name.value)
                interfaces.append(
                    cast(
                        InterfaceType,
                        self.extend_type(self.build_type(ext_interface)),
                    ),
                )

        return ObjectType(
            name,
            description=object_type.description,
            fields=fields,
            interfaces=interfaces,
            nodes=object_type.nodes + extensions,  # type: ignore
        )

    def _extend_field(self, field_def: Field) -> Field:
        return Field(
            field_def.name,
            # Object types can be recursive.
            self.delay(ft.partial(self.extend_type, field_def.type)),
            description=field_def.description,
            deprecation_reason=field_def.deprecation_reason,
            args=[self._extend_argument(a) for a in field_def.arguments],
            resolver=field_def.resolver,
            node=field_def.node,
        )

    def _extend_interface_type(
        self,
        interface_type: InterfaceType,
    ) -> InterfaceType:
        name = interface_type.name
        extensions = self._collect_extensions(name, _ast.InterfaceTypeExtension)

        field_names = set(f.name for f in interface_type.fields)
        fields = [self._extend_field(f) for f in interface_type.fields]

        for extension in extensions:
            for ext_field in extension.fields:
                if ext_field.name.value in field_names:
                    raise ExtensionError(
                        'Found duplicate field "%s" when extending interface "%s"'
                        % (ext_field.name.value, interface_type.name),
                        [ext_field],
                    )
                field_names.add(ext_field.name.value)
                fields.append(self._extend_field(self._build_field(ext_field)))

        interface_names = set(i.name for i in interface_type.interfaces)
        # No need for this to be lazy as types should have already been resolved
        # and so not lead to any recursion error.
        interfaces = [
            cast(InterfaceType, self.extend_type(interface))
            for interface in interface_type.interfaces
        ]  # type: List[Lazy[InterfaceType]]

        for extension in extensions:
            for ext_interface in extension.interfaces:
                if ext_interface.name.value in interface_names:
                    raise ExtensionError(
                        f'Interface "{ext_interface.name.value}" already '
                        f'implemented for interface "{interface_type.name}"',
                        [ext_interface],
                    )
                interface_names.add(ext_interface.name.value)
                # Interface types can be recursive. Cycles should be caught by
                # schema validation.
                interfaces.append(
                    cast(
                        Callable[[], InterfaceType],
                        lambda x=ext_interface: self.extend_type(
                            self.build_type(x),
                        ),
                    ),
                )

        return InterfaceType(
            name,
            description=interface_type.description,
            fields=fields,
            # Interface types can be recursive. Cycles should be caught by
            # schema validation.
            interfaces=self.delay(lambda: [lazy(x) for x in interfaces]),
            nodes=interface_type.nodes + extensions,  # type: ignore
        )

    def _extend_enum_type(self, enum_type: EnumType) -> EnumType:
        name = enum_type.name
        extensions = self._collect_extensions(name, _ast.EnumTypeExtension)

        values = enum_type.values[:]
        value_names = set(ev.name for ev in values)

        for extension_node in extensions:
            for value in extension_node.values:
                if value.name.value in value_names:
                    raise ExtensionError(
                        'Found duplicate enum value "%s" when extending EnumType "%s"'
                        % (value.name.value, name),
                        [value],
                    )
                values.append(self._build_enum_value(value))
                value_names.add(value.name.value)

        return EnumType(
            name,
            description=enum_type.description,
            values=values,
            nodes=enum_type.nodes + extensions,  # type: ignore
        )

    def _extend_union_type(self, union_type: UnionType) -> UnionType:
        name = union_type.name
        extensions = self._collect_extensions(name, _ast.UnionTypeExtension)

        member_names = set(t.name for t in union_type.types)
        member_types = [
            cast(ObjectType, self.extend_type(t)) for t in union_type.types
        ]

        for extension_node in extensions:
            for type_def in extension_node.types:
                if type_def.name.value in member_names:
                    raise ExtensionError(
                        'Found duplicate member type "%s" when extending UnionType "%s"'
                        % (type_def.name.value, name),
                        [type_def],
                    )
                member_types.append(
                    cast(
                        ObjectType,
                        self.extend_type(self.build_type(type_def)),
                    ),
                )
                member_names.add(type_def.name.value)

        return UnionType(
            name,
            types=member_types,
            nodes=union_type.nodes + extensions,  # type: ignore
        )

    def _extend_input_object_type(
        self,
        input_object_type: InputObjectType,
    ) -> InputObjectType:
        name = input_object_type.name
        extensions = self._collect_extensions(
            name,
            _ast.InputObjectTypeExtension,
        )

        field_names = set(f.name for f in input_object_type.fields)
        fields = [
            InputField(
                f.name,
                # Input object types can be recursive. Cycles should be caught
                # by schema validation.
                self.delay(ft.partial(self.extend_type, f.type)),
                default_value=self.delay(lambda x=f: x._default_value),  # type: ignore
                description=f.description,
                node=f.node,
            )
            for f in input_object_type.fields
        ]

        for extension_node in extensions:
            for ext_field in extension_node.fields:
                if ext_field.name.value in field_names:
                    raise ExtensionError(
                        'Found duplicate field "%s" when extending input object "%s"'
                        % (ext_field.name.value, name),
                        [ext_field],
                    )
                field_names.add(ext_field.name.value)
                fields.append(
                    self._extend_input_field(
                        self._build_input_field(ext_field),
                    ),
                )

        return InputObjectType(
            name,
            description=input_object_type.description,
            fields=fields,
            nodes=input_object_type.nodes + extensions,  # type: ignore
        )

    def _extend_input_field(self, field: InputField) -> InputField:
        return InputField(
            field.name,
            # Input object types can be recursive. Cycles should be caught by
            # schema validation.
            self.delay(ft.partial(self.extend_type, field.type)),
            default_value=self.delay(lambda x=field: x._default_value),  # type: ignore
            description=field.description,
            node=field.node,
        )

    def _extend_scalar_type(self, scalar_type: ScalarType) -> ScalarType:
        name = scalar_type.name
        extensions = self._collect_extensions(name, _ast.ScalarTypeExtension)

        return ScalarType(
            name,
            description=scalar_type.description,
            serialize=scalar_type._serialize,
            parse=scalar_type._parse,
            parse_literal=scalar_type._parse_literal,
            nodes=scalar_type.nodes + extensions,  # type: ignore
        )

    def _extend_argument(self, argument: Argument) -> Argument:
        return Argument(
            argument.name,
            self.extend_type(argument.type),
            default_value=argument._default_value,
            description=argument.description,
            node=argument.node,
        )


def _deprecation_reason(
    node: Union[_ast.FieldDefinition, _ast.EnumValueDefinition],
) -> Optional[str]:
    args = directive_arguments(DeprecatedDirective, node, {})
    return args.get("reason", None) if args else None


def _desc(node: _ast.SupportDescription) -> Optional[str]:
    return node.description.value if node.description else None
