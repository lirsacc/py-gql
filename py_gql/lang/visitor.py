# -*- coding: utf-8 -*-
"""
Visitors are the basic abstraction used to traverse a GraphQL AST.

Warning:
    While the concept is similar to the one used in the reference implementation,
    this doesn't support editing the ast, tracking of the visitor path or
    providing shared context. You can refer to :mod:`py_gql.validation` for
    example implementations.
"""

import functools as ft
from typing import Callable, Iterable, TypeVar, Union

from ..exc import GraphQLError
from . import ast as _ast

__all__ = (
    "SkipNode",
    "Visitor",
    "visit",
    "DispatchingVisitor",
    "ParallelVisitor",
)


N = TypeVar("N", bound=_ast.Node)


class SkipNode(GraphQLError):
    """
    Raise this to short-circuit traversal and ignore the node and all its
    children.
    """

    def __init__(self):
        super().__init__("")


class Visitor:
    """
    Visitor base class.
    """

    def enter(self, node: _ast.Node) -> None:
        """
        Function called when entering a node.

        Raising :class:`SkipNode` in this function will lead to ignoring the
        current node and all it's descendants. as well as prevent running
        :meth:`leave`.

        Args:
            node:
        """
        raise NotImplementedError()

    def leave(self, node: _ast.Node) -> None:
        """
        Function called when leaving a node. Will not be called if
        :class:`SkipNode` was raised in `enter`.

        Args:
            node:
        """
        raise NotImplementedError()


def visit(visitor: Visitor, ast_root: _ast.Document) -> None:
    """
    Visit a GraphQL parse tree.

    All side effects and results of traversal should be contained in the
    visitor instance.

    Args:
        visitor (Visitor): Visitor instance
        ast_root (py_gql.lang.ast.Document): Parsed GraphQL document
    """
    _visit_document(visitor, ast_root)


def _visiting(
    func: Callable[[Visitor, N], None]
) -> Callable[[Visitor, N], None]:
    """
    Wrap a function to call the provided visitor ``enter`` / ``leave``
    functions before / after processing a node.
    """

    @ft.wraps(func)
    def wrapper(visitor: Visitor, node: N) -> None:
        if node is None:
            return

        try:
            visitor.enter(node)
        except SkipNode:
            return

        func(visitor, node)
        visitor.leave(node)

    return wrapper


def _many(
    fn: Callable[[Visitor, N], None], visitor: Visitor, nodes: Iterable[N]
) -> None:
    """
    Run a visiting procedure on multiple nodes.
    """
    if nodes:
        for node in nodes:
            fn(visitor, node)


@_visiting
def _visit_document(visitor: Visitor, document: _ast.Document) -> None:
    for definition in document.definitions:
        _visit_definition(visitor, definition)


def _visit_definition(  # noqa: C901
    visitor: Visitor, definition: _ast.Definition
) -> None:
    if isinstance(definition, _ast.OperationDefinition):
        _visit_operation_definition(visitor, definition)
    elif isinstance(definition, _ast.FragmentDefinition):
        _visit_fragment_definition(visitor, definition)
    elif isinstance(definition, _ast.SchemaDefinition):
        _visit_schema_definition(visitor, definition)
    elif isinstance(definition, _ast.ScalarTypeDefinition):
        _visit_scalar_type_definition(visitor, definition)
    elif isinstance(definition, _ast.ObjectTypeDefinition):
        _visit_object_type_definition(visitor, definition)
    elif isinstance(definition, _ast.InterfaceTypeDefinition):
        _visit_interface_type_definition(visitor, definition)
    elif isinstance(definition, _ast.UnionTypeDefinition):
        _visit_union_type_definition(visitor, definition)
    elif isinstance(definition, _ast.EnumTypeDefinition):
        visit_enum_type_definition(visitor, definition)
    elif isinstance(definition, _ast.InputObjectTypeDefinition):
        _visit_input_object_type_definition(visitor, definition)
    elif isinstance(definition, _ast.SchemaExtension):
        _visit_schema_definition(visitor, definition)
    elif isinstance(definition, _ast.ScalarTypeExtension):
        _visit_scalar_type_definition(visitor, definition)
    elif isinstance(definition, _ast.ObjectTypeExtension):
        _visit_object_type_definition(visitor, definition)
    elif isinstance(definition, _ast.InterfaceTypeExtension):
        _visit_interface_type_definition(visitor, definition)
    elif isinstance(definition, _ast.UnionTypeExtension):
        _visit_union_type_definition(visitor, definition)
    elif isinstance(definition, _ast.EnumTypeExtension):
        visit_enum_type_definition(visitor, definition)
    elif isinstance(definition, _ast.InputObjectTypeExtension):
        _visit_input_object_type_definition(visitor, definition)
    elif isinstance(definition, _ast.DirectiveDefinition):
        _visit_directive_definition(visitor, definition)


