# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

import pytest

from py_gql.validation.rules import ValuesOfCorrectTypeChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_good_int_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           intArgField(intArg: 2)
        }
    }
    """,
    )


def test_good_negative_int_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           intArgField(intArg: -2)
        }
    }
    """,
    )


def test_good_boolean_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           booleanArgField(booleanArg: true)
        }
    }
    """,
    )


def test_good_string_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           stringArgField(stringArg: "foo")
        }
    }
    """,
    )


def test_good_float_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           floatArgField(floatArg: 1.1)
        }
    }
    """,
    )


def test_good_negative_float_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           floatArgField(floatArg: -1.1)
        }
    }
    """,
    )


def test_int_into_float(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           floatArgField(floatArg: 1)
        }
    }
    """,
    )


def test_int_into_id(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           idArgField(idArg: 1)
        }
    }
    """,
    )


def test_string_into_id(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           idArgField(idArg: "someIdString")
        }
    }
    """,
    )


def test_good_enum_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        dog {
            doesKnowCommand(dogCommand: SIT)
        }
    }
    """,
    )


def test_enum_with_undefined_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           enumArgField(enumArg: UNKNOWN)
        }
    }
    """,
    )


def test_enum_with_null_value(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           enumArgField(enumArg: NO_FUR)
        }
    }
    """,
    )


