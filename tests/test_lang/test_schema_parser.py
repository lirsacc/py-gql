# -*- coding: utf-8 -*-

# Test naming is not very 'pythonic' as I tried to keep a close match with the
# original ones for easy reference. Others were kept while they were specific
# to the implementation and are kept as skipped.


import pytest

from py_gql.exc import UnexpectedEOF, UnexpectedToken
from py_gql.lang import ast as _ast
from py_gql.lang.parser import parse


# Comparing dicts will result in better assertion diffs from pytest.
def assert_node_equal(ref, expected):
    # import json
    # print(json.dumps(_ast._ast_to_json(ref), sort_keys=True, indent=4))
    # print(json.dumps(_ast._ast_to_json(expected), sort_keys=True, indent=4))
    assert _ast._ast_to_json(expected) == _ast._ast_to_json(ref)


# A few syntactic sugar helpers
def _name(loc, value):
    return _ast.Name(loc=loc, value=value)


def _type(loc, value):
    return _ast.NamedType(loc=loc, name=_ast.Name(loc=loc, value=value))


def _field(loc, name, type_, args=None):
    return _ast.FieldDefinition(
        loc=loc, name=name, type=type_, arguments=args or [], directives=[]
    )


def _input(loc, name, type_, default_value=None):
    return _ast.InputValueDefinition(
        loc=loc,
        name=name,
        type=type_,
        default_value=default_value,
        directives=[],
    )


def _doc(loc, defs):
    return _ast.Document(loc=loc, definitions=defs)


def test_it_parses_simple_type():
    body = """
type Hello {
  world: String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _ast.Document(
            loc=(0, 31),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(1, 31),
                    name=_name((6, 11), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (16, 29),
                            _name((16, 21), "world"),
                            _type((23, 29), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_type_with_description_string():
    assert_node_equal(
        parse(
            """
"Description"
type Hello {
  world: String
}""",
            allow_type_system=True,
        ),
        _ast.Document(
            loc=(0, 45),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(1, 45),
                    name=_name((20, 25), "Hello"),
                    interfaces=[],
                    directives=[],
                    description=_ast.StringValue(
                        loc=(1, 14), value="Description"
                    ),
                    fields=[
                        _field(
                            (30, 43),
                            _name((30, 35), "world"),
                            _type((37, 43), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_type_with_description_multi_line_string():
    body = '''
"""
Description
"""
# Even with comments between them
type Hello {
  world: String
}'''

    assert_node_equal(
        parse(body, allow_type_system=True),
        _ast.Document(
            loc=(0, 85),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(1, 85),
                    name=_name((60, 65), "Hello"),
                    interfaces=[],
                    directives=[],
                    description=_ast.StringValue(
                        loc=(1, 20), value="Description", block=True
                    ),
                    fields=[
                        _field(
                            (70, 83),
                            _name((70, 75), "world"),
                            _type((77, 83), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_extension():
    body = """
