# -*- coding: utf-8 -*-

from typing import List, Tuple

from py_gql._string_utils import dedent
from py_gql.lang import ast as _ast
from py_gql.lang.parser import parse
from py_gql.lang.printer import print_ast
from py_gql.lang.visitor import ASTVisitor, DispatchingVisitor, SkipNode


class NullVisitor(ASTVisitor):
    pass


def test_null_visitor_does_not_crash():
    ast = parse("{ a }", no_location=True)
    NullVisitor().visit(ast)


def test_null_visitor_does_not_crash_on_kitchen_sink(fixture_file):
    source = fixture_file("kitchen-sink.graphql")
    ast = parse(source, no_location=True)
    NullVisitor().visit(ast)


def test_null_visitor_does_not_crash_on_kitchen_sink_schema(fixture_file):
    source = fixture_file("schema-kitchen-sink.graphql")
    ast = parse(source, no_location=True, allow_type_system=True)
    NullVisitor().visit(ast)


class Tracker(ASTVisitor):
    def __init__(self):
        self.stack = []  # type: List[Tuple[str, str]]

    def enter(self, node):
        self.stack.append(("enter", node.__class__.__name__))
        return node

    def leave(self, node):
        self.stack.append(("leave", node.__class__.__name__))


def test_it_processes_nodes_in_the_correct_order():
    ast = parse("{ a }", no_location=True)
    visitor = Tracker()
    visitor.visit(ast)
    assert visitor.stack == [
        ("enter", "Document"),
        ("enter", "OperationDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "OperationDefinition"),
        ("leave", "Document"),
    ]


def test_it_allows_early_exit():
    """ interrupt processing by raising """
    ast = parse("{ a { b { c { d { e } } } } }", no_location=True)

    class _Visitor(Tracker):
        def enter(self, node):
            n = super(_Visitor, self).enter(node)
            if n and isinstance(n, _ast.Field) and n.name.value == "b":
                raise SkipNode()
            return n

    visitor = _Visitor()
    visitor.visit(ast)

    assert visitor.stack == [
        ("enter", "Document"),
        ("enter", "OperationDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "OperationDefinition"),
        ("leave", "Document"),
    ]


def test_it_processes_kitchen_sink(fixture_file):
    ks = fixture_file("kitchen-sink.graphql")
    visitor = Tracker()

    visitor.visit(parse(ks, no_location=True))

    assert visitor.stack == [
        ("enter", "Document"),
        ("enter", "OperationDefinition"),
        ("enter", "VariableDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "VariableDefinition"),
        ("enter", "VariableDefinition"),
        ("enter", "EnumValue"),
        ("leave", "EnumValue"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "VariableDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "Argument"),
        ("enter", "ListValue"),
        ("enter", "IntValue"),
        ("leave", "IntValue"),
        ("enter", "IntValue"),
        ("leave", "IntValue"),
        ("leave", "ListValue"),
        ("leave", "Argument"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("enter", "InlineFragment"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("enter", "Field"),
        ("enter", "Argument"),
        ("enter", "IntValue"),
        ("leave", "IntValue"),
        ("leave", "Argument"),
        ("enter", "Argument"),
        ("enter", "Variable"),
        ("leave", "Variable"),
        ("leave", "Argument"),
        ("enter", "Directive"),
        ("enter", "Argument"),
        ("enter", "Variable"),
        ("leave", "Variable"),
        ("leave", "Argument"),
        ("leave", "Directive"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("enter", "FragmentSpread"),
        ("leave", "FragmentSpread"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "InlineFragment"),
        ("enter", "InlineFragment"),
        ("enter", "Directive"),
        ("enter", "Argument"),
        ("enter", "Variable"),
        ("leave", "Variable"),
        ("leave", "Argument"),
        ("leave", "Directive"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "InlineFragment"),
        ("enter", "InlineFragment"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "InlineFragment"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "OperationDefinition"),
        ("enter", "OperationDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "Argument"),
        ("enter", "IntValue"),
        ("leave", "IntValue"),
        ("leave", "Argument"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "OperationDefinition"),
        ("enter", "OperationDefinition"),
        ("enter", "VariableDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "VariableDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "Argument"),
        ("enter", "Variable"),
        ("leave", "Variable"),
        ("leave", "Argument"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("enter", "Field"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "OperationDefinition"),
        ("enter", "FragmentDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "Argument"),
        ("enter", "Variable"),
        ("leave", "Variable"),
        ("leave", "Argument"),
        ("enter", "Argument"),
        ("enter", "Variable"),
        ("leave", "Variable"),
        ("leave", "Argument"),
        ("enter", "Argument"),
        ("enter", "ObjectValue"),
        ("enter", "ObjectField"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "ObjectField"),
        ("enter", "ObjectField"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "ObjectField"),
        ("leave", "ObjectValue"),
        ("leave", "Argument"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "FragmentDefinition"),
        ("enter", "OperationDefinition"),
        ("enter", "SelectionSet"),
        ("enter", "Field"),
        ("enter", "Argument"),
        ("enter", "BooleanValue"),
        ("leave", "BooleanValue"),
        ("leave", "Argument"),
        ("enter", "Argument"),
        ("enter", "BooleanValue"),
        ("leave", "BooleanValue"),
        ("leave", "Argument"),
        ("enter", "Argument"),
        ("enter", "NullValue"),
        ("leave", "NullValue"),
        ("leave", "Argument"),
        ("leave", "Field"),
        ("enter", "Field"),
        ("leave", "Field"),
        ("leave", "SelectionSet"),
        ("leave", "OperationDefinition"),
        ("leave", "Document"),
    ]


def test_it_processes_schema_kitchen_sink(fixture_file):
    ks = fixture_file("schema-kitchen-sink.graphql")
    visitor = Tracker()
    visitor.visit(parse(ks, no_location=True, allow_type_system=True))
    assert visitor.stack == [
        ("enter", "Document"),
        ("enter", "SchemaDefinition"),
        ("enter", "OperationTypeDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "OperationTypeDefinition"),
        ("enter", "OperationTypeDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "OperationTypeDefinition"),
        ("leave", "SchemaDefinition"),
        ("enter", "ObjectTypeDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NonNullType"),
        ("leave", "NonNullType"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "InputValueDefinition"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "ListType"),
        ("leave", "ListType"),
        ("enter", "ListValue"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "ListValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "ObjectValue"),
        ("enter", "ObjectField"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "ObjectField"),
        ("leave", "ObjectValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NullValue"),
        ("leave", "NullValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("leave", "ObjectTypeDefinition"),
        ("enter", "ObjectTypeDefinition"),
        ("enter", "Directive"),
        ("enter", "Argument"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "Argument"),
        ("leave", "Directive"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "InputValueDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "FieldDefinition"),
        ("leave", "ObjectTypeDefinition"),
        ("enter", "ObjectTypeDefinition"),
        ("leave", "ObjectTypeDefinition"),
        ("enter", "ObjectTypeExtension"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "ListType"),
        ("leave", "ListType"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("leave", "ObjectTypeExtension"),
        ("enter", "ObjectTypeExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "ObjectTypeExtension"),
        ("enter", "InterfaceTypeDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "FieldDefinition"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "StringValue"),
        ("leave", "StringValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("leave", "InterfaceTypeDefinition"),
        ("enter", "InterfaceTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "InputValueDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "FieldDefinition"),
        ("leave", "InterfaceTypeDefinition"),
        ("enter", "InterfaceTypeDefinition"),
        ("leave", "InterfaceTypeDefinition"),
        ("enter", "InterfaceTypeExtension"),
        ("enter", "FieldDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "InputValueDefinition"),
        ("enter", "NonNullType"),
        ("leave", "NonNullType"),
        ("leave", "InputValueDefinition"),
        ("leave", "FieldDefinition"),
        ("leave", "InterfaceTypeExtension"),
        ("enter", "InterfaceTypeExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "InterfaceTypeExtension"),
        ("enter", "UnionTypeDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "UnionTypeDefinition"),
        ("enter", "UnionTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "UnionTypeDefinition"),
        ("enter", "UnionTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "UnionTypeDefinition"),
        ("enter", "UnionTypeDefinition"),
        ("leave", "UnionTypeDefinition"),
        ("enter", "UnionTypeExtension"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "UnionTypeExtension"),
        ("enter", "UnionTypeExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "UnionTypeExtension"),
        ("enter", "ScalarTypeDefinition"),
        ("leave", "ScalarTypeDefinition"),
        ("enter", "ScalarTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "ScalarTypeDefinition"),
        ("enter", "ScalarTypeExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "ScalarTypeExtension"),
        ("enter", "EnumTypeDefinition"),
        ("enter", "EnumValueDefinition"),
        ("leave", "EnumValueDefinition"),
        ("enter", "EnumValueDefinition"),
        ("leave", "EnumValueDefinition"),
        ("leave", "EnumTypeDefinition"),
        ("enter", "EnumTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "EnumValueDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "EnumValueDefinition"),
        ("enter", "EnumValueDefinition"),
        ("leave", "EnumValueDefinition"),
        ("leave", "EnumTypeDefinition"),
        ("enter", "EnumTypeDefinition"),
        ("leave", "EnumTypeDefinition"),
        ("enter", "EnumTypeExtension"),
        ("enter", "EnumValueDefinition"),
        ("leave", "EnumValueDefinition"),
        ("leave", "EnumTypeExtension"),
        ("enter", "EnumTypeExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "EnumTypeExtension"),
        ("enter", "InputObjectTypeDefinition"),
        ("enter", "InputValueDefinition"),
        ("enter", "NonNullType"),
        ("leave", "NonNullType"),
        ("leave", "InputValueDefinition"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "IntValue"),
        ("leave", "IntValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "InputObjectTypeDefinition"),
        ("enter", "InputObjectTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "InputValueDefinition"),
        ("leave", "InputObjectTypeDefinition"),
        ("enter", "InputObjectTypeDefinition"),
        ("leave", "InputObjectTypeDefinition"),
        ("enter", "InputObjectTypeExtension"),
        ("enter", "InputValueDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("enter", "FloatValue"),
        ("leave", "FloatValue"),
        ("leave", "InputValueDefinition"),
        ("leave", "InputObjectTypeExtension"),
        ("enter", "InputObjectTypeExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "InputObjectTypeExtension"),
        ("enter", "DirectiveDefinition"),
        ("enter", "InputValueDefinition"),
        ("enter", "NonNullType"),
        ("leave", "NonNullType"),
        ("leave", "InputValueDefinition"),
        ("leave", "DirectiveDefinition"),
        ("enter", "DirectiveDefinition"),
        ("enter", "InputValueDefinition"),
        ("enter", "NonNullType"),
        ("leave", "NonNullType"),
        ("leave", "InputValueDefinition"),
        ("leave", "DirectiveDefinition"),
        ("enter", "DirectiveDefinition"),
        ("enter", "InputValueDefinition"),
        ("enter", "NonNullType"),
        ("leave", "NonNullType"),
        ("leave", "InputValueDefinition"),
        ("leave", "DirectiveDefinition"),
        ("enter", "SchemaExtension"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "SchemaExtension"),
        ("enter", "SchemaExtension"),
        ("enter", "OperationTypeDefinition"),
        ("enter", "NamedType"),
        ("leave", "NamedType"),
        ("leave", "OperationTypeDefinition"),
        ("enter", "Directive"),
        ("leave", "Directive"),
        ("leave", "SchemaExtension"),
        ("leave", "Document"),
    ]


def test_it_processes_github_schema_sink_without_crashing(fixture_file):
    sdl = fixture_file("github-schema.graphql")
    visitor = Tracker()
    visitor.visit(parse(sdl, no_location=True, allow_type_system=True))


# TODO: The following tests are not super exhaustive, which is in part due to
# the verbose Visitor implementation.
def test_node_removal():
    class Visitor(DispatchingVisitor):
        def enter_field(self, field):
            if field.name.value == "foo":
                return None
            return field

    visited = Visitor().visit(parse("{ foo, bar, baz }"))

    assert visited is not None

    assert print_ast(visited) == dedent(
        """
        {
          bar
          baz
        }
        """
    )


def test_node_inline_modification():
    class Visitor(DispatchingVisitor):
        def enter_field(self, field):
            if field.name.value == "foo":
                field.name.value = "Foo"
            return field

    visited = Visitor().visit(parse("{ foo, bar, baz }"))

    assert visited is not None

    assert print_ast(visited) == dedent(
        """
        {
          Foo
          bar
          baz
        }
        """
    )


def test_node_return_modification():
    class Visitor(DispatchingVisitor):
        def enter_field(self, field):
            if field.name.value == "foo":
                return _ast.Field(
                    name=_ast.Name("Foo"),
                    arguments=[
                        _ast.Argument(_ast.Name("arg"), _ast.IntValue("42"))
                    ],
                )
            return field

    visited = Visitor().visit(parse("{ foo, bar, baz }"))

    assert visited is not None

    assert print_ast(visited) == dedent(
        """
        {
          Foo(arg: 42)
          bar
          baz
        }
        """
    )
