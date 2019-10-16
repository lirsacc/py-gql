# -*- coding: utf-8 -*-
"""
"""

from functools import reduce
from typing import Any

from ..lang.ast import Document
from .wrappers import GraphQLResult, ResolveInfo


class Instrumentation:
    """Instrumentation provides a pattern to hook into and customise py_gql's
    execution process.

    Instrumentation objects provide multiple of categories of hooks:

        - ``on_*`` hooks do not modify runtime values and are used to wrap
          execution stages. They can be used for observability or to trigger
          side effects.

        - ``transform_*`` hooks modify runtime values in between execution stages.
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

    # Transform hooks ---------------------------------------------------------

    def transform_ast(self, ast: Document) -> Document:
        """Modify the document AST.

        You should use this stage to apply any necessary transforms to the ast,
        such as field renaming or filtering.

        Any :class:`~py_gql.exc.GraphQLResponseError` raised here will interrupt
        execution and be included in the response.
        """
        return ast

    def transform_result(self, result: GraphQLResult) -> GraphQLResult:
        """ This will be called just before the result is returned to the client.

        You should use this stage to apply any necessary transforms to the
        returned data.

        Any :class:`~py_gql.exc.ExecutionError` raised here will interrupt
        execution and be included in the response.
        """
        return result


class MultiInstrumentation(Instrumentation):
    """Combine multiple :class:`Instrumentation` instances.

    Instrumentations will be processed as a stack: ``transform_*``, and
    ``on_start*`` hooks will be called in order while ``on_*_end`` hooks will be
    called in reverse order.
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

    def transform_ast(self, ast: Document) -> Document:
        return reduce(
            lambda acc, i: i.transform_ast(acc), self.instrumentations, ast
        )

    def transform_result(self, result: GraphQLResult) -> GraphQLResult:
        return reduce(
            lambda acc, i: i.transform_result(acc),
            self.instrumentations,
            result,
        )
