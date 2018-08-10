# -*- coding: utf-8 -*-
"""
"""

from ..._string_utils import infer_suggestions, quoted_options_list
from ...exc import ScalarParsingError, UnknownEnumValue
from ...lang.visitor import SkipNode
from ...schema import (
    EnumType,
    InputObjectType,
    NonNullType,
    ScalarType,
    unwrap_type,
)
from ...schema.scalars import SPECIFIED_SCALAR_TYPES
from ..visitors import ValidationVisitor


class ValuesOfCorrectTypeChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all value literals are of the type
    expected at their position. """

    # WARN: This check ignores cases where the input type is not known, which
    # should be caught by other validators.

    def _report_bad_value(self, input_type, node, extra=None):
        msg = "Expected type %s, found %s" % (input_type, node)
        if extra:
            msg += " (%s)" % extra
        self.add_error(msg, [node])

    def _check_scalar(self, node):
        input_type = self.type_info.input_type
        if not input_type:
            return

        named_type = unwrap_type(input_type)
        if not isinstance(named_type, ScalarType):
            self._report_bad_value(input_type, node)
        else:
            try:
                named_type.parse_literal(node)
            except ScalarParsingError as err:
                is_custom = named_type not in SPECIFIED_SCALAR_TYPES
                extra = str(err) if is_custom else None
                # Preserve message for custom scalar types.
                self._report_bad_value(input_type, node, extra=extra)

    enter_int_value = _check_scalar
    enter_float_value = _check_scalar
    enter_string_value = _check_scalar
    enter_boolean_value = _check_scalar

    def enter_null_value(self, node):
        input_type = self.type_info.input_type
        if input_type and isinstance(input_type, NonNullType):
            self._report_bad_value(input_type, node)

    def enter_enum_value(self, node):
        input_type = unwrap_type(self.type_info.input_type)
        if not input_type:
            return

        if not isinstance(input_type, EnumType):
            self._check_scalar(node)
        else:
            try:
                input_type.get_value(node.value)
            except UnknownEnumValue:
                self._report_bad_value(input_type, node)

    def enter_object_value(self, node):
        named_type = unwrap_type(self.type_info.input_type)
        if not isinstance(named_type, InputObjectType):
            self._check_scalar(node)
            raise SkipNode()

        input_fields = [f.name.value for f in node.fields]
        for field_def in named_type.fields:
            if field_def.required and field_def.name not in input_fields:
                self.add_error(
                    "Required field %s.%s of type %s was not provided"
                    % (named_type.name, field_def.name, field_def.type),
                    [node],
                )

    def enter_object_field(self, node):
        parent_type = unwrap_type(self.type_info.parent_input_type)
        field_type = self.type_info.input_type
        if field_type is None and isinstance(parent_type, InputObjectType):
            suggestions = infer_suggestions(
                node.name.value, [f.name for f in parent_type.fields]
            )
            if suggestions:
                self.add_error(
                    "Field %s is not defined by type %s, did you mean %s?"
                    % (
                        node.name.value,
                        parent_type,
                        quoted_options_list(suggestions),
                    ),
                    [node],
                )
            else:
                self.add_error(
                    "Field %s is not defined by type %s"
                    % (node.name.value, parent_type),
                    [node],
                )
