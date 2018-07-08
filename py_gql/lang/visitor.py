# -*- coding: utf-8 -*-
""" Traverse a GraphQL AST.
"""

import abc
import functools as ft

import six

from . import ast as _ast
from ..exc import GraphQLError


class SkipNode(GraphQLError):
    """ Raise this in :meth:`Visitor.enter` to ignore all children of that node.
    """

    def __init__(self):
        self.message = ""


@six.add_metaclass(abc.ABCMeta)
class Visitor:
    """ Visitor metaclass

    Note:
        This doesn't support editing the ast, tracking of the visitor
        path or providing shared context by default like the JS reference
        implementation.
    """

    @abc.abstractmethod
    def enter(self, node):
        """ Function called when entering a node.

        Raising :class:`SkipNode` in this function will lead to ignoring the
        current node and all it's descendants.

        Args:
            node (py_gql.lang.ast.Node) Node being visited
        """
        pass

    @abc.abstractmethod
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


_HANDLERS = {
    _ast.Document: "document",
    _ast.OperationDefinition: "operation_definition",
    _ast.FragmentDefinition: "fragment_definition",
    _ast.VariableDefinition: "variable_definition",
    _ast.Directive: "directive",
    _ast.Argument: "argument",
    _ast.SelectionSet: "selection_set",
    _ast.Field: "field",
    _ast.FragmentSpread: "fragment_spread",
    _ast.InlineFragment: "inline_fragment",
    _ast.NullValue: "null_value",
    _ast.IntValue: "int_value",
    _ast.FloatValue: "float_value",
    _ast.StringValue: "string_value",
    _ast.BooleanValue: "boolean_value",
    _ast.EnumValue: "enum_value",
    _ast.Variable: "variable_value",
    _ast.ListValue: "list_value",
    _ast.ObjectValue: "object_value",
    _ast.ObjectField: "object_field",
    _ast.NamedType: "named_type",
    _ast.ListType: "named_type",
    _ast.NonNullType: "named_type",
    _ast.SchemaDefinition: "schema_definition",
    _ast.OperationTypeDefinition: "operation_type_definition",
    _ast.ScalarTypeDefinition: "scalar_type_definition",
    _ast.ObjectTypeDefinition: "object_type_definition",
    _ast.FieldDefinition: "field_definition",
    _ast.InputValueDefinition: "input_value_definition",
    _ast.InterfaceTypeDefinition: "interface_type_definition",
    _ast.UnionTypeDefinition: "union_type_definition",
    _ast.EnumTypeDefinition: "enum_type_definition",
    _ast.EnumValueDefinition: "enum_value_definition",
    _ast.InputObjectTypeDefinition: "input_object_type_definition",
    _ast.ScalarTypeExtension: "scalar_type_extension",
    _ast.ObjectTypeExtension: "object_type_extension",
    _ast.InterfaceTypeExtension: "interface_type_extension",
    _ast.UnionTypeExtension: "union_type_extension",
    _ast.EnumTypeExtension: "enum_type_extension",
    _ast.InputObjectTypeExtension: "input_object_type_extension",
    _ast.DirectiveDefinition: "directive_definition",
}


class DispatchingVisitor(Visitor):
    """ Class to base specialised visitor on.

    You can either:

    - implement ``handler`` for custom method resolution
    - implement methods named "enter_*". "leave_*" where * represents one of
      the values in `_HANDLERS` (essentially the Python / Snake case version of
      the node class). The method will be called on the matching node class.

    If no function is found (``handler`` returns ``None``) for a node, ``enter``
    and / or ``leave`` will noop.
    """

    def handler(self, node, stage="enter"):
        """ Resolve the handler based on the node type and visiting stage.

        Args:
            node (py_gql.lang.ast.Node): AST node to visit
            stage (str): One of `enter` or `leave`

        Returns:
            callable: Visitor function or ``None``
        """
        handler_name = _HANDLERS.get(type(node), None)
        if handler_name is None:
            raise TypeError("Unknown node type %s", type(node))
        return getattr(self, "%s_%s" % (stage, handler_name), None)

    def enter(self, node):
        handler = self.handler(node, "enter")
        if handler is not None:
            handler(node)

    def leave(self, node):
        handler = self.handler(node, "leave")
        if handler is not None:
            handler(node)


class ParrallelVisitor(Visitor):
    """ Abstraction to run multiple visitor instances as one.

    Args:
        *visitors (List[Visitor]): List of visitors to run
    """

    def __init__(self, *visitors):
        self.visitors = visitors

    def enter(self, node):
        for v in self.visitors:
            v.enter(node)

    def leave(self, node):
        for v in self.visitors[::-1]:
            v.leave(node)
