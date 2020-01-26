# -*- coding: utf-8 -*-
"""This module implements all the exceptions exposed by this library."""

from typing import Any, Dict, List, Mapping, Optional, Sequence

from ._string_utils import (
    ResponsePath,
    highlight_location,
    index_to_loc,
    stringify_path,
)
from .lang import ast as _ast


class GraphQLError(Exception):
    """
    Base GraphQL exception from which all other inherit. You should prefer
    using one of its subclasses most of the time.
    """

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class GraphQLResponseError(GraphQLError):
    """
    Implementors of this are suitable for usage in GraphQL responses and
    exposing to end users.

    See `the relevant part of the spec
    <https://graphql.github.io/graphql-spec/June2018/#sec-Errors>`_ for more
    information on response errors.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionnary that can be serialized to
        JSON and exposed in a GraphQL response.

        Returns:
            JSON serializable representation of the error.
        """
        raise NotImplementedError()


class GraphQLSyntaxError(GraphQLResponseError):
    """
    Syntax error while parsing a GraphQL document (query or schema definition).

    Args:
        message: Explanatory message
        position: 0-indexed position locating the syntax error
        source: Source string from which the syntax error originated

    Attributes:
        message (str): Explanatory message
        position (int): 0-indexed position locating the syntax error
        source (str): Source string from which the syntax error originated
    """

    def __init__(self, message: str, position: int, source: str):
        super().__init__(message)
        self.source = source
        self.position = position
        self._highlighted = None  # type: Optional[str]

    @property
    def highlighted(self) -> str:
        """
        str: Message followed by a view of the source document pointing at
        the exact location of the error.
        """
        if self._highlighted is not None:
            return self._highlighted

        highlight = highlight_location(self.source, self.position)
        self._highlighted = "%s %s" % (self.message, highlight)
        return self._highlighted

    def __str__(self) -> str:
        return self.highlighted

    def to_dict(self) -> Dict[str, Any]:
        line, col = index_to_loc(self.source, self.position)
        return {
            "message": str(self),
            "locations": [{"line": line, "columne": col}],
        }


class InvalidCharacter(GraphQLSyntaxError):
    pass


class UnexpectedCharacter(GraphQLSyntaxError):
    pass


class UnexpectedEOF(GraphQLSyntaxError):
    """
    Args:
        position: 0-indexed position locating the syntax error
        source: Source string from which the syntax error originated
    """

    def __init__(self, position: int, source: str):
        super().__init__("Unexpected <EOF>", position, source)


class NonTerminatedString(GraphQLSyntaxError):
    pass


class InvalidEscapeSequence(GraphQLSyntaxError):
    pass


class UnexpectedToken(GraphQLSyntaxError):
    pass


class GraphQLLocatedError(GraphQLResponseError):
    """
    Response error that can be traced back to specific position(s) and
    parse node(s) in the source document.

    Args:
        message: Explanatory message
        nodes: Nodes relevant to the exception
        path: Location of the error during execution

    Attributes:
        message (str): Explanatory message
        nodes (List[py_gql.lang.ast.Node]): Nodes relevant to the exception
        path (Optional[Sequence[Union[int, str]]]):
            Location of the error during execution
    """

    def __init__(
        self,
        message: str,
        nodes: Optional[Sequence[_ast.Node]] = None,
        path: Optional[ResponsePath] = None,
    ):
        super().__init__(message)
        self.path = path
        self.nodes = list(nodes[:]) if nodes else []  # type: List[_ast.Node]

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        kv = (
            ("message", str(self)),
            (
                "locations",
                [
                    {"line": line, "column": col}
                    for line, col in (
                        index_to_loc(node.source, node.loc[0])
                        for node in self.nodes
                        if node.loc and node.source
                    )
                ],
            ),
            ("path", self.path if self.path is not None else None),
        )
        return {k: v for k, v in kv if v}


class InvalidValue(GraphQLLocatedError, ValueError):
    pass


class UnknownEnumValue(InvalidValue):
    pass


