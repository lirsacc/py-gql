# -*- coding: utf-8 -*-

import pytest

from py_gql import build_schema, graphql_blocking
from py_gql._string_utils import dedent
from py_gql.schema import Schema
from py_gql.schema.transforms import CamelCaseSchemaTransform, transform_schema


@pytest.fixture
def schema() -> Schema:
    return build_schema(
        """
        directive @foo(arg_one: Int!, arg_two: InputObject) on FIELD

        input InputObject {
            field_one: Int!
            field_two: String
        }

        type Query {
            snake_case_field: Int,
            field_with_arguments(arg_one: Int!, arg_two: InputObject): String,
        }
        """
    )


def test_it_renames_relevant_schema_elements(schema: Schema) -> None:
    new_schema = transform_schema(schema, CamelCaseSchemaTransform())
    assert new_schema.to_string() == dedent(
        """
        directive @foo(argOne: Int!, argTwo: InputObject) on FIELD

        input InputObject {
            fieldOne: Int!
            fieldTwo: String
        }

        type Query {
            snakeCaseField: Int
            fieldWithArguments(argOne: Int!, argTwo: InputObject): String
        }
        """
    )


def test_default_resolver_still_works(schema: Schema) -> None:
    new_schema = transform_schema(schema, CamelCaseSchemaTransform())
    result = graphql_blocking(
        new_schema, "{ snakeCaseField }", root={"snake_case_field": 42}
    )
    assert result and result.response()["data"] == {"snakeCaseField": 42}


def test_custom_resolver_still_works(schema: Schema) -> None:
    schema.register_resolver("Query", "snake_case_field", lambda *_: 42)
    new_schema = transform_schema(schema, CamelCaseSchemaTransform())
    result = graphql_blocking(new_schema, "{ snakeCaseField }", root={})
    assert result and result.response()["data"] == {"snakeCaseField": 42}


def test_arguments_and_input_fields_are_handled_correctly(
    schema: Schema,
) -> None:
    def resolver(_root, _ctx, _info, *, arg_one, arg_two):
        return arg_one + arg_two["field_one"]

    schema.register_resolver("Query", "field_with_arguments", resolver)
    new_schema = transform_schema(schema, CamelCaseSchemaTransform())

    result = graphql_blocking(
        new_schema,
        "{ fieldWithArguments(argOne: 42, argTwo: { fieldOne: 42 }) }",
        root={},
    )

    assert result and result.response()["data"] == {"fieldWithArguments": "84"}
