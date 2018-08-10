# -*- coding: utf-8 -*-
""" Performance / Observability hooks for GraphQL execution.
"""

import contextlib


class GraphQLTracer(object):
    """ Subclass this to implement custom tracing.

    You can either override the :meth:`trace` method or the specific
    ``on_.*_(start|end)`` event handlers.
    """

    def trace(self, evt, stage, **kwargs):
        """ Register a trace event.

        The default behaviour is to dispatch to other methods.

        Args:
            evt (str): Event type
            stage (str): "start" or "end"
            **kwargs: Event payload
        """
        getattr(self, "on_%s_%s" % (evt, stage))(**kwargs)

    @contextlib.contextmanager
    def _trace_context(self, evt, **kwargs):
        self.trace(evt, "start", **kwargs)
        try:
            yield
        finally:
            self.trace(evt, "end", **kwargs)

    def _middleware(self, next_step, root, args, context, info):
        self.trace("field", "start", args=args, info=info)
        yield next_step(root, args, context, info)
        self.trace("field", "end", args=args, info=info)

    def on_query_start(self, document, variables, operation_name):
        """ Called before graphql processing starts.

        Args:
            document (str): The query document as a string
            variables (Optiona[dict]): Raw JSON Variables
            operation_name (Optiona[str]): Operation name
        """
        pass

    def on_query_end(self, document, variables, operation_name):
        """ Called after graphql processing ends.

        Args:
            document (str): The query document as a string
            variables (Optiona[dict]): Raw JSON Variables
            operation_name (Optiona[str]): Operation name
        """
        pass

    def on_parse_start(self, document):
        """ Called before graphql parsing starts.

        Args:
            document (str): The query document as a string
        """
        pass

    def on_parse_end(self, document):
        """ Called after graphql parsing ends.

        Args:
            document (str): The query document as a string
        """
        pass

    def on_validate_start(self, ast):
        """ Called before graphql validation starts.

        Args:
            ast (py_gql.lang.ast.Document): The parsed query
        """
        pass

    def on_validate_end(self, ast):
        """ Called after graphql validation ends.

        Args:
            ast (py_gql.lang.ast.Document): The parsed query
        """
        pass

    def on_execute_start(self, ast, variables):
        """ Called before graphql execution starts.

        Args:
            ast (py_gql.lang.ast.Document): The parsed query
            variables (Optiona[dict]): Raw JSON Variables
        """
        pass

    def on_execute_end(self, ast, variables):
        """ Called after graphql execution ends.

        Args:
            ast (py_gql.lang.ast.Document): The parsed query
            variables (Optiona[dict]): Raw JSON Variables
        """
        pass

    def on_field_start(self, args, info):
        """ Called before graphql field resolution starts.

        Args:
            args (dict): Coereced field arguments
            info (py_gql.execution.ResolveInfo): Resolution context
        """
        pass

    def on_field_end(self, args, info):
        """ Called after graphql field resolution is complete, including
        all child fields.

        Args:
            args (dict): Coereced field arguments
            info (py_gql.execution.ResolveInfo): Resolution context
        """
        pass


class NullTracer(GraphQLTracer):
    """ Default noop tracer
    """

    def trace(self, *args, **kwargs):
        pass
