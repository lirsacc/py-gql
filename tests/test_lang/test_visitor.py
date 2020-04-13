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
    ast = parse("{ a { b { c { d { e } } } } }", no_location=True)

    class _Visitor(Tracker):
        def enter(self, node):
            n = super(_Visitor, self).enter(node)
            if n and isinstance(n, _ast.Field) and n.name.value == "b":
                # Interrupt processing by raising.
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


def test_it_processes_schema_kitchen_sink(fixture_file):
    ks = fixture_file("schema-kitchen-sink.graphql")
    visitor = Tracker()
    visitor.visit(parse(ks, no_location=True, allow_type_system=True))


def test_it_processes_github_schema_sink_without_crashing(fixture_file):
    sdl = fixture_file("github-schema.graphql")
    visitor = Tracker()
    visitor.visit(parse(sdl, no_location=True, allow_type_system=True))


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
