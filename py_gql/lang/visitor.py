# -*- coding: utf-8 -*-
"""
Visitors provide abstractions for traversing and transforming a GraphQL AST.
"""

import functools
from typing import Optional, TypeVar, Union

from .._utils import classdispatch, map_and_filter
from ..exc import GraphQLError
from . import ast as _ast

T = TypeVar("T")
N = TypeVar("N", bound=_ast.Node)
S = TypeVar("S", bound=_ast.Selection)


__all__ = (
    "SkipNode",
    "ASTVisitor",
    "DispatchingVisitor",
    "ChainedVisitor",
)


class SkipNode(GraphQLError):
    """
    Raise this to short-circuit traversal and ignore the node and all its
    children.
    """

    pass


def _visit_method(method):
    @functools.wraps(method)
    def wrapper(inst, node):
        try:
            node = inst.enter(node)
        except SkipNode:
            return node

        if node is not None:
            node = method(inst, node)

        if node is not None:
            inst.leave(node)

        return node

    return wrapper


class ASTVisitor:
    """
    Base visitor class used to build complex AST tarversal and trnsform
    behaviours.
    """

    def enter(self, node: N) -> Optional[N]:
        """
        Implement this for the main visiting behaviour (i.e. before a node's
        children have been visited).

        Return ``None`` to delete the node from
        it's parent context or raise :class:`SkipNode` to prevent any further
        processing (children do not get visited and `leave` doesn't get
        called for that node).
        """
        return node

    def leave(self, node: N) -> None:
        """
        Implement this if you need behaviour to run after a node's children
        have been visited.

        This is called with the corresponding value returned by :meth:`enter`.
        In case you modify the node, this will be called on the modified node.
        This doesn't run if :meth:`enter` returned ``None`` or raised
        :class:`SkipNode`.
        """
        pass

    def visit(self, node: N) -> Optional[N]:
        """
        Apply visitor's behaviour to a given node.

        Warning:
            Transformations are applied inline. If you rely on node identity
            in your tooling, you should use `copy.deepcopy` or analogous before
            calling this.

        Warning:
            In general you should not override this method as this is where
            tarversal of a node's children and orchestration around :meth:`enter`
            and :meth:`leave` is encoded.
        """
        return classdispatch(
            node,
            {
                _ast.Document: self._visit_document,
                _ast.OperationDefinition: self._visit_operation_definition,
                _ast.VariableDefinition: self._visit_variable_definition,
                _ast.Variable: self._visit_variable,
                _ast.SelectionSet: self._visit_selection_set,
                _ast.Field: self._visit_field,
                _ast.Argument: self._visit_argument,
                _ast.FragmentSpread: self._visit_fragment_spread,
                _ast.InlineFragment: self._visit_inline_fragment,
                _ast.FragmentDefinition: self._visit_fragment_definition,
                _ast.IntValue: self._visit_value,
                _ast.FloatValue: self._visit_value,
                _ast.BooleanValue: self._visit_value,
                _ast.NullValue: self._visit_value,
                _ast.EnumValue: self._visit_value,
                _ast.StringValue: self._visit_value,
                _ast.ListValue: self._visit_value,
                _ast.ObjectValue: self._visit_value,
                _ast.ObjectField: self._visit_object_field,
                _ast.Directive: self._visit_directive,
                _ast.NonNullType: self._visit_type,
                _ast.ListType: self._visit_type,
                _ast.NamedType: self._visit_type,
                _ast.SchemaDefinition: self._visit_schema_definition,
                _ast.OperationTypeDefinition: self._visit_operation_type_definition,
                _ast.ScalarTypeDefinition: self._visit_scalar_type_definition,
                _ast.ObjectTypeDefinition: self._visit_object_type_definition,
                _ast.FieldDefinition: self._visit_field_definition,
                _ast.InputValueDefinition: self._visit_input_value_definition,
                _ast.InterfaceTypeDefinition: self._visit_interface_type_definition,
                _ast.UnionTypeDefinition: self._visit_union_type_definition,
                _ast.EnumTypeDefinition: self._visit_enum_type_definition,
                _ast.EnumValueDefinition: self._visit_enum_value_definition,
                _ast.InputObjectTypeDefinition: (
                    self._visit_input_object_type_definition
                ),
                _ast.SchemaExtension: self._visit_schema_definition,
                _ast.ScalarTypeExtension: self._visit_scalar_type_definition,
                _ast.ObjectTypeExtension: self._visit_object_type_definition,
                _ast.InterfaceTypeExtension: self._visit_interface_type_definition,
                _ast.UnionTypeExtension: self._visit_union_type_definition,
                _ast.EnumTypeExtension: self._visit_enum_type_definition,
                _ast.InputObjectTypeExtension: self._visit_input_object_type_definition,
                _ast.DirectiveDefinition: self._visit_directive_definition,
            },
        )

    @_visit_method
    def _visit_document(self, document: _ast.Document) -> _ast.Document:
        document.definitions = map_and_filter(
            self._visit_definition, document.definitions
        )
        return document

    def _visit_definition(self, node: _ast.Definition) -> _ast.Definition:
        return classdispatch(
            node,
            {
                _ast.OperationDefinition: self._visit_operation_definition,
                _ast.FragmentDefinition: self._visit_fragment_definition,
                _ast.SchemaDefinition: self._visit_schema_definition,
                _ast.ScalarTypeDefinition: self._visit_scalar_type_definition,
                _ast.ObjectTypeDefinition: self._visit_object_type_definition,
                _ast.InterfaceTypeDefinition: self._visit_interface_type_definition,
                _ast.UnionTypeDefinition: self._visit_union_type_definition,
                _ast.EnumTypeDefinition: self._visit_enum_type_definition,
                _ast.InputObjectTypeDefinition: (
                    self._visit_input_object_type_definition
                ),
                _ast.SchemaExtension: self._visit_schema_definition,
                _ast.ScalarTypeExtension: self._visit_scalar_type_definition,
                _ast.ObjectTypeExtension: self._visit_object_type_definition,
                _ast.InterfaceTypeExtension: self._visit_interface_type_definition,
                _ast.UnionTypeExtension: self._visit_union_type_definition,
                _ast.EnumTypeExtension: self._visit_enum_type_definition,
                _ast.InputObjectTypeExtension: self._visit_input_object_type_definition,
                _ast.DirectiveDefinition: self._visit_directive_definition,
            },
        )

    @_visit_method
    def _visit_operation_definition(
        self, definition: _ast.OperationDefinition
    ) -> _ast.OperationDefinition:
        definition.variable_definitions = map_and_filter(
            self._visit_variable_definition, definition.variable_definitions
        )
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.selection_set = self._visit_selection_set(
            definition.selection_set
        )
        return definition

    @_visit_method
    def _visit_fragment_definition(
        self, definition: _ast.FragmentDefinition
    ) -> _ast.FragmentDefinition:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.selection_set = self._visit_selection_set(
            definition.selection_set
        )
        return definition

    @_visit_method
    def _visit_variable_definition(
        self, definition: _ast.VariableDefinition
    ) -> _ast.VariableDefinition:
        if definition.default_value:
            definition.default_value = self._visit_value(
                definition.default_value
            )
        definition.type = self._visit_type(definition.type)
        return definition

    @_visit_method
    def _visit_type(self, type_: _ast.Type) -> _ast.Type:
        return type_

    @_visit_method
    def _visit_directive(self, directive: _ast.Directive) -> _ast.Directive:
        directive.arguments = map_and_filter(
            self._visit_argument, directive.arguments
        )
        return directive

    @_visit_method
    def _visit_argument(self, argument: _ast.Argument) -> _ast.Argument:
        argument.value = self._visit_input_value(argument.value)
        return argument

    @_visit_method
    def _visit_selection_set(
        self, selection_set: _ast.SelectionSet
    ) -> _ast.SelectionSet:
        selection_set.selections = map_and_filter(
            self._visit_selection, selection_set.selections
        )
        return selection_set

    def _visit_selection(self, selection: S) -> S:
        return classdispatch(
            selection,
            {
                _ast.Field: self._visit_field,
                _ast.FragmentSpread: self._visit_fragment_spread,
                _ast.InlineFragment: self._visit_inline_fragment,
            },
        )

    @_visit_method
    def _visit_field(self, field: _ast.Field) -> _ast.Field:
        field.arguments = map_and_filter(self._visit_argument, field.arguments)
        field.directives = map_and_filter(
            self._visit_directive, field.directives
        )
        if field.selection_set is not None:
            field.selection_set = self._visit_selection_set(field.selection_set)
        return field

    @_visit_method
    def _visit_fragment_spread(
        self, spread: _ast.FragmentSpread
    ) -> _ast.FragmentSpread:
        spread.directives = list(
            map_and_filter(self._visit_directive, spread.directives)
        )
        return spread

    @_visit_method
    def _visit_inline_fragment(
        self, fragment: _ast.InlineFragment
    ) -> _ast.InlineFragment:
        fragment.directives = map_and_filter(
            self._visit_directive, fragment.directives
        )
        fragment.selection_set = self._visit_selection_set(
            fragment.selection_set
        )
        return fragment

    def _visit_input_value(
        self, value: Union[_ast.Value, _ast.Variable]
    ) -> Union[_ast.Value, _ast.Variable]:
        if isinstance(value, _ast.Variable):
            return self._visit_variable(value)  # type: ignore
        return self._visit_value(value)  # type: ignore

    @_visit_method
    def _visit_variable(self, var: _ast.Variable) -> _ast.Variable:
        return var

    @_visit_method
    def _visit_value(self, value: _ast.Value) -> _ast.Value:
        if isinstance(value, _ast.ObjectValue):
            value.fields = map_and_filter(
                self._visit_object_field, value.fields
            )
        elif isinstance(value, _ast.ListValue):
            value.values = map_and_filter(self._visit_input_value, value.values)
        return value

    @_visit_method
    def _visit_object_field(self, field: _ast.ObjectField) -> _ast.ObjectField:
        field.value = self._visit_value(field.value)
        return field

    @_visit_method
    def _visit_schema_definition(
        self, definition: Union[_ast.SchemaDefinition, _ast.SchemaExtension]
    ) -> Union[_ast.SchemaDefinition, _ast.SchemaExtension]:
        definition.operation_types = map_and_filter(
            self._visit_operation_type_definition, definition.operation_types
        )
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        return definition

    @_visit_method
    def _visit_operation_type_definition(
        self, definition: _ast.OperationTypeDefinition
    ) -> _ast.OperationTypeDefinition:
        definition.type = self._visit_type(definition.type)
        return definition

    @_visit_method
    def _visit_scalar_type_definition(
        self,
        definition: Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension],
    ) -> Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension]:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        return definition

    @_visit_method
    def _visit_object_type_definition(
        self,
        definition: Union[_ast.ObjectTypeDefinition, _ast.ObjectTypeExtension],
    ) -> Union[_ast.ObjectTypeDefinition, _ast.ObjectTypeExtension]:
        definition.interfaces = map_and_filter(
            self._visit_type, definition.interfaces
        )
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.fields = map_and_filter(
            self._visit_field_definition, definition.fields
        )
        return definition

    @_visit_method
    def _visit_interface_type_definition(
        self,
        definition: Union[
            _ast.InterfaceTypeDefinition, _ast.InterfaceTypeExtension
        ],
    ) -> Union[_ast.InterfaceTypeDefinition, _ast.InterfaceTypeExtension]:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.fields = map_and_filter(
            self._visit_field_definition, definition.fields
        )
        return definition

    @_visit_method
    def _visit_union_type_definition(
        self,
        definition: Union[_ast.UnionTypeDefinition, _ast.UnionTypeExtension],
    ) -> Union[_ast.UnionTypeDefinition, _ast.UnionTypeExtension]:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.types = map_and_filter(self._visit_type, definition.types)
        return definition

    @_visit_method
    def _visit_enum_type_definition(
        self, definition: Union[_ast.EnumTypeDefinition, _ast.EnumTypeExtension]
    ) -> Union[_ast.EnumTypeDefinition, _ast.EnumTypeExtension]:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.values = map_and_filter(
            self._visit_enum_value_definition, definition.values
        )
        return definition

    @_visit_method
    def _visit_input_object_type_definition(
        self,
        definition: Union[
            _ast.InputObjectTypeDefinition, _ast.InputObjectTypeExtension
        ],
    ) -> Union[_ast.InputObjectTypeDefinition, _ast.InputObjectTypeExtension]:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        definition.fields = map_and_filter(
            self._visit_input_value_definition, definition.fields
        )
        return definition

    @_visit_method
    def _visit_field_definition(
        self, definition: _ast.FieldDefinition
    ) -> _ast.FieldDefinition:
        definition.type = self._visit_type(definition.type)
        definition.arguments = map_and_filter(
            self._visit_input_value_definition, definition.arguments
        )
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        return definition

    @_visit_method
    def _visit_input_value_definition(
        self, definition: _ast.InputValueDefinition
    ) -> _ast.InputValueDefinition:
        definition.type = self._visit_type(definition.type)
        if definition.default_value is not None:
            self._visit_input_value(definition.default_value)
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        return definition

    @_visit_method
    def _visit_enum_value_definition(
        self, definition: _ast.EnumValueDefinition
    ) -> _ast.EnumValueDefinition:
        definition.directives = map_and_filter(
            self._visit_directive, definition.directives
        )
        return definition

    @_visit_method
    def _visit_directive_definition(
        self, definition: _ast.DirectiveDefinition
    ) -> _ast.DirectiveDefinition:
        definition.arguments = map_and_filter(
            self._visit_input_value_definition, definition.arguments
        )
        return definition


