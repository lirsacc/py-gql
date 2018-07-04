# -*- coding: utf-8 -*-

import logging
import time

from py_gql.schema import Schema, ObjectType, String, Field
from py_gql.utilities.tracers import SlowQueryLog
from py_gql import graphql


def slow_resolver(*args, **kwargs):
    time.sleep(0.2)
    return "Foo"


def test_slow_query_log(caplog):
    schema = Schema(
        ObjectType("Query", [Field("foo", String, resolve=slow_resolver)])
    )

    graphql(schema, "{ foo }", tracer=SlowQueryLog(100))

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert record.name == "py_gql.slow_query_log"
    _, _, op, doc, variables = record.args
    assert op is None
    assert doc == "{ foo }"
    assert variables == "null"


def test_slow_query_log_not_triggered(caplog):
    schema = Schema(
        ObjectType("Query", [Field("foo", String, resolve=slow_resolver)])
    )
    graphql(schema, "{ foo }", tracer=SlowQueryLog(3000))
    assert len(caplog.records) == 0


def test_slow_query_log_custom_logger(caplog):
    schema = Schema(
        ObjectType("Query", [Field("foo", String, resolve=slow_resolver)])
    )
    logger = logging.getLogger("my_custom_logger")
    logger.setLevel(logging.DEBUG)

    graphql(
        schema,
        "{ foo }",
        tracer=SlowQueryLog(100, logger=logger, level=logging.INFO),
    )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert record.name == "my_custom_logger"


def test_slow_query_log_custom_class(caplog):
    class RedactedLogger(SlowQueryLog):
        def format_document(self, document):
            return "<REDACTED>"

        def format_variables(self, document):
            return "<REDACTED>"

    schema = Schema(
        ObjectType("Query", [Field("foo", String, resolve=slow_resolver)])
    )
    logger = logging.getLogger("my_custom_logger")
    logger.setLevel(logging.DEBUG)

    graphql(
        schema,
        "{ foo }",
        tracer=RedactedLogger(100, logger=logger, level=logging.INFO),
    )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert record.name == "my_custom_logger"

    _, _, _, doc, variables = record.args
    assert doc == "<REDACTED>"
    assert variables == "<REDACTED>"
