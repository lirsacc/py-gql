# -*- coding: utf-8 -*-
""" Visitors are the basic abstraction used to traverse a GraphQL AST.

Note:
    While the concept is similar to the one used in the reference implementation,
    this doesn't support editing the ast, tracking of the visitor path or
    providing shared context. You can refer to :mod:`py_gql.validation` for
    example implementations.
"""

import functools as ft

from . import ast as _ast
from ..exc import GraphQLError


class SkipNode(GraphQLError):
    def __init__(self):
        super(SkipNode, self).__init__("")


class Visitor(object):
    """ Visitor base class. """

    def enter(self, node):
        """ Function called when entering a node.

        Raising :class:`SkipNode` in this function will lead to ignoring the
        current node and all it's descendants. as well as prevent running
        :meth:`leave`.

        Args:
            node (py_gql.lang.ast.Node) Node being visited
        """
        pass

    def leave(self, node):
        """ Function called when leaving a node. Will not be called if
        :class:`SkipNode` was raised in `enter`.

        Args:
            node (py_gql.lang.ast.Node) Node being visited
        """
        pass


def visit(visitor, ast_root):
    """ Visit a GraphQL parse tree.

    All side effects and results of traversal should be contained in the
    visitor instance.

    Args:
        visitor (Visitor): Visitor instance
        ast_root (py_gql.lang.ast.Document): Parsed GraphQL document
    """
    assert isinstance(ast_root, _ast.Document)
    _visit_document(visitor, ast_root)


def _visiting(func):
    """ Wrap a function to call the provided visitor ``enter`` / ``leave``
    functions before / after processing a node.
    """

    @ft.wraps(func)
    def wrapper(visitor, node):
        if node is None:
            return

        try:
            visitor.enter(node)
        except SkipNode:
            return

        func(visitor, node)
        visitor.leave(node)

    return wrapper


def _many(fn, visitor, nodes):
    """ Run a visiting procedure on multiple nodes """
    if nodes:
        for node in nodes:
            fn(visitor, node)


@_visiting
def _visit_document(visitor, document):
    for definition in document.definitions:
        _visit_definition(visitor, definition)


def _visit_definition(visitor, definition):
    func = {
        _ast.OperationDefinition: _visit_operation_definition,
        _ast.FragmentDefinition: _visit_fragment_definition,
        _ast.SchemaDefinition: _visit_schema_definition,
        _ast.ScalarTypeDefinition: _visit_scalar_type_definition,
        _ast.ObjectTypeDefinition: _visit_object_type_definition,
        _ast.InterfaceTypeDefinition: _visit_interface_type_definition,
        _ast.UnionTypeDefinition: _visit_union_type_definition,
        _ast.EnumTypeDefinition: visit_enum_type_definition,
        _ast.InputObjectTypeDefinition: _visit_input_object_type_definition,
        _ast.SchemaExtension: _visit_schema_definition,
        _ast.ScalarTypeExtension: _visit_scalar_type_definition,
        _ast.ObjectTypeExtension: _visit_object_type_definition,
        _ast.InterfaceTypeExtension: _visit_interface_type_definition,
        _ast.UnionTypeExtension: _visit_union_type_definition,
        _ast.EnumTypeExtension: visit_enum_type_definition,
        _ast.InputObjectTypeExtension: _visit_input_object_type_definition,
        _ast.DirectiveDefinition: _visit_directive_definition,
    }.get(type(definition), None)
    if func is not None:
        func(visitor, definition)


@_visiting
def _visit_operation_definition(visitor, definition):
    _many(_visit_variable_definition, visitor, definition.variable_definitions)
    _many(_visit_directive, visitor, definition.directives)
    _visit_selection_set(visitor, definition.selection_set)


@_visiting
def _visit_fragment_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)
    _visit_selection_set(visitor, definition.selection_set)


@_visiting
def _visit_variable_definition(visitor, variable_definition):
    if variable_definition.default_value:
        _visit_input_value(visitor, variable_definition.default_value)
    _visit_named_type(visitor, variable_definition.type)


@_visiting
def _visit_named_type(visitor, named_type):
    pass


@_visiting
def _visit_directive(visitor, directive):
    _many(_visit_argument, visitor, directive.arguments)


@_visiting
def _visit_argument(visitor, argument):
    _visit_input_value(visitor, argument.value)


@_visiting
def _visit_selection_set(visitor, selection_set):
    _many(_visit_selection, visitor, selection_set.selections)


