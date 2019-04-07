# -*- coding: utf-8 -*-

import asyncio
import functools as ft
from inspect import isawaitable, iscoroutinefunction
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from ..exc import CoercionError, ResolverError
from ..lang import ast as _ast
from ..schema import Field, GraphQLType, ObjectType
from .executor import Executor
from .middleware import apply_middlewares
from .wrappers import GroupedFields, ResolveInfo, ResponsePath

T = TypeVar("T")

Resolver = Callable[..., Any]
MaybeAwaitable = Union[Awaitable[T], T]


async def unwrap_coro(maybe_coro):
    if isawaitable(maybe_coro):
        return await unwrap_coro(await maybe_coro)

    return maybe_coro


class AsyncExecutor(Executor):
    @staticmethod
    async def map_value(value, func):
        return func(await unwrap_coro(value))

    async def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Dict[str, Any]:

        keys = []
        pending = []

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            resolved = self.resolve_field(
                parent_type, root, field_def, nodes, path + [key]
            )

            keys.append(key)
            pending.append(resolved)

        return dict(zip(keys, await asyncio.gather(*pending)))

    async def execute_fields_serially(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Dict[str, Any]:
        args = []
        done = []  # type: List[Tuple[str, Any]]

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            # Needed because closures. Might be a better way to do this without
            # resorting to inlining deferred_serial.
            args.append((key, field_def, nodes, path + [key]))

        async def _next() -> Dict[str, Any]:
            try:
                k, f, n, p = args.pop(0)
            except IndexError:
                return dict(done)
            else:
                resolved = await self.resolve_field(parent_type, root, f, n, p)
                done.append((k, resolved))
                return await _next()

        return await _next()

    async def resolve_field(
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
            resolved = await resolver(
                parent_value, self.context_value, info, **coerced_args
            )
        except (CoercionError, ResolverError) as err:
            self.add_error(err, path, node)
            return None
        else:
            return await self.complete_value(
                field_definition.type, nodes, path, resolved
            )

    async def complete_value(
        self,
        field_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        resolved_value: Any,
    ) -> Any:
        return await unwrap_coro(
            super().complete_value(
                field_type, nodes, path, await unwrap_coro(resolved_value)
            )
        )

    async def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        iterable: Any,
    ) -> List[Any]:
        return cast(
            List[Any],
            await asyncio.gather(
                *(
                    self.complete_value(
                        inner_type, nodes, path + [index], entry
                    )
                    for index, entry in enumerate(iterable)
                )
            ),
        )

    async def handle_non_nullable_value(
        self, nodes: List[_ast.Field], path: ResponsePath, resolved_value: Any
    ) -> Any:
        return super().handle_non_nullable_value(
            nodes, path, await unwrap_coro(resolved_value)
        )

    def get_field_resolver(self, base: Resolver) -> Resolver:
        try:
            return self._resolver_cache[base]
        except KeyError:
            if not iscoroutinefunction(base):

                async def resolver(*args, **kwargs):
                    return await asyncio.get_event_loop().run_in_executor(
                        None, ft.partial(base, *args, **kwargs)
                    )

            else:
                resolver = base

            resolver = apply_middlewares(resolver, self._middlewares)
            self._resolver_cache[base] = resolver
            return resolver
