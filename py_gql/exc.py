# -*- coding: utf-8 -*-
""" Library excceptions sink. """

from ._utils import cached_property


class GraphQLError(Exception):
    """ Base GraphQL exception."""

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return self.message


class GraphQLSyntaxError(GraphQLError):
    """  Syntax error in the GraphQL document."""
    def __init__(self, msg, position, source):
        """
        :type msg: str
        :type position: int
        :type source: py_gql.lang.source.Source
        """
        self.message = msg
        self.source = source
        self.position = position

    def __str__(self):
        from py_gql.lang.utils import highlight_location
        return (self.message + "\n" +
                highlight_location(self.source.body, self.position))

    __repr__ = __str__


class InvalidCharacter(GraphQLSyntaxError):
    pass


class UnexpectedCharacter(GraphQLSyntaxError):
    pass


class UnexpectedEOF(GraphQLSyntaxError):
    pass


class NonTerminatedString(GraphQLSyntaxError):
    pass


class InvalidEscapeSequence(GraphQLSyntaxError):
    pass


class UnexpectedToken(GraphQLSyntaxError):
    pass


class InvalidValue(GraphQLError, ValueError):
    pass


class UnknownEnumValue(InvalidValue):
    pass


class UnknownVariable(InvalidValue):
    pass


class ScalarSerializationError(GraphQLError):
    pass


class ScalarParsingError(InvalidValue):
    pass


class SchemaError(GraphQLError):
    pass


class UnknownType(SchemaError, KeyError):
    pass


class ExecutionError(GraphQLError):
    pass


class DocumentValidationError(ExecutionError):
    def __init__(self, errors):
        self.errors = errors


class VariableCoercionError(ExecutionError):
    def __init__(self, errors):
        assert errors
        self._errors = errors

    @cached_property
    def errors(self):
        return [str(err) if isinstance(err, Exception) else err
                for err in self._errors]

    def __str__(self):
        if len(self.errors) == 1:
            return str(self.errors[0])
        return str(self.errors)


class ResolverError(GraphQLError):
    def __init__(self, msg):
        self.message = msg


class CoercionError(GraphQLError):
    def __init__(self, msg, node=None, path=None):
        self.message = msg
        self.node = node
        self.path = path

    def __str__(self):
        if self.path:
            return '%s at %s' % (self.message, self.path)
        return self.message
