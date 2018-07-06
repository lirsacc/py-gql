# -*- coding: utf-8 -*-
""" All exceptions for this library are defined here.

Exception classes that expose a ``to_json`` method, such as
:class:`GraphQLLocatedError` or :class:`ResolverError` should be suitable for
exposing to consumers of your GraphQL API.
"""

from ._utils import cached_property
from ._string_utils import highlight_location, index_to_loc


class GraphQLError(Exception):
    """ Base GraphQL exception from which all other inherit """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class GraphQLSyntaxError(GraphQLError):
    """ Raised when the GraphQL document being parsed is invalid."""

    def __init__(self, msg, position, source):
        """
        :type msg: str
        :param msg: Text of the exception

        :type position: int
        :param position: 0-index position locating the syntax error

        :type source: str
        :param source: Source string from which the syntax error originated
        """
        self.message = msg
        self.source = source
        self.position = position

    @cached_property
    def highlighted(self):
        """ Message followed by a view of the source document pointing at the
        exact location of the error """
        if self.source is not None:
            return (
                self.message
                + " "
                + highlight_location(self.source, self.position)
            )
        return self.message

    def __str__(self):
        return self.highlighted

    def to_json(self):
        """ Convert the exception to a dictionnary that can be serialized to
        JSON and exposed in a graphql response

        :rtype: dict
        """
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
    def __init__(self, position, source):
        """
        :type position: int
        :param position: 0-index position locating the syntax error

        :type source: str
        :param source: Source string from which the syntax error originated
        """
        self.message = "Unexpected <EOF>"
        self.source = source
        self.position = position


class NonTerminatedString(GraphQLSyntaxError):
    pass


class InvalidEscapeSequence(GraphQLSyntaxError):
    pass


class UnexpectedToken(GraphQLSyntaxError):
    pass


class GraphQLLocatedError(GraphQLError):
    """ Raised when the error can be traced back to specific position in the
    document """

    def __init__(self, message, nodes=None, path=None):
        """
        :type message: str
        :param message: Text of the exception

        :type nodes: Optional[Union[List[py_gql.lang.ast.Node], py_gql.lang.ast.Node]]
        :param nodes: Node or nodes relevant to the exception

        :type path: py_gql.utilities.Path
        :param path: Location of the error in the execution chain
        """
        self.message = message
        self.path = path

        if not nodes:
            self.nodes = []
        elif not isinstance(nodes, list):
            self.nodes = [nodes]
        else:
            self.nodes = nodes[:]

    def __str__(self):
        return self.message

    def to_json(self):
        """ Convert the exception to a dictionnary that can be serialized to
        JSON and exposed in a graphql response

        :rtype: dict
        """
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
            ("path", list(self.path) if self.path is not None else None),
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


class UnknownType(SchemaError, KeyError):
    pass


class ValidationError(GraphQLLocatedError):
    pass


class ExecutionError(GraphQLError):
    def to_json(self):
        return {"message": str(self)}


class VariableCoercionError(GraphQLLocatedError):
    pass


class VariablesCoercionError(GraphQLError):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        if len(self.errors) == 1:
            return str(self.errors[0])
        return str(self.errors)


class CoercionError(GraphQLLocatedError):
    def __init__(self, msg, node=None, path=None, value_path=None):
        super(CoercionError, self).__init__(msg, node, path)
        self.value_path = value_path

    def __str__(self):
        if self.value_path:
            return "%s at %s" % (self.message, self.value_path)
        return self.message


class ResolverError(GraphQLLocatedError):
    """ Raised when an expected error happens during field resolution.

    Subclass or raise this exception directly for use in your own
    resolvers in order for them to report errors instead of crashing execution.
    If your exception exposes an ``extensions`` attribute it will be included
    in the serialized version without the need to override :meth:`to_json`.
    """

    def __init__(self, msg, node=None, path=None, extensions=None):
        """
        :type message: str
        :param message: Text of the exception

        :type node: Optional[py_gql.lang.ast.Node]
        :param node: Node relevant to the exception

        :type path: py_gql.utilities.Path
        :param path: Location of the error in the execution chain

        :type extensions: Optional[dict]
        :param extensions: Any custom error information you want in the response
        """
        super(ResolverError, self).__init__(msg, node, path)
        self.extensions = extensions

    def to_json(self):
        """ Convert the exception to a dictionnary that can be serialized to
        JSON and exposed in a graphql response

        :rtype: dict
        """
        d = super(ResolverError, self).to_json()
        if self.extensions:
            d["extensions"] = dict(self.extensions)
        return d


class SDLError(GraphQLLocatedError):
    pass


class TypeExtensionError(SDLError):
    pass


class SchemaDirectiveError(SDLError):
    pass
