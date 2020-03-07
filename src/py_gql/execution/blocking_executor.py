# -*- coding: utf-8 -*-

from typing import Any, Callable, Dict, List

from .._utils import OrderedDict
from ..exc import CoercionError, ResolverError
from ..lang import ast as _ast
from ..schema import Field, GraphQLType, ObjectType
from .executor import Executor
from .wrappers import GroupedFields, ResolveInfo, ResponsePath

Resolver = Callable[..., Any]


class BlockingExecutor(Executor):
    """
    Executor implementation optimised for synchronous, blocking execution.

    Warning:
        This is aimed to be used internally to optimise the blocking execution
        case while keeping the base `Executor` class as generic as possible by
        side-stepping some of the operations that need to happen when working
        with arbitrary wrapper types such as Awaitable. As a result this
        overrides much more of the base class than should be necessary to
        implement custom executors and should not be taken as an example.
    """

    def execute_fields(
        self,
        parent_type: ObjectType,
        root: Any,
        path: ResponsePath,
        fields: GroupedFields,
    ) -> Dict[str, Any]:
        result = OrderedDict()  # type: Dict[str, Any]

        for key, field_def, nodes in self._iterate_fields(parent_type, fields):
            result[key] = self.resolve_field(
                parent_type, root, field_def, nodes, path + [key]
            )

        return result

    execute_fields_serially = execute_fields

    def resolve_field(
        self,
        parent_type: ObjectType,
        parent_value: Any,
        field_definition: Field,
        nodes: List[_ast.Field],
        path: ResponsePath,
    ) -> Any:
        resolver = self.field_resolver(parent_type, field_definition)
        node = nodes[0]
        info = ResolveInfo(
            field_definition, path, parent_type, nodes, self.runtime, self,
        )

        self.instrumentation.on_field_start(
            parent_value, self.context_value, info
        )

        try:
            coerced_args = self.argument_values(field_definition, node)
            resolved = resolver(
                parent_value, self.context_value, info, **coerced_args
            )
        except (CoercionError, ResolverError) as err:
            self.add_error(err, path, node)
            return None
        finally:
            self.instrumentation.on_field_end(
                parent_value, self.context_value, info
            )

        return self.complete_value(
            field_definition.type, nodes, path, info, resolved
        )

    def complete_list_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        info: ResolveInfo,
        resolved_value: Any,
    ) -> List[Any]:
        return [
            self.complete_value(inner_type, nodes, path + [index], info, entry)
            for index, entry in enumerate(resolved_value)
        ]

    def complete_non_nullable_value(
        self,
        inner_type: GraphQLType,
        nodes: List[_ast.Field],
        path: ResponsePath,
        info: ResolveInfo,
        resolved_value: Any,
    ) -> Any:
        return self._handle_non_nullable_value(
            nodes,
            path,
            self.complete_value(inner_type, nodes, path, info, resolved_value),
        )
