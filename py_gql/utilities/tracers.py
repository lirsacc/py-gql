# -*- coding: utf-8 -*-
""" Some useful middlewares """

import datetime as dt
import json
import logging

from .._utils import OrderedDict
from ..execution import GraphQLExtension, GraphQLTracer


def _nanoseconds(delta):
    return int(delta.total_seconds() * 1e9)


def _rfc3339(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class ApolloTracer(GraphQLTracer, GraphQLExtension):
    """ `Apollo Tracing <https://github.com/apollographql/apollo-tracing>`_
    implementation """

    def __init__(self):
        self.start = None
        self.validation_start = None
        self.validation_end = None
        self.parse_start = None
        self.parse_end = None
        self.fields = OrderedDict()
        self.end = None

    def on_query_start(self, **_):
        self.start = dt.datetime.utcnow()

    def on_query_end(self, **_):
        self.end = dt.datetime.utcnow()

    def on_parse_start(self, **_):
        self.parse_start = dt.datetime.utcnow()

    def on_parse_end(self, **_):
        self.parse_end = dt.datetime.utcnow()

    def on_validate_start(self, **_):
        self.validation_start = dt.datetime.utcnow()

    def on_validate_end(self, **_):
        self.validation_end = dt.datetime.utcnow()

    def on_field_start(self, info, **_):
        start = dt.datetime.utcnow()
        self.fields[str(info.path)] = {
            "path": list(info.path),
            "parentType": info.parent_type.name,
            "fieldName": info.field_def.name,
            "returnType": str(info.field_def.type),
            "startOffset": _nanoseconds(start - self.start),
            "start": start,
        }

    def on_field_end(self, info, **_):
        end = dt.datetime.utcnow()
        start = self.fields[str(info.path)].pop("start")
        self.fields[str(info.path)]["duration"] = _nanoseconds(end - start)

    def name(self):
        return "tracing"

    def payload(self):
        return {
            "version": 1,
            "startTime": _rfc3339(self.start),
            "endTime": _rfc3339(self.end),
            "duration": _nanoseconds(self.end - self.start),
            "execution": (
                {"resolvers": list(self.fields.values())}
                if self.fields
                else None
            ),
            "validation": (
                {
                    "duration": _nanoseconds(
                        self.validation_end - self.validation_start
                    ),
                    "startOffset": _nanoseconds(
                        self.validation_start - self.start
                    ),
                }
                if self.validation_start is not None
                else None
            ),
            "parsing": (
                {
                    "duration": _nanoseconds(self.parse_end - self.parse_start),
                    "startOffset": _nanoseconds(self.parse_start - self.start),
                }
                if self.parse_start is not None
                else None
            ),
        }


_SLOW_LOG_FORMAT_STR = """GraphQL query took too long (duration = %fms, \
threshold = %fms, operation = %s, document = '''
%s
''', variables = %s)"""


class SlowQueryLog(GraphQLTracer):
    """ Log slow queries.

    By default this logs the entire query and variables, if this is not
    suitable (e.g. you need to redact the query) you can subclass this class
    and override :meth:`format_document` and :meth:`format_variables`
    """

    def __init__(
        self, threshold, logger=None, level=logging.WARNING, format_str=None
    ):
        """
        :type threshold: int
        :param threshold: Slow threshold in ms

        :type logger: Optional[logging.Logger]
        :param logger: Custom logger instance top use

        :type level: Optional[int]
        :param level: Log level to use

        :type format_str: Optional[str]
        :param format_str: Log format to use
        """
        self._threshold = threshold
        self._logger = (
            logger
            if logger is not None
            else logging.getLogger("py_gql.slow_query_log")
        )
        self._level = level
        self._format_str = format_str or _SLOW_LOG_FORMAT_STR

    def format_document(self, document):
        return document

    def format_variables(self, variables):
        return json.dumps(variables, indent=4, sort_keys=True)

    def on_query_start(self, **_):
        self._start = dt.datetime.utcnow()

    def on_query_end(self, document, variables, operation_name):
        end = dt.datetime.utcnow()
        duration = (end - self._start).total_seconds() * 1000
        if duration > self._threshold:
            self._logger.log(
                self._level,
                self._format_str,
                duration,
                self._threshold,
                operation_name,
                self.format_document(document),
                self.format_variables(variables),
            )
