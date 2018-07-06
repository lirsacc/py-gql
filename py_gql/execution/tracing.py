# -*- coding: utf-8 -*-
""" Performance / Observability hooks for GraphQL execution.
"""

import contextlib


class GraphQLTracer(object):
    """ Subclass this to implement custom tracing.

    You can either override the :meth:`trace` method or the specific
    `on_.*_(start|end)` handlers.

    Trace order during standard processing is as such:

    - :meth:`trace`('query', 'start', `document`, `variables`, `operation_name`) \
-> :meth:`on_query_start`
    - :meth:`trace`('parse', 'start', `query string`) -> :meth:`on_parse_start`
    - :meth:`trace`('parse', 'end', `query string`) -> :meth:`on_parse_end`
    - :meth:`trace`('validate', 'start', `ast`) -> :meth:`on_validate_start`
    - :meth:`trace`('validate', 'end', `ast`) -> :meth:`on_validate_end`
    - :meth:`trace`('execute', 'start', `ast`, `variables`) -> :meth:`on_execute_start`
        Interleaved until all fields have resolved:
            - :meth:`trace`('field', 'start', `args`, `info`) -> :meth:`on_field_start`
            - :meth:`trace`('field', 'end', `args`, `info`) -> :meth:`on_field_end`
    - :meth:`trace`('execute', 'end', `ast`, `variables`) -> :meth:`on_execute_end`
    - :meth:`trace`('query', 'end', `document`, `variables`, `operation_name`) \
-> :meth:`on_query_end`
    """

    def trace(self, evt, stage, **kwargs):
        handler = getattr(self, "on_%s_%s" % (evt, stage))
        return handler(**kwargs)

    @contextlib.contextmanager
    def trace_context(self, evt, **kwargs):
        self.trace(evt, "start", **kwargs)
        try:
            yield
        finally:
            self.trace(evt, "end", **kwargs)

    def middleware(self, next_step, root, args, context, info):
        """ Suport tracing field execution as an execution middleware.
        """
        self.trace("field", "start", args=args, info=info)
        yield next_step(root, args, context, info)
        self.trace("field", "end", args=args, info=info)

    def on_query_start(self, document, variables, operation_name):
        """ Called before graphql processing starts

        :type document: str
        :param document: The query document as a string

        :type variables: Optional[dict]
        :param variables: Raw JSON Variables

        :type operation_name: Optional[str]
        :param operation_name: Operation name
        """
        pass

    def on_query_end(self, document, variables, operation_name):
        """ Called after graphql processing ends

        :type document: str
        :param document: The query document as a string

        :type variables: Optional[dict]
        :param variables: Raw JSON Variables

        :type operation_name: Optional[str]
        :param operation_name: Operation name
        """
        pass

    def on_parse_start(self, document):
        """ Called before graphql parsing starts

        :type document: str
        :param document: The query document as a string
        """
        pass

    def on_parse_end(self, document):
        """ Called after graphql parsing ends

        :type document: str
        :param document: The query document as a string
        """
        pass

    def on_validate_start(self, ast):
        """ Called before graphql validation starts

        :type ast: py_gql.lang.ast.Document
        :param ast: The parsed query
        """
        pass

    def on_validate_end(self, ast):
        """ Called after graphql validation ends

        :type ast: py_gql.lang.ast.Document
        :param ast: The parsed query
        """
        pass

    def on_execute_start(self, ast, variables):
        """ Called before graphql execution starts

        :type ast: py_gql.lang.ast.Document
        :param ast: The parsed query

        :type variables: dict
        :param variables: Query variables
        """
        pass

    def on_execute_end(self, ast, variables):
        """ Called after graphql execution ends

        :type ast: py_gql.lang.ast.Document
        :param ast: The parsed query

        :type variables: dict
        :param variables: Query variables
        """
        pass

    def on_field_start(self, args, info):
        """ Called before graphql field resolution starts

        :type args: dict
        :param args: Coereced field arguments

        :type info: py_gql.execution.ResolveInfo
        :param info: Resolution context
        """
        pass

    def on_field_end(self, args, info):
        """ Called after graphql field resolution is complete, including
        all child fields

        :type args: dict
        :param args: Coereced field arguments

        :type info: py_gql.execution.ResolveInfo
        :param info: Resolution context
        """
        pass


class NullTracer(GraphQLTracer):
    """ Default noop tracer
    """

    def trace(self, *args, **kwargs):
        pass
