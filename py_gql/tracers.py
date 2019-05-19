# -*- coding: utf-8 -*-
"""
Collection of useful tracers implementations.
"""

import datetime
from typing import Any, Dict, Tuple, Union, cast

from ._utils import OrderedDict
from .execution import GraphQLExtension, Instrumentation, ResolveInfo

__all__ = ("TimingTracer", "ApolloTracer")


def _ns(start: datetime.datetime, end: datetime.datetime) -> int:
    return int((end - start).total_seconds() * 1e9)


def _rfc3339(ts: datetime.datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class FieldTiming:
    __slots__ = ("info", "start", "end")

    def __init__(self, info: ResolveInfo):
        self.info = info
        self.start = datetime.datetime.utcnow()
        self.end = None


class TimingTracer(Instrumentation):
    """
    Default implementation for tracers that collect GraphQL execution timing
    using the :py:mod:`datetime` module. All times are collected as UTC.
    """

    def __init__(self):
        self.fields = (
            OrderedDict()
        )  # type: Dict[Tuple[Union[str, int]], FieldTiming]
        self.start = None
        self.end = None
        self.parse_end = None
        self.parse_start = None
        self.query_end = None
        self.query_start = None
        self.validation_end = None
        self.validation_start = None

    def on_query(self):
        self.start = datetime.datetime.utcnow()
        return self.on_query_end

    def on_query_end(self):
        self.end = datetime.datetime.utcnow()

    def on_execution(self):
        self.query_start = datetime.datetime.utcnow()
        return self.on_execution_end

    def on_execution_end(self):
        self.query_end = datetime.datetime.utcnow()

    def on_parse(self):
        self.parse_start = datetime.datetime.utcnow()
        return self.on_parse_end

    def on_parse_end(self):
        self.parse_end = datetime.datetime.utcnow()

    def on_validate(self):
        self.validation_start = datetime.datetime.utcnow()
        return self.on_validate_end

    def on_validate_end(self):
        self.validation_end = datetime.datetime.utcnow()

    def on_field(self, _root, _ctx, info):
        self.fields[tuple(info.path)] = FieldTiming(info)

        def on_field_end():
            self.fields[tuple(info.path)].end = datetime.datetime.utcnow()

        return on_field_end


class ApolloTracer(TimingTracer, GraphQLExtension):
    """
    Tracer implementation compatible with the `Apollo Tracing
    <https://github.com/apollographql/apollo-tracing>`_ specification.

    This tracers also implements :class:`py_gql.GraphQLExtension` in order to be
    included in the response according to the specification.
    """

    name = "tracing"

    def _field(self, field_timing: FieldTiming) -> Dict[str, Any]:
        return {
            "path": list(field_timing.info.path),
            "parentType": field_timing.info.parent_type.name,
            "fieldName": field_timing.info.field_definition.name,
            "returnType": str(field_timing.info.field_definition.type),
            "startOffset": _ns(
                cast(datetime.datetime, self.start), field_timing.start
            ),
            "duration": _ns(
                field_timing.start, cast(datetime.datetime, field_timing.end)
            ),
        }

    def payload(self):
        return {
            "version": 1,
            "startTime": _rfc3339(self.start),
            "endTime": _rfc3339(self.end),
            "duration": _ns(self.start, self.end),
            "execution": (
                {"resolvers": [self._field(ft) for ft in self.fields.values()]}
                if self.fields
                else None
            ),
            "validation": (
                {
                    "duration": _ns(self.validation_start, self.validation_end),
                    "startOffset": _ns(self.start, self.validation_start),
                }
                if self.validation_start is not None
                else None
            ),
            "parsing": (
                {
                    "duration": _ns(self.parse_start, self.parse_end),
                    "startOffset": _ns(self.start, self.parse_start),
                }
                if self.parse_start is not None
                else None
            ),
        }
