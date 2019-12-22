# -*- coding: utf-8 -*-
"""
"""

import abc
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

E = TypeVar("E", bound=Exception)


class Runtime:
    """
    """

    def ensure_wrapped(self, value: Any) -> Any:
        """Ensure values are wrapped in the necessary container type.

        This is essentially used after execution has finished to make sure the
        final value conforms to the expected types (e.g. coroutines) and avoid
        consumers having to typecheck them needlessly.
        """
        return value

    def gather_values(self, values: Iterable[Any]) -> Any:
        """Group multiple wrapped values inside a single wrapped value.

        This is equivalent to the `asyncio.gather` semantics.
        """
        return values

    def map_value(
        self,
        value: Any,
        then: Callable[[Any], Any],
        else_: Optional[
            Tuple[Union[Type[E], Tuple[Type[E], ...]], Callable[[E], Any]]
        ] = None,
    ) -> Any:
        """Execute a callback on a wrapped value, potentially catching exceptions.

        This is used internally to orchestrate callbacks and should be treated
        similarly to `await` semantics the `map` in Future combinators.
        """
        try:
            return then(value)
        except Exception as err:
            if else_ and isinstance(err, else_[0]):
                return else_[1](err)  # type: ignore
            raise

    def unwrap_value(self, value):
        """Recursively traverse wrapped values.

        Given that resolution across the graph can span multiple level, this is
        used to support resolved values depending on deeper values (such as
        object fields).
        """
        return value

    def wrap_callable(self, func: Callable[..., Any]) -> Callable[..., Any]:
        return func


class SubscriptionEnabledRuntime(Runtime, abc.ABC):
    @abc.abstractmethod
    def map_stream(
        self, source_stream: Any, map_value: Callable[[Any], Any]
    ) -> Any:
        raise NotImplementedError()