def test_null_into_nullable_type_1(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           intArgField(intArg: null)
        }
    }
    """,
    )


def test_null_into_nullable_type_2(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
     {
        dog(a: null, b: null, c:{ requiredField: true, intField: null }) {
           name
        }
    }
    """,
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            "1", "Expected type String, found 1", (70, 71), id="int -> string"
        ),
        pytest.param(
            "1.0",
            "Expected type String, found 1.0",
            (70, 73),
            id="float -> string",
        ),
        pytest.param(
            "true",
            "Expected type String, found true",
            (70, 74),
            id="bool -> string",
        ),
        pytest.param(
            "BAR",
            "Expected type String, found BAR",
            (70, 73),
            id="enum -> string",
        ),
    ],
)
def test_invalid_string_values(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           stringArgField(stringArg: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            '"3"', 'Expected type Int, found "3"', (64, 67), id="string -> int"
        ),
        pytest.param(
            "829384293849283498239482938",
            "Expected type Int, found 829384293849283498239482938",
            (64, 91),
            id="big int -> int",
        ),
        pytest.param(
            "FOO", "Expected type Int, found FOO", (64, 67), id="enum -> int"
        ),
        pytest.param(
            "3.0", "Expected type Int, found 3.0", (64, 67), id="float -> int"
        ),
        pytest.param(
            "true", "Expected type Int, found true", (64, 68), id="bool -> int"
        ),
        pytest.param(
            "3.333",
            "Expected type Int, found 3.333",
            (64, 69),
            id="float -> int",
        ),
    ],
)
def test_invalid_int_values(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           intArgField(intArg: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            '"3"',
            'Expected type Float, found "3"',
            (68, 71),
            id="string -> float",
        ),
        pytest.param(
            '"3.333"',
            'Expected type Float, found "3.333"',
            (68, 75),
            id="string -> float",
        ),
        pytest.param(
            "true",
            "Expected type Float, found true",
            (68, 72),
            id="bool -> float",
        ),
        pytest.param(
            "FOO",
            "Expected type Float, found FOO",
            (68, 71),
            id="enum -> float",
        ),
    ],
)
def test_invalid_float_values(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           floatArgField(floatArg: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            "2", "Expected type Boolean, found 2", (72, 73), id="int -> boolean"
        ),
        pytest.param(
            "1.0",
            "Expected type Boolean, found 1.0",
            (72, 75),
            id="float -> boolean",
        ),
        pytest.param(
            '"true"',
            'Expected type Boolean, found "true"',
            (72, 78),
            id="string -> boolean",
        ),
        pytest.param(
            "TRUE",
            "Expected type Boolean, found TRUE",
            (72, 76),
            id="enum -> boolean",
        ),
    ],
)
def test_invalid_boolean_values(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           booleanArgField(booleanArg: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            "1.0", "Expected type ID, found 1.0", (62, 65), id="float -> ID"
        ),
        pytest.param(
            "true", "Expected type ID, found true", (62, 66), id="boolean -> ID"
        ),
        pytest.param(
            "SOMETHING",
            "Expected type ID, found SOMETHING",
            (62, 71),
            id="enum -> ID",
        ),
    ],
)
def test_invalid_id_values(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           idArgField(idArg: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            "1", "Expected type DogCommand, found 1", (61, 62), id="int -> enum"
        ),
        pytest.param(
            "1.0",
            "Expected type DogCommand, found 1.0",
            (61, 64),
            id="float -> enum",
        ),
        pytest.param(
            '"SIT"',
            'Expected type DogCommand, found "SIT"',
            (61, 66),
            id="string -> enum",
        ),
        pytest.param(
            "true",
            "Expected type DogCommand, found true",
            (61, 65),
            id="boolean -> enum",
        ),
        pytest.param(
            "JUGGLE",
            "Expected type DogCommand, found JUGGLE",
            (61, 67),
            id="unknown enum -> enum",
        ),
        pytest.param(
            "sit",
            "Expected type DogCommand, found sit",
            (61, 64),
            id="unknown enum (case) -> enum",
        ),
    ],
)
def test_invalid_enum_values(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        dog {
            doesKnowCommand(dogCommand: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param('["one", null, "two"]', id="good"),
        pytest.param("[]", id="empty"),
        pytest.param("null", id="null"),
        pytest.param('["one"]', id="single value into list"),
    ],
)
def test_valid_list_value(schema, value):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           stringListArgField(stringListArg: %s)
        }
    }
    """
        % value,
    )


@pytest.mark.parametrize(
    "value,expected_err,loc",
    [
        pytest.param(
            '["one", 2]',
            "Expected type String, found 2",
            (86, 87),
            id="incorrect item type",
        ),
        pytest.param(
            "1",
            "Expected type [String], found 1",
            (78, 79),
            id="single value of incorrect type",
        ),
    ],
)
def test_invalid_list_value(schema, value, expected_err, loc):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        complicatedArgs {
           stringListArgField(stringListArg: %s)
        }
    }
    """
        % value,
        [expected_err],
        [loc],
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            """
        {
            dog {
            isHousetrained(atOtherHomes: true)
            }
        }
        """,
            id="Arg On Optional Arg",
        ),
        pytest.param(
            """
        {
            dog {
            isHousetrained
            }
        }
        """,
            id="No Arg On Optional Arg",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
                multipleReqs(req1: 1, req2: 2)
            }
        }
        """,
            id="Multiple Args",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
            multipleReqs(req2: 2, req1: 1)
            }
        }
        """,
            id="Multiple Args Reverse Order",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
            multipleOpts
            }
        }
        """,
            id="No Args On Multiple Optional",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
            multipleOpts(opt1: 1)
            }
        }
        """,
            id="One Arg On Multiple Optional",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
                multipleOpts(opt2: 1)
            }
        }
        """,
            id="Second Arg On Multiple Optional",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
            multipleOptAndReq(req1: 3, req2: 4)
            }
        }
        """,
            id="Multiple Reqs On Mixed List",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
            multipleOptAndReq(req1: 3, req2: 4, opt1: 5)
            }
        }
        """,
            id="Multiple Reqs And One Opt On Mixed List",
        ),
        pytest.param(
            """
        {
            complicatedArgs {
                multipleOptAndReq(req1: 3, req2: 4, opt1: 5, opt2: 6)
            }
        }
        """,
            id="All Reqs And Opts On Mixed List",
        ),
    ],
)
def test_valid_non_nullable_value(schema, value):
    run_test(ValuesOfCorrectTypeChecker, schema, value)


@pytest.mark.parametrize(
    "value,expected_errors,locs",
    [
        pytest.param(
            """
        {
          complicatedArgs {
            multipleReqs(req2: "two", req1: "one")
          }
        }
        """,
            [
                'Expected type Int!, found "two"',
                'Expected type Int!, found "one"',
            ],
            [(70, 75), (83, 88)],
            id="Incorrect value type",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            multipleReqs(req1: "one")
          }
        }
        """,
            ['Expected type Int!, found "one"'],
            [(70, 75)],
            id="Incorrect value and missing argument (ProvidedNonNullArguments)",
        ),
        pytest.param(
            """
         {
          complicatedArgs {
            multipleReqs(req1: null)
          }
        }
        """,
            ["Expected type Int!, found null"],
            [(71, 75)],
            id="Null value",
        ),
    ],
)
def test_invalid_non_nullable_value(schema, value, expected_errors, locs):
    run_test(ValuesOfCorrectTypeChecker, schema, value, expected_errors, locs)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField
          }
        }
        """,
            id="Optional arg, despite required field in type",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: { requiredField: true })
          }
        }
        """,
            id="Partial object, only required",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: { requiredField: false })
          }
        }
        """,
            id="Partial object, required field can be falsey",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: { requiredField: true, intField: 4 })
          }
        }
        """,
            id="Partial object, including required",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: {
              requiredField: true,
              intField: 4,
              stringField: "foo",
              booleanField: false,
              stringListField: ["one", "two"]
            })
          }
        }
        """,
            id="Full object",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: {
              stringListField: ["one", "two"],
              booleanField: false,
              requiredField: true,
              stringField: "foo",
              intField: 4,
            })
          }
        }
        """,
            id="Full object with fields in different order",
        ),
        pytest.param(
            """
        {
          test1: anyArg(arg: 123)
          test2: anyArg(arg: "abc")
          test3: anyArg(arg: [123, "abc"])
          test4: anyArg(arg: {deep: [123, "abc"]})
        }
        """,
            id="allows custom scalar to accept complex literals",
        ),
    ],
)
def test_valid_input_object_value(schema, value):
    run_test(ValuesOfCorrectTypeChecker, schema, value)


