# -*- coding: utf-8 -*-
"""
"""

from py_gql.lang import ast as _ast
from py_gql.lang.parser import parse
from py_gql.lang.visitor import visit_document, Visitor, SkipNode


class NullVisitor(Visitor):

    def enter(self, node):
        pass

    def leave(self, node):
        pass


def test_null_visitor_does_not_crash():
    ast = parse('{ a }', no_location=True)
    visit_document(NullVisitor(), ast)


def test_null_visitor_does_not_crash_on_kitchen_sink(fixture_file):
    source = fixture_file('kitchen-sink.graphql')
    ast = parse(source, no_location=True)
    visit_document(NullVisitor(), ast)


def test_null_visitor_does_not_crash_on_kitchen_sink_schema(fixture_file):
    source = fixture_file('schema-kitchen-sink.graphql')
    ast = parse(source, no_location=True)
    visit_document(NullVisitor(), ast)


class Tracker(NullVisitor):

    def __init__(self):
        self.stack = []

    def enter(self, node):
        self.stack.append(('enter', node.__class__.__name__))

    def leave(self, node):
        self.stack.append(('leave', node.__class__.__name__))


def test_it_processes_nodes_in_the_correct_order():
    ast = parse('{ a }', no_location=True)
    visitor = Tracker()
    visit_document(visitor, ast)
    assert visitor.stack == [
        ('enter', 'Document'),
        ('enter', 'OperationDefinition'),
        ('enter', 'SelectionSet'),
        ('enter', 'Field'),
        ('leave', 'Field'),
        ('leave', 'SelectionSet'),
        ('leave', 'OperationDefinition'),
        ('leave', 'Document')
    ]


def test_it_allows_early_exit():
    """ interrupt processing by raising """
    ast = parse('{ a { b { c { d { e } } } } }', no_location=True)

    class _Visitor(Tracker):
        def enter(self, node):
            super(_Visitor, self).enter(node)
            if isinstance(node, _ast.Field) and node.name.value == 'b':
                raise SkipNode()

    visitor = _Visitor()
    visit_document(visitor, ast)

    assert visitor.stack == [
        ('enter', 'Document'),
        ('enter', 'OperationDefinition'),
        ('enter', 'SelectionSet'),
        ('enter', 'Field'),
        ('enter', 'SelectionSet'),
        ('enter', 'Field'),
        ('leave', 'SelectionSet'),
        ('leave', 'Field'),
        ('leave', 'SelectionSet'),
        ('leave', 'OperationDefinition'),
        ('leave', 'Document')
    ]
