# -*- coding: utf-8 -*-

# REVIEW: This is likely suboptimal and create too many wrapping Future
# instances.

import functools
from concurrent.futures import (
    CancelledError,
    Future,
    ThreadPoolExecutor as _ThreadPoolExecutor,
)
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..exc import CoercionError, ResolverError
from ..lang import ast as _ast
from ..schema import Field, GraphQLType, ObjectType
from .executor import Executor
from .wrappers import GroupedFields, ResolveInfo, ResponsePath

T = TypeVar("T")
G = TypeVar("G")
E = TypeVar("E", bound=Exception)

Resolver = Callable[..., Any]

MaybeFuture = Union["Future[T]", T]


class ThreadPoolExecutor(Executor):
    @staticmethod
    def map_value(value, func):
        return chain(value, func)

    __slots__ = (
        "schema",
        "document",
        "variables",
        "fragments",
        "operation",
        "context_value",
        "_grouped_fields",
        "_fragment_type_applies",
        "_field_defs",
        "_argument_values",
        "_resolver_cache",
        "_errors",
        "_inner",
    )

    def __init__(
        # fmt: off
        self,
        *args: Any,
        inner_executor: Optional[_ThreadPoolExecutor] = None,
        **kwargs: Any
        # fmt: on
    ):
        super().__init__(*args, **kwargs)
        self._inner = inner_executor or _ThreadPoolExecutor()

    def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> "Future[Dict[str, Any]]":

        keys = []
        pending = []

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            resolved = unwrap_future(
                self.resolve_field(
                    parent_type, root, field_def, nodes, path + [key]
                )
            )

            keys.append(key)
            pending.append(resolved)

        return cast(
            "Future[Dict[str, Any]]",
            chain(  # type: ignore
                gather(pending), lambda values: dict(zip(keys, values))
            ),
        )

    def execute_fields_serially(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> "Future[Dict[str, Any]]":
        args = []
        done = []  # type: List[Tuple[str, Any]]

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            # Needed because closures. Might be a better way to do this without
            # resorting to inlining deferred_serial.
            args.append((key, field_def, nodes, path + [key]))

        final = Future()  # type: Future[Dict[str, Any]]

        def _next():
            try:
                k, f, n, p = args.pop(0)
            except IndexError:
                return final.set_result(dict(done))
            else:
                resolved = self.resolve_field(parent_type, root, f, n, p)

                def cb(f):
                    try:
                        r = f.result()
                    # pylint: disable = broad-except
                    except Exception as err:
                        final.set_exception(err)
                    else:
                        done.append((k, r))
                        _next()

                unwrap_future(resolved).add_done_callback(cb)

        _next()
        return final

    def resolve_field(
        self,
        parent_type: ObjectType,
        parent_value: Any,
        field_definition: Field,
        nodes: List[_ast.Field],
        path: ResponsePath,
    ) -> Any:
        resolver = self.get_field_resolver(
            field_definition.resolver or self._default_resolver
        )
        node = nodes[0]
        info = ResolveInfo(
            field_definition,
            path,
            parent_type,
            self.schema,
            self.variables,
            self.fragments,
            nodes,
        )

        try:
            coerced_args = self.argument_values(field_definition, node)
            resolved = resolver(
                parent_value, self.context_value, info, **coerced_args
            )
        except (CoercionError, ResolverError) as err:
            self.add_error(err, path, node)
            return None
        else:

            def on_error(err):
                self.add_error(err, path, node)
                return None

            return chain(
                resolved,
                lambda value: self.complete_value(
                    field_definition.type, nodes, path, value
                ),
                or_else=(ResolverError, on_error),
            )

    def complete_value(
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> Any:
        return chain(
            unwrap_future(resolved_value),
            functools.partial(super().complete_value, field_type, nodes, path),
        )

    def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        iterable: Any,
    ) -> "Future[List[Any]]":
        return gather(
            unwrap_future(
                self.complete_value(inner_type, nodes, path + [index], entry)
            )
            for index, entry in enumerate(iterable)
        )

    def handle_non_nullable_value(
        self, nodes: List[_ast.Field], path: ResponsePath, resolved_value: Any
    ) -> Any:
        return chain(
            unwrap_future(resolved_value),
            functools.partial(super().handle_non_nullable_value, nodes, path),
        )

    def get_field_resolver(self, base: Resolver) -> Resolver:
        try:
            return self._resolver_cache[base]
        except KeyError:
            resolver = functools.partial(self._inner.submit, base)
            self._resolver_cache[base] = resolver
            return resolver


def unwrap_future(maybe_future):
    outer = Future()  # type: ignore
    if isinstance(maybe_future, Future):

        def cb(f):
            try:
                r = f.result()
            except CancelledError:
                outer.cancel()
            # pylint: disable = broad-except
            except Exception as err:
                outer.set_exception(err)
            else:
                if isinstance(r, Future):
                    r.add_done_callback(cb)
                else:
                    outer.set_result(r)

        maybe_future.add_done_callback(cb)
    else:
        outer.set_result(maybe_future)

    return outer


def gather(source: Iterable[MaybeFuture[T]]) -> "Future[List[T]]":
    """ Concurrently collect multiple Futures. This is based on `asyncio.gather`.

    If all futures in the ``source`` sequence complete successfully, the result
    is an aggregate list of returned values. The order of result values
    corresponds to the order of the provided futures.

    The first raised exception is immediately propagated to the future returned
    from ``gather()``. Other futures in the provided sequence won’t be
    cancelled and will continue to run.

    Cancelling ``gather()`` will attempt to cancel the source futures
    that haven't already completed. If any Future from the ``source`` sequence
    is cancelled, it is treated as if it raised `CancelledError` – the
    ``gather()`` call is not cancelled in this case. This is to prevent the
    cancellation of one submitted Future to cause other futures to be
    cancelled.
    """
    done = 0
    pending = []  # type: List[Future[T]]
    result = []  # type: List[MaybeFuture[T]]

    source_values = list(source)
    target_count = len(source_values)

    # TODO: This is not used internally and is mostly here for completeness
    # but we could drop it.
    def handle_cancel(d: "Future[List[T]]") -> Any:
        if d.cancelled():
            for inner in pending:
                inner.cancel()

    def on_finish(d: "Future[T]") -> Any:
        nonlocal done
        done += 1

        try:
            d.result()
        # pylint: disable = broad-except
        except Exception as err:
            outer.set_exception(err)
            return

        if done == target_count:
            res = [v.result() if isinstance(v, Future) else v for v in result]
            outer.set_result(res)

    outer = Future()  # type: Future[List[T]]
    outer.add_done_callback(handle_cancel)

    for maybe_future in source_values:
        if not isinstance(maybe_future, Future):
            result.append(maybe_future)
            done += 1
        else:
            pending.append(maybe_future)
            result.append(maybe_future)
            maybe_future.add_done_callback(on_finish)

    if target_count == 0:
        outer.set_result([])
    elif not pending:
        outer.set_result(cast(List[T], result))

    return outer


def chain(
    source: MaybeFuture[T],
    map_result: Callable[[T], G],
    or_else: Optional[
        Tuple[Union[Type[E], Tuple[Type[E], ...]], Callable[[E], G]]
    ] = None,
) -> "Future[G]":
    """
    """
    target = Future()  # type: Future[G]

    if isinstance(source, Future):

        def on_finish(f: "Future[T]") -> None:
            try:
                res = map_result(f.result())
            except CancelledError:
                target.cancel()
            # pylint: disable = broad-except
            except Exception as err:
                if or_else is not None:
                    exc_type, cb = or_else
                    if isinstance(err, exc_type):
                        target.set_result(cb(err))  # type: ignore
                    else:
                        target.set_exception(err)
                else:
                    target.set_exception(err)
            else:
                target.set_result(res)

        source.add_done_callback(on_finish)
    else:
        try:
            res = map_result(source)
        # pylint: disable = broad-except
        except Exception as err:
            if or_else is not None:
                exc_type, cb = or_else
                if isinstance(err, exc_type):
                    target.set_result(cb(err))  # type: ignore
                else:
                    target.set_exception(err)
            else:
                target.set_exception(err)
        else:
            target.set_result(res)

    return target
