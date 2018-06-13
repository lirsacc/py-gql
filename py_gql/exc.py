# -*- coding: utf-8 -*-
""" Library excceptions sink. """

from ._utils import cached_property
from ._string_utils import highlight_location, index_to_loc


class GraphQLError(Exception):
    """ Base GraphQL exception."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class GraphQLSyntaxError(GraphQLError):
    """  Syntax error in the GraphQL document."""

    __slots__ = "message", "position", "source"

    def __init__(self, msg, position, source):
        """
        :type msg: str
        :type position: int
        :type source: str
        """
        self.message = msg
        self.source = source
        self.position = position

    @cached_property
    def highlighted(self):
        return self.message + "\n" + highlight_location(self.source, self.position)

    def __str__(self):
        return self.highlighted

    def to_json(self):
        line, col = index_to_loc(self.source, self.position)
        return {"message": str(self), "locations": [{"line": line, "columne": col}]}


class InvalidCharacter(GraphQLSyntaxError):
    pass


class UnexpectedCharacter(GraphQLSyntaxError):
    pass


class UnexpectedEOF(GraphQLSyntaxError):
    def __init__(self, position, source):
        """
        :type position: int
        :type source: str
        """
        self.message = "Unexpected <EOF>"
        self.source = source
        self.position = position


class NonTerminatedString(GraphQLSyntaxError):
    pass


class InvalidEscapeSequence(GraphQLSyntaxError):
    pass


class UnexpectedToken(GraphQLSyntaxError):
    def __init__(self, msg, position, source):
        """
        :type msg: str
        :type position: int
        :type source: str
        """
        self.message = msg
        self.source = source
        self.position = position


class GraphQLLocatedError(GraphQLError):
    """ GraphQL exception that can be traced back to a specific node / set of nodes """

    __slots__ = "message", "nodes", "path"

    def __init__(self, message, nodes=None, path=None):
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

    __slots__ = "message", "nodes", "path", "value_path"

    def __init__(self, msg, node=None, path=None, value_path=None):
        super(CoercionError, self).__init__(msg, node, path)
        self.value_path = value_path

    def __str__(self):
        if self.value_path:
            return "%s at %s" % (self.message, self.value_path)
        return self.message


class ResolverError(GraphQLLocatedError):
    def __init__(self, msg, node=None, path=None, extensions=None):
        super(ResolverError, self).__init__(msg, node, path)
        self.extensions = extensions

    def to_json(self):
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
