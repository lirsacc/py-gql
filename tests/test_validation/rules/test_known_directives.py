# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import KnownDirectivesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_with_no_directives(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        query Foo {
            name
            ...Frag
        }

        fragment Frag on Dog {
            name
        }
        """,
    )


def test_with_known_directives(schema):
    run_test(
        KnownDirectivesChecker,
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


def test_with_unknown_directive(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        {
            dog @unknown(directive: "value") {
                name
            }
        }
        """,
        ['Unknown directive "unknown".'],
        [[(10, 38)]],
    )


def test_with_many_unknown_directives(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        {
            dog @unknown(directive: "value") {
                name
            }
            human @unknown(directive: "value") {
                name
                pets @unknown(directive: "value") {
                name
                }
            }
        }
        """,
        [
            'Unknown directive "unknown".',
            'Unknown directive "unknown".',
            'Unknown directive "unknown".',
        ],
        [[(10, 38)], [(70, 98)], [(127, 155)]],
    )


def test_with_well_placed_directives(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        query Foo @onQuery {
            name @include(if: true)
            ...Frag @include(if: true)
            skippedField @skip(if: true)
            ...SkippedFrag @skip(if: true)
        }

        mutation Bar @onMutation {
            someField
        }
        """,
    )


def test_with_misplaced_directives(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        query Foo @include(if: true) {
            name @onQuery
            ...Frag @onQuery
        }

        mutation Bar @onQuery {
            someField
        }
        """,
        [
            'Directive "include" may not be used on QUERY.',
            'Directive "onQuery" may not be used on FIELD.',
            'Directive "onQuery" may not be used on FRAGMENT_SPREAD.',
            'Directive "onQuery" may not be used on MUTATION.',
        ],
        [[(10, 28)], [(40, 48)], [(61, 69)], [(86, 94)]],
    )


def test_with_well_placed_directives_within_schema_language(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        type MyObj implements MyInterface @onObject {
            myField(myArg: Int @onArgumentDefinition): String @onFieldDefinition
        }

        extend type MyObj @onObject

        scalar MyScalar @onScalar

        extend scalar MyScalar @onScalar

        interface MyInterface @onInterface {
            myField(myArg: Int @onArgumentDefinition): String @onFieldDefinition
        }

        extend interface MyInterface @onInterface

        union MyUnion @onUnion = MyObj | Other

        extend union MyUnion @onUnion

        enum MyEnum @onEnum {
            MY_VALUE @onEnumValue
        }

        extend enum MyEnum @onEnum

        input MyInput @onInputObject {
            myField: Int @onInputFieldDefinition
        }

        extend input MyInput @onInputObject

        schema @onSchema {
            query: MyQuery
        }
        """,
    )


def test_with_misplaced_directives_within_schema_language(schema):
    run_test(
        KnownDirectivesChecker,
        schema,
        """
        type MyObj implements MyInterface @onInterface {
            myField(myArg: Int @onInputFieldDefinition): \
    String @onInputFieldDefinition
        }

        scalar MyScalar @onEnum

        interface MyInterface @onObject {
            myField(myArg: Int @onInputFieldDefinition): \
    String @onInputFieldDefinition
        }

        union MyUnion @onEnumValue = MyObj | Other

        enum MyEnum @onScalar {
            MY_VALUE @onUnion
        }

        input MyInput @onEnum {
            myField: Int @onArgumentDefinition
        }

        schema @onObject {
            query: MyQuery
        }
        """,
        [
            'Directive "onInterface" may not be used on OBJECT.',
            'Directive "onInputFieldDefinition" may not be used on '
            "ARGUMENT_DEFINITION.",
            'Directive "onInputFieldDefinition" may not be used on '
            "FIELD_DEFINITION.",
            'Directive "onEnum" may not be used on SCALAR.',
            'Directive "onObject" may not be used on INTERFACE.',
            'Directive "onInputFieldDefinition" may not be used on '
            "ARGUMENT_DEFINITION.",
            'Directive "onInputFieldDefinition" may not be used on '
            "FIELD_DEFINITION.",
            'Directive "onEnumValue" may not be used on UNION.',
            'Directive "onScalar" may not be used on ENUM.',
            'Directive "onUnion" may not be used on ENUM_VALUE.',
            'Directive "onEnum" may not be used on INPUT_OBJECT.',
            'Directive "onArgumentDefinition" may not be used on '
            "INPUT_FIELD_DEFINITION.",
            'Directive "onObject" may not be used on SCHEMA.',
        ],
    )
