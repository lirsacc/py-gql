# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

from py_gql.validation.rules import KnownArgumentNamesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_single_arg_is_known(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment argOnRequiredArg on Dog {
            doesKnowCommand(dogCommand: SIT)
        }
        """,
    )


def test_multiple_args_are_known(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment multipleArgs on ComplicatedArgs {
            multipleReqs(req1: 1, req2: 2)
        }
        """,
    )


def test_ignores_args_of_unknown_fields(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment argOnUnknownField on Dog {
            unknownField(unknownArg: SIT)
        }
        """,
    )


def test_multiple_args_in_reverse_order_are_known(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment multipleArgsReverseOrder on ComplicatedArgs {
        multipleReqs(req2: 2, req1: 1)
        }
        """,
    )


def test_no_args_on_optional_arg(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment noArgOnOptionalArg on Dog {
            isHousetrained
        }
        """,
    )


def test_args_are_known_deeply(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        {
            dog {
                doesKnowCommand(dogCommand: SIT)
            }
            human {
                pet {
                    ... on Dog {
                        doesKnowCommand(dogCommand: SIT)
                    }
                }
            }
        }
        """,
    )


def test_directive_args_are_known(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        {
            dog @skip(if: true)
        }
        """,
    )


def test_unknown_directive_args_are_invalid(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        {
            dog @skip(unless: true)
        }
        """,
        ['Unknown argument "unless" on directive "@skip".'],
        [(16, 28)],
    )


def test_misspelled_directive_args_are_reported(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        {
            dog @skip(iff: true)
        }
        """,
        ['Unknown argument "iff" on directive "@skip". Did you mean "if"?'],
        [(16, 25)],
    )


def test_invalid_arg_name(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment invalidArgName on Dog {
            doesKnowCommand(unknown: true)
        }
        """,
        [
            'Unknown argument "unknown" on field "doesKnowCommand" of type "Dog".'
        ],
        [(53, 66)],
    )


def test_misspelled_arg_name_is_reported(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment invalidArgName on Dog {
            doesKnowCommand(dogcommand: true)
        }
        """,
        [
            'Unknown argument "dogcommand" on field "doesKnowCommand" of type '
            '"Dog". Did you mean "dogCommand"?'
        ],
    )


def test_unknown_args_amongst_known_args(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        fragment oneGoodArgOneInvalidArg on Dog {
            doesKnowCommand(whoknows: 1, dogCommand: SIT, unknown: true)
        }
        """,
        [
            'Unknown argument "whoknows" on field "doesKnowCommand" of type "Dog".',
            'Unknown argument "unknown" on field "doesKnowCommand" of type "Dog".',
        ],
    )


def test_unknown_args_deeply(schema):
    run_test(
        KnownArgumentNamesChecker,
        schema,
        """
        {
        dog {
            doesKnowCommand(unknown: true)
        }
        human {
            pet {
                ... on Dog {
                    doesKnowCommand(unknown: true)
                }
            }
        }
        }
        """,
        [
            'Unknown argument "unknown" on field "doesKnowCommand" of type "Dog".',
            'Unknown argument "unknown" on field "doesKnowCommand" of type "Dog".',
        ],
    )
