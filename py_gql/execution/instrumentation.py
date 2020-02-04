# -*- coding: utf-8 -*-
"""
"""

from typing import Any

from .wrappers import ResolveInfo


class Instrumentation:
    """Instrumentation provides a pattern to hook into py_gql's execution
    process for observability purposes.
    """

    # Observability hooks -----------------------------------------------------

    def on_query_start(self) -> None:
        """This will be called at the very start of query processing."""

    def on_query_end(self) -> None:
        """This will be called once the execution result is ready."""

    def on_parsing_start(self) -> None:
        """This will be called just before the request document is parsed.

        It will not be called when the execution code is provided an already
        parsed ast.
        """

    def on_parsing_end(self) -> None:
        """This will be called after the request document has been parsed.

        This is called even if parsing failed due to a syntax error.
        """

    def on_validation_start(self) -> None:
        """This will be called before query validation."""

    def on_validation_end(self) -> None:
        """This will be called before query validation."""

    def on_execution_start(self) -> None:
        """This will be called before operation execution starts."""

    def on_execution_end(self) -> None:
        """This will be after operation execution ends
        and the execution result is ready."""

    def on_field_start(
        self, root: Any, context: Any, info: ResolveInfo
    ) -> None:
        """This will be called before field resolution starts."""

    def on_field_end(self, root: Any, context: Any, info: ResolveInfo) -> None:
        """This will be called after field resolution ends."""


class MultiInstrumentation(Instrumentation):
    """Combine multiple :class:`Instrumentation` instances.

    Instrumentations will be processed as a stack: ``on_start*`` hooks will be
    called in order while ``on_*_end`` hooks will be called in reverse order.
    """

    def __init__(self, *instrumentations: Instrumentation) -> None:
        self.instrumentations = instrumentations

    def on_query_start(self) -> None:
        for i in self.instrumentations:
            i.on_query_start()

    def on_query_end(self) -> None:
        for i in self.instrumentations[::-1]:
            i.on_query_end()

    def on_parsing_start(self) -> None:
        for i in self.instrumentations:
            i.on_parsing_start()

    def on_parsing_end(self) -> None:
        for i in self.instrumentations[::-1]:
            i.on_parsing_end()

    def on_validation_start(self) -> None:
        for i in self.instrumentations:
            i.on_validation_start()

    def on_validation_end(self) -> None:
        for i in self.instrumentations[::-1]:
            i.on_validation_end()

    def on_execution_start(self) -> None:
        for i in self.instrumentations:
            i.on_execution_start()

    def on_execution_end(self) -> None:
        for i in self.instrumentations[::-1]:
            i.on_execution_end()

    def on_field_start(
        self, root: Any, context: Any, info: ResolveInfo
    ) -> None:
        for i in self.instrumentations:
            i.on_field_start(root, context, info)

    def on_field_end(self, root: Any, context: Any, info: ResolveInfo) -> None:
        for i in self.instrumentations[::-1]:
            i.on_field_end(root, context, info)
