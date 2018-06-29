# -*- coding: utf-8 -*-

# REVIEW: Evaluate doing this with a parser generator, I guess we could likely
# achieve less code (sure) and similar to better performance (to be proven).
# This would also require as good error messages which eliminates some parser
# generators with bad disambiguation.

import functools as ft

from . import ast as _ast, token as _token
from ..exc import UnexpectedEOF, UnexpectedToken
from .lexer import Lexer
from .token import Token

DIRECTIVE_LOCATIONS = frozenset(
    [
        "QUERY",
        "MUTATION",
        "SUBSCRIPTION",
        "FIELD",
        "FRAGMENT_DEFINITION",
        "FRAGMENT_SPREAD",
        "INLINE_FRAGMENT",
        # Type System Definitions
        "SCHEMA",
        "SCALAR",
        "OBJECT",
        "FIELD_DEFINITION",
        "ARGUMENT_DEFINITION",
        "INTERFACE",
        "UNION",
        "ENUM",
        "ENUM_VALUE",
        "INPUT_OBJECT",
        "INPUT_FIELD_DEFINITION",
    ]
)


EXECUTABLE_DEFINITIONS = frozenset(
    ["query", "mutation", "subscription", "fragment"]
)


SCHEMA_DEFINITIONS = frozenset(
    [
        "schema",
        "scalar",
        "type",
        "interface",
        "union",
        "enum",
        "input",
        "extend",
        "directive",
    ]
)

OPERATION_TYPES = frozenset(["query", "mutation", "subscription"])


def _unexpected_token(msg_or_token, *args):
    if isinstance(msg_or_token, Token):
        msg_or_token = "Unexpected %s" % msg_or_token
    return UnexpectedToken(msg_or_token, *args)


def parse(source, **kwargs):
    """ Parse a string as a GraphQL Document.

    :type source: Union[str, bytes]
    :param source: The GraphQL document to parse

    :param kwargs: Remaining keyword arguments to :class:`Parser`

    :rtype: py_gql.lang.ast.Document
    :returns: Parsed document

    :Raises:

        :class:`py_gql.exc.GraphQLSyntaxError` if a syntax error is encountered.

    """
    return Parser(source, **kwargs).parse_document()


def parse_value(source, **kwargs):
    """ Parse a string as a single GraphQL value.

    This is useful within tools that operate upon GraphQL values (eg. ``[42]``) directly
    and in isolation of complete GraphQL documents. Consider providing the results
    to the utility functions :func:`py_gql.utilities.untyped_value_from_ast` and
    :func:`py_gql.utilities.value_from_ast`.

    :type source: Union[str, bytes]
    :param source: The GraphQL document to parse

    :param kwargs: Remaining keyword arguments to :class:`Parser`

    :rtype: py_gql.lang.ast.Value
    :returns: Parsed node

    :Raises:

        :class:`py_gql.exc.GraphQLSyntaxError` if a syntax error is encountered.
    """
    parser = Parser(source, **kwargs)
    parser.expect(_token.SOF)
    value = parser.parse_value_literal(False)
    parser.expect(_token.EOF)
    return value


def parse_type(source, **kwargs):
    """ Parse a string as a single GraphQL type.

    This is useful within tools that operate upon GraphQL types (eg. ``[Int!]``)
    directly and in isolation of complete GraphQL documents such as when building a
    schema from the SDL or stitching schemas together.

    :type source: Union[str, bytes]
    :param source: The GraphQL document to parse

    :param kwargs: Remaining keyword arguments to :class:`Parser`

    :rtype: py_gql.lang.ast.Type
    :returns: Parsed node

    :Raises:

        :class:`py_gql.exc.GraphQLSyntaxError` if a syntax error is encountered.
    """
    parser = Parser(source, **kwargs)
    parser.expect(_token.SOF)
    value = parser.parse_type_reference()
    parser.expect(_token.EOF)
    return value


def _is(token, *kinds):
    """ Check if a token is of certain kind(s). """
    # [TODO] This does type comparison for token type detection, could it be
    # faster by checking a string ? I assume so, but then the gain might be
    # negligible, still worth considering at some point.
    # Follow-up with a timeit microbenchmark pointed to ``t.__class__ is cls``
    # being the fastest exact type comparison method in that case.
    t = type(token)
    return any((t == kind for kind in kinds))


