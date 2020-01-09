# -*- coding: utf-8 -*-

from typing import Any, Callable, Iterable, Optional, Tuple, Type, TypeVar

from .base import Runtime

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
TException = TypeVar("TException", bound=Type[Exception])
AnyFn = Callable[..., Any]


class BlockingRuntime(Runtime):
    """Default runtime implementation which blocks the current thread."""

    def submit(self, fn: AnyFn, *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    def ensure_wrapped(self, value: Any) -> Any:
        return value

    def gather_values(self, values: Iterable[Any]) -> Any:
        return list(values)

    def map_value(
        self,
        value: Any,
        then: Callable[[Any], T],
        else_: Optional[Tuple[Type[E], Callable[[E], T]]] = None,
    ) -> Any:
        try:
            return then(value)
        except Exception as err:
            if else_ and isinstance(err, else_[0]):
                return else_[1](err)
            raise

    def unwrap_value(self, value):
        return value

    def wrap_callable(self, func: AnyFn) -> AnyFn:
        return func
