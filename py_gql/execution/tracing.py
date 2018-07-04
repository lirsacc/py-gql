# -*- coding: utf-8 -*-
""" Performance / Observability hooks for GraphQL execution.
"""

import contextlib


class GraphQLTracer(object):
    """ Subclass this to implement custom tracing.
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

    def start(self):
        pass

    def end(self):
        pass

    def on_parse_start(self, document):
        pass

    def on_parse_end(self, document):
        pass

    def on_validate_start(self, ast):
        pass

    def on_validate_end(self, ast):
        pass

    def on_execute_start(self, ast, variables):
        pass

    def on_execute_end(self, ast, variables):
        pass

    def on_field_start(self, args, info):
        pass

    def on_field_end(self, args, info):
        pass

    def middleware(self, next_step, root, args, context, info):
        """ Suport tracing field execution as an execution middleware.
        """
        self.trace("field", "start", args=args, info=info)
        yield next_step(root, args, context, info)
        self.trace("field", "end", args=args, info=info)


class NullTracer(GraphQLTracer):
    """ Default noop tracer
    """

    def trace(self, *args, **kwargs):
        pass