@pytest.mark.parametrize(
    "value, expected_errors, locs",
    [
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: { intField: 4 })
          }
        }
        """,
            [
                "Required field ComplexInput.requiredField of type Boolean! was "
                "not provided"
            ],
            [(79, 94)],
            id="Partial object, missing required",
        ),
        pytest.param(
            """
            {
                complicatedArgs {
                    complexArgField(complexArg: {
                        requiredField: true,
                        nonNullField: null,
                    })
                }
            }
            """,
            ["Expected type Boolean!, found null"],
            [(182, 186)],
            id="Partial object, null to non-null field",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: {
              stringListField: ["one", 2],
              requiredField: true,
            })
          }
        }
        """,
            ["Expected type String, found 2"],
            [(120, 121)],
            id="Partial object, invalid field type",
        ),
        pytest.param(
            """
        {
          complicatedArgs {
            complexArgField(complexArg: {
              requiredField: true,
              unknownField: "value"
            })
          }
        }
        """,
            ["Field unknownField is not defined by type ComplexInput"],
            [(130, 151)],
            id="Partial object, unknown field arg",
        ),
        pytest.param(
            """
        {
          invalidArg(arg: 123)
        }
        """,
            [
                "Expected type Invalid, found 123 (Invalid scalar is always invalid)"
            ],
            [(37, 40)],
            id="reports original error for custom scalar which throws",
        ),
    ],
)
def test_invalid_input_object_value(schema, value, expected_errors, locs):
    run_test(ValuesOfCorrectTypeChecker, schema, value, expected_errors, locs)


def test_directive_arguments_with_directives_of_valid_types(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    {
        dog @include(if: true) {
        name
        }
        human @skip(if: false) {
        name
        }
    }
    """,
    )


def test_directive_arguments_with_directive_with_incorrect_types(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
     {
        dog @include(if: "yes") {
           name @skip(if: ENUM)
        }
    }
    """,
        [
            'Expected type Boolean!, found "yes"',
            "Expected type Boolean!, found ENUM",
        ],
        [(33, 38), (68, 72)],
    )


def test_variables_with_valid_default_values(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    query WithDefaultValues(
        $a: Int = 1,
        $b: String = "ok",
        $c: ComplexInput = { requiredField: true, intField: 3 }
        $d: Int! = 123
    ) {
        dog { name }
    }
    """,
    )


def test_variables_with_valid_default_null_values(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    query WithDefaultValues(
        $a: Int = null,
        $b: String = null,
        $c: ComplexInput = { requiredField: true, intField: null }
    ) {
        dog { name }
    }
    """,
    )


def test_variables_with_invalid_default_null_values(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
    query WithDefaultValues(
        $a: Int! = null,
        $b: String! = null,
        $c: ComplexInput = { requiredField: null, intField: null }
    ) {
        dog { name }
    }
    """,
        [
            "Expected type Int!, found null",
            "Expected type String!, found null",
            "Expected type Boolean!, found null",
        ],
        [(49, 53), (77, 81), (127, 131)],
    )


def test_variables_with_invalid_default_values(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
        query InvalidDefaultValues(
            $a: Int = "one",
            $b: String = 4,
            $c: ComplexInput = "notverycomplex"
        ) {
            dog { name }
        }
        """,
        [
            'Expected type Int, found "one"',
            "Expected type String, found 4",
            'Expected type ComplexInput, found "notverycomplex"',
        ],
    )


def test_variables_with_complex_invalid_default_values(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
        query WithDefaultValues(
            $a: ComplexInput = { requiredField: 123, intField: "abc" }
        ) {
            dog { name }
        }
        """,
        ["Expected type Boolean!, found 123", 'Expected type Int, found "abc"'],
    )


def test_complex_variables_missing_required_field(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
        query MissingRequiredField($a: ComplexInput = {intField: 3}) {
            dog { name }
        }
        """,
        [
            "Required field ComplexInput.requiredField of type Boolean! "
            "was not provided"
        ],
    )


def test_list_variables_with_invalid_item(schema):
    run_test(
        ValuesOfCorrectTypeChecker,
        schema,
        """
        query InvalidItem($a: [String] = ["one", 2]) {
            dog { name }
        }
        """,
        ["Expected type String, found 2"],
    )
