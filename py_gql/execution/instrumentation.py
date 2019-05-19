# -*- coding: utf-8 -*-
"""
"""

from typing import Any, Callable, Sequence

from ..lang.ast import Document
from ..validation import ValidationResult
from .wrappers import GraphQLResult, ResolveInfo

TCallback = Callable[[], None]


class Instrumentation:
    """
    Instrumentation provides a pattern to hook into and customise the GraphQL
    execution process.

    Instrumentation objects provide two types of hooks:

        - ``on_*`` hooks which do not modify runtime values and are used to wrap
          execution stages. These hooks return a callback which will be called
          once the corresponding stage has finished.

        - ``instrument_*`` hooks which modify runtime values in between
          execution stages.
    """

    # Observability hooks -----------------------------------------------------

    def on_query(self) -> TCallback:
        """
        This will be called at the very start of query processing.

        The returned callback will be called immediatly before the execution
        result is returned to the caller.
        """
        return lambda: None

    def on_parse(self) -> TCallback:
        """
        This will be called just before the request document is parsed.
        It will not be called when the execution code is provided an already
        parsed ast.

        The returned callback will be called immediatly after the document has
        been parsed wether parsing was successful or not.
        """
        return lambda: None

    def on_validate(self) -> TCallback:
        """
        This will be called before query validation.

        The returned callback will be called immediatly after the document has
        been validated wether parsing was successful or not.
        """
        return lambda: None

    def on_execution(self) -> TCallback:
        """
        This will be called before operation execution starts.

        The returned callback will be called after operation execution ends.
        """
        return lambda: None

    def on_field(self, root: Any, context: Any, info: ResolveInfo) -> TCallback:
        """
        This will be called before field execution starts.

        The returned callback will be called after field execution ends and
        before field completion starts.
        """
        return lambda: None

    # Instrumentation hooks ---------------------------------------------------

    def instrument_ast(self, ast: Document) -> Document:
        """
        This will be called immediatly after the ast has been parsed. You
        should use this stage to apply any necessary transforms to the ast,
        such as field renaming or filtering.

        Any :class:`~py_gql.exc.GraphQLResponseError` raised here will interrupt
        execution and be included in the response.
        """
        return ast

    def instrument_validation_result(
        self, result: ValidationResult
    ) -> ValidationResult:
        """
        This will be called after validation in allows you to transform the
        validation result before the decision is taken to interrupt query
        processing, e.g. by filtering out some errors.
        """
        return result

    def instrument_result(self, result: GraphQLResult) -> GraphQLResult:
        """
        This will be called just before the result is returned to the client.
        You should use this stage to apply any necessary transforms to the
        returned data.

        Any :class:`~py_gql.exc.ExecutionError` raised here will interrupt
        execution and be included in the response.
        """
        return result


def _reverse_callback_stack(callbacks: Sequence[TCallback]) -> TCallback:
    def call() -> None:
        for cb in callbacks[::-1]:
            cb()

    return call


class MultiInstrumentation(Instrumentation):
    """
    Support for specifying multiple :class:`Instrumentation` instances
    at a time.

    Instrumentations will be processed as a stack: ``instrument_*`` and
    ``on_*`` hooks will be called in order while the callbacks will be called
    in reverse order
    """

    def __init__(self, *instrumentations: Instrumentation) -> None:
        self.instrumentations = instrumentations

    def on_query(self) -> TCallback:
        callbacks = []
        for i in self.instrumentations:
            callbacks.append(i.on_query())

        return _reverse_callback_stack(callbacks)

    def on_parse(self) -> TCallback:
        callbacks = []
        for i in self.instrumentations:
            callbacks.append(i.on_parse())

        return _reverse_callback_stack(callbacks)

    def on_validate(self) -> TCallback:
        callbacks = []
        for i in self.instrumentations:
            callbacks.append(i.on_validate())

        return _reverse_callback_stack(callbacks)

    def on_execution(self):
        callbacks = []
        for i in self.instrumentations:
            callbacks.append(i.on_execution())

        return _reverse_callback_stack(callbacks)

    def on_field(self, root: Any, context: Any, info: ResolveInfo) -> TCallback:
        callbacks = []
        for i in self.instrumentations:
            callbacks.append(i.on_field(root, context, info))

        return _reverse_callback_stack(callbacks)

    def instrument_ast(self, ast: Document) -> Document:
        for i in self.instrumentations:
            ast = i.instrument_ast(ast)
        return ast

    def instrument_validation_result(
        self, result: ValidationResult
    ) -> ValidationResult:
        for i in self.instrumentations:
            result = i.instrument_validation_result(result)
        return result

    def instrument_result(self, result: GraphQLResult) -> GraphQLResult:
        for i in self.instrumentations:
            result = i.instrument_result(result)
        return result
