# -*- coding: utf-8 -*-

from py_gql._string_utils import dedent
from py_gql.lang import parse, print_ast
from py_gql.utilities.ast_transforms import RemoveFieldAliasesVisitor


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

    visited_query = RemoveFieldAliasesVisitor().visit(query.deepcopy())

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