extend type Hello {
  world: String
}
"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 39),
            [
                _ast.ObjectTypeExtension(
                    loc=(1, 38),
                    name=_name((13, 18), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (23, 36),
                            _name((23, 28), "world"),
                            _type((30, 36), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_extension_without_fields():
    assert_node_equal(
        parse("extend type Hello implements Greeting", allow_type_system=True),
        _doc(
            (0, 37),
            [
                _ast.ObjectTypeExtension(
                    loc=(0, 37),
                    name=_name((12, 17), "Hello"),
                    interfaces=[_type((29, 37), "Greeting")],
                    fields=[],
                    directives=[],
                )
            ],
        ),
    )


def test_it_parses_extension_without_fields_followed_by_extension():
    assert_node_equal(
        parse(
            """
      extend type Hello implements Greeting

      extend type Hello implements SecondGreeting
    """,
            allow_type_system=True,
        ),
        _ast.Document(
            loc=(0, 100),
            definitions=[
                _ast.ObjectTypeExtension(
                    loc=(7, 44),
                    name=_name((19, 24), "Hello"),
                    interfaces=[_type((36, 44), "Greeting")],
                    fields=[],
                    directives=[],
                ),
                _ast.ObjectTypeExtension(
                    loc=(52, 95),
                    name=_name((64, 69), "Hello"),
                    interfaces=[_type((81, 95), "SecondGreeting")],
                    fields=[],
                    directives=[],
                ),
            ],
        ),
    )


def test_extension_without_anything_throws():
    with pytest.raises(UnexpectedEOF) as exc_info:
        parse("extend type Hello", allow_type_system=True)
    assert exc_info.value.position == 17
    assert exc_info.value.message == "Unexpected <EOF>"


def test_extension_do_not_include_descriptions_0():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(
            """
      "Description"
      extend type Hello {
        world: String
      }""",
            allow_type_system=True,
        )
    assert exc_info.value.position == 27
    assert exc_info.value.message == 'Unexpected "extend"'


def test_extension_do_not_include_descriptions_1():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(
            """
      extend "Description" type Hello {
        world: String
      }""",
            allow_type_system=True,
        )
    assert exc_info.value.position == 14
    assert exc_info.value.message == 'Unexpected "Description"'


def test_it_parses_simple_non_null_type():
    body = """
type Hello {
  world: String!
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _ast.Document(
            loc=(0, 32),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(1, 32),
                    name=_name((6, 11), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (16, 30),
                            _name((16, 21), "world"),
                            _ast.NonNullType(
                                loc=(23, 30), type=_type((23, 29), "String")
                            ),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_type_inheriting_interface():
    body = "type Hello implements World { field: String }"
    assert_node_equal(
        parse(body, allow_type_system=True),
        _ast.Document(
            loc=(0, 45),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(0, 45),
                    name=_name((5, 10), "Hello"),
                    interfaces=[_type((22, 27), "World")],
                    directives=[],
                    fields=[
                        _field(
                            (30, 43),
                            _name((30, 35), "field"),
                            _type((37, 43), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_type_inheriting_multiple_interfaces():
    body = "type Hello implements Wo & rld { field: String }"
    assert_node_equal(
        parse(body, allow_type_system=True),
        _ast.Document(
            loc=(0, 48),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(0, 48),
                    name=_name((5, 10), "Hello"),
                    interfaces=[_type((22, 24), "Wo"), _type((27, 30), "rld")],
                    directives=[],
                    fields=[
                        _field(
                            (33, 46),
                            _name((33, 38), "field"),
                            _type((40, 46), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_type_inheriting_multiple_interfaces_with_leading_ampersand():  # noqa: E501
    body = "type Hello implements & Wo & rld { field: String }"
    assert_node_equal(
        parse(body, allow_type_system=True),
        _ast.Document(
            loc=(0, 50),
            definitions=[
                _ast.ObjectTypeDefinition(
                    loc=(0, 50),
                    name=_name((5, 10), "Hello"),
                    interfaces=[_type((24, 26), "Wo"), _type((29, 32), "rld")],
                    directives=[],
                    fields=[
                        _field(
                            (35, 48),
                            _name((35, 40), "field"),
                            _type((42, 48), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_single_value_enum():
    body = "enum Hello { WORLD }"
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 20),
            [
                _ast.EnumTypeDefinition(
                    loc=(0, 20),
                    name=_name((5, 10), "Hello"),
                    directives=[],
                    values=[
                        _ast.EnumValueDefinition(
                            loc=(13, 18), name=_name((13, 18), "WORLD")
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_double_value_enum():
    body = "enum Hello { WO, RLD }"
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 22),
            [
                _ast.EnumTypeDefinition(
                    loc=(0, 22),
                    name=_name((5, 10), "Hello"),
                    directives=[],
                    values=[
                        _ast.EnumValueDefinition(
                            loc=(13, 15), name=_name((13, 15), "WO")
                        ),
                        _ast.EnumValueDefinition(
                            loc=(17, 20), name=_name((17, 20), "RLD")
                        ),
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_interface():
    body = """
interface Hello {
  world: String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 36),
            [
                _ast.InterfaceTypeDefinition(
                    loc=(1, 36),
                    name=_name((11, 16), "Hello"),
                    directives=[],
                    fields=[
                        _field(
                            (21, 34),
                            _name((21, 26), "world"),
                            _type((28, 34), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_field_with_arg():
    body = """
type Hello {
  world(flag: Boolean): String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 46),
            [
                _ast.ObjectTypeDefinition(
                    loc=(1, 46),
                    name=_name((6, 11), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (16, 44),
                            _name((16, 21), "world"),
                            _type((38, 44), "String"),
                            [
                                _input(
                                    (22, 35),
                                    _name((22, 26), "flag"),
                                    _type((28, 35), "Boolean"),
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_field_with_arg_with_default_value():
    body = """
type Hello {
  world(flag: Boolean = true): String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 53),
            [
                _ast.ObjectTypeDefinition(
                    loc=(1, 53),
                    name=_name((6, 11), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (16, 51),
                            _name((16, 21), "world"),
                            _type((45, 51), "String"),
                            [
                                _input(
                                    (22, 42),
                                    _name((22, 26), "flag"),
                                    _type((28, 35), "Boolean"),
                                    _ast.BooleanValue(loc=(38, 42), value=True),
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_field_with_list_arg():
    body = """
type Hello {
  world(things: [String]): String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 49),
            [
                _ast.ObjectTypeDefinition(
                    loc=(1, 49),
                    name=_name((6, 11), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (16, 47),
                            _name((16, 21), "world"),
                            _type((41, 47), "String"),
                            [
                                _input(
                                    (22, 38),
                                    _name((22, 28), "things"),
                                    _ast.ListType(
                                        loc=(30, 38),
                                        type=_type((31, 37), "String"),
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_field_with_two_args():
    body = """
type Hello {
  world(argOne: Boolean, argTwo: Int): String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 61),
            [
                _ast.ObjectTypeDefinition(
                    loc=(1, 61),
                    name=_name((6, 11), "Hello"),
                    interfaces=[],
                    directives=[],
                    fields=[
                        _field(
                            (16, 59),
                            _name((16, 21), "world"),
                            _type((53, 59), "String"),
                            [
                                _input(
                                    (22, 37),
                                    _name((22, 28), "argOne"),
                                    _type((30, 37), "Boolean"),
                                ),
                                _input(
                                    (39, 50),
                                    _name((39, 45), "argTwo"),
                                    _type((47, 50), "Int"),
                                ),
                            ],
                        )
                    ],
                )
            ],
        ),
    )


def test_it_parses_simple_union():
    assert_node_equal(
        parse("union Hello = World", allow_type_system=True),
        _doc(
            (0, 19),
            [
                _ast.UnionTypeDefinition(
                    loc=(0, 19),
                    name=_name((6, 11), "Hello"),
                    directives=[],
                    types=[_type((14, 19), "World")],
                )
            ],
        ),
    )


def test_it_parses_union_with_two_types():
    assert_node_equal(
        parse("union Hello = Wo | Rld", allow_type_system=True),
        _doc(
            (0, 22),
            [
                _ast.UnionTypeDefinition(
                    loc=(0, 22),
                    name=_name((6, 11), "Hello"),
                    directives=[],
                    types=[_type((14, 16), "Wo"), _type((19, 22), "Rld")],
                )
            ],
        ),
    )


def test_it_parses_union_with_two_types_and_leading_pipe():
    assert_node_equal(
        parse("union Hello = | Wo | Rld", allow_type_system=True),
        _doc(
            (0, 24),
            [
                _ast.UnionTypeDefinition(
                    loc=(0, 24),
                    name=_name((6, 11), "Hello"),
                    directives=[],
                    types=[_type((16, 18), "Wo"), _type((21, 24), "Rld")],
                )
            ],
        ),
    )


def test_union_fails_with_no_types():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("union Hello = |", allow_type_system=True)
    assert exc_info.value.position == 15
    assert exc_info.value.message == 'Expected Name but found "<EOF>"'


def test_union_fails_with_leading_douple_pipe():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("union Hello = || Wo | Rld", allow_type_system=True)
    assert exc_info.value.position == 15
    assert exc_info.value.message == 'Expected Name but found "|"'


def test_union_fails_with_double_pipe():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("union Hello = Wo || Rld", allow_type_system=True)
    assert exc_info.value.position == 18
    assert exc_info.value.message == 'Expected Name but found "|"'


def test_union_fails_with_trailing_pipe():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("union Hello = | Wo | Rld |", allow_type_system=True)
    assert exc_info.value.position == 26
    assert exc_info.value.message == 'Expected Name but found "<EOF>"'


def test_it_parses_scalar():
    assert_node_equal(
        parse("scalar Hello", allow_type_system=True),
        _doc(
            (0, 12),
            [
                _ast.ScalarTypeDefinition(
                    loc=(0, 12), name=_name((7, 12), "Hello"), directives=[]
                )
            ],
        ),
    )


def test_it_parses_simple_input_object():
    body = """
input Hello {
  world: String
}"""
    assert_node_equal(
        parse(body, allow_type_system=True),
        _doc(
            (0, 32),
            [
                _ast.InputObjectTypeDefinition(
                    loc=(1, 32),
                    name=_name((7, 12), "Hello"),
                    directives=[],
                    fields=[
                        _input(
                            (17, 30),
                            _name((17, 22), "world"),
                            _type((24, 30), "String"),
                        )
                    ],
                )
            ],
        ),
    )


def test_simple_input_object_with_args_should_fail():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(
            """
      input Hello {
        world(foo: Int): String
      }""",
            allow_type_system=True,
        )

    assert exc_info.value.position == 34
    assert exc_info.value.message == 'Expected Colon but found "("'


def test_directive_with_incorrect_locations_fails():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(
            """
      directive @foo on FIELD | INCORRECT_LOCATION""",
            allow_type_system=True,
        )

    assert exc_info.value.position == 33
    assert exc_info.value.message == "Unexpected Name INCORRECT_LOCATION"


def test_it_parses_kitchen_sink(fixture_file):
    # assert doesn't raise
    assert parse(
        fixture_file("schema-kitchen-sink.graphql"),
        no_location=True,
        allow_type_system=True,
    )


def test_it_parses_github_schema(fixture_file):
    # assert doesn't raise
    assert parse(
        fixture_file("github-schema.graphql"),
        no_location=True,
        allow_type_system=True,
    )


def test_it_does_not_parses_kitchen_sink_when_allow_type_system_is_false(
    fixture_file,
):
    with pytest.raises(UnexpectedToken):
        parse(
            fixture_file("schema-kitchen-sink.graphql"),
            no_location=True,
            allow_type_system=False,
        )
