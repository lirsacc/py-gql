# -*- coding: utf-8 -*-

import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from ..exc import GraphQLLocatedError, GraphQLResponseError
from ..lang import ast
from ..schema import Field, ObjectType, Schema
from ..schema.introspection import (
    SCHEMA_INTROSPECTION_FIELD,
    TYPE_INTROSPECTION_FIELD,
    TYPE_NAME_INTROSPECTION_FIELD,
)
from ..utilities import (
    coerce_argument_values,
    collect_fields,
    directive_arguments,
    selected_fields,
)
from .default_resolver import default_resolver as _default_resolver
from .runtime import Runtime

_UNSET = object()

Resolver = Callable[..., Any]
ResponsePath = List[Union[str, int]]
GroupedFields = Dict[str, List[ast.Field]]


class ResolutionContext:
    """Information about the current resolution."""

    __slots__ = (
        "schema",
        "document",
        "variables",
        "fragments",
        "context_value",
        "_grouped_fields",
        "_fragment_type_applies",
        "_field_defs",
        "_argument_values",
        "_default_resolver",
        "_resolver_cache",
        "_middlewares",
        "_disable_introspection",
        "_errors",
    )

    def __init__(
        self,
        schema: Schema,
        document: ast.Document,
        variables: Dict[str, Any],
        context_value: Any,
        *,
        disable_introspection: bool = False,
        default_resolver: Optional[Resolver] = None,
        middlewares: Optional[Sequence[Callable[..., Any]]] = None
    ):
        #: ~py_gql.schema.Schema: Current schema.
        self.schema = schema
        #: ~py_gql.lang.ast.Document: Parsed document.
        self.document = document
        #: Dict[str, Any]: Coerced variables
        self.variables = variables
        #: Context value
        self.context_value = context_value
        #: Dict[str, ~ast.FragmentDefinition]: Document fragments
        self.fragments = document.fragments

        self._default_resolver = default_resolver or _default_resolver
        self._disable_introspection = disable_introspection
        self._middlewares = middlewares or []

        self._errors = []  # type: List[GraphQLResponseError]

        # Caches
        self._grouped_fields = (
            {}
        )  # type: Dict[Tuple[str, Tuple[ast.Selection, ...]], GroupedFields]
        self._fragment_type_applies = (
            {}
        )  # type: Dict[Tuple[str, ast.Type], bool]
        self._field_defs = {}  # type: Dict[Tuple[str, str], Optional[Field]]
        self._argument_values = (
            {}
        )  # type: Dict[Tuple[Field, ast.Field], Dict[str, Any]]
        self._resolver_cache = {}  # type: Dict[Resolver, Resolver]

    def add_error(
        self,
        err: Union[GraphQLLocatedError],
        path: Optional[ResponsePath] = None,
        node: Optional[ast.Node] = None,
    ) -> None:
        """Register an error during the current execution."""
        if node:
            if not err.nodes:
                err.nodes = [node]
        err.path = path if path is not None else err.path
        self._errors.append(err)

    @property
    def errors(self) -> List[GraphQLResponseError]:
        """All field errors collected during query execution."""
        return self._errors[:]

    def clear_errors(self) -> None:
        """Clear any collected error from the current executor instance."""
        self._errors[:] = []

    def collect_fields(
        self,
        parent_type: ObjectType,
        selections: Sequence[ast.Selection],
        visited_fragments: Optional[Set[str]] = None,
    ) -> GroupedFields:
        cache_key = parent_type.name, tuple(selections)
        try:
            return self._grouped_fields[cache_key]
        except KeyError:
            self._grouped_fields[cache_key] = grouped_fields = collect_fields(
                self.schema,
                parent_type,
                selections,
                self.fragments,
                self.variables,
            )

            self._grouped_fields[cache_key] = grouped_fields
            return grouped_fields

    def field_definition(
        self, parent_type: ObjectType, name: str
    ) -> Optional[Field]:
        key = parent_type.name, name
        cache = self._field_defs

        try:
            return cache[key]
        except KeyError:
            if name in ("__schema", "__type", "__typename"):
                is_query_type = self.schema.query_type is parent_type
                if self._disable_introspection:
                    return None
                elif name == "__schema" and is_query_type:
                    field_def = (
                        SCHEMA_INTROSPECTION_FIELD
                    )  # type: Optional[Field]
                elif name == "__type" and is_query_type:
                    field_def = TYPE_INTROSPECTION_FIELD
                elif name == "__typename":
                    field_def = TYPE_NAME_INTROSPECTION_FIELD
            else:
                field_def = parent_type.field_map.get(name, None)

            cache[key] = field_def
            return field_def

    def argument_values(
        self, field_definition: Field, node: ast.Field
    ) -> Dict[str, Any]:
        cache_key = field_definition, node
        try:
            return self._argument_values[cache_key]
        except KeyError:
            av = self._argument_values[cache_key] = coerce_argument_values(
                field_definition, node, self.variables
            )
            return av