class UnknownVariable(InvalidValue):
    pass


class ScalarSerializationError(GraphQLError, ValueError):
    pass


class ScalarParsingError(InvalidValue):
    pass


class SchemaError(GraphQLError):
    pass


class SchemaValidationError(SchemaError):
    def __init__(self, errors: Sequence[SchemaError]):
        super().__init__("Invalid schema: %d errors" % len(errors))
        self.errors = errors

    def __str__(self) -> str:
        if len(self.errors) == 1:
            return str(self.errors[0])
        return ",\n".join([str(err) for err in self.errors])


class UnknownType(SchemaError, KeyError):
    pass


class ValidationError(GraphQLLocatedError):
    pass


class ExecutionError(GraphQLResponseError):
    """
    Error that prevented execution of a query.

    Args:
        message: Explanatory message

    Attributes:
        message (str): Explanatory message
    """

    def to_dict(self) -> Dict[str, Any]:
        return {"message": str(self)}


class InvalidOperationError(ExecutionError):
    pass


class VariableCoercionError(GraphQLLocatedError):
    pass


class VariablesCoercionError(GraphQLError):
    """
    Collection of multiple :class:`VariableCoercionError`.

    Args:
        errors: Wrapped errors

    Attributes:
        errors (Sequence[VariableCoercionError]): Wrapped errors
    """

    def __init__(self, errors: Sequence[VariableCoercionError]):
        super().__init__("%d errors" % len(errors))
        self.errors = errors

    def __str__(self) -> str:
        if len(self.errors) == 1:
            return str(self.errors[0])
        return ",\n".join([str(err) for err in self.errors])


class CoercionError(GraphQLLocatedError):
    def __init__(self, message, node=None, path=None, value_path=None):
        super().__init__(message, node, path)
        self.value_path = value_path

    def __str__(self):
        if self.value_path:
            return "%s at %s" % (self.message, stringify_path(self.value_path))
        return self.message


class MultiCoercionError(CoercionError):
    """
    Collection of multiple :class:`CoercionError`.

    Args:
        errors: Wrapped errors

    Attributes:
        errors (Sequence[CoercionError]): Wrapped errors
    """

    def __init__(self, errors: Sequence[CoercionError]):
        super().__init__("%d errors" % len(errors))
        self.errors = errors

    def __str__(self):
        if len(self.errors) == 1:
            return str(self.errors[0])
        return ",\n".join([str(err) for err in self.errors])


class ResolverError(GraphQLLocatedError):
    """
    Raised when an expected error happens during field resolution.

    Subclass or raise this exception directly for use in your own
    resolvers in order for them to report errors instead of crashing the
    query execution.

    If your exception exposes an ``extensions`` attribute it will be included
    in the serialized version without the need to override :meth:`to_dict`.

    Args:
        message: Explanatory message
        nodes: Node or nodes relevant to the exception
        path: Location of the error during execution
        extensions: Error extensions

    Attributes:
        message (str): Explanatory message
        nodes (List[py_gql.lang.ast.Node]): Node or nodes relevant to the exception
        path (Optional[Sequence[Union[int, str]]]):
            Location of the error during execution
        extensions (Optional[Mapping[str, Any]]): Error extensions

    """

    def __init__(
        self,
        message: str,
        nodes: Optional[Sequence[_ast.Node]] = None,
        path: Optional[ResponsePath] = None,
        extensions: Optional[Mapping[str, Any]] = None,
    ):
        super().__init__(message, nodes, path)
        self.extensions = extensions

    def to_dict(self) -> Dict[str, Any]:
        dict_ = super().to_dict()
        if self.extensions:
            dict_["extensions"] = dict(self.extensions)
        return dict_


class SDLError(GraphQLLocatedError):
    """
    Error that occured when parsing and / or applying a schema definition
    document (SDL).
    """


class ExtensionError(SDLError):
    """
    Error that occured when applying a schema or type extension node
    to an existing schema.
    """


class SchemaDirectiveError(SDLError):
    """
    Error that occured when applying schema directives.
    """