def _visit_selection(visitor, selection):
    func = {
        _ast.Field: _visit_field,
        _ast.FragmentSpread: _visit_fragment_spread,
        _ast.InlineFragment: _visit_inline_fragment,
    }[type(selection)]
    func(visitor, selection)


@_visiting
def _visit_field(visitor, field):
    _many(_visit_argument, visitor, field.arguments)
    _many(_visit_directive, visitor, field.directives)
    _visit_selection_set(visitor, field.selection_set)


@_visiting
def _visit_fragment_spread(visitor, spread):
    _many(_visit_directive, visitor, spread.directives)


@_visiting
def _visit_inline_fragment(visitor, fragment):
    _many(_visit_directive, visitor, fragment.directives)
    if fragment.selection_set:
        _visit_selection_set(visitor, fragment.selection_set)


@_visiting
def _visit_input_value(visitor, input_value):
    kind = type(input_value)
    if kind == _ast.ObjectValue:
        _many(_visit_object_field, visitor, input_value.fields)
    elif kind == _ast.ListValue:
        _many(_visit_input_value, visitor, input_value.values)


@_visiting
def _visit_object_field(visitor, field):
    _visit_input_value(visitor, field.value)


@_visiting
def _visit_schema_definition(visitor, definition):
    _many(_visit_operation_type_definition, visitor, definition.operation_types)
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_operation_type_definition(visitor, definition):
    _visit_named_type(visitor, definition.type)


@_visiting
def _visit_scalar_type_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_object_type_definition(visitor, definition):
    _many(_visit_named_type, visitor, definition.interfaces)
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_field_definition, visitor, definition.fields)


@_visiting
def _visit_interface_type_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_field_definition, visitor, definition.fields)


@_visiting
def _visit_union_type_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_named_type, visitor, definition.types)


@_visiting
def visit_enum_type_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_enum_value_definition, visitor, definition.values)


@_visiting
def _visit_input_object_type_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_input_value_definition, visitor, definition.fields)


@_visiting
def _visit_field_definition(visitor, definition):
    _visit_named_type(visitor, definition.type)
    _many(_visit_input_value_definition, visitor, definition.arguments)
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_input_value_definition(visitor, definition):
    _visit_named_type(visitor, definition.type)
    _visit_input_value(visitor, definition.default_value)
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_enum_value_definition(visitor, definition):
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_directive_definition(visitor, definition):
    _many(_visit_input_value_definition, visitor, definition.arguments)