class DispatchingVisitor(ASTVisitor):
    """
    Base class for specialised visitors.

    You should subclass this and implement methods named ``enter_*`` and
    ``leave_*`` where ``*`` represents the node class to be handled.
    For instance to process :class:`py_gql.lang.ast.FloatValue` nodes,
    implement ``enter_float_value``.

    Default behaviour is noop for all node types.
    """

    def enter(self, node: N) -> Optional[N]:
        # Not sure why typechecking doesn't work here, maybe something to do
        # with the decorator?
        return classdispatch(  # type: ignore
            node,
            {
                _ast.Document: self.enter_document,
                _ast.OperationDefinition: self.enter_operation_definition,
                _ast.FragmentDefinition: self.enter_fragment_definition,
                _ast.VariableDefinition: self.enter_variable_definition,
                _ast.Directive: self.enter_directive,
                _ast.Argument: self.enter_argument,
                _ast.SelectionSet: self.enter_selection_set,
                _ast.Field: self.enter_field,
                _ast.FragmentSpread: self.enter_fragment_spread,
                _ast.InlineFragment: self.enter_inline_fragment,
                _ast.NullValue: self.enter_null_value,
                _ast.IntValue: self.enter_int_value,
                _ast.FloatValue: self.enter_float_value,
                _ast.StringValue: self.enter_string_value,
                _ast.BooleanValue: self.enter_boolean_value,
                _ast.EnumValue: self.enter_enum_value,
                _ast.Variable: self.enter_variable,
                _ast.ListValue: self.enter_list_value,
                _ast.ObjectValue: self.enter_object_value,
                _ast.ObjectField: self.enter_object_field,
                _ast.NamedType: self.enter_named_type,
                _ast.ListType: self.enter_list_type,
                _ast.NonNullType: self.enter_non_null_type,
                _ast.SchemaDefinition: self.enter_schema_definition,
                _ast.OperationTypeDefinition: self.enter_operation_type_definition,
                _ast.ScalarTypeDefinition: self.enter_scalar_type_definition,
                _ast.ObjectTypeDefinition: self.enter_object_type_definition,
                _ast.FieldDefinition: self.enter_field_definition,
                _ast.InputValueDefinition: self.enter_input_value_definition,
                _ast.InterfaceTypeDefinition: self.enter_interface_type_definition,
                _ast.UnionTypeDefinition: self.enter_union_type_definition,
                _ast.EnumTypeDefinition: self.enter_enum_type_definition,
                _ast.EnumValueDefinition: self.enter_enum_value_definition,
                _ast.InputObjectTypeDefinition: self.enter_input_object_type_definition,
                _ast.SchemaExtension: self.enter_schema_extension,
                _ast.ScalarTypeExtension: self.enter_scalar_type_extension,
                _ast.ObjectTypeExtension: self.enter_object_type_extension,
                _ast.InterfaceTypeExtension: self.enter_interface_type_extension,
                _ast.UnionTypeExtension: self.enter_union_type_extension,
                _ast.EnumTypeExtension: self.enter_enum_type_extension,
                _ast.InputObjectTypeExtension: self.enter_input_object_type_extension,
                _ast.DirectiveDefinition: self.enter_directive_definition,
            },
        )

    # Not sure why typechecking doesn't work here, maybe something to do
    # with the decorator?
    def leave(self, node: _ast.Node) -> None:
        return classdispatch(  # type: ignore
            node,
            {
                _ast.Document: self.leave_document,
                _ast.OperationDefinition: self.leave_operation_definition,
                _ast.FragmentDefinition: self.leave_fragment_definition,
                _ast.VariableDefinition: self.leave_variable_definition,
                _ast.Directive: self.leave_directive,
                _ast.Argument: self.leave_argument,
                _ast.SelectionSet: self.leave_selection_set,
                _ast.Field: self.leave_field,
                _ast.FragmentSpread: self.leave_fragment_spread,
                _ast.InlineFragment: self.leave_inline_fragment,
                _ast.NullValue: self.leave_null_value,
                _ast.IntValue: self.leave_int_value,
                _ast.FloatValue: self.leave_float_value,
                _ast.StringValue: self.leave_string_value,
                _ast.BooleanValue: self.leave_boolean_value,
                _ast.EnumValue: self.leave_enum_value,
                _ast.Variable: self.leave_variable,
                _ast.ListValue: self.leave_list_value,
                _ast.ObjectValue: self.leave_object_value,
                _ast.ObjectField: self.leave_object_field,
                _ast.NamedType: self.leave_named_type,
                _ast.ListType: self.leave_list_type,
                _ast.NonNullType: self.leave_non_null_type,
                _ast.SchemaDefinition: self.leave_schema_definition,
                _ast.OperationTypeDefinition: self.leave_operation_type_definition,
                _ast.ScalarTypeDefinition: self.leave_scalar_type_definition,
                _ast.ObjectTypeDefinition: self.leave_object_type_definition,
                _ast.FieldDefinition: self.leave_field_definition,
                _ast.InputValueDefinition: self.leave_input_value_definition,
                _ast.InterfaceTypeDefinition: self.leave_interface_type_definition,
                _ast.UnionTypeDefinition: self.leave_union_type_definition,
                _ast.EnumTypeDefinition: self.leave_enum_type_definition,
                _ast.EnumValueDefinition: self.leave_enum_value_definition,
                _ast.InputObjectTypeDefinition: self.leave_input_object_type_definition,
                _ast.SchemaExtension: self.leave_schema_extension,
                _ast.ScalarTypeExtension: self.leave_scalar_type_extension,
                _ast.ObjectTypeExtension: self.leave_object_type_extension,
                _ast.InterfaceTypeExtension: self.leave_interface_type_extension,
                _ast.UnionTypeExtension: self.leave_union_type_extension,
                _ast.EnumTypeExtension: self.leave_enum_type_extension,
                _ast.InputObjectTypeExtension: self.leave_input_object_type_extension,
                _ast.DirectiveDefinition: self.leave_directive_definition,
            },
        )

    def enter_document(self, node: _ast.Document) -> Optional[_ast.Document]:
        return node

    def leave_document(self, _: _ast.Document) -> None:
        pass

    def enter_operation_definition(
        self, node: _ast.OperationDefinition
    ) -> Optional[_ast.OperationDefinition]:
        return node

    def leave_operation_definition(self, _: _ast.OperationDefinition) -> None:
        pass

    def enter_fragment_definition(
        self, node: _ast.FragmentDefinition
    ) -> Optional[_ast.FragmentDefinition]:
        return node

    def leave_fragment_definition(self, _: _ast.FragmentDefinition) -> None:
        pass

    def enter_variable_definition(
        self, node: _ast.VariableDefinition
    ) -> Optional[_ast.VariableDefinition]:
        return node

    def leave_variable_definition(self, _: _ast.VariableDefinition) -> None:
        pass

    def enter_directive(self, node: _ast.Directive) -> Optional[_ast.Directive]:
        return node

    def leave_directive(self, _: _ast.Directive) -> None:
        pass

    def enter_argument(self, node: _ast.Argument) -> Optional[_ast.Argument]:
        return node

    def leave_argument(self, _: _ast.Argument) -> None:
        pass

    def enter_selection_set(
        self, node: _ast.SelectionSet
    ) -> Optional[_ast.SelectionSet]:
        return node

    def leave_selection_set(self, _: _ast.SelectionSet) -> None:
        pass

    def enter_field(self, node: _ast.Field) -> Optional[_ast.Field]:
        return node

    def leave_field(self, _: _ast.Field) -> None:
        pass

    def enter_fragment_spread(
        self, node: _ast.FragmentSpread
    ) -> Optional[_ast.FragmentSpread]:
        return node

    def leave_fragment_spread(self, _: _ast.FragmentSpread) -> None:
        pass

    def enter_inline_fragment(
        self, node: _ast.InlineFragment
    ) -> Optional[_ast.InlineFragment]:
        return node

    def leave_inline_fragment(self, _: _ast.InlineFragment) -> None:
        pass

    def enter_null_value(
        self, node: _ast.NullValue
    ) -> Optional[_ast.NullValue]:
        return node

    def leave_null_value(self, _: _ast.NullValue) -> None:
        pass

    def enter_int_value(self, node: _ast.IntValue) -> Optional[_ast.IntValue]:
        return node

    def leave_int_value(self, _: _ast.IntValue) -> None:
        pass

    def enter_float_value(
        self, node: _ast.FloatValue
    ) -> Optional[_ast.FloatValue]:
        return node

    def leave_float_value(self, _: _ast.FloatValue) -> None:
        pass

    def enter_string_value(
        self, node: _ast.StringValue
    ) -> Optional[_ast.StringValue]:
        return node

    def leave_string_value(self, _: _ast.StringValue) -> None:
        pass

    def enter_boolean_value(
        self, node: _ast.BooleanValue
    ) -> Optional[_ast.BooleanValue]:
        return node

    def leave_boolean_value(self, _: _ast.BooleanValue) -> None:
        pass

    def enter_enum_value(
        self, node: _ast.EnumValue
    ) -> Optional[_ast.EnumValue]:
        return node

    def leave_enum_value(self, _: _ast.EnumValue) -> None:
        pass

    def enter_variable(self, node: _ast.Variable) -> Optional[_ast.Variable]:
        return node

    def leave_variable(self, _: _ast.Variable) -> None:
        pass

    def enter_list_value(
        self, node: _ast.ListValue
    ) -> Optional[_ast.ListValue]:
        return node

    def leave_list_value(self, _: _ast.ListValue) -> None:
        pass

    def enter_object_value(
        self, node: _ast.ObjectValue
    ) -> Optional[_ast.ObjectValue]:
        return node

    def leave_object_value(self, _: _ast.ObjectValue) -> None:
        pass

    def enter_object_field(
        self, node: _ast.ObjectField
    ) -> Optional[_ast.ObjectField]:
        return node

    def leave_object_field(self, _: _ast.ObjectField) -> None:
        pass

    def enter_named_type(
        self, node: _ast.NamedType
    ) -> Optional[_ast.NamedType]:
        return node

    def leave_named_type(self, _: _ast.NamedType) -> None:
        pass

    def enter_list_type(self, node: _ast.ListType) -> Optional[_ast.ListType]:
        return node

    def leave_list_type(self, _: _ast.ListType) -> None:
        pass

    def enter_non_null_type(
        self, node: _ast.NonNullType
    ) -> Optional[_ast.NonNullType]:
        return node

    def leave_non_null_type(self, _: _ast.NonNullType) -> None:
        pass

    def enter_schema_definition(
        self, node: _ast.SchemaDefinition
    ) -> Optional[_ast.SchemaDefinition]:
        return node

    def leave_schema_definition(self, _: _ast.SchemaDefinition) -> None:
        pass

    def enter_operation_type_definition(
        self, node: _ast.OperationTypeDefinition
    ) -> Optional[_ast.OperationTypeDefinition]:
        return node

    def leave_operation_type_definition(
        self, _: _ast.OperationTypeDefinition
    ) -> None:
        pass

    def enter_scalar_type_definition(
        self, node: _ast.ScalarTypeDefinition
    ) -> Optional[_ast.ScalarTypeDefinition]:
        return node

    def leave_scalar_type_definition(
        self, _: _ast.ScalarTypeDefinition
    ) -> None:
        pass

    def enter_object_type_definition(
        self, node: _ast.ObjectTypeDefinition
    ) -> Optional[_ast.ObjectTypeDefinition]:
        return node

    def leave_object_type_definition(
        self, _: _ast.ObjectTypeDefinition
    ) -> None:
        pass

    def enter_field_definition(
        self, node: _ast.FieldDefinition
    ) -> Optional[_ast.FieldDefinition]:
        return node

    def leave_field_definition(self, _: _ast.FieldDefinition) -> None:
        pass

    def enter_input_value_definition(
        self, node: _ast.InputValueDefinition
    ) -> Optional[_ast.InputValueDefinition]:
        return node

    def leave_input_value_definition(
        self, _: _ast.InputValueDefinition
    ) -> None:
        pass

    def enter_interface_type_definition(
        self, node: _ast.InterfaceTypeDefinition
    ) -> Optional[_ast.InterfaceTypeDefinition]:
        return node

    def leave_interface_type_definition(
        self, _: _ast.InterfaceTypeDefinition
    ) -> None:
        pass

    def enter_union_type_definition(
        self, node: _ast.UnionTypeDefinition
    ) -> Optional[_ast.UnionTypeDefinition]:
        return node

    def leave_union_type_definition(self, _: _ast.UnionTypeDefinition) -> None:
        pass

    def enter_enum_type_definition(
        self, node: _ast.EnumTypeDefinition
    ) -> Optional[_ast.EnumTypeDefinition]:
        return node

    def leave_enum_type_definition(self, _: _ast.EnumTypeDefinition) -> None:
        pass

    def enter_enum_value_definition(
        self, node: _ast.EnumValueDefinition
    ) -> Optional[_ast.EnumValueDefinition]:
        return node

    def leave_enum_value_definition(self, _: _ast.EnumValueDefinition) -> None:
        pass

    def enter_input_object_type_definition(
        self, node: _ast.InputObjectTypeDefinition
    ) -> Optional[_ast.InputObjectTypeDefinition]:
        return node

    def leave_input_object_type_definition(
        self, _: _ast.InputObjectTypeDefinition
    ) -> None:
        pass

    def enter_schema_extension(
        self, node: _ast.SchemaExtension
    ) -> Optional[_ast.SchemaExtension]:
        return node

    def leave_schema_extension(self, _: _ast.SchemaExtension) -> None:
        pass

    def enter_scalar_type_extension(
        self, node: _ast.ScalarTypeExtension
    ) -> Optional[_ast.ScalarTypeExtension]:
        return node

    def leave_scalar_type_extension(self, _: _ast.ScalarTypeExtension) -> None:
        pass

    def enter_object_type_extension(
        self, node: _ast.ObjectTypeExtension
    ) -> Optional[_ast.ObjectTypeExtension]:
        return node

    def leave_object_type_extension(self, _: _ast.ObjectTypeExtension) -> None:
        pass

    def enter_interface_type_extension(
        self, node: _ast.InterfaceTypeExtension
    ) -> Optional[_ast.InterfaceTypeExtension]:
        return node

    def leave_interface_type_extension(
        self, _: _ast.InterfaceTypeExtension
    ) -> None:
        pass

    def enter_union_type_extension(
        self, node: _ast.UnionTypeExtension
    ) -> Optional[_ast.UnionTypeExtension]:
        return node

    def leave_union_type_extension(self, _: _ast.UnionTypeExtension) -> None:
        pass

    def enter_enum_type_extension(
        self, node: _ast.EnumTypeExtension
    ) -> Optional[_ast.EnumTypeExtension]:
        return node

    def leave_enum_type_extension(self, _: _ast.EnumTypeExtension) -> None:
        pass

    def enter_input_object_type_extension(
        self, node: _ast.InputObjectTypeExtension
    ) -> Optional[_ast.InputObjectTypeExtension]:
        return node

    def leave_input_object_type_extension(
        self, _: _ast.InputObjectTypeExtension
    ) -> None:
        pass

    def enter_directive_definition(
        self, node: _ast.DirectiveDefinition
    ) -> Optional[_ast.DirectiveDefinition]:
        return node

    def leave_directive_definition(self, _: _ast.DirectiveDefinition) -> None:
        pass


class ChainedVisitor(ASTVisitor):
    """Run multiple visitor instances in sequence.

    - All visitors are run in the order they are defined, with enter being
      called in order and leave in reverse order.
    - raising :class:`SkipNode` in one of them will prevent any later visitor
      to run.

    Args:
        *visitors: List of visitors to run.

    Attributes:
        visitors (List[ASTVisitor]): Children visitors.
    """

    def __init__(self, *visitors: ASTVisitor):
        self.visitors = tuple(visitors)

    def enter(self, node: N) -> N:
        cur = node  # type: Optional[N]
        for v in self.visitors:
            if cur is None:
                break
            cur = v.enter(cur)

        return node

    def leave(self, node: N) -> None:
        for v in self.visitors[::-1]:
            v.leave(node)
