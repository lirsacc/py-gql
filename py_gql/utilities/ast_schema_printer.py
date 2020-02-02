# -*- coding: utf-8 -*-
""" Export schema as SDL. """

from typing import Any, Sequence, Union

from .._string_utils import wrapped_lines
from .._utils import flatten
from ..lang import print_ast
from ..schema import (
    SPECIFIED_DIRECTIVES,
    SPECIFIED_SCALAR_TYPES,
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputObjectType,
    InputValue,
    InterfaceType,
    ObjectType,
    ScalarType,
    Schema,
    String,
    UnionType,
)
from ..schema.directives import DEFAULT_DEPRECATION
from ..schema.introspection import is_introspection_type
from .ast_node_from_value import ast_node_from_value


class ASTSchemaPrinter:
    """
    Encode schema serialisation as a valid SDL document.

    Args:
        indent: Indent character or number of spaces

        include_descriptions: If ``True`` include descriptions in the output

        use_legacy_comment_descriptions: Control how descriptions are formatted.
            Set to ``True`` for the old standard (use comments) which will be
            compatible with most GraphQL parsers while the default settings is
            to use block strings and is part of the most recent specification.

        include_introspection: If ``True``, include introspection types in the output

        include_custom_directives: Include custom directives collected when
            building the schema from an SDL document.

            By default this class will not print any directive included in the
            schema as there is no guarantee any external tooling consuming the
            SDL will undertand them. You can set this flag to ``True`` to
            include all of them or use a whitelist of directive names.

            This applies only to directive locations and not directive
            definitions as they could be relevant to clients regardless of their
            use in the schema.
    """

    __slots__ = (
        "indent",
        "include_descriptions",
        "use_legacy_comment_descriptions",
        "include_introspection",
        "include_custom_directives",
    )

    def __init__(
        self,
        indent: Union[str, int] = 4,
        include_descriptions: bool = True,
        include_introspection: bool = False,
        # TODO: Can this be dropped?
        use_legacy_comment_descriptions: bool = False,
        include_custom_directives: Union[bool, Sequence[str]] = False,
    ):
        self.include_descriptions = include_descriptions
        self.use_legacy_comment_descriptions = use_legacy_comment_descriptions

        if isinstance(indent, int):
            self.indent = indent * " "  # type: str
        else:
            self.indent = indent

        self.include_introspection = include_introspection
        self.include_custom_directives = include_custom_directives

    def __call__(self, schema: Schema) -> str:
        directives = sorted(
            (
                d
                for d in schema.directives.values()
                if d not in SPECIFIED_DIRECTIVES
            ),
            key=lambda x: x.name,
        )

        types = sorted(
            (
                t
                for t in schema.types.values()
                if (
                    t not in SPECIFIED_SCALAR_TYPES
                    and (
                        self.include_introspection
                        or not is_introspection_type(t)
                    )
                )
            ),
            key=lambda x: x.name,
        )

        parts = (
            [self.print_schema_definition(schema)]
            + (
                [
                    self.print_directive_definition(d)
                    for d in SPECIFIED_DIRECTIVES
                ]
                if self.include_introspection
                else []
            )
            + [self.print_directive_definition(d) for d in directives]
            + [self.print_type(t) for t in types]
        )

        if not any(p for p in parts):
            return ""
        return "\n\n".join(part for part in parts if part) + "\n"

    def print_description(
        self, definition: Any, depth: int = 0, first_in_block: bool = True
    ) -> str:
        """ Format an object description according to current configuration.

        Args:
            definitions: Described object
            depth: Level of indentation
            first_in_block:
        """
        if not self.include_descriptions or not definition.description:
            return ""

        indent = self.indent * depth

        if self.use_legacy_comment_descriptions:
            prefix = indent + "# "
            max_len = 120 - len(prefix)
            lines = [
                (prefix + line.rstrip()) if line else "#"
                for line in wrapped_lines(
                    definition.description.split("\n"), max_len
                )
            ]
            return (
                ("\n" if not first_in_block else "") + "\n".join(lines) + "\n"
            )

        else:
            max_len = 120 - len(indent)
            lines = list(
                wrapped_lines(definition.description.split("\n"), max_len)
            )
            first = lines[0]

            if len(lines) == 1 and len(first) < 70 and not first.endswith('"'):
                body = first.replace('"""', '\\"""')
            else:
                has_leading_whitespace = len(first) > len(first.lstrip())
                body = (
                    "\n".join(
                        [
                            "%s%s%s"
                            % (
                                "\n"
                                if (i == 0 and not has_leading_whitespace)
                                else "",
                                indent
                                if (i > 0 or not has_leading_whitespace)
                                else "",
                                line.replace('"""', '\\"""'),
                            )
                            for i, line in enumerate(lines)
                        ]
                    )
                    + "\n"
                    + indent
                )

            return '%s%s"""%s"""\n' % (
                "\n" if indent and not first_in_block else "",
                indent,
                body,
            )

    def print_deprecated(
        self, field_or_enum_value: Union[Field, EnumValue]
    ) -> str:
        if not field_or_enum_value.deprecated:
            return ""
        elif (
            not field_or_enum_value.deprecation_reason
            or field_or_enum_value.deprecation_reason == DEFAULT_DEPRECATION
        ):
            return " @deprecated"
        return " @deprecated(reason: %s)" % print_ast(
            ast_node_from_value(field_or_enum_value.deprecation_reason, String)
        )

    def include_custom_directive(self, directive_name: str) -> bool:
        known_directive_names = (d.name for d in SPECIFIED_DIRECTIVES)
        if directive_name in known_directive_names:
            return False

        if not isinstance(self.include_custom_directives, bool):
            return directive_name in self.include_custom_directives
        else:
            return True

    def print_directives(
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
    ) -> str:
        if not self.include_custom_directives:
            return ""

        if isinstance(definition, (Field, InputValue, EnumValue)):
            directives_nodes = (
                definition.node.directives
                if definition.node is not None
                else []
            )
        else:
            directives_nodes = list(
                flatten(n.directives for n in definition.nodes if n)
            )

        if not directives_nodes:
            return ""

        return " " + " ".join(
            print_ast(directive_node)
            for directive_node in directives_nodes
            if self.include_custom_directive(directive_node.name.value)
        )

    def print_type(self, type_: GraphQLType) -> str:
        if isinstance(type_, ScalarType):
            return self.print_scalar_type(type_)
        elif isinstance(type_, ObjectType):
            return self.print_object_type(type_)
        elif isinstance(type_, InterfaceType):
            return self.print_interface_type(type_)
        elif isinstance(type_, UnionType):
            return self.print_union_type(type_)
        elif isinstance(type_, EnumType):
            return self.print_enum_type(type_)
        elif isinstance(type_, InputObjectType):
            return self.print_input_object_type(type_)

        raise TypeError(type_)

    def print_scalar_type(self, type_: ScalarType) -> str:
        return "%sscalar %s%s" % (
            self.print_description(type_, 0, True),
            type_.name,
            self.print_directives(type_),
        )

    def print_enum_type(self, type_: EnumType) -> str:
        return "%senum %s%s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            self.print_directives(type_),
            "\n".join(
                [
                    "".join(
                        [
                            self.print_description(enum_value, 1, not i),
                            self.indent,
                            enum_value.name,
                            self.print_deprecated(enum_value),
                            self.print_directives(enum_value),
                        ]
                    ).rstrip()
                    for i, enum_value in enumerate(type_.values)
                ]
            ),
        )

    def print_union_type(self, type_: UnionType) -> str:
        return "%sunion %s%s = %s" % (
            self.print_description(type_),
            type_.name,
            self.print_directives(type_),
            " | ".join((t.name for t in type_.types)),
        )

    def print_object_type(self, type_: ObjectType) -> str:
        return "%stype %s%s%s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            (
                " implements %s"
                % " & ".join([i.name for i in type_.interfaces])
                if type_.interfaces
                else ""
            ),
            self.print_directives(type_),
            self.print_fields(type_),
        )

    def print_interface_type(self, type_: InterfaceType) -> str:
        return "%sinterface %s%s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            self.print_directives(type_),
            self.print_fields(type_),
        )

    def print_fields(self, type_: Union[ObjectType, InterfaceType]) -> str:
        return "\n".join(
            [
                "".join(
                    [
                        self.print_description(field, 1, not i),
                        self.indent,
                        field.name,
                        self.print_arguments(field.arguments, 1),
                        ": %s" % field.type,
                        self.print_deprecated(field),
                        self.print_directives(field),
                    ]
                ).rstrip()
                for i, field in enumerate(type_.fields)
            ]
        )

    def print_input_object_type(self, type_: InputObjectType) -> str:
        return "%sinput %s%s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            self.print_directives(type_),
            "\n".join(
                [
                    "%s%s%s"
                    % (
                        self.print_description(field, 1, not i),
                        self.indent,
                        self.print_input_value(field),
                    )
                    for i, field in enumerate(type_.fields)
                ]
            ),
        )

    def print_directive_definition(self, directive: Directive) -> str:
        return "%sdirective @%s%s on %s" % (
            self.print_description(directive),
            directive.name,
            self.print_arguments(directive.arguments, 0),
            " | ".join(directive.locations),
        )

    def print_arguments(self, args: Sequence[Argument], depth: int = 0) -> str:
        if not args:
            return ""

        indent = self.indent * depth
        if self.include_descriptions and any(a.description for a in args):
            return "%s(\n%s\n%s)" % (
                indent,
                "\n".join(
                    [
                        "".join(
                            [
                                self.print_description(arg, depth + 1, not i),
                                self.indent + indent,
                                self.print_input_value(arg),
                            ]
                        )
                        for i, arg in enumerate(args)
                    ]
                ),
                indent,
            )
        else:
            return "(%s)" % ", ".join(
                [self.print_input_value(arg) for arg in args]
            )

    def print_input_value(self, arg_or_inut_field: Union[InputValue]) -> str:
        s = "%s: %s" % (arg_or_inut_field.name, arg_or_inut_field.type)
        if arg_or_inut_field.has_default_value:
            s += " = %s" % print_ast(
                ast_node_from_value(
                    arg_or_inut_field.default_value, arg_or_inut_field.type
                )
            )
        return (s + self.print_directives(arg_or_inut_field)).strip()

    def print_schema_definition(self, schema: Schema) -> str:
        directives = self.print_directives(schema)

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
        ):
            return ""

        operation_types = []
        if schema.query_type:
            operation_types.append(
                "%squery: %s" % (self.indent, schema.query_type.name)
            )
        if schema.mutation_type:
            operation_types.append(
                "%smutation: %s" % (self.indent, schema.mutation_type.name)
            )
        if schema.subscription_type:
            operation_types.append(
                "%ssubscription: %s"
                % (self.indent, schema.subscription_type.name)
            )

        return "schema%s {\n%s\n}" % (directives, "\n".join(operation_types))
