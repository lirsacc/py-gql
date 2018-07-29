# -*- coding: utf-8 -*-
""" Export schema as SDL. """
from __future__ import unicode_literals

import operator as op

from .._string_utils import leading_whitespace, wrapped_lines
from ..lang import print_ast
from ..utilities import ast_node_from_value
from .directives import DEFAULT_DEPRECATION, SPECIFIED_DIRECTIVES
from .introspection import is_introspection_type
from .scalars import SPECIFIED_SCALAR_TYPES, String
from .types import (
    EnumType,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    UnionType,
)


class SchemaPrinter(object):
    """
    Args:
        indent (Union[str, int]): Indent character or number of spaces

        include_descriptions (bool):
            If ``True`` include descriptions in the output

        description_format ("comments"|"block"):
            Control how descriptions are formatted. ``"comments"`` is the
            old standard and will be compatible with most GraphQL parsers
            while ``"block"`` is part of the most recent specification and
            includes descriptions as block strings that can be extracted
            according to the specification.

        include_introspection (bool):
            If ``True``, include introspection types in the output
    """

    __slots__ = (
        "indent",
        "include_descriptions",
        "description_format",
        "include_introspection",
    )

    def __init__(
        self,
        indent=4,
        include_descriptions=True,
        description_format="block",
        include_introspection=False,
    ):
        self.include_descriptions = include_descriptions
        self.description_format = description_format
        if isinstance(indent, int):
            self.indent = indent * " "
        else:
            self.indent = indent

        self.include_introspection = include_introspection

    def __call__(self, schema):
        """
        schema (py_gql.schema.Schema): Schema to format

        Returns:
            str: Formatted GraphQL schema
        """
        directives = sorted(
            [
                d
                for d in schema.directives.values()
                if d not in SPECIFIED_DIRECTIVES
            ],
            key=op.attrgetter("name"),
        )

        types = sorted(
            [
                t
                for t in schema.types.values()
                if (
                    t not in SPECIFIED_SCALAR_TYPES
                    and (
                        self.include_introspection
                        or not is_introspection_type(t)
                    )
                )
            ],
            key=op.attrgetter("name"),
        )

        parts = (
            [_schema_definition(schema, self.indent)]
            + [
                self.print_directive(d)
                for d in (
                    SPECIFIED_DIRECTIVES if self.include_introspection else []
                )
            ]
            + [self.print_directive(d) for d in directives]
            + [self.print_type(t) for t in types]
        )

        return "\n\n".join((p for p in parts if p)) + "\n"

    def print_description(self, definition, depth=0, first_in_block=True):
        """ Format an object description according to current configuration.

        Args:
            definitions (any): Described object
            depth (int): Level of indentation
            first_in_block (bool):

        Returns:
            str:
        """
        if not self.include_descriptions or not getattr(
            definition, "description"
        ):
            return ""

        indent = self.indent * depth

        if self.description_format == "comments":
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

        elif self.description_format == "block":
            max_len = 120 - len(indent)
            lines = list(
                wrapped_lines(definition.description.split("\n"), max_len)
            )
            first = lines[0]

            if len(lines) == 1 and len(first) < 70 and not first.endswith('"'):
                body = first.replace('"""', '\\"""')
            else:
                has_leading_whitespace = leading_whitespace(first)
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

        raise ValueError(
            "Invalid description format %s" % self.description_format
        )

    def print_deprecated(self, field_or_enum_value):
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

    def print_type(self, type_):
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

    def print_scalar_type(self, type_):
        """
        """
        return "%sscalar %s" % (
            self.print_description(type_, 0, True),
            type_.name,
        )

    def print_enum_type(self, type_):
        return "%senum %s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            "\n".join(
                [
                    "".join(
                        [
                            self.print_description(enum_value, 1, not i),
                            self.indent,
                            enum_value.name,
                            self.print_deprecated(enum_value),
                        ]
                    )
                    for i, enum_value in enumerate(type_.values)
                ]
            ),
        )

    def print_union_type(self, type_):
        return "%sunion %s = %s" % (
            self.print_description(type_),
            type_.name,
            " | ".join((t.name for t in type_.types)),
        )

    def print_object_type(self, type_):
        return "%stype %s%s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            " implements %s"
            % " & ".join([iface.name for iface in type_.interfaces])
            if type_.interfaces
            else "",
            self.print_fields(type_),
        )

    def print_interface_type(self, type_):
        return "%sinterface %s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
            self.print_fields(type_),
        )

    def print_fields(self, type_):
        return "\n".join(
            [
                "".join(
                    [
                        self.print_description(field, 1, not i),
                        self.indent,
                        field.name,
                        self.print_arguments(field.args, 1),
                        ": %s" % field.type,
                        self.print_deprecated(field),
                    ]
                )
                for i, field in enumerate(type_.fields)
            ]
        )

    def print_input_object_type(self, type_):
        return "%sinput %s {\n%s\n}" % (
            self.print_description(type_),
            type_.name,
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

    def print_directive(self, directive):
        return "%sdirective @%s%s on %s" % (
            self.print_description(directive),
            directive.name,
            self.print_arguments(directive.arguments, 0),
            " | ".join(directive.locations),
        )

    def print_arguments(self, args, depth=0):
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

    def print_input_value(self, arg_or_inut_field):
        s = "%s: %s" % (arg_or_inut_field.name, arg_or_inut_field.type)
        if arg_or_inut_field.has_default_value:
            s += " = %s" % print_ast(
                ast_node_from_value(
                    arg_or_inut_field.default_value, arg_or_inut_field.type
                )
            )
        return s


def _schema_definition(schema, indent):
    if (
        (not schema.query_type or schema.query_type.name == "Query")
        and (
            not schema.mutation_type or schema.mutation_type.name == "Mutation"
        )
        and (
            not schema.subscription_type
            or schema.subscription_type.name == "Subscription"
        )
    ):
        return ""

    operation_types = []
    if schema.query_type:
        operation_types.append("%squery: %s" % (indent, schema.query_type.name))
    if schema.mutation_type:
        operation_types.append(
            "%smutation: %s" % (indent, schema.mutation_type.name)
        )
    if schema.subscription_type:
        operation_types.append(
            "%ssubscription: %s" % (indent, schema.subscription_type.name)
        )

    return "schema {\n%s\n}" % ("\n".join(operation_types))
