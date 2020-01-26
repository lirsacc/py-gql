# -*- coding: utf-8 -*-

from typing import cast

from py_gql.lang import ast, parse
from py_gql.utilities import selected_fields

DOCUMENT = """
    query {
        foo {
            field
            aliased: other_field {
                nested_field {
                    deeper_nested_field
                }
            }

            ... on Bar {
                bar
            }

            ...baz_fields
        }
    }

    fragment baz_fields on Baz {
        baz {
            nested_baz_field
        }
    }
"""


def _first_field(doc: ast.Document) -> ast.Field:
    return cast(
        ast.Field,
        cast(
            ast.OperationDefinition, doc.definitions[0]
        ).selection_set.selections[0],
    )


def test_default_case():
    document = parse(DOCUMENT)
    field = _first_field(document)
    fieldnames = selected_fields(
        field, fragments=document.fragments, variables={}
    )
    assert fieldnames == [
        "field",
        "other_field",
        "bar",
        "baz",
    ]


def test_example_case():
    document = parse(
        """
        query {
            field {
                foo {
                    bar {
                        baz
                    }
                }
            }
        }
        """
    )
    field = _first_field(document)
    fieldnames = selected_fields(field, fragments={}, variables={}, maxdepth=0)
    assert fieldnames == ["foo", "foo/bar", "foo/bar/baz"]


def test_nesting():
    document = parse(DOCUMENT)
    field = _first_field(document)
    fieldnames = selected_fields(
        field, fragments=document.fragments, variables={}, maxdepth=2
    )
    assert fieldnames == [
        "field",
        "other_field",
        "other_field/nested_field",
        "bar",
        "baz",
        "baz/nested_baz_field",
    ]


def test_nesting_no_maxdepth():
    document = parse(DOCUMENT)
    field = _first_field(document)
    fieldnames = selected_fields(
        field, fragments=document.fragments, variables={}, maxdepth=0
    )
    assert fieldnames == [
        "field",
        "other_field",
        "other_field/nested_field",
        "other_field/nested_field/deeper_nested_field",
        "bar",
        "baz",
        "baz/nested_baz_field",
    ]


def test_filtering():
    document = parse(DOCUMENT)
    field = _first_field(document)
    fieldnames = selected_fields(
        field,
        fragments=document.fragments,
        variables={},
        maxdepth=3,
        pattern="other_field/*",
    )
    assert fieldnames == [
        "other_field/nested_field",
        "other_field/nested_field/deeper_nested_field",
    ]


def test_skip_and_include_directives_on_fields():
    document = parse(
        """
        query {
            foo {
                default {
                    nested
                }
                skipped @skip(if: true) {
                    nested
                }
                not_included @include(if: false) {
                    nested
                }
            }
        }
    """
    )
    field = _first_field(document)
    fieldnames = selected_fields(
        field, fragments=document.fragments, variables={}, maxdepth=3
    )
    assert fieldnames == [
        "default",
        "default/nested",
    ]
