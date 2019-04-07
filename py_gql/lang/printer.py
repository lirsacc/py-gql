# -*- coding: utf-8 -*-

import json
from typing import Iterable, Optional, Union

from . import ast as _ast


class ASTPrinter:
    """ String formatter for ast node.

    Args:
        indent (Union[str, int]): Indent character or number of spaces

        include_descriptions (bool):
            If ``True`` include descriptions as leading block strings in the
            output. Only relevant for SDL nodes.

        use_legacy_comment_descriptions: Control how descriptions are formatted.
            Set to ``True`` for the old standard (use comments) which will be
            compatible with most GraphQL parsers while the default settings is
            to use block strings and is part of the most recent specification.
    """

    __slots__ = (
        "indent",
        "include_descriptions",
        "use_legacy_comment_descriptions",
    )

    def __init__(
        self,
        indent: Union[str, int] = 4,
        include_descriptions: bool = True,
        use_legacy_comment_descriptions: bool = False,
    ):
        self.include_descriptions = include_descriptions
        self.use_legacy_comment_descriptions = use_legacy_comment_descriptions
        if isinstance(indent, int):
            self.indent = indent * " "
        else:
            self.indent = indent

    def __call__(self, node: Optional[_ast.Node]) -> str:  # noqa: C901
        """ Converts an AST into a string, using a set of reasonable
        formatting rules.

        Args:
            node (py_gql.lang.ast.Node): Input node

        Returns:
            str: Formatted value for the provided node
        """
        if node is None:
            return ""

        if isinstance(node, _ast.Name):
            return self.print_name(node)
        elif isinstance(node, _ast.Variable):
            return self.print_variable(node)
        elif isinstance(node, _ast.Document):
            return self.print_document(node)
        elif isinstance(node, _ast.OperationDefinition):
            return self.print_operation_definition(node)
        elif isinstance(node, _ast.VariableDefinition):
            return self.print_variable_definition(node)
        elif isinstance(node, _ast.SelectionSet):
            return self.print_selection_set(node)
        elif isinstance(node, _ast.Field):
            return self.print_field(node)
        elif isinstance(node, _ast.Argument):
            return self.print_argument(node)
        elif isinstance(node, _ast.FragmentSpread):
            return self.print_fragment_spread(node)
        elif isinstance(node, _ast.InlineFragment):
            return self.print_inline_fragment(node)
        elif isinstance(node, _ast.IntValue):
            return self.print_int_value(node)
        elif isinstance(node, _ast.FloatValue):
            return self.print_float_value(node)
        elif isinstance(node, _ast.EnumValue):
            return self.print_enum_value(node)
        elif isinstance(node, _ast.BooleanValue):
            return self.print_boolean_value(node)
        elif isinstance(node, _ast.NullValue):
            return self.print_null_value(node)
        elif isinstance(node, _ast.StringValue):
            return self.print_string_value(node)
        elif isinstance(node, _ast.ListValue):
            return self.print_list_value(node)
        elif isinstance(node, _ast.ObjectValue):
            return self.print_object_value(node)
        elif isinstance(node, _ast.ObjectField):
            return self.print_object_field(node)
        elif isinstance(node, _ast.Directive):
            return self.print_directive(node)
        elif isinstance(node, _ast.NamedType):
            return self.print_named_type(node)
        elif isinstance(node, _ast.ListType):
            return self.print_list_type(node)
        elif isinstance(node, _ast.NonNullType):
            return self.print_non_null_type(node)
        elif isinstance(node, _ast.FragmentDefinition):
            return self.print_fragment_definition(node)
        elif isinstance(node, _ast.SchemaDefinition):
            return self.print_schema_definition(node)
        elif isinstance(node, _ast.SchemaExtension):
            return self.print_schema_extension(node)
        elif isinstance(node, _ast.OperationTypeDefinition):
            return self.print_operation_type_definition(node)
        elif isinstance(node, _ast.ScalarTypeDefinition):
            return self.print_scalar_type_definition(node)
        elif isinstance(node, _ast.ScalarTypeExtension):
            return self.print_scalar_type_extension(node)
        elif isinstance(node, _ast.ObjectTypeDefinition):
            return self.print_object_type_definition(node)
        elif isinstance(node, _ast.ObjectTypeExtension):
            return self.print_object_type_extension(node)
        elif isinstance(node, _ast.FieldDefinition):
            return self.print_field_definition(node)
        elif isinstance(node, _ast.InputValueDefinition):
            return self.print_input_value_definition(node)
        elif isinstance(node, _ast.InterfaceTypeDefinition):
            return self.print_interface_type_definition(node)
        elif isinstance(node, _ast.InterfaceTypeExtension):
            return self.print_interface_type_extension(node)
        elif isinstance(node, _ast.UnionTypeDefinition):
            return self.print_union_type_definition(node)
        elif isinstance(node, _ast.UnionTypeExtension):
            return self.print_union_type_extension(node)
        elif isinstance(node, _ast.EnumTypeDefinition):
            return self.print_enum_type_definition(node)
        elif isinstance(node, _ast.EnumTypeExtension):
            return self.print_enum_type_extension(node)
        elif isinstance(node, _ast.EnumValueDefinition):
            return self.print_enum_value_definition(node)
        elif isinstance(node, _ast.InputObjectTypeDefinition):
            return self.print_input_object_type_definition(node)
        elif isinstance(node, _ast.InputObjectTypeExtension):
            return self.print_input_object_type_extension(node)
        elif isinstance(node, _ast.DirectiveDefinition):
            return self.print_directive_definition(node)

        raise TypeError(type(node))

    def print_name(self, node: _ast.Name) -> str:
        return node.value

    def print_variable(self, node: _ast.Variable) -> str:
        return "$%s" % node.name.value

    def print_document(self, node: _ast.Document) -> str:
        return _join(map(self, node.definitions), "\n\n") + "\n"

    def print_operation_definition(self, node: _ast.OperationDefinition) -> str:
        op = node.operation
        name = node.name.value if node.name else ""
        var_defs = self.print_variable_definitions(node)
        directives = self.print_directives(node)
        selection_set = self._selection_set(node)
        use_short_form = (
            not name
            and not directives
            and not var_defs
            and (op == "query" or not op)
        )
        if use_short_form:
            return selection_set
        return _join(
            [op, _join([name, var_defs]), directives, selection_set], " "
        )

    def print_variable_definition(self, node: _ast.VariableDefinition) -> str:
        return "%s: %s%s" % (
            self.print_variable(node.variable),
            self(node.type),
            _wrap(" = ", self(node.default_value)),
        )

    def print_variable_definitions(
        self, node: Union[_ast.OperationDefinition, _ast.FragmentDefinition]
    ) -> str:
        return _wrap(
            "(",
            _join(
                map(self.print_variable_definition, node.variable_definitions),
                ", ",
            ),
            ")",
        )

    def _selection_set(
        self,
        node: Union[
            _ast.InlineFragment,
            _ast.FragmentDefinition,
            _ast.OperationDefinition,
            _ast.Field,
        ],
    ) -> str:
        return (
            self.print_selection_set(node.selection_set)
            if node.selection_set
            else ""
        )

    def print_selection_set(self, node: _ast.SelectionSet) -> str:
        return _block(map(self, node.selections), self.indent)

    def print_field(self, node: _ast.Field) -> str:
        if node.alias:
            lead = _join([_wrap("", node.alias.value, ": "), node.name.value])
        else:
            lead = node.name.value

        return _join(
            [
                _join([lead, self.print_arguments(node)]),
                self.print_directives(node),
                self._selection_set(node),
            ],
            " ",
        )

    def print_arguments(self, node: Union[_ast.Field, _ast.Directive]) -> str:
        return _wrap(
            "(", _join(map(self.print_argument, node.arguments), ", "), ")"
        )

    def print_argument(self, node: _ast.Argument) -> str:
        return "%s: %s" % (node.name.value, self(node.value))

    def print_fragment_spread(self, node: _ast.FragmentSpread) -> str:
        return "...%s%s" % (
            node.name.value,
            _wrap(" ", self.print_directives(node)),
        )

    def print_inline_fragment(self, node: _ast.InlineFragment) -> str:
        return _join(
            [
                "...",
                _wrap("on ", self(node.type_condition)),
                self.print_directives(node),
                self._selection_set(node),
            ],
            " ",
        )

    def print_int_value(self, node: _ast.IntValue) -> str:
        return node.value

    def print_float_value(self, node: _ast.FloatValue) -> str:
        return node.value

    def print_enum_value(self, node: _ast.EnumValue) -> str:
        return node.value

    def print_boolean_value(self, node: _ast.BooleanValue) -> str:
        return str(node.value).lower()

    def print_null_value(self, _node: _ast.NullValue) -> str:
        return "null"

    def print_string_value(self, node: _ast.StringValue) -> str:
        value = node.value
        return (
            _block_string(value, self.indent)
            if node.block
            else json.dumps(value)
        )

    def print_list_value(self, node: _ast.ListValue) -> str:
        return "[%s]" % _join(map(self, node.values), ", ")

    def print_object_value(self, node: _ast.ObjectValue) -> str:
        return "{%s}" % _join(map(self.print_object_field, node.fields), ", ")

    def print_object_field(self, node: _ast.ObjectField) -> str:
        return "%s: %s" % (node.name.value, self(node.value))

    def print_directives(self, node: _ast.SupportDirectives) -> str:
        return _join(map(self.print_directive, node.directives), " ")

    def print_directive(self, node: _ast.Directive) -> str:
        return "@%s%s" % (node.name.value, self.print_arguments(node))

    def print_named_type(self, node: _ast.NamedType) -> str:
        return node.name.value

    def print_list_type(self, node: _ast.ListType) -> str:
        return "[%s]" % self(node.type)

    def print_non_null_type(self, node: _ast.NonNullType) -> str:
        return "%s!" % self(node.type)

    # NOTE: fragment variable definitions are experimental and may be
    # changed or removed in the future.
    def print_fragment_definition(self, node: _ast.FragmentDefinition) -> str:
        return "fragment %s%s on %s %s%s" % (
            node.name.value,
            self.print_variable_definitions(node),
            self(node.type_condition),
            self.print_directives(node),
            self._selection_set(node),
        )

    def print_schema_definition(self, node: _ast.SchemaDefinition) -> str:
        return _join(
            [
                "schema",
                self.print_directives(node),
                _block(map(self, node.operation_types), self.indent),
            ],
            " ",
        )

    def print_schema_extension(self, node: _ast.SchemaExtension) -> str:
        return _join(
            [
                "extend schema",
                self.print_directives(node),
                _block(map(self, node.operation_types), self.indent),
            ],
            " ",
        )

    def print_operation_type_definition(
        self, node: _ast.OperationTypeDefinition
    ) -> str:
        return "%s: %s" % (node.operation, self(node.type))

    def print_scalar_type_definition(
        self, node: _ast.ScalarTypeDefinition
    ) -> str:
        return self._with_desc(
            _join(
                ["scalar", node.name.value, self.print_directives(node)], " "
            ),
            node.description,
        )

    def print_scalar_type_extension(
        self, node: _ast.ScalarTypeExtension
    ) -> str:
        return _join(
            ["extend scalar", node.name.value, self.print_directives(node)], " "
        )

    def print_object_type_definition(
        self, node: _ast.ObjectTypeDefinition
    ) -> str:
        return self._with_desc(
            _join(
                [
                    "type",
                    node.name.value,
                    _wrap(
                        "implements ", _join(map(self, node.interfaces), " & ")
                    ),
                    self.print_directives(node),
                    _block(map(self, node.fields), self.indent),
                ],
                " ",
            ),
            node.description,
        )

    def print_object_type_extension(
        self, node: _ast.ObjectTypeExtension
    ) -> str:
        return _join(
            [
                "extend type",
                node.name.value,
                _wrap("implements ", _join(map(self, node.interfaces), " & ")),
                self.print_directives(node),
                _block(map(self, node.fields), self.indent),
            ],
            " ",
        )

    def print_field_definition(self, node: _ast.FieldDefinition) -> str:
        return _join(
            [
                node.name.value,
                self.print_argument_definitions(node),
                ": ",
                self(node.type),
                _wrap(" ", self.print_directives(node)),
            ]
        )

    def print_input_value_definition(
        self, node: _ast.InputValueDefinition
    ) -> str:
        return _join(
            [
                _join([node.name.value, ": ", self(node.type)]),
                _wrap(" = ", self(node.default_value)),
                _wrap(" ", self.print_directives(node)),
            ]
        )

    def print_interface_type_definition(
        self, node: _ast.InterfaceTypeDefinition
    ) -> str:
        return self._with_desc(
            _join(
                [
                    "interface",
                    node.name.value,
                    self.print_directives(node),
                    _block(map(self, node.fields), self.indent),
                ],
                " ",
            ),
            node.description,
        )

    def print_interface_type_extension(
        self, node: _ast.InterfaceTypeExtension
    ) -> str:
        return _join(
            [
                "extend interface",
                node.name.value,
                self.print_directives(node),
                _block(map(self, node.fields), self.indent),
            ],
            " ",
        )

    def print_union_type_definition(
        self, node: _ast.UnionTypeDefinition
    ) -> str:
        return self._with_desc(
            _join(
                [
                    "union",
                    node.name.value,
                    self.print_directives(node),
                    _wrap("= ", _join(map(self, node.types), " | ")),
                ],
                " ",
            ),
            node.description,
        )

    def print_union_type_extension(self, node: _ast.UnionTypeExtension) -> str:
        return _join(
            [
                "extend union",
                node.name.value,
                self.print_directives(node),
                _wrap("= ", _join(map(self, node.types), " | ")),
            ],
            " ",
        )

    def print_enum_type_definition(self, node: _ast.EnumTypeDefinition) -> str:
        return self._with_desc(
            _join(
                [
                    "enum",
                    node.name.value,
                    self.print_directives(node),
                    _block(map(self, node.values), self.indent),
                ],
                " ",
            ),
            node.description,
        )

    def print_enum_type_extension(self, node: _ast.EnumTypeExtension) -> str:
        return _join(
            [
                "extend enum",
                node.name.value,
                self.print_directives(node),
                _block(map(self, node.values), self.indent),
            ],
            " ",
        )

    def print_enum_value_definition(
        self, node: _ast.EnumValueDefinition
    ) -> str:
        return _join([node.name.value, self.print_directives(node)], " ")

    def print_input_object_type_definition(
        self, node: _ast.InputObjectTypeDefinition
    ) -> str:
        return self._with_desc(
            _join(
                [
                    "input",
                    node.name.value,
                    self.print_directives(node),
                    _block(map(self, node.fields), self.indent),
                ],
                " ",
            ),
            node.description,
        )

    def print_input_object_type_extension(
        self, node: _ast.InputObjectTypeExtension
    ) -> str:
        return _join(
            [
                "extend input",
                node.name.value,
                self.print_directives(node),
                _block(map(self, node.fields), self.indent),
            ],
            " ",
        )

    def print_directive_definition(self, node: _ast.DirectiveDefinition) -> str:
        return self._with_desc(
            _join(
                [
                    "directive @",
                    node.name.value,
                    self.print_argument_definitions(node),
                    " on ",
                    _join(map(self, node.locations), " | "),
                ]
            ),
            node.description,
        )

    def print_argument_definitions(
        self, node: Union[_ast.FieldDefinition, _ast.DirectiveDefinition]
    ) -> str:
        args = list(map(self, node.arguments))
        if not any("\n" in a for a in args):
            return _wrap("(", _join(args, ", "), ")")
        else:
            return _wrap("(\n", _indent(_join(args, "\n"), self.indent), "\n)")

    def _with_desc(
        self, formatted: str, desc: Optional[_ast.StringValue]
    ) -> str:
        if desc is None or not self.include_descriptions:
            return formatted

        if not self.use_legacy_comment_descriptions:
            desc_str = _block_string(desc.value, self.indent, True)
        else:
            desc_str = "\n".join(
                ("# " + line for line in desc.value.split("\n"))
            )

        return _join([desc_str, formatted], "\n")


