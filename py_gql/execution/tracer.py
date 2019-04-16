# -*- coding: utf-8 -*-

from .wrappers import ResolveInfo


class Tracer:
    """
    Tracer implementation are used to record and monitor graphql operation
    performance.
    """

    def on_start(self):
        pass

    def on_end(self):
        pass

    def on_parse_start(self) -> None:
        pass

    def on_parse_end(self) -> None:
        pass

    def on_validate_start(self) -> None:
        pass

    def on_validate_end(self) -> None:
        pass

    def on_query_start(self) -> None:
        pass

    def on_query_end(self) -> None:
        pass

    def on_field_start(self, info: ResolveInfo) -> None:
        pass

    def on_field_end(self, info: ResolveInfo) -> None:
        pass


class NullTracer(Tracer):
    """
    Noop tracer used in case no tracer is defined.
    """

    pass