@_visiting
def _visit_operation_definition(
    visitor: Visitor, definition: _ast.OperationDefinition
) -> None:
    _many(_visit_variable_definition, visitor, definition.variable_definitions)
    _many(_visit_directive, visitor, definition.directives)
    _visit_selection_set(visitor, definition.selection_set)


@_visiting
def _visit_fragment_definition(
    visitor: Visitor, definition: _ast.FragmentDefinition
) -> None:
    _many(_visit_directive, visitor, definition.directives)
    _visit_selection_set(visitor, definition.selection_set)


@_visiting
def _visit_variable_definition(
    visitor: Visitor, variable_definition: _ast.VariableDefinition
) -> None:
    if variable_definition.default_value:
        _visit_input_value(visitor, variable_definition.default_value)
    _visit_type(visitor, variable_definition.type)


@_visiting
def _visit_type(_visitor: Visitor, _type: _ast.Type) -> None:
    pass


@_visiting
def _visit_directive(visitor: Visitor, directive: _ast.Directive) -> None:
    _many(_visit_argument, visitor, directive.arguments)


@_visiting
def _visit_argument(visitor: Visitor, argument: _ast.Argument) -> None:
    _visit_input_value(visitor, argument.value)


@_visiting
def _visit_selection_set(
    visitor: Visitor, selection_set: _ast.SelectionSet
) -> None:
    _many(_visit_selection, visitor, selection_set.selections)


def _visit_selection(visitor: Visitor, selection: _ast.Selection) -> None:
    if isinstance(selection, _ast.Field):
        _visit_field(visitor, selection)
    elif isinstance(selection, _ast.FragmentSpread):
        _visit_fragment_spread(visitor, selection)
    elif isinstance(selection, _ast.InlineFragment):
        _visit_inline_fragment(visitor, selection)


@_visiting
def _visit_field(visitor: Visitor, field: _ast.Field) -> None:
    _many(_visit_argument, visitor, field.arguments)
    _many(_visit_directive, visitor, field.directives)
    if field.selection_set is not None:
        _visit_selection_set(visitor, field.selection_set)


@_visiting
def _visit_fragment_spread(
    visitor: Visitor, spread: _ast.FragmentSpread
) -> None:
    _many(_visit_directive, visitor, spread.directives)


@_visiting
def _visit_inline_fragment(
    visitor: Visitor, fragment: _ast.InlineFragment
) -> None:
    _many(_visit_directive, visitor, fragment.directives)
    if fragment.selection_set:
        _visit_selection_set(visitor, fragment.selection_set)


@_visiting
def _visit_input_value(
    visitor: Visitor, input_value: Union[_ast.Value, _ast.Variable]
) -> None:
    if isinstance(input_value, _ast.ObjectValue):
        _many(_visit_object_field, visitor, input_value.fields)
    elif isinstance(input_value, _ast.ListValue):
        _many(_visit_input_value, visitor, input_value.values)


@_visiting
def _visit_object_field(visitor: Visitor, field: _ast.ObjectField) -> None:
    _visit_input_value(visitor, field.value)


