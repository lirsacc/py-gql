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
from .schema import Schema
from .types import (
    EnumType,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    UnionType,
)


def print_schema(schema, **opts):
    """ Print a GraphQL schema object in a standard SDL formatted string.

    :type **opts: dict
    :param opts: Keyword arguments passed to `SchemaPrinter`

    :rtype: str
    :returns: Formatted GraphQL schema
    """
    assert isinstance(schema, Schema), "Expected Schema object"
    return SchemaPrinter(**opts)(schema)


class SchemaPrinter(object):
    def __init__(
        self,
        include_descriptions=True,
        description_format="block",
        indent="  ",
        include_introspection_types=False,
    ):
        """ Format a GraphQL schema object into a valid SDL string.

        :type include_descriptions: bool
        :param include_descriptions: Control how descriptions are printed.
            Falsy values disable the inclusion of descriptions while truthy values
            enable including descriptions as comments above the related type.

        :type description_format: "comments"|"block"
        :param description_format: Control how descriptions are formatted.
            "comments" is the old standard and will be compatible with most GraphQL
            parser while "block" is part of the most recent release and includes
            descriptions as block strings that can be extracted.

        :type indent: int
        :param indent: Control indent size
        """
        self.include_descriptions = include_descriptions
        self.description_format = description_format
        self.indent = indent
        self.include_introspection_types = include_introspection_types

    def __call__(self, schema):
        """
        :type schema: py_gql.schema.Schema
        :param schema: Schema to print

        :rtype: str
        :returns: Formatted GraphQL schema
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
                        self.include_introspection_types
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
                    SPECIFIED_DIRECTIVES
                    if self.include_introspection_types
                    else []
                )
            ]
            + [self.print_directive(d) for d in directives]
            + [self.print_type(t) for t in types]
        )

        return "\n\n".join((p for p in parts if p)) + "\n"

    def print_description(self, definition, depth=0, first_in_block=True):
        """
        :type definitions: any
        :param definition: Described object

        :type depth: int
        :parma depth: Level of indentation

        :type first_in_block: bool
        :param first_in_block:

        :rtype: str
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
                body = _escape_triple_quotes(first)
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
                                _escape_triple_quotes(line),
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

        else:
            raise RuntimeError(
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

    def print_type(self, typ):
        if isinstance(typ, ScalarType):
            return self.print_scalar_type(typ)
        elif isinstance(typ, ObjectType):
            return self.print_object_type(typ)
        elif isinstance(typ, InterfaceType):
            return self.print_interface_type(typ)
        elif isinstance(typ, UnionType):
            return self.print_union_type(typ)
        elif isinstance(typ, EnumType):
            return self.print_enum_type(typ)
        elif isinstance(typ, InputObjectType):
            return self.print_input_object_type(typ)

        raise TypeError(typ)

    def print_scalar_type(self, typ):
        """
        :type typ: py_gql.schema.ScalarType

        :rtype str
        """
        return "%sscalar %s" % (self.print_description(typ, 0, True), typ.name)

    def print_enum_type(self, typ):
        """
        :type typ: py_gql.schema.EnumType

        :rtype: str
        """
        return "%senum %s {\n%s\n}" % (
            self.print_description(typ),
            typ.name,
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
                    for i, enum_value in enumerate(typ.values.values())
                ]
            ),
        )

    def print_union_type(self, typ):
        """
        :type typ: py_gql.schema.UnionType

        :rtype: str
        """
        return "%sunion %s = %s" % (
            self.print_description(typ),
            typ.name,
            " | ".join((t.name for t in typ.types)),
        )

    def print_object_type(self, typ):
        """
        :type typ: py_gql.schema.ObjectType

        :rtype: str
        """
        return "%stype %s%s {\n%s\n}" % (
            self.print_description(typ),
            typ.name,
            " implements %s"
            % " & ".join([iface.name for iface in typ.interfaces])
            if typ.interfaces
            else "",
            self.print_fields(typ),
        )

    def print_interface_type(self, typ):
        """
        :type typ: py_gql.schema.InterfaceType

        :rtype: str
        """
        return "%sinterface %s {\n%s\n}" % (
            self.print_description(typ),
            typ.name,
            self.print_fields(typ),
        )

    def print_fields(self, typ):
        """
        :type typ: py_gql.schema.ObjectType|py_gql.schema.InterfaceType

        :rtype: str
        """
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
                for i, field in enumerate(typ.fields)
            ]
        )

    def print_input_object_type(self, typ):
        """
        :type typ: py_gql.schema.InputObjectType

        :rtype: str
        """
        return "%sinput %s {\n%s\n}" % (
            self.print_description(typ),
            typ.name,
            "\n".join(
                [
                    "%s%s%s"
                    % (
                        self.print_description(field, 1, not i),
                        self.indent,
                        self.print_input_value(field),
                    )
                    for i, field in enumerate(typ.fields)
                ]
            ),
        )

    def print_directive(self, directive):
        """
        :type directive: py_gql.schema.Directive
        :param directive: Directive to print
        """
        return "%sdirective @%s%s on %s" % (
            self.print_description(directive),
            directive.name,
            self.print_arguments(directive.arguments, 0),
            " | ".join(directive.locations),
        )

    def print_arguments(self, args, depth=0):
        """
        :type args: py_gql.schema.Argument
        :param args: Argument to print

        :type depth: int
        :parma depth: Level of indentation
        """
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
        """
        :type arg: py_gql.schema.Argument|py_gql.schema.InputObjectField
        :param arg:

        :rtype: str
        """
        s = "%s: %s" % (arg_or_inut_field.name, arg_or_inut_field.type)
        if arg_or_inut_field.has_default_value:
            s += " = %s" % print_ast(
                ast_node_from_value(
                    arg_or_inut_field.default_value, arg_or_inut_field.type
                )
            )
        return s


def _schema_definition(schema, indent):
    """
    :type schema: py_gql.schema.Schema
    :param schema: Schema to print

    :rtype: str
    """
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


def _escape_triple_quotes(value):
    return value.replace('"""', '\\"""')