class DispatchingVisitor(Visitor):
    """ Base class for specialised visitors.

    You should subclass this and implement methods named "enter_*". "leave_*"
    where * represents the node class to be handled. For instance to process
    :class:`py_gql.lang.ast.FloatValue` nodes, implement ``enter_float_value``.

    Default behaviour is noop for all classes.
    """

    def enter(self, node):  # noqa: C901
        kind = type(node)
        if kind is _ast.Document:
            self.enter_document(node)
        elif kind is _ast.OperationDefinition:
            self.enter_operation_definition(node)
        elif kind is _ast.FragmentDefinition:
            self.enter_fragment_definition(node)
        elif kind is _ast.VariableDefinition:
            self.enter_variable_definition(node)
        elif kind is _ast.Directive:
            self.enter_directive(node)
        elif kind is _ast.Argument:
            self.enter_argument(node)
        elif kind is _ast.SelectionSet:
            self.enter_selection_set(node)
        elif kind is _ast.Field:
            self.enter_field(node)
        elif kind is _ast.FragmentSpread:
            self.enter_fragment_spread(node)
        elif kind is _ast.InlineFragment:
            self.enter_inline_fragment(node)
        elif kind is _ast.NullValue:
            self.enter_null_value(node)
        elif kind is _ast.IntValue:
            self.enter_int_value(node)
        elif kind is _ast.FloatValue:
            self.enter_float_value(node)
        elif kind is _ast.StringValue:
            self.enter_string_value(node)
        elif kind is _ast.BooleanValue:
            self.enter_boolean_value(node)
        elif kind is _ast.EnumValue:
            self.enter_enum_value(node)
        elif kind is _ast.Variable:
            self.enter_variable(node)
        elif kind is _ast.ListValue:
            self.enter_list_value(node)
        elif kind is _ast.ObjectValue:
            self.enter_object_value(node)
        elif kind is _ast.ObjectField:
            self.enter_object_field(node)
        elif kind is _ast.NamedType:
            self.enter_named_type(node)
        elif kind is _ast.ListType:
            self.enter_list_type(node)
        elif kind is _ast.NonNullType:
            self.enter_non_null_type(node)
        elif kind is _ast.SchemaDefinition:
            self.enter_schema_definition(node)
        elif kind is _ast.OperationTypeDefinition:
            self.enter_operation_type_definition(node)
        elif kind is _ast.ScalarTypeDefinition:
            self.enter_scalar_type_definition(node)
        elif kind is _ast.ObjectTypeDefinition:
            self.enter_object_type_definition(node)
        elif kind is _ast.FieldDefinition:
            self.enter_field_definition(node)
        elif kind is _ast.InputValueDefinition:
            self.enter_input_value_definition(node)
        elif kind is _ast.InterfaceTypeDefinition:
            self.enter_interface_type_definition(node)
        elif kind is _ast.UnionTypeDefinition:
            self.enter_union_type_definition(node)
        elif kind is _ast.EnumTypeDefinition:
            self.enter_enum_type_definition(node)
        elif kind is _ast.EnumValueDefinition:
            self.enter_enum_value_definition(node)
        elif kind is _ast.InputObjectTypeDefinition:
            self.enter_input_object_type_definition(node)
        elif kind is _ast.SchemaExtension:
            self.enter_schema_extension(node)
        elif kind is _ast.ScalarTypeExtension:
            self.enter_scalar_type_extension(node)
        elif kind is _ast.ObjectTypeExtension:
            self.enter_object_type_extension(node)
        elif kind is _ast.InterfaceTypeExtension:
            self.enter_interface_type_extension(node)
        elif kind is _ast.UnionTypeExtension:
            self.enter_union_type_extension(node)
        elif kind is _ast.EnumTypeExtension:
            self.enter_enum_type_extension(node)
        elif kind is _ast.InputObjectTypeExtension:
            self.enter_input_object_type_extension(node)
        elif kind is _ast.DirectiveDefinition:
            self.enter_directive_definition(node)

    def leave(self, node):  # noqa: C901
        kind = type(node)
        if kind is _ast.Document:
            self.leave_document(node)
        elif kind is _ast.OperationDefinition:
            self.leave_operation_definition(node)
        elif kind is _ast.FragmentDefinition:
            self.leave_fragment_definition(node)
        elif kind is _ast.VariableDefinition:
            self.leave_variable_definition(node)
        elif kind is _ast.Directive:
            self.leave_directive(node)
        elif kind is _ast.Argument:
            self.leave_argument(node)
        elif kind is _ast.SelectionSet:
            self.leave_selection_set(node)
        elif kind is _ast.Field:
            self.leave_field(node)
        elif kind is _ast.FragmentSpread:
            self.leave_fragment_spread(node)
        elif kind is _ast.InlineFragment:
            self.leave_inline_fragment(node)
        elif kind is _ast.NullValue:
            self.leave_null_value(node)
        elif kind is _ast.IntValue:
            self.leave_int_value(node)
        elif kind is _ast.FloatValue:
            self.leave_float_value(node)
        elif kind is _ast.StringValue:
            self.leave_string_value(node)
        elif kind is _ast.BooleanValue:
            self.leave_boolean_value(node)
        elif kind is _ast.EnumValue:
            self.leave_enum_value(node)
        elif kind is _ast.Variable:
            self.leave_variable(node)
        elif kind is _ast.ListValue:
            self.leave_list_value(node)
        elif kind is _ast.ObjectValue:
            self.leave_object_value(node)
        elif kind is _ast.ObjectField:
            self.leave_object_field(node)
        elif kind is _ast.NamedType:
            self.leave_named_type(node)
        elif kind is _ast.ListType:
            self.leave_list_type(node)
        elif kind is _ast.NonNullType:
            self.leave_non_null_type(node)
        elif kind is _ast.SchemaDefinition:
            self.leave_schema_definition(node)
        elif kind is _ast.OperationTypeDefinition:
            self.leave_operation_type_definition(node)
        elif kind is _ast.ScalarTypeDefinition:
            self.leave_scalar_type_definition(node)
        elif kind is _ast.ObjectTypeDefinition:
            self.leave_object_type_definition(node)
        elif kind is _ast.FieldDefinition:
            self.leave_field_definition(node)
        elif kind is _ast.InputValueDefinition:
            self.leave_input_value_definition(node)
        elif kind is _ast.InterfaceTypeDefinition:
            self.leave_interface_type_definition(node)
        elif kind is _ast.UnionTypeDefinition:
            self.leave_union_type_definition(node)
        elif kind is _ast.EnumTypeDefinition:
            self.leave_enum_type_definition(node)
        elif kind is _ast.EnumValueDefinition:
            self.leave_enum_value_definition(node)
        elif kind is _ast.InputObjectTypeDefinition:
            self.leave_input_object_type_definition(node)
        elif kind is _ast.SchemaExtension:
            self.leave_schema_extension(node)
        elif kind is _ast.ScalarTypeExtension:
            self.leave_scalar_type_extension(node)
        elif kind is _ast.ObjectTypeExtension:
            self.leave_object_type_extension(node)
        elif kind is _ast.InterfaceTypeExtension:
            self.leave_interface_type_extension(node)
        elif kind is _ast.UnionTypeExtension:
            self.leave_union_type_extension(node)
        elif kind is _ast.EnumTypeExtension:
            self.leave_enum_type_extension(node)
        elif kind is _ast.InputObjectTypeExtension:
            self.leave_input_object_type_extension(node)
        elif kind is _ast.DirectiveDefinition:
            self.leave_directive_definition(node)

    def default_handler(self, node):
        pass

    enter_document = default_handler
    leave_document = default_handler

    enter_operation_definition = default_handler
    leave_operation_definition = default_handler

    enter_fragment_definition = default_handler
    leave_fragment_definition = default_handler

    enter_variable_definition = default_handler
    leave_variable_definition = default_handler

    enter_directive = default_handler
    leave_directive = default_handler

    enter_argument = default_handler
    leave_argument = default_handler

    enter_selection_set = default_handler
    leave_selection_set = default_handler

    enter_field = default_handler
    leave_field = default_handler

    enter_fragment_spread = default_handler
    leave_fragment_spread = default_handler

    enter_inline_fragment = default_handler
    leave_inline_fragment = default_handler

    enter_null_value = default_handler
    leave_null_value = default_handler

    enter_int_value = default_handler
    leave_int_value = default_handler

    enter_float_value = default_handler
    leave_float_value = default_handler

    enter_string_value = default_handler
    leave_string_value = default_handler

    enter_boolean_value = default_handler
    leave_boolean_value = default_handler

    enter_enum_value = default_handler
    leave_enum_value = default_handler

    enter_variable = default_handler
    leave_variable = default_handler

    enter_list_value = default_handler
    leave_list_value = default_handler

    enter_object_value = default_handler
    leave_object_value = default_handler

    enter_object_field = default_handler
    leave_object_field = default_handler

    enter_named_type = default_handler
    leave_named_type = default_handler

    enter_list_type = default_handler
    leave_list_type = default_handler

    enter_non_null_type = default_handler
    leave_non_null_type = default_handler

    enter_schema_definition = default_handler
    leave_schema_definition = default_handler

    enter_operation_type_definition = default_handler
    leave_operation_type_definition = default_handler

    enter_scalar_type_definition = default_handler
    leave_scalar_type_definition = default_handler

    enter_object_type_definition = default_handler
    leave_object_type_definition = default_handler

    enter_field_definition = default_handler
    leave_field_definition = default_handler

    enter_input_value_definition = default_handler
    leave_input_value_definition = default_handler

    enter_interface_type_definition = default_handler
    leave_interface_type_definition = default_handler

    enter_union_type_definition = default_handler
    leave_union_type_definition = default_handler

    enter_enum_type_definition = default_handler
    leave_enum_type_definition = default_handler

    enter_enum_value_definition = default_handler
    leave_enum_value_definition = default_handler

    enter_input_object_type_definition = default_handler
    leave_input_object_type_definition = default_handler

    enter_schema_extension = default_handler
    leave_schema_extension = default_handler

    enter_scalar_type_extension = default_handler
    leave_scalar_type_extension = default_handler

    enter_object_type_extension = default_handler
    leave_object_type_extension = default_handler

    enter_interface_type_extension = default_handler
    leave_interface_type_extension = default_handler

    enter_union_type_extension = default_handler
    leave_union_type_extension = default_handler

    enter_enum_type_extension = default_handler
    leave_enum_type_extension = default_handler

    enter_input_object_type_extension = default_handler
    leave_input_object_type_extension = default_handler

    enter_directive_definition = default_handler
    leave_directive_definition = default_handler


class ParrallelVisitor(Visitor):
    """ Abstraction to run multiple visitor instances as one.

    - All visitors are run in the order they are defined
    - raising :class:`SkipNode` in one of them will prevent any later visitor
      to run

    Args:
        *visitors (List[Visitor]): List of visitors to run
    """

    # pylint: disable = super-init-not-called
    def __init__(self, *visitors):
        self.visitors = visitors

    def enter(self, node):
        for v in self.visitors:
            v.enter(node)

    def leave(self, node):
        for v in self.visitors[::-1]:
            v.leave(node)