@_visiting
def _visit_schema_definition(
    visitor: Visitor,
    definition: Union[_ast.SchemaDefinition, _ast.SchemaExtension],
) -> None:
    _many(_visit_operation_type_definition, visitor, definition.operation_types)
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_operation_type_definition(
    visitor: Visitor, definition: _ast.OperationTypeDefinition
) -> None:
    _visit_type(visitor, definition.type)


@_visiting
def _visit_scalar_type_definition(
    visitor: Visitor,
    definition: Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension],
) -> None:
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_object_type_definition(
    visitor: Visitor,
    definition: Union[_ast.ObjectTypeDefinition, _ast.ObjectTypeExtension],
) -> None:
    _many(_visit_type, visitor, definition.interfaces)
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_field_definition, visitor, definition.fields)


@_visiting
def _visit_interface_type_definition(
    visitor: Visitor,
    definition: Union[
        _ast.InterfaceTypeDefinition, _ast.InterfaceTypeExtension
    ],
) -> None:
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_field_definition, visitor, definition.fields)


@_visiting
def _visit_union_type_definition(
    visitor: Visitor,
    definition: Union[_ast.UnionTypeDefinition, _ast.UnionTypeExtension],
) -> None:
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_type, visitor, definition.types)


@_visiting
def visit_enum_type_definition(
    visitor: Visitor,
    definition: Union[_ast.EnumTypeDefinition, _ast.EnumTypeExtension],
) -> None:
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_enum_value_definition, visitor, definition.values)


@_visiting
def _visit_input_object_type_definition(
    visitor: Visitor,
    definition: Union[
        _ast.InputObjectTypeDefinition, _ast.InputObjectTypeExtension
    ],
) -> None:
    _many(_visit_directive, visitor, definition.directives)
    _many(_visit_input_value_definition, visitor, definition.fields)


@_visiting
def _visit_field_definition(
    visitor: Visitor, definition: _ast.FieldDefinition
) -> None:
    _visit_type(visitor, definition.type)
    _many(_visit_input_value_definition, visitor, definition.arguments)
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_input_value_definition(
    visitor: Visitor, definition: _ast.InputValueDefinition
) -> None:
    _visit_type(visitor, definition.type)
    if definition.default_value is not None:
        _visit_input_value(visitor, definition.default_value)
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_enum_value_definition(
    visitor: Visitor, definition: _ast.EnumValueDefinition
) -> None:
    _many(_visit_directive, visitor, definition.directives)


@_visiting
def _visit_directive_definition(
    visitor: Visitor, definition: _ast.DirectiveDefinition
) -> None:
    _many(_visit_input_value_definition, visitor, definition.arguments)


