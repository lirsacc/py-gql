# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import ScalarLeafsChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_valid_scalar_selection(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelection on Dog {
            barks
        }
        """,
    )


def test_object_type_missing_selection(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        query directQueryOnObjectWithoutSubFields {
            human
        }
        """,
        [
            'Field "human" of type "Human" must have a selection of subfields. '
            'Did you mean "human { ... }"?'
        ],
    )


def test_interface_type_missing_selection(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        {
            human { pets }
        }
        """,
        [
            'Field "pets" of type "[Pet]" must have a selection of subfields. '
            'Did you mean "pets { ... }"?'
        ],
    )


def test_valid_scalar_selection_with_args(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelectionWithArgs on Dog {
            doesKnowCommand(dogCommand: SIT)
        }
        """,
    )


def test_scalar_selection_not_allowed_on_boolean(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelectionsNotAllowedOnBoolean on Dog {
            barks { sinceWhen }
        }
        """,
        [
            'Field "barks" must not have a selection since type "Boolean" '
            "has no subfields."
        ],
    )


def test_scalar_selection_not_allowed_on_enum(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelectionsNotAllowedOnEnum on Cat {
            furColor { inHexdec }
        }
        """,
        [
            'Field "furColor" must not have a selection since type "FurColor" '
            "has no subfields."
        ],
    )


def test_scalar_selection_not_allowed_with_args(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelectionsNotAllowedWithArgs on Dog {
            doesKnowCommand(dogCommand: SIT) { sinceWhen }
        }
        """,
        [
            'Field "doesKnowCommand" must not have a selection since type '
            '"Boolean" has no subfields.'
        ],
    )


def test_scalar_selection_not_allowed_with_directives(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelectionsNotAllowedWithDirectives on Dog {
            name @include(if: true) { isAlsoHumanName }
        }
        """,
        [
            'Field "name" must not have a selection since type "String" '
            "has no subfields."
        ],
    )


def test_scalar_selection_not_allowed_with_directives_and_args(schema):
    run_test(
        ScalarLeafsChecker,
        schema,
        """
        fragment scalarSelectionsNotAllowedWithDirectivesAndArgs on Dog {
            doesKnowCommand(dogCommand: SIT) @include(if: true) { sinceWhen }
        }
        """,
        [
            'Field "doesKnowCommand" must not have a selection since type '
            '"Boolean" has no subfields.'
        ],
    )
