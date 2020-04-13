from typing import Container, List, Optional, Union

from .._utils import flatten
from ..lang import ast
from ..schema import (
    SPECIFIED_DIRECTIVES,
    SPECIFIED_SCALAR_TYPES,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputObjectType,
    InputValue,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    UnionType,
    is_introspection_type,
)
from ..schema.directives import DEFAULT_DEPRECATION
from ..utilities.ast_node_from_value import ast_node_from_value


_SPECIFIED_DIRECTIVE_NAMES = (d.name for d in SPECIFIED_DIRECTIVES)


class ASTSchemaConverter:
    """
    Convert a Schema to a valid GraphQL schema definition Document.

    Args:
        include_introspection: If ``True``, include introspection types in the output
        include_custom_schema_directives: Include custom directives collected when
            building the schema from an SDL document.

            By default this class will not include any custom schema directive
            included in the schema as there is no guarantee external tooling
            consuming the resulting AST will understand them. You can set
            this flag to ``True`` to include all of them or use a whitelist of
            directive names to only include some of them.

            This applies only to directive locations and not directive
            definitions as they could be relevant to clients regardless of
            their use in the schema.

    """

    def __init__(
        self,
        include_introspection: bool = False,
        include_custom_schema_directives: Union[bool, Container[str]] = False,
    ) -> None:
        self.include_introspection = include_introspection
        self.include_custom_schema_directives = include_custom_schema_directives

    def __call__(self, schema: Schema) -> ast.Document:
        definitions = []  # type: List[ast.Definition]

        for d in sorted(schema.directives.values(), key=lambda x: x.name):
            if not self.include_introspection and d in SPECIFIED_DIRECTIVES:
                continue

            definitions.append(self.directive(d))

        schema_def = self.schema(schema)
        if schema_def:
            definitions.append(schema_def)

        for t in sorted(schema.types.values(), key=lambda x: x.name):
            if t in SPECIFIED_SCALAR_TYPES or (
                not self.include_introspection and is_introspection_type(t)
            ):
                continue

            if isinstance(t, ScalarType):
                definitions.append(self.scalar_type(t))
            elif isinstance(t, ObjectType):
                definitions.append(self.object_type(t))
            elif isinstance(t, InterfaceType):
                definitions.append(self.interface_type(t))
            elif isinstance(t, UnionType):
                definitions.append(self.union_type(t))
            elif isinstance(t, EnumType):
                definitions.append(self.enum_type(t))
            elif isinstance(t, InputObjectType):
                definitions.append(self.input_type(t))

        return ast.Document(definitions=definitions)

    def schema(self, schema: Schema) -> Optional[ast.SchemaDefinition]:
        directives = self.directive_nodes(schema)

        if (
            not directives
            and (not schema.query_type or schema.query_type.name == "Query")
            and (
                not schema.mutation_type
                or schema.mutation_type.name == "Mutation"
            )
            and (
                not schema.subscription_type
                or schema.subscription_type.name == "Subscription"
            )
            and not schema.description
        ):
            return None

        operation_types = []
        if schema.query_type:
            operation_types.append(
                ast.OperationTypeDefinition(
                    "query", _named_type(schema.query_type)
                )
            )
        if schema.mutation_type:
            operation_types.append(
                ast.OperationTypeDefinition(
                    "mutation", _named_type(schema.mutation_type),
                )
            )
        if schema.subscription_type:
            operation_types.append(
                ast.OperationTypeDefinition(
                    "subscription", _named_type(schema.subscription_type),
                )
            )

        return ast.SchemaDefinition(
            directives=directives,
            operation_types=operation_types,
            description=_desc_node(schema.description),
        )

    def object_type(self, object_type: ObjectType) -> ast.ObjectTypeDefinition:
        return ast.ObjectTypeDefinition(
            name=ast.Name(value=object_type.name),
            interfaces=[_named_type(i) for i in object_type.interfaces],
            directives=self.directive_nodes(object_type),
            fields=[self.field(f) for f in object_type.fields],
            description=_desc_node(object_type.description),
        )

    def interface_type(
        self, interface_type: InterfaceType
    ) -> ast.InterfaceTypeDefinition:
        return ast.InterfaceTypeDefinition(
            name=ast.Name(value=interface_type.name),
            directives=self.directive_nodes(interface_type),
            fields=[self.field(f) for f in interface_type.fields],
            description=_desc_node(interface_type.description),
        )

    def union_type(self, union_type: UnionType) -> ast.UnionTypeDefinition:
        return ast.UnionTypeDefinition(
            name=ast.Name(value=union_type.name),
            directives=self.directive_nodes(union_type),
            types=[_named_type(t) for t in union_type.types],
            description=_desc_node(union_type.description),
        )

    def input_type(
        self, input_type: InputObjectType
    ) -> ast.InputObjectTypeDefinition:
        return ast.InputObjectTypeDefinition(
            name=ast.Name(value=input_type.name),
            directives=self.directive_nodes(input_type),
            fields=[self.input_value(f) for f in input_type.fields],
            description=_desc_node(input_type.description),
        )

    def scalar_type(self, scalar_type: ScalarType) -> ast.ScalarTypeDefinition:
        return ast.ScalarTypeDefinition(
            name=ast.Name(value=scalar_type.name),
            directives=self.directive_nodes(scalar_type),
            description=_desc_node(scalar_type.description),
        )

    def enum_type(self, enum_type: EnumType) -> ast.EnumTypeDefinition:
        return ast.EnumTypeDefinition(
            name=ast.Name(value=enum_type.name),
            directives=self.directive_nodes(enum_type),
            description=_desc_node(enum_type.description),
            values=[
                ast.EnumValueDefinition(
                    name=ast.Name(value=ev.name),
                    directives=self.directive_nodes(ev),
                    description=_desc_node(ev.description),
                )
                for ev in enum_type.values
            ],
        )

    def field(self, field: Field) -> ast.FieldDefinition:
        return ast.FieldDefinition(
            name=ast.Name(value=field.name),
            arguments=[self.input_value(a) for a in field.arguments],
            type=_type_node(field.type),
            directives=self.directive_nodes(field),
            description=_desc_node(field.description),
        )

    def directive(self, directive: Directive) -> ast.DirectiveDefinition:
        return ast.DirectiveDefinition(
            name=ast.Name(value=directive.name),
            arguments=[self.input_value(a) for a in directive.arguments],
            repeatable=directive.repeatable,
            locations=[ast.Name(value=loc) for loc in directive.locations],
            description=_desc_node(directive.description),
        )

    def input_value(self, iv: InputValue) -> ast.InputValueDefinition:
        return ast.InputValueDefinition(
            name=ast.Name(value=iv.name),
            type=_type_node(iv.type),
            directives=self.directive_nodes(iv),
            default_value=(
                ast_node_from_value(iv.default_value, iv.type)
                if iv.has_default_value
                else None
            ),
            description=_desc_node(iv.description),
        )

    def include_directive(self, name: str) -> bool:
        # The only specified schema directive is currently @deprecated and
        # it special cased to handle code-based schemas.
        if name in _SPECIFIED_DIRECTIVE_NAMES:
            return False

        if not isinstance(self.include_custom_schema_directives, bool):
            return name in self.include_custom_schema_directives
        else:
            return True

    def directive_nodes(
        self,
        definition: Union[
            EnumType,
            EnumValue,
            Field,
            InputObjectType,
            InputValue,
            InterfaceType,
            ObjectType,
            ScalarType,
            Schema,
            UnionType,
        ],
    ) -> List[ast.Directive]:

        directives = []

        if isinstance(definition, (Field, EnumValue)):
            if definition.deprecated:
                directives.append(
                    ast.Directive(
                        name=ast.Name(value="deprecated"),
                        arguments=[
                            ast.Argument(
                                name=ast.Name("reason"),
                                value=ast.StringValue(
                                    value=definition.deprecation_reason
                                ),
                            )
                        ]
                        if definition.deprecation_reason
                        and definition.deprecation_reason != DEFAULT_DEPRECATION
                        else [],
                    )
                )

        if not self.include_custom_schema_directives:
            return directives

        if isinstance(definition, (Field, InputValue, EnumValue)):
            nodes = (
                definition.node.directives
                if definition.node is not None
                else []
            )
        else:
            nodes = list(flatten(n.directives for n in definition.nodes if n))

        if not nodes:
            return directives

        return directives + [
            d for d in nodes if self.include_directive(d.name.value)
        ]


def _type_node(t: GraphQLType) -> ast.Type:
    if isinstance(t, NonNullType):
        return ast.NonNullType(type=_type_node(t.type))
    elif isinstance(t, ListType):
        return ast.ListType(type=_type_node(t.type))
    elif isinstance(t, NamedType):
        return ast.NamedType(name=ast.Name(value=t.name))
    raise TypeError(type(t))


def _desc_node(desc: Optional[str]) -> Optional[ast.StringValue]:
    return None if desc is None else ast.StringValue(value=desc)


def _named_type(t: NamedType) -> ast.NamedType:
    return ast.NamedType(name=ast.Name(value=t.name))
