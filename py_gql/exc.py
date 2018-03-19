# -*- coding: utf-8 -*-
""" Library excceptions sink. """


class GraphQLError(Exception):
    """ Base Exception for the library """
    pass


class GraphQLSyntaxError(GraphQLError):
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
