# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import ProvidedRequiredArgumentsChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_ignores_unknown_arguments(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            dog {
                isHousetrained(unknownArgument: true)
            }
        }
        """,
    )


def test_arg_on_optional_arg(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            dog {
                isHousetrained(atOtherHomes: true)
            }
        }
        """,
    )


def test_no_arg_on_optional_arg(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            dog {
                isHousetrained
            }
        }
        """,
    )


def test_no_arg_on_non_null_field_with_default(schema_2):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema_2,
        """
        {
            complicatedArgs {
                nonNullFieldWithDefault
            }
        }
        """,
    )


def test_multiple_args(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
            multipleReqs(req1: 1, req2: 2)
            }
        }
        """,
    )


def test_multiple_args_reverse_order(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleReqs(req2: 2, req1: 1)
            }
        }
        """,
    )


def test_no_args_on_multiple_optional(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleOpts
            }
        }
        """,
    )


def test_one_arg_on_multiple_optional(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleOpts(opt1: 1)
            }
        }
        """,
    )


def test_second_arg_on_multiple_optional(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleOpts(opt2: 1)
            }
        }
        """,
    )


def test_multiple_reqs_on_mixed_list(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleOptAndReq(req1: 3, req2: 4)
            }
        }
        """,
    )


def test_multiple_reqs_and_one_opt_on_mixed_list(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleOptAndReq(req1: 3, req2: 4, opt1: 5)
            }
        }
        """,
    )


def test_all_reqs_and_opts_on_mixed_list(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleOptAndReq(req1: 3, req2: 4, opt1: 5, opt2: 6)
            }
        }
        """,
    )


def test_missing_one_non_nullable_argument(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
                multipleReqs(req2: 2)
            }
        }
        """,
        [
            'Field "multipleReqs" argument "req1" of type Int! is required '
            "but not provided"
        ],
        [[(32, 53)]],
    )


def test_missing_multiple_non_nullable_arguments(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
            multipleReqs
            }
        }
        """,
        [
            'Field "multipleReqs" argument "req1" of type Int! is required '
            "but not provided",
            'Field "multipleReqs" argument "req2" of type Int! is required '
            "but not provided",
        ],
    )


def test_incorrect_value_and_missing_argument(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            complicatedArgs {
            multipleReqs(req1: "one")
            }
        }
        """,
        [
            'Field "multipleReqs" argument "req2" of type Int! is required '
            "but not provided"
        ],
    )


def test_it_ignores_unknown_directives(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            dog @unknown
        }
        """,
    )


def test_directives_of_valid_types(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
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


def test_directive_with_missing_types(schema):
    run_test(
        ProvidedRequiredArgumentsChecker,
        schema,
        """
        {
            dog @include {
                name @skip
            }
        }
        """,
        [
            'Directive "@include" argument "if" of type Boolean! is required '
            "but not provided",
            'Directive "@skip" argument "if" of type Boolean! is required '
            "but not provided",
        ],
    )
