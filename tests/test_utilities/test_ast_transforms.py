# -*- coding: utf-8 -*-

from py_gql._string_utils import dedent
from py_gql.lang import parse, print_ast
from py_gql.utilities import ast_transforms


def test_RemoveFieldAliasesVisitor():
    query = parse(
        """
        {
            foo: bar {
                foo_one: one
                ... on Object {
                    foo_two: two
                }
                ... A
            }
        }

        fragment A on Object {
            foo_three: three
        }
        """
    )

    visited_query = ast_transforms.RemoveFieldAliasesVisitor().visit(
        query.deepcopy()
    )

    assert visited_query

    assert print_ast(visited_query, indent=4) == dedent(
        """
        {
            bar {
                one
                ... on Object {
                    two
                }
                ...A
            }
        }

        fragment A on Object {
            three
        }
        """
    )


def test_CamelCaseToSnakeCaseVisitor():
    query = parse(
        """
        {
            fooBar {
                barFoo
                ... on Object {
                    bazFoo
                }
            }
        }

        fragment A on Object {
            fooBaz
        }
        """
    )

    visited_query = ast_transforms.CamelCaseToSnakeCaseVisitor().visit(
        query.deepcopy()
    )

    assert visited_query

    assert print_ast(visited_query, indent=4) == dedent(
        """
        {
            foo_bar {
                bar_foo
                ... on Object {
                    baz_foo
                }
            }
        }

        fragment A on Object {
            foo_baz
        }
        """
    )


def test_SnakeCaseToCamelCaseVisitor():
    query = parse(
        """
        {
            foo_bar {
                bar_foo
                ... on Object {
                    baz_foo
                }
            }
        }

        fragment A on Object {
            foo_baz
        }
        """
    )

    visited_query = ast_transforms.SnakeCaseToCamelCaseVisitor().visit(
        query.deepcopy()
    )

    assert visited_query

    assert print_ast(visited_query, indent=4) == dedent(
        """
        {
            fooBar {
                barFoo
                ... on Object {
                    bazFoo
                }
            }
        }

        fragment A on Object {
            fooBaz
        }
        """
    )
