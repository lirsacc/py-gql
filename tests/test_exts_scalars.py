import re
import uuid

import pytest

from py_gql.exc import ScalarParsingError, ScalarSerializationError
from py_gql.exts.scalars import UUID, RegexType
from py_gql.lang import parse_value


class TestUUID:
    def test_parse_string(self):
        assert UUID.parse("c4da8450-ec7a-4d3b-9ade-18194daeb2d6") == uuid.UUID(
            "c4da8450-ec7a-4d3b-9ade-18194daeb2d6"
        )

    def test_serialize(self):
        assert (
            UUID.serialize(uuid.UUID("c4da8450-ec7a-4d3b-9ade-18194daeb2d6"))
            == "c4da8450-ec7a-4d3b-9ade-18194daeb2d6"
        )

    def test_parse_invalid(self):
        with pytest.raises(ScalarParsingError) as exc_info:
            UUID.parse("foo")
        assert str(exc_info.value) == "badly formed hexadecimal UUID string"

    def test_serialize_invalid(self):
        with pytest.raises(ScalarSerializationError) as exc_info:
            UUID.serialize("foo")
        assert str(exc_info.value) == "badly formed hexadecimal UUID string"


class TestRegexType:
    def test_accepts_string(self):
        t = RegexType("RE", r"[a-z][a-z_]*")
        assert t.parse("a_b") == "a_b"

    def test_accepts_compiled_regex(self):
        p = re.compile(r"[a-d]+", re.IGNORECASE)
        t = RegexType("RE", p)
        assert t.parse("aD") == "aD"

    def test_parse_fail(self):
        p = re.compile(r"^[a-d]+$", re.IGNORECASE)
        t = RegexType("RE", p)
        with pytest.raises(ScalarParsingError) as exc_info:
            t.parse("aF")
        assert str(exc_info.value) == '"aF" does not match pattern "^[a-d]+$"'

    def test_parse_literal_ok(self):
        p = re.compile(r"^[a-d]+$", re.IGNORECASE)
        t = RegexType("RE", p)
        assert t.parse_literal(parse_value('"aBcD"')) == "aBcD"  # type: ignore

    def test_parse_literal_fail(self):
        p = re.compile(r"^[a-d]+$", re.IGNORECASE)
        t = RegexType("RE", p)
        with pytest.raises(ScalarParsingError) as exc_info:
            t.parse_literal(parse_value('"aF"'))  # type: ignore
        assert str(exc_info.value) == '"aF" does not match pattern "^[a-d]+$"'

    def test_parse_literal_non_string(self):
        p = re.compile(r"^[a-d]+$", re.IGNORECASE)
        t = RegexType("RE", p)
        with pytest.raises(ScalarParsingError) as exc_info:
            t.parse_literal(parse_value("1"))  # type: ignore
        assert str(exc_info.value) == "Invalid literal IntValue"
