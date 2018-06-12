# -*- coding: utf-8 -*-
""" Converting AST and values into nicely, standardised formatted strings.
"""

import json

from six.moves import map

from py_gql.lang import ast as _ast


def print_ast(node):  # noqa: C901
    """ Converts an AST into a string, using one set of reasonable
    formatting rules.

    Useful to print some isoldated nodes in errors or for debugging.

    Args:
        node (py_gql.lang.ast.Node): Ast node to print

    Returns:
        str: Formatted value for the provided node
    """
    kind = type(node)

    _print = print_ast
    _map = lambda c: map(_print, c if c is not None else [])
    _value = lambda: _print(node.value)
    _var_defs = lambda: _wrap("(", _join(_map(node.variable_definitions), ", "), ")")
    _directives = lambda: _join(_map(node.directives), " ")
    _name = lambda: node.name.value
    _type = lambda: _print(node.type)
    _selection_set = lambda: _print(node.selection_set)
    _args = lambda: _wrap("(", _join(_map(node.arguments), ", "), ")")

    _with_desc = lambda s: (
        _join([_block_string(node.description.value, True), s], "\n")
        if node.description
        else s
    )

    def _arg_defs():
        args = list(_map(node.arguments))
        if not any(("\n" in a for a in args)):
            return _wrap("(", _join(args, ", "), ")")
        else:
            return _wrap("(\n", _indent(_join(args, "\n")), "\n)")

    if kind is _ast.Name:
        return node.value

    if kind is _ast.Variable:
        return "$%s" % _name()

    if kind is _ast.Document:
        return _join(_map(node.definitions), "\n\n") + "\n"

    if kind is _ast.OperationDefinition:
        op = node.operation
        name = node.name.value if node.name else ""
        var_defs = _var_defs()
        directives = _directives()
        selection_set = _selection_set()
        return (
            # Anonymous queries with no directives or variable definitions
            # can use the query short form.
            selection_set
            if (
                (not name)
                and (not directives)
                and (not var_defs)
                and (op == "query" or not op)
            )
            else _join([op, _join([name, var_defs]), directives, selection_set], " ")
        )

    if kind is _ast.VariableDefinition:
        return "%s: %s%s" % (
            _print(node.variable),
            _print(node.type),
            _wrap(" = ", _print(node.default_value)),
        )

    if kind is _ast.SelectionSet:
        return _block(_map(node.selections))

    if kind is _ast.Field:
        return _join(
            [
                _join([_wrap("", _print(node.alias), ": "), _name(), _args()]),
                _directives(),
                _selection_set(),
            ],
            " ",
        )

    if kind is _ast.Argument:
        return "%s: %s" % (_name(), _value())

    if kind is _ast.FragmentSpread:
        return "...%s%s" % (_name(), _wrap(" ", _directives()))

    if kind is _ast.InlineFragment:
        return _join(
            [
                "...",
                _wrap("on ", _print(node.type_condition)),
                _directives(),
                _selection_set(),
            ],
            " ",
        )

    if kind is _ast.IntValue:
        return node.value

    if kind is _ast.FloatValue:
        return node.value

    if kind is _ast.EnumValue:
        return node.value

    if kind is _ast.BooleanValue:
        return str(node.value).lower()

    if kind is _ast.NullValue:
        return "null"

    if kind is _ast.StringValue:
        value = node.value
        return _block_string(value) if node.block else json.dumps(value)

    if kind is _ast.ListValue:
        return "[%s]" % _join(_map(node.values), ", ")

    if kind is _ast.ObjectValue:
        return "{%s}" % _join(_map(node.fields), ", ")

    if kind is _ast.ObjectField:
        return "%s: %s" % (_name(), _value())

    if kind is _ast.Directive:
        return "@%s%s" % (_name(), _args())

    if kind is _ast.NamedType:
        return node.name.value

    if kind is _ast.ListType:
        return "[%s]" % _print(node.type)

    if kind is _ast.NonNullType:
        return "%s!" % _print(node.type)

    # NOTE: fragment variable definitions are experimental and may be
    # changed or removed in the future.
    if kind is _ast.FragmentDefinition:
        return "fragment %s%s on %s %s%s" % (
            _name(),
            _var_defs(),
            _print(node.type_condition),
            _directives(),
            _selection_set(),
        )

    if kind is _ast.SchemaDefinition:
        return _join(["schema", _directives(), _block(_map(node.operation_types))])

    if kind is _ast.OperationTypeDefinition:
        return "%s: %s" % (node.operation, _type())

    if kind is _ast.ScalarTypeDefinition:
        return _with_desc(_join(["scalar", _name(), _directives()], " "))

    if kind is _ast.ScalarTypeExtension:
        return _join(["extend scalar", _name(), _directives()], " ")

    if kind is _ast.ObjectTypeDefinition:
        return _with_desc(
            _join(
                [
                    "type",
                    _name(),
                    _wrap("implements ", _join(_map(node.interfaces), " & ")),
                    _directives(),
                    _block(_map(node.fields)),
                ],
                " ",
            )
        )

    if kind is _ast.ObjectTypeExtension:
        return _join(
            [
                "extend type",
                _name(),
                _wrap("implements ", _join(_map(node.interfaces), " & ")),
                _directives(),
                _block(_map(node.fields)),
            ],
            " ",
        )

    if kind is _ast.FieldDefinition:
        return _join([_name(), _arg_defs(), ": ", _type(), _wrap(" ", _directives())])

    if kind is _ast.InputValueDefinition:
        return _join(
            [
                _join([_name(), ": ", _type()]),
                _wrap(" = ", _print(node.default_value)),
                _wrap(" ", _directives()),
            ]
        )

    if kind is _ast.InterfaceTypeDefinition:
        return _with_desc(
            _join(["interface", _name(), _directives(), _block(_map(node.fields))], " ")
        )

    if kind is _ast.InterfaceTypeExtension:
        return _join(
            ["extend interface", _name(), _directives(), _block(_map(node.fields))], " "
        )

    if kind is _ast.UnionTypeDefinition:
        return _with_desc(
            _join(
                [
                    "union",
                    _name(),
                    _directives(),
                    _wrap("= ", _join(_map(node.types), " | ")),
                ],
                " ",
            )
        )

    if kind is _ast.UnionTypeExtension:
        return _join(
            [
                "extend union",
                _name(),
                _directives(),
                _wrap("= ", _join(_map(node.types), " | ")),
            ],
            " ",
        )

    if kind is _ast.EnumTypeDefinition:
        return _with_desc(
            _join(["enum", _name(), _directives(), _block(_map(node.values))], " ")
        )

    if kind is _ast.EnumTypeExtension:
        return _join(
            ["extend enum", _name(), _directives(), _block(_map(node.values))], " "
        )

    if kind is _ast.EnumValueDefinition:
        return _join([_name(), _directives()], " ")

    if kind is _ast.InputObjectTypeDefinition:
        return _with_desc(
            _join(["input", _name(), _directives(), _block(_map(node.fields))], " ")
        )

    if kind is _ast.InputObjectTypeExtension:
        return _join(
            ["extend input", _name(), _directives(), _block(_map(node.fields))], " "
        )

    if kind is _ast.DirectiveDefinition:
        return _with_desc(
            _join(
                [
                    "directive @",
                    _name(),
                    _arg_defs(),
                    " on ",
                    _join(_map(node.locations), " | "),
                ]
            )
        )


def _wrap(start, maybe_string, end=None):
    return ("%s%s%s" % (start, maybe_string, end or "")) if maybe_string else ""


def _join(entries, separator=""):
    if entries is None:
        entries = []
    return separator.join([x for x in entries if x])


def _indent(maybe_string):
    return maybe_string and ("  " + maybe_string.replace("\n", "\n  "))


def _block(iterator):
    arr = list(iterator)
    if not arr:
        return ""
    return "{\n%s\n}" % _join(map(_indent, arr), "\n")


# Print a block string in the indented block form by adding a leading and
# trailing blank line. However, if a block string starts with whitespace and
# is a single-line, adding a leading blank line would strip that whitespace.
def _block_string(value, is_description=False):
    escaped = value.replace('"""', '\\"""')
    if (value[0] == " " or value[0] == "\t") and "\n" not in value:
        if escaped.endswith('"'):
            escaped = escaped + "\n"
        return '"""%s"""' % escaped
    return '"""\n%s\n"""' % (escaped if is_description else _indent(escaped))
