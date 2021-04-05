# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are applicable but
# they conserved as comments for reference.


from py_gql.validation.rules import UniqueDirectivesPerLocationChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_no_directives(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field
        }
        """,
    )


# Should have been caught by KnownDirectivesChecker
def test_unknown_directives(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @unknownOnType {
            field @unknownOnField
        }
        """,
    )


def test_unique_directives_in_different_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directiveA {
            field @directiveB
        }
        """,
    )


def test_unique_directives_in_same_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directiveA @directiveB {
            field @directiveA @directiveB
        }
        """,
    )


def test_same_directives_in_different_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directiveA {
            field @directiveA
        }
        """,
    )


def test_same_directives_in_similar_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @directive
            field @directive
        }
        """,
    )


def test_duplicate_directives_in_one_location(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @onField @onField
        }
        """,
        ['Duplicate directive "@onField"'],
        [[(43, 51)]],
    )


def test_many_duplicate_directives_in_one_location(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @onField @onField @onField
        }
        """,
        ['Duplicate directive "@onField"', 'Duplicate directive "@onField"'],
        [[(43, 51)], [(52, 60)]],
    )


def test_different_duplicate_directives_in_one_location(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @onField @onField2 @onField @onField2
        }
        """,
        ['Duplicate directive "@onField"', 'Duplicate directive "@onField2"'],
        [[(53, 61)], [(62, 71)]],
    )


def test_duplicate_directives_in_many_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @onObject @onObject {
            field @onField @onField
        }
        """,
        ['Duplicate directive "@onObject"', 'Duplicate directive "@onField"'],
        [[(32, 41)], [(63, 71)]],
    )


def test_duplicate_repeatable_directive(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @onFieldRepeatable @onFieldRepeatable
        }
        """,
    )
