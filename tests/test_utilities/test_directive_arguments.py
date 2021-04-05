import pytest

from py_gql.exc import CoercionError
from py_gql.lang import parse
from py_gql.schema import Argument, Directive, IncludeDirective, Int, String
from py_gql.utilities import all_directive_arguments, directive_arguments


CustomDirective = Directive(
    "custom",
    ["FIELD"],
    [Argument("a", String), Argument("b", Int)],
)


CustomRepeatableDirective = Directive(
    "customRepeat",
    ["FIELD"],
    [Argument("a", String), Argument("b", Int)],
    repeatable=True,
)


class TestDirectiveArguments:
    def test_include(self):
        doc = parse("{ a @include(if: true) }")
        assert (
            directive_arguments(
                IncludeDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {},
            )
            == {"if": True}
        )

    def test_include_missing(self):
        doc = parse("{ a @include(a: 42) }")
        with pytest.raises(CoercionError):
            directive_arguments(
                IncludeDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {},
            )

    def test_include_extra(self):
        doc = parse("{ a @include(a: 42, if: true) }")
        assert (
            directive_arguments(
                IncludeDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {},
            )
            == {"if": True}
        )

    def test_custom_directive_field(self):
        doc = parse('{ a @custom(a: "foo", b: 42) }')
        assert (
            directive_arguments(
                CustomDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {},
            )
            == {"a": "foo", "b": 42}
        )

    def test_custom_directive_field_variables(self):
        doc = parse('{ a @custom(a: "foo", b: $b) }')
        assert (
            directive_arguments(
                CustomDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            == {"a": "foo", "b": 42}
        )

    def test_repeatable_directive_missing(self):
        doc = parse('{ a @custom(a: "foo", b: $b) }')
        assert (
            directive_arguments(
                CustomRepeatableDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            is None
        )

    def test_repeatable_directive_once(self):
        doc = parse('{ a @customRepeat(a: "foo", b: $b) }')
        assert (
            directive_arguments(
                CustomRepeatableDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            == {"a": "foo", "b": 42}
        )

    def test_repeatable_directive_multiple(self):
        doc = parse(
            '{ a @customRepeat(a: "foo", b: $b) @customRepeat(a: "bar", b: 41) }',
        )
        assert (
            directive_arguments(
                CustomRepeatableDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            == {"a": "foo", "b": 42}
        )


class TestAllDirectiveArguments:
    def test_repeatable_directive_missing(self):
        doc = parse('{ a @custom(a: "foo", b: $b) }')
        assert (
            all_directive_arguments(
                CustomRepeatableDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            == []
        )

    def test_repeatable_directive_once(self):
        doc = parse('{ a @customRepeat(a: "foo", b: $b) }')
        assert (
            all_directive_arguments(
                CustomRepeatableDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            == [{"a": "foo", "b": 42}]
        )

    def test_repeatable_directive_multiple(self):
        doc = parse(
            '{ a @customRepeat(a: "foo", b: $b) @customRepeat(a: "bar", b: 41) }',
        )
        assert (
            all_directive_arguments(
                CustomRepeatableDirective,
                doc.definitions[0].selection_set.selections[0],  # type: ignore
                {"b": 42},
            )
            == [{"a": "foo", "b": 42}, {"a": "bar", "b": 41}]
        )
