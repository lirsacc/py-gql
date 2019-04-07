# -*- coding: utf-8 -*-

import json
from typing import Any, Dict, List, Optional, Sequence, Set, Union

from ..exc import GraphQLResponseError
from ..lang import ast as _ast
from ..schema import Field, ObjectType, Schema

_UNSET = object()

ResponsePath = List[Union[str, int]]
GroupedFields = Dict[str, List[_ast.Field]]


class ResolveInfo:
    __slots__ = (
        "field_definition",
        "path",
        "parent_type",
        "schema",
        "variables",
        "fragments",
        "nodes",
    )

    def __init__(
        self,
        field_definition: Field,
        path: ResponsePath,
        parent_type: ObjectType,
        schema: Schema,
        variables: Dict[str, Any],
        fragments: Dict[str, _ast.FragmentDefinition],
        nodes: List[_ast.Field],
    ):
        self.field_definition = field_definition
        self.path = path
        self.parent_type = parent_type
        self.schema = schema
        self.variables = variables
        self.fragments = fragments
        self.nodes = nodes


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
            response using :meth:`~GraphQLResponseError.to_dict`.
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
        self.extensions = []  # type: List[GraphQLExtension]
        self._known_extensions = set()  # type: Set[str]

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
        if ext.name in self._known_extensions:
            raise ValueError('Duplicate extension "%s"' % ext.name)
        self.extensions.append(ext)
        self._known_extensions.add(ext.name)

    def response(self) -> Dict[str, Any]:
        """ Generate an ordered response dict. """
        d = {}
        if self.errors:
            d["errors"] = [error.to_dict() for error in self.errors]
        if self.data is not _UNSET:
            d["data"] = self.data
        if self.extensions:
            d["extensions"] = {  # type: ignore
                e.name: e.payload() for e in self.extensions
            }
        return d

    def json(self, **kw: Any) -> str:
        """ Encode response as JSON using the standard lib ``json`` module.

        Args:
            **kw: Keyword args passed to to ``json.dumps``
        """
        return json.dumps(self.response(), **kw)
