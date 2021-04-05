# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are applicable but
# they conserved as comments for reference.


from py_gql.validation.rules import SingleFieldSubscriptionsChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_valid_subscription(schema):
    run_test(
        SingleFieldSubscriptionsChecker,
        schema,
        """
        subscription ImportantEmails {
            importantEmails
        }
        """,
    )


def test_fails_with_more_than_one_root_field(schema):
    run_test(
        SingleFieldSubscriptionsChecker,
        schema,
        """
        subscription ImportantEmails {
            importantEmails
            notImportantEmails
        }
        """,
        [
            'Subscription "ImportantEmails" must select only one '
            "top level field.",
        ],
    )


def test_fails_with_more_than_one_root_field_including_introspection(schema):
    run_test(
        SingleFieldSubscriptionsChecker,
        schema,
        """
        subscription ImportantEmails {
            importantEmails
            __typename
        }
        """,
        [
            'Subscription "ImportantEmails" must select only one '
            "top level field.",
        ],
    )


def test_fails_with_many_more_than_one_root_field(schema):
    run_test(
        SingleFieldSubscriptionsChecker,
        schema,
        """
        subscription ImportantEmails {
            importantEmails
            notImportantEmails
            spamEmails
        }
        """,
        [
            'Subscription "ImportantEmails" must select only one '
            "top level field.",
        ],
    )


def test_fails_with_more_than_one_root_field_in_anonymous_subscriptions(schema):
    run_test(
        SingleFieldSubscriptionsChecker,
        schema,
        """
        subscription {
            importantEmails
            notImportantEmails
        }
        """,
        ["Subscription must select only one " "top level field."],
    )