class DispatchingVisitor(Visitor):
    """
    Base class for specialised visitors.

    You should subclass this and implement methods named ``enter_*`` and
    ``leave_*`` where ``*`` represents the node class to be handled.
    For instance to process :class:`py_gql.lang.ast.FloatValue` nodes,
    implement ``enter_float_value``.

    Default behaviour is noop for all token types.
    """

    def enter(self, node: _ast.Node) -> None:  # noqa: C901
        kind = type(node)
        if kind is _ast.Document:
            self.enter_document(node)  # type: ignore
        elif kind is _ast.OperationDefinition:
            self.enter_operation_definition(node)  # type: ignore
        elif kind is _ast.FragmentDefinition:
            self.enter_fragment_definition(node)  # type: ignore
        elif kind is _ast.VariableDefinition:
            self.enter_variable_definition(node)  # type: ignore
        elif kind is _ast.Directive:
            self.enter_directive(node)  # type: ignore
        elif kind is _ast.Argument:
            self.enter_argument(node)  # type: ignore
        elif kind is _ast.SelectionSet:
            self.enter_selection_set(node)  # type: ignore
        elif kind is _ast.Field:
            self.enter_field(node)  # type: ignore
        elif kind is _ast.FragmentSpread:
            self.enter_fragment_spread(node)  # type: ignore
        elif kind is _ast.InlineFragment:
            self.enter_inline_fragment(node)  # type: ignore
        elif kind is _ast.NullValue:
            self.enter_null_value(node)  # type: ignore
        elif kind is _ast.IntValue:
            self.enter_int_value(node)  # type: ignore
        elif kind is _ast.FloatValue:
            self.enter_float_value(node)  # type: ignore
        elif kind is _ast.StringValue:
            self.enter_string_value(node)  # type: ignore
        elif kind is _ast.BooleanValue:
            self.enter_boolean_value(node)  # type: ignore
        elif kind is _ast.EnumValue:
            self.enter_enum_value(node)  # type: ignore
        elif kind is _ast.Variable:
            self.enter_variable(node)  # type: ignore
        elif kind is _ast.ListValue:
            self.enter_list_value(node)  # type: ignore
        elif kind is _ast.ObjectValue:
            self.enter_object_value(node)  # type: ignore
        elif kind is _ast.ObjectField:
            self.enter_object_field(node)  # type: ignore
        elif kind is _ast.NamedType:
            self.enter_named_type(node)  # type: ignore
        elif kind is _ast.ListType:
            self.enter_list_type(node)  # type: ignore
        elif kind is _ast.NonNullType:
            self.enter_non_null_type(node)  # type: ignore
        elif kind is _ast.SchemaDefinition:
            self.enter_schema_definition(node)  # type: ignore
        elif kind is _ast.OperationTypeDefinition:
            self.enter_operation_type_definition(node)  # type: ignore
        elif kind is _ast.ScalarTypeDefinition:
            self.enter_scalar_type_definition(node)  # type: ignore
        elif kind is _ast.ObjectTypeDefinition:
            self.enter_object_type_definition(node)  # type: ignore
        elif kind is _ast.FieldDefinition:
            self.enter_field_definition(node)  # type: ignore
        elif kind is _ast.InputValueDefinition:
            self.enter_input_value_definition(node)  # type: ignore
        elif kind is _ast.InterfaceTypeDefinition:
            self.enter_interface_type_definition(node)  # type: ignore
        elif kind is _ast.UnionTypeDefinition:
            self.enter_union_type_definition(node)  # type: ignore
        elif kind is _ast.EnumTypeDefinition:
            self.enter_enum_type_definition(node)  # type: ignore
        elif kind is _ast.EnumValueDefinition:
            self.enter_enum_value_definition(node)  # type: ignore
        elif kind is _ast.InputObjectTypeDefinition:
            self.enter_input_object_type_definition(node)  # type: ignore
        elif kind is _ast.SchemaExtension:
            self.enter_schema_extension(node)  # type: ignore
        elif kind is _ast.ScalarTypeExtension:
            self.enter_scalar_type_extension(node)  # type: ignore
        elif kind is _ast.ObjectTypeExtension:
            self.enter_object_type_extension(node)  # type: ignore
        elif kind is _ast.InterfaceTypeExtension:
            self.enter_interface_type_extension(node)  # type: ignore
        elif kind is _ast.UnionTypeExtension:
            self.enter_union_type_extension(node)  # type: ignore
        elif kind is _ast.EnumTypeExtension:
            self.enter_enum_type_extension(node)  # type: ignore
        elif kind is _ast.InputObjectTypeExtension:
            self.enter_input_object_type_extension(node)  # type: ignore
        elif kind is _ast.DirectiveDefinition:
            self.enter_directive_definition(node)  # type: ignore

    def leave(self, node: _ast.Node) -> None:  # noqa: C901
        kind = type(node)
        if kind is _ast.Document:
            self.leave_document(node)  # type: ignore
        elif kind is _ast.OperationDefinition:
            self.leave_operation_definition(node)  # type: ignore
        elif kind is _ast.FragmentDefinition:
            self.leave_fragment_definition(node)  # type: ignore
        elif kind is _ast.VariableDefinition:
            self.leave_variable_definition(node)  # type: ignore
        elif kind is _ast.Directive:
            self.leave_directive(node)  # type: ignore
        elif kind is _ast.Argument:
            self.leave_argument(node)  # type: ignore
        elif kind is _ast.SelectionSet:
            self.leave_selection_set(node)  # type: ignore
        elif kind is _ast.Field:
            self.leave_field(node)  # type: ignore
        elif kind is _ast.FragmentSpread:
            self.leave_fragment_spread(node)  # type: ignore
        elif kind is _ast.InlineFragment:
            self.leave_inline_fragment(node)  # type: ignore
        elif kind is _ast.NullValue:
            self.leave_null_value(node)  # type: ignore
        elif kind is _ast.IntValue:
            self.leave_int_value(node)  # type: ignore
        elif kind is _ast.FloatValue:
            self.leave_float_value(node)  # type: ignore
        elif kind is _ast.StringValue:
            self.leave_string_value(node)  # type: ignore
        elif kind is _ast.BooleanValue:
            self.leave_boolean_value(node)  # type: ignore
        elif kind is _ast.EnumValue:
            self.leave_enum_value(node)  # type: ignore
        elif kind is _ast.Variable:
            self.leave_variable(node)  # type: ignore
        elif kind is _ast.ListValue:
            self.leave_list_value(node)  # type: ignore
        elif kind is _ast.ObjectValue:
            self.leave_object_value(node)  # type: ignore
        elif kind is _ast.ObjectField:
            self.leave_object_field(node)  # type: ignore
        elif kind is _ast.NamedType:
            self.leave_named_type(node)  # type: ignore
        elif kind is _ast.ListType:
            self.leave_list_type(node)  # type: ignore
        elif kind is _ast.NonNullType:
            self.leave_non_null_type(node)  # type: ignore
        elif kind is _ast.SchemaDefinition:
            self.leave_schema_definition(node)  # type: ignore
        elif kind is _ast.OperationTypeDefinition:
            self.leave_operation_type_definition(node)  # type: ignore
        elif kind is _ast.ScalarTypeDefinition:
            self.leave_scalar_type_definition(node)  # type: ignore
        elif kind is _ast.ObjectTypeDefinition:
            self.leave_object_type_definition(node)  # type: ignore
        elif kind is _ast.FieldDefinition:
            self.leave_field_definition(node)  # type: ignore
        elif kind is _ast.InputValueDefinition:
            self.leave_input_value_definition(node)  # type: ignore
        elif kind is _ast.InterfaceTypeDefinition:
            self.leave_interface_type_definition(node)  # type: ignore
        elif kind is _ast.UnionTypeDefinition:
            self.leave_union_type_definition(node)  # type: ignore
        elif kind is _ast.EnumTypeDefinition:
            self.leave_enum_type_definition(node)  # type: ignore
        elif kind is _ast.EnumValueDefinition:
            self.leave_enum_value_definition(node)  # type: ignore
        elif kind is _ast.InputObjectTypeDefinition:
            self.leave_input_object_type_definition(node)  # type: ignore
        elif kind is _ast.SchemaExtension:
            self.leave_schema_extension(node)  # type: ignore
        elif kind is _ast.ScalarTypeExtension:
            self.leave_scalar_type_extension(node)  # type: ignore
        elif kind is _ast.ObjectTypeExtension:
            self.leave_object_type_extension(node)  # type: ignore
        elif kind is _ast.InterfaceTypeExtension:
            self.leave_interface_type_extension(node)  # type: ignore
        elif kind is _ast.UnionTypeExtension:
            self.leave_union_type_extension(node)  # type: ignore
        elif kind is _ast.EnumTypeExtension:
            self.leave_enum_type_extension(node)  # type: ignore
        elif kind is _ast.InputObjectTypeExtension:
            self.leave_input_object_type_extension(node)  # type: ignore
        elif kind is _ast.DirectiveDefinition:
            self.leave_directive_definition(node)  # type: ignore

    def _default_handler(self, node):
        pass

    def enter_document(self, _: _ast.Document) -> None:
        pass

    def leave_document(self, _: _ast.Document) -> None:
        pass

    def enter_operation_definition(self, _: _ast.OperationDefinition) -> None:
        pass

    def leave_operation_definition(self, _: _ast.OperationDefinition) -> None:
        pass

    def enter_fragment_definition(self, _: _ast.FragmentDefinition) -> None:
        pass

    def leave_fragment_definition(self, _: _ast.FragmentDefinition) -> None:
        pass

    def enter_variable_definition(self, _: _ast.VariableDefinition) -> None:
        pass

    def leave_variable_definition(self, _: _ast.VariableDefinition) -> None:
        pass

    def enter_directive(self, _: _ast.Directive) -> None:
        pass

    def leave_directive(self, _: _ast.Directive) -> None:
        pass

    def enter_argument(self, _: _ast.Argument) -> None:
        pass

    def leave_argument(self, _: _ast.Argument) -> None:
        pass

    def enter_selection_set(self, _: _ast.SelectionSet) -> None:
        pass

    def leave_selection_set(self, _: _ast.SelectionSet) -> None:
        pass

    def enter_field(self, _: _ast.Field) -> None:
        pass

    def leave_field(self, _: _ast.Field) -> None:
        pass

    def enter_fragment_spread(self, _: _ast.FragmentSpread) -> None:
        pass

    def leave_fragment_spread(self, _: _ast.FragmentSpread) -> None:
        pass

    def enter_inline_fragment(self, _: _ast.InlineFragment) -> None:
        pass

    def leave_inline_fragment(self, _: _ast.InlineFragment) -> None:
        pass

    def enter_null_value(self, _: _ast.NullValue) -> None:
        pass

    def leave_null_value(self, _: _ast.NullValue) -> None:
        pass

    def enter_int_value(self, _: _ast.IntValue) -> None:
        pass

    def leave_int_value(self, _: _ast.IntValue) -> None:
        pass

    def enter_float_value(self, _: _ast.FloatValue) -> None:
        pass

    def leave_float_value(self, _: _ast.FloatValue) -> None:
        pass

    def enter_string_value(self, _: _ast.StringValue) -> None:
        pass

    def leave_string_value(self, _: _ast.StringValue) -> None:
        pass

    def enter_boolean_value(self, _: _ast.BooleanValue) -> None:
        pass

    def leave_boolean_value(self, _: _ast.BooleanValue) -> None:
        pass

    def enter_enum_value(self, _: _ast.EnumValue) -> None:
        pass

    def leave_enum_value(self, _: _ast.EnumValue) -> None:
        pass

    def enter_variable(self, _: _ast.Variable) -> None:
        pass

    def leave_variable(self, _: _ast.Variable) -> None:
        pass

    def enter_list_value(self, _: _ast.ListValue) -> None:
        pass

    def leave_list_value(self, _: _ast.ListValue) -> None:
        pass

    def enter_object_value(self, _: _ast.ObjectValue) -> None:
        pass

    def leave_object_value(self, _: _ast.ObjectValue) -> None:
        pass

    def enter_object_field(self, _: _ast.ObjectField) -> None:
        pass

    def leave_object_field(self, _: _ast.ObjectField) -> None:
        pass

    def enter_named_type(self, _: _ast.NamedType) -> None:
        pass

    def leave_named_type(self, _: _ast.NamedType) -> None:
        pass

    def enter_list_type(self, _: _ast.ListType) -> None:
        pass

    def leave_list_type(self, _: _ast.ListType) -> None:
        pass

    def enter_non_null_type(self, _: _ast.NonNullType) -> None:
        pass

    def leave_non_null_type(self, _: _ast.NonNullType) -> None:
        pass

    def enter_schema_definition(self, _: _ast.SchemaDefinition) -> None:
        pass

    def leave_schema_definition(self, _: _ast.SchemaDefinition) -> None:
        pass

    def enter_operation_type_definition(
        self, _: _ast.OperationTypeDefinition
    ) -> None:
        pass

    def leave_operation_type_definition(
        self, _: _ast.OperationTypeDefinition
    ) -> None:
        pass

    def enter_scalar_type_definition(
        self, _: _ast.ScalarTypeDefinition
    ) -> None:
        pass

    def leave_scalar_type_definition(
        self, _: _ast.ScalarTypeDefinition
    ) -> None:
        pass

    def enter_object_type_definition(
        self, _: _ast.ObjectTypeDefinition
    ) -> None:
        pass

    def leave_object_type_definition(
        self, _: _ast.ObjectTypeDefinition
    ) -> None:
        pass

    def enter_field_definition(self, _: _ast.FieldDefinition) -> None:
        pass

    def leave_field_definition(self, _: _ast.FieldDefinition) -> None:
        pass

    def enter_input_value_definition(
        self, _: _ast.InputValueDefinition
    ) -> None:
        pass

    def leave_input_value_definition(
        self, _: _ast.InputValueDefinition
    ) -> None:
        pass

    def enter_interface_type_definition(
        self, _: _ast.InterfaceTypeDefinition
    ) -> None:
        pass

    def leave_interface_type_definition(
        self, _: _ast.InterfaceTypeDefinition
    ) -> None:
        pass

    def enter_union_type_definition(self, _: _ast.UnionTypeDefinition) -> None:
        pass

    def leave_union_type_definition(self, _: _ast.UnionTypeDefinition) -> None:
        pass

    def enter_enum_type_definition(self, _: _ast.EnumTypeDefinition) -> None:
        pass

    def leave_enum_type_definition(self, _: _ast.EnumTypeDefinition) -> None:
        pass

    def enter_enum_value_definition(self, _: _ast.EnumValueDefinition) -> None:
        pass

    def leave_enum_value_definition(self, _: _ast.EnumValueDefinition) -> None:
        pass

    def enter_input_object_type_definition(
        self, _: _ast.InputObjectTypeDefinition
    ) -> None:
        pass

    def leave_input_object_type_definition(
        self, _: _ast.InputObjectTypeDefinition
    ) -> None:
        pass

    def enter_schema_extension(self, _: _ast.SchemaExtension) -> None:
        pass

    def leave_schema_extension(self, _: _ast.SchemaExtension) -> None:
        pass

    def enter_scalar_type_extension(self, _: _ast.ScalarTypeExtension) -> None:
        pass

    def leave_scalar_type_extension(self, _: _ast.ScalarTypeExtension) -> None:
        pass

    def enter_object_type_extension(self, _: _ast.ObjectTypeExtension) -> None:
        pass

    def leave_object_type_extension(self, _: _ast.ObjectTypeExtension) -> None:
        pass

    def enter_interface_type_extension(
        self, _: _ast.InterfaceTypeExtension
    ) -> None:
        pass

    def leave_interface_type_extension(
        self, _: _ast.InterfaceTypeExtension
    ) -> None:
        pass

    def enter_union_type_extension(self, _: _ast.UnionTypeExtension) -> None:
        pass

    def leave_union_type_extension(self, _: _ast.UnionTypeExtension) -> None:
        pass

    def enter_enum_type_extension(self, _: _ast.EnumTypeExtension) -> None:
        pass

    def leave_enum_type_extension(self, _: _ast.EnumTypeExtension) -> None:
        pass

    def enter_input_object_type_extension(
        self, _: _ast.InputObjectTypeExtension
    ) -> None:
        pass

    def leave_input_object_type_extension(
        self, _: _ast.InputObjectTypeExtension
    ) -> None:
        pass

    def enter_directive_definition(self, _: _ast.DirectiveDefinition) -> None:
        pass

    def leave_directive_definition(self, _: _ast.DirectiveDefinition) -> None:
        pass


class ParallelVisitor(Visitor):
    """
    Abstraction to run multiple visitor instances as one.

    - All visitors are run in the order they are defined.
    - raising :class:`SkipNode` in one of them will prevent any later visitor
      to run.

    Args:
        *visitors: List of visitors to run.

    Attributes:
        visitors (List[Visitor]): Children visitors.
    """

    def __init__(self, *visitors: Visitor):
        self.visitors = tuple(visitors)

    def enter(self, node: _ast.Node) -> None:
        for v in self.visitors:
            v.enter(node)

    def leave(self, node: _ast.Node) -> None:
        for v in self.visitors[::-1]:
            v.leave(node)