def _wrap(start: str, maybe_string: Optional[str], end: str = "") -> str:
    return "%s%s%s" % (start, maybe_string, end) if maybe_string else ""


def _join(entries: Iterable[str], separator: str = "") -> str:
    if not entries:
        return ""
    return separator.join([x for x in entries if x])


def _indent(maybe_string: str, indent: str) -> str:
    return maybe_string and (indent + maybe_string.replace("\n", "\n  "))


def _block(iterator: Iterable[str], indent: str) -> str:
    arr = list(iterator)
    if not arr:
        return ""
    return "{\n%s\n}" % _join(map(lambda s: _indent(s, indent), arr), "\n")


# Print a block string in the indented block form by adding a leading and
# trailing blank line. However, if a block string starts with whitespace and
# is a single-line, adding a leading blank line would strip that whitespace.
def _block_string(value: str, indent: str, is_description: bool = False) -> str:
    escaped = value.replace('"""', '\\"""')
    if (value[0] == " " or value[0] == "\t") and "\n" not in value:
        if escaped.endswith('"'):
            escaped = escaped + "\n"
        return '"""%s"""' % escaped
    return '"""\n%s\n"""' % (
        escaped if is_description else _indent(escaped, indent)
    )


def print_ast(
    node: _ast.Node, indent: int = 2, include_descriptions: bool = True
) -> str:
    """ Converts an AST node into a valid GraphQL string, using a set of
    reasonable formatting rules.

    Args:
        node (py_gql.lanf.ast.Node): Node to format.

        indent (Union[str, int]): Indent character or number of spaces

        include_descriptions (bool):
            If ``True`` include descriptions as leading block strings in the
            output. Only relevant for SDL nodes.

    Returns:
        str:
    """
    return ASTPrinter(indent=indent, include_descriptions=include_descriptions)(
        node
    )
