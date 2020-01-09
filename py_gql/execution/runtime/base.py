# -*- coding: utf-8 -*-

import abc
from typing import Any, Callable, Iterable, Optional, Tuple, Type, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
AnyFn = Callable[..., Any]


class Runtime(abc.ABC):
    """Runtime base class.

    A runtime is a way for consumers to implement specific execution primitives
    (especially around I/O considerations).
    """

    # TODO: Usage of types is not great, there must be a way to make them more
    # useful, but I haven't managed to express it. I am also not sure the
    # semantics are correct (e.g. container type, wrapped values).

    @abc.abstractmethod
    def submit(self, fn: AnyFn, *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the runtime."""
        raise NotImplementedError()

    @abc.abstractmethod
    def ensure_wrapped(self, value: Any) -> Any:
        """Ensure values are wrapped in the necessary container type.

        This is essentially used after execution has finished to make sure the
        final value conforms to the expected types (e.g. coroutines) and avoid
        consumers having to typecheck them needlessly.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def gather_values(self, values: Iterable[Any]) -> Any:
        """Group multiple wrapped values inside a single wrapped value.

        This is equivalent to the `asyncio.gather` semantics.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def map_value(
        self,
        value: Any,
        then: Callable[[Any], Any],
        else_: Optional[Tuple[Type[E], Callable[[E], Any]]] = None,
    ) -> Any:
        """Execute a callback on a wrapped value, potentially catching exceptions.

        This is used internally to orchestrate callbacks and should be treated
        similarly to `await` semantics `map` in Future combinators.
        The ``else_`` argument can be used to handle exceptions (limited to a
        single exception type).
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unwrap_value(self, value):
        """Recursively traverse wrapped values.

        Given that resolution across the graph can span multiple level, this is
        used to support resolved values depending on deeper values (such as
        object fields).
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def wrap_callable(self, func: AnyFn) -> AnyFn:
        """Wrap a function to be called through the executor. """
        raise NotImplementedError()


class SubscriptionRuntime(Runtime):
    """Subscription runtime base class.

    By default runtimes are assumed to not support subscriptions which ususally
    require implementing some form of background streams to be useful.
    Implementing this instead of the base `Runtime` class notifies the library
    that subscriptions are available.
    """

    @abc.abstractmethod
    def map_stream(
        self, source_stream: Any, map_value: Callable[[Any], Any]
    ) -> Any:
        """Apply a mapping function to a stream / iterable of values."""
        raise NotImplementedError()