class Parser(object):
    """ GraphQL syntax parser.

    Call :meth:`parse_document` to parse a GraphQL document.

    All ``parse_*`` methods will raise :class:`py_gql.exc.GraphQLSyntaxError` if a
    syntax error is encountered.
    """

    def __init__(
        self,
        source,
        no_location=False,
        allow_type_system=True,
        allow_legacy_sdl_empty_fields=False,
        allow_legacy_sdl_implements_interfaces=False,
        experimental_fragment_variables=False,
    ):
        """
        :type source: Union[str, bytes]
        :param source: The GraphQL document to parse

        :type no_location: `bool`
        :param no_location:
            By default, the parser creates AST nodes that know the location
            in the source that they correspond to. This configuration flag
            disables that behavior for performance or testing reasons.

        :type allow_type_system: bool
        :param allow_type_system:
            By default, the parser will accept schema definition nodes, when
            only executing GraphQL queries setting this to ``False`` can save
            operations and remove the need for some later validation.

        :type allow_legacy_sdl_empty_fields: bool
        :param allow_legacy_sdl_empty_fields:
            If enabled, the parser will parse empty fields sets in the Schema
            Definition Language. Otherwise, the parser will follow the current
            specification.

            .. warning::

                This option is provided to ease adoption of the final SDL
                specification and will be removed in a future major release.

        :type allow_legacy_sdl_implements_interfaces: bool
        :param allow_legacy_sdl_implements_interfaces:
            If enabled, the parser will parse implemented interfaces with no
            `&` character between each interface. Otherwise, the parser will
            follow the current specification.

            .. warning::

                This option is provided to ease adoption of the final SDL
                specification and will be removed in a future major release.

        :type experimental_fragment_variables: bool
        :param experimental_fragment_variables:
            If enabled, the parser will understand and parse variable
            definitions contained in a fragment definition. They'll be
            represented in the `variable_definitions` field of the
            FragmentDefinition.

            The syntax is identical to normal, query-defined variables.
            For example:

            .. code-block:: graphql

                fragment A($var: Boolean = false) on T  {
                    ...
                }

            .. warning::

                This feature is experimental and may change or be removed
                in the future.
        """
        self.lexer = Lexer(source)
        self.source = self.lexer._source

        self.no_location = no_location
        self.allow_type_system = allow_type_system
        self.allow_legacy_sdl_empty_fields = allow_legacy_sdl_empty_fields
        self.allow_legacy_sdl_implements_interfaces = (
            allow_legacy_sdl_implements_interfaces
        )
        self.experimental_fragment_variables = experimental_fragment_variables

        # Keep track of the current parsing window + last seen token internally
        # as the Lexer iterator itself doesn't handle backtracking or lookahead
        # semantics and can only be consumed once.
        self._window = None
        self._last = None

    def _advance_window(self):
        """ Advance the parsing window by one element.
        Raise ``py_gql.exc.UnexpectedEOF`` error when trying to advance past
        EOF when parsing window is empty.
        """
        if self._window is None:
            self._window = []

        try:
            self._window.append(next(self.lexer))
        except StopIteration:
            if len(self._window) == 0:
                raise UnexpectedEOF(self.lexer._len, self.lexer._source)

    def peek(self, count=1):
        """ Look at a token ahead of the current position without advancing the parsing
        position.

        :type count: int
        :param count: How many tokens to look ahead.

        :rtype: py_gql.lang.token.Token
        :returns: Token a ``current position + count``

        :Raises:
            :class:`py_gql.exc.UnexpectedEOF` if there is not enough tokens left in the
            lexer.
        """
        delta = 1 if self._window is None else (count - len(self._window))
        for _ in range(delta):
            self._advance_window()
        if len(self._window) >= count:
            return self._window[count - 1]
        return None

    def advance(self):
        """ Move parsing window forward and return the next token.

        :rtype: py_gql.lang.token.Token

        :Raises:
            :class:`py_gql.exc.UnexpectedEOF` if there is not enough tokens left in the
            lexer.
        """
        self._advance_window()
        self._last = self._window.pop(0)
        return self._last

    def expect(self, kind):
        """ Advance the parser and check that the next token is of the
        given token class otherwise raises :class:`py_gql.exc.UnexpectedToken`.

        :type kind: type
        :param kind: A subclass of ``py_gql.lang.token.Token``

        :rtype: py_gql.lang.token.Token
        """
        next_token = self.peek()
        if _is(next_token, kind):
            return self.advance()

        raise _unexpected_token(
            "Expected %s but found %s" % (kind.__name__, next_token),
            next_token.start,
            self.lexer._source,
        )

    def expect_keyword(self, keyword):
        """ Advance the parser and check that the next token is a Name with the given
        valueof otherwise raises :class:`py_gql.exc.UnexpectedToken`.

        :type keyword: str
        :param keyword: Expectd keyword

        :rtype: py_gql.lang.token.Name
        """
        next_token = self.peek()
        if _is(next_token, _token.Name) and next_token.value == keyword:
            return self.advance()

        raise _unexpected_token(
            'Expected "%s" but found %s' % (keyword, next_token),
            next_token.start,
            self.lexer._source,
        )

    def skip(self, kind):
        """ If the next token is of the given kind, return ``True`` after
        advancing the parser. Otherwise, do not change the parser state and
        return ``False``.

        :type kind: type
        :param kind: A subclass of ``py_gql.lang.token.Token``

        :rtype: bool
        """
        if _is(self.peek(), kind):
            self.advance()
            return True
        return False

    def many(self, open_kind, parse_fn, close_kind):
        """ Return a non-empty list of parse nodes, determined by
        ``parse_fn`` which are surrounded by ``open_kind`` and ``close_kind`` tokens.
        Advances the parser to the next lex token after the closing token.

        :type open_kind: type
        :param open_kind: A subclass of ``py_gql.lang.token.Token``

        :type parse_fn: callable
        :param parse_fn:
            Function to call for every item, should be a method of :class:`Parser`

        :type close_kind: type
        :param close_kind: A subclass of ``py_gql.lang.token.Token``

        :rtype: List[py_gql.lang.ast.Node]

        :Raises:

            :class:`py_gql.exc.UnexpectedToken` if opening, entry or closing token do
            not match.
        """
        self.expect(open_kind)
        nodes = []
        while True:
            nodes.append(parse_fn())
            if self.skip(close_kind):
                break
        return nodes

    def any(self, open_kind, parse_fn, close_kind):
        """ Return a non-empty list of parse nodes, determined by
        ``parse_fn`` which are surrounded by ``open_kind`` and ``close_kind`` tokens.
        Advances the parser to the next lex token after the closing token.

        :type open_kind: type
        :param open_kind: A subclass of ``py_gql.lang.token.Token``

        :type parse_fn: callable
        :param parse_fn:
            Function to call for every item, should be a method of :class:`Parser`

        :type close_kind: type
        :param close_kind: A subclass of ``py_gql.lang.token.Token``

        :rtype: List[py_gql.lang.ast.Node]

        :Raises:

            :class:`py_gql.exc.UnexpectedToken` if opening, entry or closing token do
            not match.
        """
        self.expect(open_kind)
        nodes = []
        while not self.skip(close_kind):
            nodes.append(parse_fn())
        return nodes

    def delimited_list(self, delimiter, parse_fn):
        """ Return a non-empty list of parse nodes determined by ``parse_fn`` and
        separated by a delimiter token of type ``delimiter`` Advances the parser to
        the next lex token after the last token.

        :type delimiter: type
        :param delimiter: A subclass of ``py_gql.lang.token.Token``

        :type parse_fn: callable
        :param parse_fn:
            Function to call for every item, should be a method of :class:`Parser`

        :rtype: List[py_gql.lang.ast.Node]

        :Raises:

            :class:`py_gql.exc.UnexpectedToken` if opening, entry or closing token do
            not match.
        """
        items = []
        self.skip(delimiter)
        while True:
            items.append(parse_fn())
            if not self.skip(delimiter):
                break
        return items

    def _loc(self, start):
        """ Return the location tuple or ``None`` if the instance is set to not track
        locations. """
        if self.no_location:
            return None
        return (start.start, self._last.end)

    def parse_document(self):
        """ Document : Definition+

        :rtype: py_gql.lang.ast.Document
        """
        start = self.peek()
        self.expect(_token.SOF)
        definitions = []
        while True:
            definitions.append(self.parse_definition())
            if self.skip(_token.EOF):
                break
        return _ast.Document(
            definitions=definitions, loc=self._loc(start), source=self.source
        )

    def parse_definition(self):
        """ Definition : ExecutableDefinition | TypeSystemDefinition

        Ignores type system definitions if ``allow_type_system`` was set to ``False``.

        :rtype: py_gql.lang.ast.Definition
        """
        start = self.peek()
        if _is(start, _token.Name):
            if start.value in EXECUTABLE_DEFINITIONS:
                return self.parse_executable_definition()
            elif self.allow_type_system and start.value in SCHEMA_DEFINITIONS:
                return self.parse_type_system_definition()
        elif _is(start, _token.CurlyOpen):
            return self.parse_executable_definition()
        elif self.allow_type_system and _is(
            start, _token.String, _token.BlockString
        ):
            return self.parse_type_system_definition()

        raise _unexpected_token(start, start.start, self.lexer._source)

    def parse_name(self):
        """ Convert a name lex token into a name parse node.

        :rtype: py_gql.lang.ast.Name
        """
        token = self.expect(_token.Name)
        return _ast.Name(
            value=token.value, loc=self._loc(token), source=self.source
        )

    def parse_executable_definition(self):
        """ ExecutableDefinition : OperationDefinition | FragmentDefinition

        :rtype: py_gql.lang.ast.ExecutableDefinition
        """
        start = self.peek()
        if _is(start, _token.Name):
            if start.value in OPERATION_TYPES:
                return self.parse_operation_definition()
            elif start.value == "fragment":
                return self.parse_fragment_definition()
        elif _is(start, _token.CurlyOpen):
            return self.parse_operation_definition()
        raise _unexpected_token(start, start.start, self.lexer._source)

    def parse_operation_definition(self):
        """ OperationDefinition : SelectionSet
        | OperationType Name? VariableDefinitions? Directives? SelectionSet

        :rtype: py_gql.lang.ast.OperationDefinition
        """
        start = self.peek()
        if _is(start, _token.CurlyOpen):
            return _ast.OperationDefinition(
                operation="query",
                name=None,
                variable_definitions=[],
                directives=[],
                selection_set=self.parse_selection_set(),
                loc=self._loc(start),
                source=self.source,
            )

        return _ast.OperationDefinition(
            operation=self.parse_operation_type(),
            name=self.parse_name() if _is(self.peek(), _token.Name) else None,
            variable_definitions=self.parse_variable_definitions(),
            directives=self.parse_directives(False),
            selection_set=self.parse_selection_set(),
            loc=self._loc(start),
        )

    def parse_operation_type(self):
        """ OperationType : one of "query" "mutation" "subscription"

        :rtype: str
        """
        token = self.expect(_token.Name)
        if token.value in ("query", "mutation", "subscription"):
            return token.value
        raise _unexpected_token(token, token.start, self.lexer._source)

    def parse_variable_definitions(self):
        """ VariableDefinitions : ( VariableDefinition+ )

        :rtype: List[py_gql.lang.ast.VariableDefinition]
        """
        if _is(self.peek(), _token.ParenOpen):
            return self.many(
                _token.ParenOpen,
                self.parse_variable_definition,
                _token.ParenClose,
            )
        return []

    def parse_variable_definition(self):
        """ VariableDefinition : Variable : Type DefaultValue?

        :rtype: py_gql.lang.ast.VariableDefinition
        """
        start = self.peek()
        return _ast.VariableDefinition(
            variable=self.parse_variable(),
            type=self.expect(_token.Colon) and self.parse_type_reference(),
            default_value=(
                self.parse_value_literal(True)
                if self.skip(_token.Equals)
                else None
            ),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_variable(self):
        """ Variable : $ Name

        :rtype: py_gql.lang.ast.Variable
        """
        start = self.peek()
        self.expect(_token.Dollar)
        return _ast.Variable(
            name=self.parse_name(), loc=self._loc(start), source=self.source
        )

    def parse_selection_set(self):
        """ SelectionSet : { Selection+ }

        :rtype: py_gql.lang.ast.SelectionSet
        """
        start = self.peek()
        return _ast.SelectionSet(
            selections=self.many(
                _token.CurlyOpen, self.parse_selection, _token.CurlyClose
            ),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_selection(self):
        """ Selection : Field | FragmentSpread | InlineFragment

        :rtype: py_gql.lang.ast.Selection
        """
        if _is(self.peek(), _token.Ellipsis):
            return self.parse_fragment()
        return self.parse_field()

    def parse_field(self):
        """ Field : Alias? Name Arguments? Directives? SelectionSet?

        - Alias : Name :

        :rtype: py_gql.lang.ast.Field
        """
        start = self.peek()
        name_or_alias = self.parse_name()
        if self.skip(_token.Colon):
            alias, name = name_or_alias, self.parse_name()
        else:
            alias, name = None, name_or_alias

        return _ast.Field(
            alias=alias,
            name=name,
            arguments=self.parse_arguments(False),
            directives=self.parse_directives(False),
            selection_set=(
                self.parse_selection_set()
                if _is(self.peek(), _token.CurlyOpen)
                else None
            ),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_arguments(self, const=False):
        """ Arguments[Const] : ( Argument[?Const]+ )

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: List[py_gql.lang.ast.Argument]
        """
        parse = ft.partial(self.parse_argument, const)
        if _is(self.peek(), _token.ParenOpen):
            return self.many(_token.ParenOpen, parse, _token.ParenClose)
        return []

    def parse_argument(self, const=False):
        """ Argument[Const] : Name : Value[?Const]

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: py_gql.lang.ast.Argument
        """
        start = self.peek()
        return _ast.Argument(
            name=self.parse_name(),
            value=(
                self.expect(_token.Colon) and self.parse_value_literal(False)
            ),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_fragment(self):
        """ FragmeSpread | InlineFragment

        - FragmentSpread : ... FragmentName Directives?
        - InlineFragment : ... TypeCondition? Directives? SelectionSet

        :rtype: Union[py_gql.lang.ast.FragmentSpread, py_gql.lang.ast.InlineFragment]
        """
        start = self.peek()
        self.expect(_token.Ellipsis)

        lead = self.peek()
        if _is(lead, _token.Name) and lead.value != "on":
            return _ast.FragmentSpread(
                name=self.parse_fragment_name(),
                directives=self.parse_directives(False),
                loc=self._loc(start),
                source=self.source,
            )

        return _ast.InlineFragment(
            type_condition=(
                (self.advance() and self.parse_named_type())
                if lead.value == "on"
                else None
            ),
            directives=self.parse_directives(False),
            selection_set=self.parse_selection_set(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_fragment_definition(self):
        """ FragmentDefinition : \
        fragment FragmentName on TypeCondition Directives? SelectionSet

        - TypeCondition : NamedType

        :rtype: py_gql.lang.ast.FragmentDefinition
        """
        start = self.peek()
        self.expect_keyword("fragment")
        return _ast.FragmentDefinition(
            name=self.parse_fragment_name(),
            variable_definitions=(
                self.parse_variable_definitions()
                if self.experimental_fragment_variables
                else None
            ),
            type_condition=(
                self.expect_keyword("on") and self.parse_named_type()
            ),
            directives=self.parse_directives(False),
            selection_set=self.parse_selection_set(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_fragment_name(self):
        """ FragmentName : Name but not "on"

        :rtype: py_gql.lang.ast.Name
        """
        token = self.peek()
        if token.value == "on":
            raise _unexpected_token(token, token.start, self.lexer._source)
        return self.parse_name()

    def parse_value_literal(self, const=False):
        """ Value[Const] : [~Const]Variable | IntValue | FloatValue | StringValue \
        | BooleanValue | NullValue | EnumValue \
        | ListValue[?Const] | ObjectValue[?Const]

        - BooleanValue : one of "true" "false"
        - NullValue : "null"
        - EnumValue : Name but not "true", "false" or "null"

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: py_gql.lang.ast.Value
        """
        token = self.peek()
        kind = type(token)
        value = token.value

        if kind == _token.BracketOpen:
            return self.parse_list(const)
        elif kind == _token.CurlyOpen:
            return self.parse_object(const)
        elif kind == _token.Integer:
            self.advance()
            return _ast.IntValue(
                value=value, loc=self._loc(token), source=self.source
            )
        elif kind == _token.Float:
            self.advance()
            return _ast.FloatValue(
                value=value, loc=self._loc(token), source=self.source
            )
        elif kind in (_token.String, _token.BlockString):
            return self.parse_string_literal()
        elif kind == _token.Name:
            if value in ("true", "false"):
                self.advance()
                return _ast.BooleanValue(
                    value=value == "true",
                    loc=self._loc(token),
                    source=self.source,
                )
            elif value == "null":
                self.advance()
                return _ast.NullValue(loc=self._loc(token), source=self.source)
            else:
                self.advance()
                return _ast.EnumValue(
                    value=value, loc=self._loc(token), source=self.source
                )
        elif kind == _token.Dollar and not const:
            return self.parse_variable()
        raise _unexpected_token(token, token.start, self.lexer._source)

    def parse_string_literal(self):
        """
        :rtype: py_gql.lang.ast.StringValue
        """
        token = self.advance()

        return _ast.StringValue(
            value=token.value,
            block=_is(token, _token.BlockString),
            loc=self._loc(token),
            source=self.source,
        )

    def parse_list(self, const=False):
        """ ListValue[Const] : [ ] | [ Value[?Const]+ ]

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: py_gql.lang.ast.ListValue
        """
        start = self.peek()
        item = ft.partial(self.parse_value_literal, const)
        return _ast.ListValue(
            values=self.any(_token.BracketOpen, item, _token.BracketClose),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_object(self, const=False):
        """ ObjectValue[Const] { } | { ObjectField[?Const]+ }

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: py_gql.lang.ast.ObjectValue
        """
        start = self.expect(_token.CurlyOpen)
        fields = []
        while not self.skip(_token.CurlyClose):
            fields.append(self.parse_object_field(const))
        return _ast.ObjectValue(
            fields=fields, loc=self._loc(start), source=self.source
        )

    def parse_object_field(self, const=False):
        """ ObjectField[Const] : Name : Value[?Const]

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: py_gql.lang.ast.ObjectField
        """
        start = self.peek()
        return _ast.ObjectField(
            name=self.parse_name(),
            value=(
                self.expect(_token.Colon) and self.parse_value_literal(const)
            ),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_directives(self, const=False):
        """ Directives[Const] : Directive[?Const]+

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: List[py_gql.lang.ast.Directive]
        """
        directives = []
        while _is(self.peek(), _token.At):
            directives.append(self.parse_directive(const))
        return directives

    def parse_directive(self, const=False):
        """ Directive[Const] : @ Name Arguments[?Const]?

        :type const: bool
        :param const: Whether or not to parse the Const variant

        :rtype: py_gql.lang.ast.
        """
        start = self.expect(_token.At)
        return _ast.Directive(
            name=self.parse_name(),
            arguments=self.parse_arguments(const),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_type_reference(self):
        """ Type : NamedType | ListType | NonNullType

        :rtype: py_gql.lang.ast.Type
        """
        start = self.peek()
        if self.skip(_token.BracketOpen):
            inner_type = self.parse_type_reference()
            self.expect(_token.BracketClose)
            typ = _ast.ListType(
                type=inner_type, loc=self._loc(start), source=self.source
            )
        else:
            typ = self.parse_named_type()

        if self.skip(_token.ExclamationMark):
            return _ast.NonNullType(
                type=typ, loc=self._loc(start), source=self.source
            )

        return typ

    def parse_named_type(self):
        """ NamedType : Name

        :rtype: py_gql.lang.ast.NamedType
        """
        start = self.peek()
        return _ast.NamedType(
            name=self.parse_name(), loc=self._loc(start), source=self.source
        )

    def parse_type_system_definition(self):
        """ TypeSystemDefinition : SchemaDefinition | TypeDefinition | TypeExtension \
        | DirectiveDefinition

        - TypeDefinition : ScalarTypeDefinition | ObjectTypeDefinition \
        | InterfaceTypeDefinition | UnionTypeDefinition | EnumTypeDefinition \
        | InputObjectTypeDefinition

        :rtype: py_gql.lang.ast.TypeSystemDefinition
        """
        keyword = (
            self.peek(2)
            if _is(self.peek(), _token.String, _token.BlockString)
            else self.peek()
        )

        if type(keyword) == _token.Name:
            if keyword.value == "schema":
                return self.parse_schema_definition()
            elif keyword.value == "scalar":
                return self.parse_scalar_type_definition()
            elif keyword.value == "type":
                return self.parse_object_type_definition()
            elif keyword.value == "interface":
                return self.parse_interface_type_definition()
            elif keyword.value == "union":
                return self.parse_union_type_definition()
            elif keyword.value == "enum":
                return self.parse_enum_type_definition()
            elif keyword.value == "input":
                return self.parse_input_object_type_definition()
            elif keyword.value == "extend":
                return self.parse_type_extension()
            elif keyword.value == "directive":
                return self.parse_directive_definition()

        raise _unexpected_token(keyword, keyword.start, self.lexer._source)

    def parse_description(self):
        """ Description : StringValue

        :rtype: py_gql.lang.ast.StringValue
        """
        return (
            self.parse_string_literal()
            if _is(self.peek(), _token.String, _token.BlockString)
            else None
        )

    def parse_schema_definition(self):
        """ SchemaDefinition : schema Directives[Const]? { OperationTypeDefinition+ }

        :rtype: py_gql.lang.ast.SchemaDefinition
        """
        start = self.peek()
        self.expect_keyword("schema")
        return _ast.SchemaDefinition(
            directives=self.parse_directives(True),
            operation_types=self.many(
                _token.CurlyOpen,
                self.parse_operation_type_definition,
                _token.CurlyClose,
            ),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_operation_type_definition(self):
        """ OperationTypeDefinition : OperationType : NamedType

        :rtype: py_gql.lang.ast.OperationTypeDefinition
        """
        start = self.peek()
        operation = self.parse_operation_type()
        self.expect(_token.Colon)
        return _ast.OperationTypeDefinition(
            operation=operation,
            type=self.parse_named_type(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_scalar_type_definition(self):
        """ ScalarTypeDefinition : Description? scalar Name Directives[Const]?

        :rtype: py_gql.lang.ast.ScalarTypeDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("scalar")
        return _ast.ScalarTypeDefinition(
            description=desc,
            name=self.parse_name(),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_object_type_definition(self):
        """ ObjectTypeDefinition : Description? type Name ImplementsInterfaces? \
        Directives[Const]? FieldsDefinition?

        :rtype: py_gql.lang.ast.ObjectTypeDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("type")
        return _ast.ObjectTypeDefinition(
            description=desc,
            name=self.parse_name(),
            interfaces=self.parse_implements_interfaces(),
            directives=self.parse_directives(True),
            fields=self.parse_fields_definition(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_implements_interfaces(self):
        """ ImplementsInterfaces : implements `&`? NamedType \
        | ImplementsInterfaces & NamedType

        :rtype: List[py_gql.lang.ast.NamedType]
        """
        token = self.peek()
        types = []
        if token.value == "implements":
            self.advance()
            self.skip(_token.Ampersand)
            while True:
                types.append(self.parse_named_type())
                if not (
                    self.skip(_token.Ampersand)
                    or (
                        self.allow_legacy_sdl_implements_interfaces
                        and _is(self.peek(), _token.Name)
                    )
                ):
                    break
        return types

    def parse_fields_definition(self):
        """ FieldsDefinition : { FieldDefinition+ }

        :rtype: List[py_gql.lang.ast.FieldDefinition]
        """
        if (
            self.allow_legacy_sdl_empty_fields
            and _is(self.peek(), _token.CurlyOpen)
            and type(self.peek(2)) == _token.CurlyClose
        ):
            self.advance()
            self.advance()
            return []
        return (
            self.many(
                _token.CurlyOpen, self.parse_field_definition, _token.CurlyClose
            )
            if _is(self.peek(), _token.CurlyOpen)
            else []
        )

    def parse_field_definition(self):
        """ FieldDefinition : \
        Description? Name ArgumentsDefinition? : Type Directives[Const]?

        :rtype: py_gql.lang.ast.FieldDefinition
        """
        start = self.peek()
        desc, name = self.parse_description(), self.parse_name()
        args = self.parse_argument_defs()
        self.expect(_token.Colon)
        return _ast.FieldDefinition(
            description=desc,
            name=name,
            arguments=args,
            type=self.parse_type_reference(),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_argument_defs(self):
        """ ArgumentsDefinition : ( InputValueDefinition+ )

        :rtype: List[py_gql.lang.ast.InputValueDefinition]
        """
        return (
            self.many(
                _token.ParenOpen, self.parse_input_value_def, _token.ParenClose
            )
            if _is(self.peek(), _token.ParenOpen)
            else []
        )

    def parse_input_value_def(self):
        """ InputValueDefinition : \
        Description? Name : Type DefaultValue? Directives[Const]?

        :rtype: py_gql.lang.ast.
        """
        start = self.peek()
        desc, name = self.parse_description(), self.parse_name()
        self.expect(_token.Colon)
        return _ast.InputValueDefinition(
            description=desc,
            name=name,
            type=self.parse_type_reference(),
            default_value=(
                self.parse_value_literal(True)
                if self.skip(_token.Equals)
                else None
            ),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_interface_type_definition(self):
        """ InterfaceTypeDefinition : \
        Description? interface Name Directives[Const]? FieldsDefinition?

        :rtype: py_gql.lang.ast.InterfaceTypeDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("interface")
        return _ast.InterfaceTypeDefinition(
            description=desc,
            name=self.parse_name(),
            directives=self.parse_directives(True),
            fields=self.parse_fields_definition(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_union_type_definition(self):
        """ UnionTypeDefinition : \
        Description? union Name Directives[Const]? UnionMemberTypes?

        :rtype: py_gql.lang.ast.UnionTypeDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("union")
        return _ast.UnionTypeDefinition(
            description=desc,
            name=self.parse_name(),
            directives=self.parse_directives(True),
            types=self.parse_union_member_types(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_union_member_types(self):
        """ UnionMemberTypes : = `|`? NamedType | UnionMemberTypes | NamedType

        :rtype: List[py_gql.lang.ast.NamedType]
        """
        if self.skip(_token.Equals):
            return self.delimited_list(_token.Pipe, self.parse_named_type)
        return []

    def parse_enum_type_definition(self):
        """ EnumTypeDefinition : \
        Description? enum Name Directives[Const]? EnumValuesDefinition?

        :rtype: py_gql.lang.ast.EnumTypeDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("enum")
        return _ast.EnumTypeDefinition(
            description=desc,
            name=self.parse_name(),
            directives=self.parse_directives(True),
            values=self.parse_enum_values_definition(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_enum_values_definition(self):
        """ EnumValuesDefinition : { EnumValueDefinition+ }

        :rtype: List[py_gql.lang.ast.EnumValueDefinition]
        """
        return (
            self.many(
                _token.CurlyOpen,
                self.parse_enum_value_definition,
                _token.CurlyClose,
            )
            if _is(self.peek(), _token.CurlyOpen)
            else []
        )

    def parse_enum_value_definition(self):
        """ EnumValueDefinition : Description? EnumValue Directives[Const]?

        - EnumValue : Name

        :rtype: py_gql.lang.ast.EnumValueDefinition
        """
        start = self.peek()
        return _ast.EnumValueDefinition(
            description=self.parse_description(),
            name=self.parse_name(),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_input_object_type_definition(self):
        """ InputObjectTypeDefinition : \
        Description? input Name Directives[Const]? InputFieldsDefinition?

        :rtype: py_gql.lang.ast.InputObjectTypeDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("input")
        return _ast.InputObjectTypeDefinition(
            description=desc,
            name=self.parse_name(),
            directives=self.parse_directives(True),
            fields=self.parse_input_fields_definition(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_input_fields_definition(self):
        """ InputFieldsDefinition : { InputValueDefinition+ }

        :rtype: List[py_gql.lang.ast.InputValueDefinition]
        """
        return (
            self.many(
                _token.CurlyOpen, self.parse_input_value_def, _token.CurlyClose
            )
            if _is(self.peek(), _token.CurlyOpen)
            else []
        )

    def parse_type_extension(self):
        """ TypeExtension : ScalarTypeExtension | ObjectTypeExtension | \
        InterfaceTypeExtension | UnionTypeExtension | EnumTypeExtension | \
        InputObjectTypeDefinition

        :rtype: py_gql.lang.ast.
        """
        keyword = self.peek(2)
        if _is(keyword, _token.Name):
            if keyword.value == "scalar":
                return self.parse_scalar_type_extension()
            elif keyword.value == "type":
                return self.parse_object_type_extension()
            elif keyword.value == "interface":
                return self.parse_interface_type_extension()
            elif keyword.value == "union":
                return self.parse_union_type_extension()
            elif keyword.value == "enum":
                return self.parse_enum_type_extension()
            elif keyword.value == "input":
                return self.parse_input_object_type_extension()

        raise _unexpected_token(keyword, keyword.start, self.lexer._source)

    def parse_scalar_type_extension(self):
        """ ScalarTypeExtension : extend scalar Name Directives[Const]

        :rtype: py_gql.lang.ast.ScalarTypeExtension
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("scalar")
        name = self.parse_name()
        directives = self.parse_directives(True)
        if not directives:
            raise _unexpected_token(start, start.start, self.lexer._source)
        return _ast.ScalarTypeExtension(
            name=name,
            directives=directives,
            loc=self._loc(start),
            source=self.source,
        )

    def parse_object_type_extension(self):
        """ ObjectTypeExtension : \
        extend type Name ImplementsInterfaces? Directives[Const]? FieldsDefinition \
        | extend type Name ImplementsInterfaces? Directives[Const] \
        | extend type Name ImplementsInterfaces

        :rtype: py_gql.lang.ast.ObjectTypeExtension
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("type")
        name = self.parse_name()
        interfaces = self.parse_implements_interfaces()
        directives = self.parse_directives(True)
        fields = self.parse_fields_definition()
        if (not interfaces) and (not directives) and (not fields):
            tok = self.peek()
            raise _unexpected_token(tok, tok.start, self.lexer._source)
        return _ast.ObjectTypeExtension(
            name=name,
            interfaces=interfaces,
            directives=directives,
            fields=fields,
            loc=self._loc(start),
            source=self.source,
        )

    def parse_interface_type_extension(self):
        """ InterfaceTypeExtension : \
        extend interface Name Directives[Const]? FieldsDefinition \
        | extend interface Name Directives[Const]

        :rtype: py_gql.lang.ast.InterfaceTypeExtension
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("interface")
        name = self.parse_name()
        directives = self.parse_directives(True)
        fields = self.parse_fields_definition()
        if (not directives) and (not fields):
            tok = self.peek()
            raise _unexpected_token(tok, tok.start, self.lexer._source)

        return _ast.InterfaceTypeExtension(
            name=name,
            directives=directives,
            fields=fields,
            loc=self._loc(start),
            source=self.source,
        )

    def parse_union_type_extension(self):
        """ UnionTypeExtension : \
        | extend union Name Directives[Const]? UnionMemberTypes \
        | extend union Name Directives[Const]

        :rtype: py_gql.lang.ast.UnionTypeExtension
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("union")
        name = self.parse_name()
        directives = self.parse_directives(True)
        types = self.parse_union_member_types()
        if (not directives) and (not types):
            tok = self.peek()
            raise _unexpected_token(tok, tok.start, self.lexer._source)

        return _ast.UnionTypeExtension(
            name=name,
            directives=directives,
            types=types,
            loc=self._loc(start),
            source=self.source,
        )

    def parse_enum_type_extension(self):
        """ EnumTypeExtension : \
        extend enum Name Directives[Const]? EnumValuesDefinition \
        | extend enum Name Directives[Const]

        :rtype: py_gql.lang.ast.EnumTypeExtension
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("enum")
        name = self.parse_name()
        directives = self.parse_directives(True)
        values = self.parse_enum_values_definition()
        if (not directives) and (not values):
            tok = self.peek()
            raise _unexpected_token(tok, tok.start, self.lexer._source)

        return _ast.EnumTypeExtension(
            name=name,
            directives=directives,
            values=values,
            loc=self._loc(start),
            source=self.source,
        )

    def parse_input_object_type_extension(self):
        """ InputObjectTypeExtension : \
        extend input Name Directives[Const]? InputFieldsDefinition \
        | extend input Name Directives[Const]

        :rtype: py_gql.lang.ast.InputObjectTypeExtension
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("input")
        name = self.parse_name()
        directives = self.parse_directives(True)
        fields = self.parse_input_fields_definition()
        if (not directives) and (not fields):
            raise _unexpected_token("", start.start, self.lexer._source)

        return _ast.InputObjectTypeExtension(
            name=name,
            directives=directives,
            fields=fields,
            loc=self._loc(start),
            source=self.source,
        )

    def parse_directive_definition(self):
        """ DirectiveDefinition : Description? directive @ Name ArgumentsDefinition? \
        on DirectiveLocations

        :rtype: py_gql.lang.ast.DirectiveDefinition
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("directive")
        self.expect(_token.At)
        name = self.parse_name()
        args = self.parse_argument_defs()
        self.expect_keyword("on")
        return _ast.DirectiveDefinition(
            description=desc,
            name=name,
            arguments=args,
            locations=self.parse_directive_locations(),
            loc=self._loc(start),
            source=self.source,
        )

    def parse_directive_locations(self):
        """ DirectiveLocations : \
        `|`? DirectiveLocation \ `|` DirectiveLocations `|` DirectiveLocation

        :rtype: List[py_gql.lang.ast.DirectiveLocation]
        """
        return self.delimited_list(_token.Pipe, self.parse_directive_location)

    def parse_directive_location(self):
        """ DirectiveLocation : ExecutableDirectiveLocation \
        | TypeSystemDirectiveLocation

        - ExecutableDirectiveLocation : one of QUERY MUTATION SUBSCRIPTION FIELD \
        FRAGMENT_DEFINITION FRAGMENT_SPREAD INLINE_FRAGMENT

        - TypeSystemDirectiveLocation : one of SCHEMA SCALAR OBJECT FIELD_DEFINITION \
        ARGUMENT_DEFINITION INTERFACE UNION ENUM ENUM_VALUE INPUT_OBJECT \
        INPUT_FIELD_DEFINITION

        :rtype: py_gql.lang.ast.Name
        """
        start = self.peek()
        name = self.parse_name()
        if name.value in DIRECTIVE_LOCATIONS:
            return name
        raise _unexpected_token(
            "Unexpected Name %s" % name.value, start.start, self.lexer._source
        )
