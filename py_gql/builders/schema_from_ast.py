# -*- coding: utf-8 -*-

import collections
import functools as ft
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

from .._utils import lazy
from ..exc import ExtensionError, SDLError
from ..lang import ast as _ast, parse
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
    Schema,
    UnionType,
)
from ..schema.introspection import INTROPSPECTION_TYPES
from ..schema.scalars import default_scalar
from ..utilities import directive_arguments, value_from_ast
from .schema_directives import SchemaDirective, apply_schema_directives

T = TypeVar("T", bound=type)
TTypeExtension = TypeVar("TTypeExtension", bound=Type[_ast.TypeExtension])


_DEFAULT_TYPES_MAP = {}  # type: Dict[str, NamedType]

for t in SPECIFIED_SCALAR_TYPES:
    _DEFAULT_TYPES_MAP[t.name] = t

for t in INTROPSPECTION_TYPES:
    _DEFAULT_TYPES_MAP[t.name] = t


__all__ = ("build_schema", "extend_schema")


def build_schema(
    # fmt: off
    document: Union[_ast.Document, str],
    *,
    additional_types: Optional[List[NamedType]] = None,
    schema_directives: Optional[Mapping[str, Type[SchemaDirective]]] = None
    # fmt: on
) -> Schema:
    """ Build an executable schema from a GraphQL document.

    This includes:

        - Generating types from their definitions
        - Applying schema and type extensions
        - Applying schema directives

    Args:
        document: SDL document

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
            corresponding definition must be present in the document.

            See :func:`~py_gql.schema.apply_schema_directives` for more details.

    Returns:
        Executable schema

    Raises:
        py_gql.exc.SDLError:
    """
    ast = _document_ast(document)
    schema = build_schema_ignoring_extensions(
        ast, additional_types=additional_types
    )

    schema = extend_schema(
        schema, ast, additional_types=additional_types, strict=False
    )

    if schema_directives:
        schema = apply_schema_directives(schema, schema_directives)

    schema.validate()

    return schema


def build_schema_ignoring_extensions(
    # fmt: off
    document: Union[_ast.Document, str],
    *,
    additional_types: Optional[List[NamedType]] = None
    # fmt: on
) -> Schema:
    """ Build an executable schema from an SDL-based schema definition ignoring
    extensions.

    Args:
        document: SDL document

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

    types = [builder.build_type(type_def) for type_def in type_defs.values()]

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
    # fmt: off
    schema: Schema,
    document: Union[_ast.Document, str],
    *,
    additional_types: Optional[List[NamedType]] = None,
    strict: bool = True
    # fmt: on
) -> Schema:
    """ Extend an existing Schema according to a GraphQL document (adding new
    types and directives + extending known types).

    Warning:
        Specified types (scalars, introspection) cannot be replace or extended.

    Args:
        schema (py_gql.schema.Schema): Executable schema

        document (Union[str, _ast.Document]): SDL document

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

    builder = ASTTypeBuilder(
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


def _deprecation_reason(
    node: Union[_ast.FieldDefinition, _ast.EnumValueDefinition]
) -> Optional[str]:
    args = directive_arguments(DeprecatedDirective, node, {})
    return args.get("reason", None) if args else None


def _desc(node: _ast.SupportDescription) -> Optional[str]:
    return node.description.value if node.description else None


class ASTTypeBuilder:
    """ Build and extend type definitions from AST nodes.

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

    def _collect_extensions(
        self, target_name: str, ext_type: TTypeExtension
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
        self, type_node: Union[_ast.Type, _ast.TypeDefinition]
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
                            "Type %s not found in document" % type_name,
                            [type_node],
                        )
                else:
                    type_def = cast(_ast.TypeDefinition, type_node)

                if isinstance(type_def, _ast.ObjectTypeDefinition):
                    built = self._build_object_type(
                        type_def
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
        self, directive_def: _ast.DirectiveDefinition
    ) -> Directive:
        return Directive(
            name=directive_def.name.value,
            description=_desc(directive_def),
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
            locations=directive.locations,
            args=[self._extend_argument(a) for a in directive.arguments],
            node=directive.node,
        )

    def _build_object_type(
        self, type_def: _ast.ObjectTypeDefinition
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
        self, type_def: _ast.InterfaceTypeDefinition
    ) -> InterfaceType:
        return InterfaceType(
            name=type_def.name.value,
            description=_desc(type_def),
            fields=[
                self._build_field(field_node) for field_node in type_def.fields
            ],
            nodes=[type_def],
        )

    def _build_field(self, field_def: _ast.FieldDefinition) -> Field:
        return Field(
            field_def.name.value,
            # has to be lazy to support cyclic definition
            ft.partial(self.build_type, field_def.type),
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
        self, type_def: _ast.UnionTypeDefinition
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
        self, type_def: _ast.ScalarTypeDefinition
    ) -> ScalarType:
        return default_scalar(
            name=type_def.name.value,
            description=_desc(type_def),
            nodes=[type_def],
        )

    def _build_input_object_type(
        self, type_def: _ast.InputObjectTypeDefinition
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
        kwargs = dict(description=_desc(node), node=node)
        if node.default_value is not None:
            kwargs["default_value"] = value_from_ast(
                node.default_value, lazy(type_)
            )
        return Argument(node.name.value, type_, **kwargs)  # type: ignore

    def _build_input_field(self, node: _ast.InputValueDefinition) -> InputField:
        type_ = self.build_type(node.type)
        kwargs = dict(description=_desc(node), node=node)
        if node.default_value is not None:
            kwargs["default_value"] = value_from_ast(
                node.default_value, lazy(type_)
            )
        return InputField(node.name.value, type_, **kwargs)  # type: ignore

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
                    )
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
            lambda: self.extend_type(field_def.type),
            description=field_def.description,
            deprecation_reason=field_def.deprecation_reason,
            args=[self._extend_argument(a) for a in field_def.arguments],
            resolver=field_def.resolver,
            node=field_def.node,
        )

    def _extend_interface_type(
        self, interface_type: InterfaceType
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

        return InterfaceType(
            name,
            description=interface_type.description,
            fields=fields,
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
                        ObjectType, self.extend_type(self.build_type(type_def))
                    )
                )
                member_names.add(type_def.name.value)

        return UnionType(
            name,
            types=member_types,
            nodes=union_type.nodes + extensions,  # type: ignore
        )

    def _extend_input_object_type(
        self, input_object_type: InputObjectType
    ) -> InputObjectType:
        name = input_object_type.name
        extensions = self._collect_extensions(
            name, _ast.InputObjectTypeExtension
        )

        field_names = set(f.name for f in input_object_type.fields)
        fields = [
            InputField(
                f.name,
                self.extend_type(f.type),
                default_value=f._default_value,
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
                fields.append(self._build_input_field(ext_field))

        return InputObjectType(
            name,
            description=input_object_type.description,
            fields=fields,
            nodes=input_object_type.nodes + extensions,  # type: ignore
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
