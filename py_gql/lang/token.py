# -*- coding: utf-8 -*-
""" """


class Token(object):
    """ Token class used by ``py_gql.lang.lexer.Lexer`` to represent
    the source elements that make up a GraphQL document.
    """

    __slots__ = ('start', 'end', 'value', '__kind__')

    def __init__(self, start, end, value=None):
        """
        :type start: int
        :type end: int
        :type value: str
        """
        self.start = start
        self.end = end
        self.value = value

    def __repr__(self):
        return ('<Token.%s: value=`%s` at (%d, %d)>'
                % (self.__class__.__name__, self, self.start, self.end))

    def __str__(self):
        return '%s' % self.value

    def __eq__(self, rhs):
        return (self.__class__ is rhs.__class__ and
                self.value == rhs.value and
                self.start == rhs.start and
                self.end == rhs.end)


class SOF(Token):
    def __str__(self):
        return '<SOF>'


class EOF(Token):
    def __str__(self):
        return '<EOF>'


class CharToken(Token):
    def __str__(self):
        return self.__char__


class ExclamationMark(CharToken):
    __char__ = '!'


class Dollar(CharToken):
    __char__ = '$'


class ParenOpen(CharToken):
    __char__ = '('


class ParenClose(CharToken):
    __char__ = ')'


class BracketOpen(CharToken):
    __char__ = '['


class BracketClose(CharToken):
    __char__ = ']'


class CurlyOpen(CharToken):
    __char__ = '{'


class CurlyClose(CharToken):
    __char__ = '}'


class Colon(CharToken):
    __char__ = ':'


class Equals(CharToken):
    __char__ = '='


class At(CharToken):
    __char__ = '@'


class Pipe(CharToken):
    __char__ = '|'


class Ampersand(CharToken):
    __char__ = '&'


class Ellipsis(Token):
    def __str__(self):
        return '...'


class Integer(Token):
    pass


class Float(Token):
    pass


class Name(Token):
    pass


class String(Token):
    pass


class BlockString(Token):
    pass