class ResolveInfo:
    """Expose information about the field currently being resolved.

    This is the 3rd positional argument provided to resolver functions and is
    constructed internally during query execution.
    """

    __slots__ = (
        "field_definition",
        "path",
        "parent_type",
        "nodes",
        "runtime",
        "_context",
        "_directive_arguments",
    )

    def __init__(
        self,
        field_definition: Field,
        path: ResponsePath,
        parent_type: ObjectType,
        nodes: List[ast.Field],
        runtime: Runtime,
        context: ResolutionContext,
    ):
        #: ~py_gql.schema.Field: Root field being resolved.
        self.field_definition = field_definition
        #: ~py_gql.execution.ResponsePath: Current traversal path through the query.
        self.path = path
        #: ~py_gql.schema.ObjectType: Type from which the field is being resolved.
        self.parent_type = parent_type
        #: ~py_gql.lang.ast.Field: AST nodes extracted from the document.
        self.nodes = nodes
        #: ~py_gq.execution.runtime.Runtime:Current runtime.
        self.runtime = runtime

        self._context = context
        self._directive_arguments = (
            {}
        )  # type: Dict[str, Optional[Dict[str, Any]]]

    @property
    def schema(self) -> Schema:
        """Current schema."""
        return self._context.schema

    @property
    def variables(self) -> Dict[str, Any]:
        """Coerced variables."""
        return self._context.variables

    @property
    def fragments(self) -> Dict[str, ast.FragmentDefinition]:
        """Document fragments."""
        return self._context.fragments

    def get_directive_arguments(self, name: str) -> Optional[Dict[str, Any]]:
        """Extract arguments for a given directive on the current field.

        Warning:
            This method assumes the document has been validated and the
            definition exists and is valid at this position.

        Args:
            name: The name of the directive to extract.

        Returns:
            ``None`` if the directive is not present on the current field and a
            dictionnary of coerced arguments otherwise.
        """
        try:
            return self._directive_arguments[name]
        except KeyError:
            args = self._directive_arguments[name] = directive_arguments(
                self._context.schema.directives[name],
                self.nodes[0],
                self._context.variables,
            )
            return args

    def selected_fields(
        self, *, maxdepth: int = 1, pattern: Optional[str] = None
    ) -> List[str]:
        """Extract the list of fields selected by the field currently being
        resolved.

        Refer to :func:`~py_gql.utilities.selected_fields` for documentation.
        """
        return selected_fields(
            self.nodes[0],
            fragments=self._context.fragments,
            variables=self._context.variables,
            maxdepth=maxdepth,
            pattern=pattern,
        )


class GraphQLExtension:
    """ Encode a GraphQL response extension.

    Use in conjonction with :meth:`GraphQLResult.add_extension` to encode the
    response alongside an execution result.
    """

    def payload(self):
        """
        Returns:
            Any: Extension payload; **must** be JSON serialisable.
        """
        raise NotImplementedError()

    @property
    def name(self) -> str:
        """
        Returns:
            Name of the extension used as the key in the response.
        """
        raise NotImplementedError()


class GraphQLResult:
    """
    Wrapper encoding the behaviour described in the `Response
    <http://facebook.github.io/graphql/June2018/#sec-Response>`_ part of the
    specification.

    Args:
        data (Optional[Dict[`str`, `Any`]]):
            The data part of the response.

        errors (Optional[Sequence[`GraphQLResponseError`]]):
            The errors part of the response. All errors will be included in the
            response using :meth:`~py_gql.exc.GraphQLResponseError.to_dict`.
    """

    __slots__ = ("data", "errors", "extensions", "_known_extensions")

    def __init__(
        self,
        data: Optional[Any] = _UNSET,
        errors: Optional[Sequence[GraphQLResponseError]] = None,
    ):
        self.data = data  # type: Any
        self.errors = (
            list(errors) if errors is not None else []
        )  # type: List[GraphQLResponseError]
        self.extensions = {}  # type: Dict[str, GraphQLExtension]

    def __bool__(self) -> bool:
        return not self.errors

    def __iter__(self):
        return iter((self.data, self.errors))

    def add_extension(self, ext):
        """ Add an extensions to the result.

        Args:
            Extension instance

        Raises:
            ValueError: Extension with the same name has already been added
        """
        if ext.name in self.extensions:
            raise ValueError('Duplicate extension "%s"' % ext.name)
        self.extensions[ext.name] = ext

    def response(self) -> Dict[str, Any]:
        """ Generate an ordered response dict. """
        d = {}
        if self.errors:
            d["errors"] = [error.to_dict() for error in self.errors]
        if self.data is not _UNSET:
            d["data"] = self.data
        if self.extensions:
            d["extensions"] = {  # type: ignore
                e.name: e.payload() for e in self.extensions.values()
            }
        return d

    def json(self, **kw: Any) -> str:
        """ Encode response as JSON using the standard lib ``json`` module.

        Args:
            **kw: Keyword args passed to to ``json.dumps``
        """
        return json.dumps(self.response(), **kw)
