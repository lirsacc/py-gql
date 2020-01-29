# -*- coding: utf-8 -*-

import collections
import functools as ft
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..exc import GraphQLSyntaxError, UnexpectedEOF, UnexpectedToken
from . import ast as _ast
from .lexer import Lexer
from .token import (
    EOF,
    SOF,
    Ampersand,
    At,
    BlockString,
    BracketClose,
    BracketOpen,
    Colon,
    CurlyClose,
    CurlyOpen,
    Dollar,
    Ellip,
    Equals,
    ExclamationMark,
    Float,
    Integer,
    Name,
    ParenClose,
    ParenOpen,
    Pipe,
    String,
    Token,
)

DIRECTIVE_LOCATIONS = frozenset(
    [
        "QUERY",
        "MUTATION",
        "SUBSCRIPTION",
        "FIELD",
        "FRAGMENT_DEFINITION",
        "FRAGMENT_SPREAD",
        "INLINE_FRAGMENT",
        "VARIABLE_DEFINITION",
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


EXECUTABLE_DEFINITIONS_KEYWORDS = frozenset(
    ["query", "mutation", "subscription", "fragment"]
)


SCHEMA_DEFINITIONS_KEYWORDS = frozenset(
    [
        "schema",
        "scalar",
        "type",
        "interface",
        "union",
        "enum",
        "input",
        "directive",
    ]
)

OPERATION_TYPES_KEYWORDS = frozenset(["query", "mutation", "subscription"])


if TYPE_CHECKING:
    # typing.Deque was only included in Python 3.5.4 and given that some pretty
    # used distros such as debian stretch still default to 3.5.3 it is worth
    # special-casing this. It will break when running mypy under these
    # conditions but that's an acceptable tradeoff.
    from typing import Deque


Kind = Type[Token]
K = TypeVar("K", bound=Kind)
N = TypeVar("N", bound=_ast.Node)
LocCallable = Callable[[Token], Optional[Tuple[int, int]]]


def _unexpected(
    msg_or_token: Union[str, Token], position: int, source: str
) -> GraphQLSyntaxError:
    if isinstance(msg_or_token, Token):
        if isinstance(msg_or_token, EOF):
            return UnexpectedEOF(position, source)
        msg_or_token = 'Unexpected "%s"' % msg_or_token
    return UnexpectedToken(msg_or_token, position, source)


def parse(source: Union[str, bytes], **kwargs: Any) -> _ast.Document:
    """
    Parse a string as a GraphQL Document.

    Args:
        source (Union[str, bytes]): source document.
        **kwargs: Remaining keyword arguments passed to :class:`Parser`

    Raises:
        :class:`~py_gql.exc.GraphQLSyntaxError`: if a syntax error is encountered.

    Returns:
        `py_gql.lang.ast.Document`: Parsed document.
    """
    return Parser(source, **kwargs).parse_document()


def parse_value(
    source: Union[str, bytes], **kwargs: Any
) -> Union[_ast.Variable, _ast.Value]:
    """
    Parse a string as a single GraphQL value.

    This is useful within tools that operate upon GraphQL values (eg. ``[42]``)
    directly and in isolation of complete GraphQL documents. Consider providing
    the results to the utility functions
    :func:`py_gql.utilities.untyped_value_from_ast` and
    :func:`py_gql.utilities.value_from_ast`.

    Args:
        source (Union[str, bytes]): source document
        **kwargs: Remaining keyword arguments passed to :class:`Parser`

    Raises:
        :class:`~py_gql.exc.GraphQLSyntaxError`: if a syntax error is encountered.
    """
    parser = Parser(source, **kwargs)
    parser.expect(SOF)
    value = parser.parse_value_literal(False)
    parser.expect(EOF)
    return value


def parse_type(source: Union[str, bytes], **kwargs: Any) -> _ast.Type:
    """
    Parse a string as a single GraphQL type.

    This is useful within tools that operate upon GraphQL types (eg. ``[Int!]``)
    directly and in isolation of complete GraphQL documents such as when
    building a schema from the SDL or stitching schemas together.

    Args:
        source (Union[str, bytes]): source document
        **kwargs: Remaining keyword arguments passed to :class:`Parser`

    Raises:
        :class:`~py_gql.exc.GraphQLSyntaxError`: if a syntax error is encountered.
    """
    parser = Parser(source, **kwargs)
    parser.expect(SOF)
    value = parser.parse_type_reference()
    parser.expect(EOF)
    return value


class Parser:
    """
    GraphQL syntax parser.

    Call :meth:`parse_document` to parse a GraphQL document.

    All ``parse_*`` methods will raise :class:`~py_gql.exc.GraphQLSyntaxError`
    if a syntax error is encountered.

    Args:
        source (Union[str, bytes]): source document

        no_location (bool):
            By default, the parser creates AST nodes that know the location
            in the source that they correspond to. This configuration flag
            disables that behavior for performance or testing reasons.

        allow_type_system (bool):
            By default, the parser will accept schema definition nodes, when
            only executing GraphQL queries setting this to ``False`` can save
            operations and remove the need for some later validation.

        experimental_fragment_variables (bool):
            If enabled, the parser will understand and parse variable
            definitions contained in a fragment definition. They'll be
            represented in the ``variable_definitions`` field of the
            FragmentDefinition.

            The syntax is identical to normal, query-defined variables,
            for example:

            .. code-block:: graphql

                fragment A($var: Boolean = false) on T  {
                    ...
                }

            Warning:
                This feature is experimental and may change or be removed
                in the future. See https://github.com/graphql/graphql-spec/issues/204
                for the open spec PR.

    """

    __slots__ = (
        "_lexer",
        "_source",
        "_loc",
        "_allow_type_system",
        "_experimental_fragment_variables",
        "_buffer",
        "_last",
    )

    def __init__(
        self,
        source: Union[str, bytes],
        no_location: bool = False,
        allow_type_system: bool = False,
        experimental_fragment_variables: bool = False,
    ):
        self._lexer = Lexer(source)
        self._source = self._lexer._source

        self._allow_type_system = allow_type_system
        self._experimental_fragment_variables = experimental_fragment_variables

        self._loc = (
            (lambda _: None)
            if no_location
            else (lambda start: (start.start, self._last.end))
        )  # type: LocCallable

        # Keep track of the current parsing window + last seen token internally
        # as the Lexer iterator itself doesn't handle backtracking or lookahead
        # semantics and can only be consumed once.
        # TODO: Do we need dequeue here or can we go with a list?
        self._buffer = collections.deque()  # type: Deque[Token]

    def _advance_window(self, by: int = 1) -> None:
        """
        Advance the parsing window by one element.
        Raise ``py_gql.exc.UnexpectedEOF`` error when trying to advance past
        EOF when parsing window is empty. """
        c = 0
        while c < by:
            try:
                self._buffer.appendleft(next(self._lexer))
                c += 1
            except StopIteration:
                if len(self._buffer) == 0:
                    raise UnexpectedEOF(self._lexer._len, self._lexer._source)

    def peek(self, count: int = 1) -> Token:
        """
        Look at a token ahead of the current position without advancing the
        parsing position.

        Args:
            count (int): How many tokens should we look ahead

        Raises:
            :class:`~py_gql.exc.UnexpectedEOF`:
                if there is not enough tokens left in the lexer.
        """
        delta = count - len(self._buffer)
        if delta:
            self._advance_window(by=delta)

        return self._buffer[-count]

    def advance(self) -> Token:
        """
        Move parsing window forward and return the next token.

        Raises:
            :class:`~py_gql.exc.UnexpectedEOF`:
                if there is not enough tokens left in the lexer.
        """
        if not self._buffer:
            self._advance_window()

        self._last = self._buffer.pop()
        return self._last

    def expect(self, kind: Kind) -> Token:
        """
        Advance the parser and check that the next token is of the
        given token class otherwise raises :class:`~py_gql.exc.UnexpectedToken`.

        Args:
            kind: Expected token kind. Must be a subclass of
                :class:`py_gql.lang.token.Token`
        """
        next_token = self.peek()
        if next_token.__class__ is kind:
            return self.advance()

        raise _unexpected(
            'Expected %s but found "%s"' % (kind.__name__, next_token),
            next_token.start,
            self._lexer._source,
        )

    def expect_keyword(self, keyword: str) -> Name:
        """
        Advance the parser and check that the next token is a Name with
        the given value otherwise raises :class:`~py_gql.exc.UnexpectedToken`.

        Args:
            keyword (str): Expected keyword
        """
        next_token = self.peek()
        if next_token.__class__ is Name and next_token.value == keyword:
            return cast(Name, self.advance())

        raise _unexpected(
            'Expected "%s" but found "%s"' % (keyword, next_token),
            next_token.start,
            self._lexer._source,
        )

    def skip(self, kind: Kind) -> bool:
        """
        If the next token is of the given kind, return ``True`` after
        advancing the parser. Otherwise, do not change the parser state and
        return ``False``.

        Args:
            kind: Token kind to read over. Must be a subclass of
                :class:`py_gql.lang.token.Token`
        """
        if self.peek().__class__ is kind:
            self.advance()
            return True
        return False

    def many(
        self, open_kind: Kind, parse_fn: Callable[[], N], close_kind: Kind
    ) -> List[N]:
        """
        Return a non-empty list of parse nodes, determined by
        ``parse_fn`` which are surrounded by ``open_kind`` and ``close_kind`` tokens.
        Advances the parser to the next lex token after the closing token.

        Args:
            open_kind: Opening token kind. Must be a subclass of
                :class:`py_gql.lang.token.Token`

            parse_fn (callable): Function to call for every item, should be a
                method of the :class:`Parser` instance.

            close_kind: Closing token kind. Must be a subclass of
                :class:`py_gql.lang.token.Token`

        Raises:
            :class:`~py_gql.exc.UnexpectedToken`:
                if opening, entry or closing token do not match.
        """
        self.expect(open_kind)
        nodes = []
        while True:
            nodes.append(parse_fn())
            if self.skip(close_kind):
                break
        return nodes

    def any_(
        self, open_kind: Kind, parse_fn: Callable[[], N], close_kind: Kind
    ) -> List[N]:
        """
        Return a non-empty list of parse nodes, determined by
        ``parse_fn`` which are surrounded by ``open_kind`` and ``close_kind`` tokens.
        Advances the parser to the next lex token after the closing token.

        Args:
            open_kind: Opening token kind. Must be a subclass of
                :class:`py_gql.lang.token.Token`

            parse_fn (callable): Function to call for every item, should be a
                method of the :class:`Parser` instance.

            close_kind: Closing token kind. Must be a subclass of
                :class:`py_gql.lang.token.Token`

        Raises:
            :class:`~py_gql.exc.UnexpectedToken`:
                if opening, entry or closing token do not match.
        """
        self.expect(open_kind)
        nodes = []
        while not self.skip(close_kind):
            nodes.append(parse_fn())
        return nodes

    def delimited_list(
        self, delimiter: Kind, parse_fn: Callable[[], N]
    ) -> List[N]:
        """
        Return a non-empty list of parse nodes determined by ``parse_fn`` and
        separated by a delimiter token of type ``delimiter`` Advances the parser to
        the next lex token after the last token.

        Args:
            delimiter: Delimiter kind. Must be a subclass of
                :class:`py_gql.lang.token.Token`

            parse_fn (callable): Function to call for every item, should be a
                method of the :class:`Parser` instance.

        Raises:
            :class:`~py_gql.exc.UnexpectedToken`:
                if opening, entry or closing token do not match.
        """
        items = []
        self.skip(delimiter)
        while True:
            items.append(parse_fn())
            if not self.skip(delimiter):
                break
        return items

    def parse_document(self) -> _ast.Document:
        """
        Document : Definition+
        """
        start = self.peek()
        self.expect(SOF)
        definitions = []
        while True:
            definitions.append(self.parse_definition())
            if self.skip(EOF):
                break

        return _ast.Document(
            definitions=definitions, loc=self._loc(start), source=self._source
        )

    def parse_definition(self) -> _ast.Definition:
        """
        Definition : ExecutableDefinition | TypeSystemDefinition

        Ignores type system definitions if ``allow_type_system``
        was set to ``False``.
        """
        start = self.peek()
        if start.__class__ is Name:
            if start.value in EXECUTABLE_DEFINITIONS_KEYWORDS:
                return self.parse_executable_definition()
            elif self._allow_type_system:
                if start.value in SCHEMA_DEFINITIONS_KEYWORDS:
                    return self.parse_type_system_definition()
                elif start.value == "extend":
                    return self.parse_type_system_extension()
        elif start.__class__ is CurlyOpen:
            return self.parse_executable_definition()
        elif self._allow_type_system and (
            start.__class__ is String or start.__class__ is BlockString
        ):
            return self.parse_type_system_definition()

        raise _unexpected(start, start.start, self._lexer._source)

    def parse_name(self) -> _ast.Name:
        """
        Convert a name lex token into a name parse node.
        """
        token = self.expect(Name)
        return _ast.Name(
            value=token.value, loc=self._loc(token), source=self._source
        )

    def parse_executable_definition(self) -> _ast.ExecutableDefinition:
        """
        ExecutableDefinition : OperationDefinition | FragmentDefinition
        """
        start = self.peek()
        if start.__class__ is Name:
            if start.value in OPERATION_TYPES_KEYWORDS:
                return self.parse_operation_definition()
            elif start.value == "fragment":
                return self.parse_fragment_definition()
        elif start.__class__ is CurlyOpen:
            return self.parse_operation_definition()
        raise _unexpected(start, start.start, self._lexer._source)

    def parse_operation_definition(self) -> _ast.OperationDefinition:
        """
        OperationDefinition : SelectionSet
        | OperationType Name? VariableDefinitions? Directives? SelectionSet
        """
        start = self.peek()
        if start.__class__ is CurlyOpen:
            return _ast.OperationDefinition(
                operation="query",
                name=None,
                variable_definitions=[],
                directives=[],
                selection_set=self.parse_selection_set(),
                loc=self._loc(start),
                source=self._source,
            )

        return _ast.OperationDefinition(
            operation=self.parse_operation_type(),
            name=self.parse_name() if self.peek().__class__ is Name else None,
            variable_definitions=self.parse_variable_definitions(),
            directives=self.parse_directives(False),
            selection_set=self.parse_selection_set(),
            loc=self._loc(start),
        )

    def parse_operation_type(self) -> str:
        """
        OperationType : one of "query" "mutation" "subscription"
        """
        token = self.expect(Name)
        if token.value in ("query", "mutation", "subscription"):
            return token.value
        raise _unexpected(token, token.start, self._lexer._source)

    def parse_variable_definitions(self) -> List[_ast.VariableDefinition]:
        """
        VariableDefinitions : ( VariableDefinition+ )

        Returns:
            List[py_gql.lang.ast.VariableDefinition]:
        """
        if self.peek().__class__ is ParenOpen:
            return self.many(
                ParenOpen, self.parse_variable_definition, ParenClose
            )
        return []

    def parse_variable_definition(self) -> _ast.VariableDefinition:
        """
        VariableDefinition : Variable : Type DefaultValue? Directives[Const]?
        """
        start = self.peek()
        return _ast.VariableDefinition(
            variable=self.parse_variable(),
            type=cast(
                _ast.Type, self.expect(Colon) and self.parse_type_reference()
            ),
            default_value=(
                cast(_ast.Value, self.parse_value_literal(True))
                if self.skip(Equals)
                else None
            ),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_variable(self) -> _ast.Variable:
        """
        Variable : $ Name
        """
        start = self.peek()
        self.expect(Dollar)
        return _ast.Variable(
            name=self.parse_name(), loc=self._loc(start), source=self._source
        )

    def parse_selection_set(self) -> _ast.SelectionSet:
        """
        SelectionSet : { Selection+ }
        """
        start = self.peek()
        return _ast.SelectionSet(
            selections=self.many(CurlyOpen, self.parse_selection, CurlyClose),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_selection(self) -> _ast.Selection:
        """
        Selection : Field | FragmentSpread | InlineFragment
        """
        if self.peek().__class__ is Ellip:
            return self.parse_fragment()
        return self.parse_field()

    def parse_field(self) -> _ast.Field:
        """
        Field : Alias? Name Arguments? Directives? SelectionSet?

        - Alias : Name :
        """
        start = self.peek()
        name_or_alias = self.parse_name()
        if self.skip(Colon):
            alias = name_or_alias  # type: Optional[_ast.Name]
            name = self.parse_name()  # type: _ast.Name
        else:
            alias, name = None, name_or_alias

        return _ast.Field(
            alias=alias,
            name=name,
            arguments=self.parse_arguments(False),
            directives=self.parse_directives(False),
            selection_set=(
                self.parse_selection_set()
                if self.peek().__class__ is CurlyOpen
                else None
            ),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_arguments(self, const: bool = False) -> List[_ast.Argument]:
        """
        Arguments[Const] : ( Argument[?Const]+ )

        Args:
            const: Whether or not to parse the Const variant
        """
        if self.peek().__class__ is ParenOpen:
            return self.many(
                ParenOpen, ft.partial(self.parse_argument, const), ParenClose
            )
        return []

    def parse_argument(self, const: bool = False) -> _ast.Argument:
        """
        Argument[Const] : Name : Value[?Const]

        Args:
            const: Whether or not to parse the Const variant
        """
        start = self.peek()
        return _ast.Argument(
            name=self.parse_name(),
            value=cast(
                Union[_ast.Value, _ast.Variable],
                self.expect(Colon) and self.parse_value_literal(const),
            ),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_fragment(self) -> Union[_ast.InlineFragment, _ast.FragmentSpread]:
        """
        FragmeSpread | InlineFragment

        - FragmentSpread : ... FragmentName Directives?
        - InlineFragment : ... TypeCondition? Directives? SelectionSet
        """
        start = self.peek()
        self.expect(Ellip)

        lead = self.peek()
        if lead.__class__ is Name and lead.value != "on":
            return _ast.FragmentSpread(
                name=self.parse_fragment_name(),
                directives=self.parse_directives(False),
                loc=self._loc(start),
                source=self._source,
            )

        return _ast.InlineFragment(
            type_condition=(
                cast(_ast.NamedType, self.advance() and self.parse_named_type())
                if lead.value == "on"
                else None
            ),
            directives=self.parse_directives(False),
            selection_set=self.parse_selection_set(),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_fragment_definition(self) -> _ast.FragmentDefinition:
        """
        FragmentDefinition : \
        fragment FragmentName on TypeCondition Directives? SelectionSet

        - TypeCondition : NamedType
        """
        start = self.peek()
        self.expect_keyword("fragment")
        return _ast.FragmentDefinition(
            name=self.parse_fragment_name(),
            variable_definitions=(
                self.parse_variable_definitions()
                if self._experimental_fragment_variables
                else None
            ),
            type_condition=cast(
                _ast.NamedType,
                self.expect_keyword("on") and self.parse_named_type(),
            ),
            directives=self.parse_directives(False),
            selection_set=self.parse_selection_set(),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_fragment_name(self) -> _ast.Name:
        """
        FragmentName : Name but not "on"
        """
        token = self.peek()
        if token.value == "on":
            raise _unexpected(token, token.start, self._lexer._source)
        return self.parse_name()

    def parse_value_literal(
        self, const: bool = False
    ) -> Union[_ast.Value, _ast.Variable]:
        """
        Value[Const] : [~Const]Variable | IntValue | FloatValue | StringValue \
        | BooleanValue | NullValue | EnumValue \
        | ListValue[?Const] | ObjectValue[?Const]

        - BooleanValue : one of "true" "false"
        - NullValue : "null"
        - EnumValue : Name but not "true", "false" or "null"

        Args:
            const: Whether or not to parse the Const variant
        """
        token = self.peek()
        kind = type(token)
        value = token.value

        if kind is BracketOpen:
            return self.parse_list(const)
        elif kind is CurlyOpen:
            return self.parse_object(const)
        elif kind is Integer:
            self.advance()
            return _ast.IntValue(
                value=value, loc=self._loc(token), source=self._source
            )
        elif kind is Float:
            self.advance()
            return _ast.FloatValue(
                value=value, loc=self._loc(token), source=self._source
            )
        elif kind in (String, BlockString):
            return self.parse_string_literal()
        elif kind is Name:
            if value in ("true", "false"):
                self.advance()
                return _ast.BooleanValue(
                    value=value == "true",
                    loc=self._loc(token),
                    source=self._source,
                )
            elif value == "null":
                self.advance()
                return _ast.NullValue(loc=self._loc(token), source=self._source)
            else:
                self.advance()
                return _ast.EnumValue(
                    value=value, loc=self._loc(token), source=self._source
                )
        elif kind is Dollar and not const:
            return self.parse_variable()

        raise _unexpected(token, token.start, self._lexer._source)

    def parse_string_literal(self) -> _ast.StringValue:
        token = self.advance()

        return _ast.StringValue(
            value=token.value,
            block=token.__class__ is BlockString,
            loc=self._loc(token),
            source=self._source,
        )

    def parse_list(self, const: bool = False) -> _ast.ListValue:
        """
        ListValue[Const] : [ ] | [ Value[?Const]+ ]

        Args:
            const: Whether or not to parse the Const variant
        """
        start = self.peek()
        return _ast.ListValue(
            values=self.any_(
                BracketOpen,
                ft.partial(self.parse_value_literal, const),
                BracketClose,
            ),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_object(self, const: bool = False) -> _ast.ObjectValue:
        """
        ObjectValue[Const] { } | { ObjectField[?Const]+ }

        Args:
            const: Whether or not to parse the Const variant
        """
        start = self.expect(CurlyOpen)
        fields = []
        while not self.skip(CurlyClose):
            fields.append(self.parse_object_field(const))
        return _ast.ObjectValue(
            fields=fields, loc=self._loc(start), source=self._source
        )

    def parse_object_field(self, const: bool = False) -> _ast.ObjectField:
        """
        ObjectField[Const] : Name : Value[?Const]

        Args:
            const: Whether or not to parse the Const variant

        Returns:
            py_gql.lang.ast.ObjectField:
        """
        start = self.peek()
        return _ast.ObjectField(
            name=self.parse_name(),
            value=cast(
                _ast.Value,
                self.expect(Colon) and self.parse_value_literal(const),
            ),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_directives(self, const: bool = False) -> List[_ast.Directive]:
        """
        Directives[Const] : Directive[?Const]+

        Args:
            const: Whether or not to parse the Const variant
        """
        directives = []
        while self.peek().__class__ is At:
            directives.append(self.parse_directive(const))
        return directives

    def parse_directive(self, const: bool = False) -> _ast.Directive:
        """
        Directive[Const] : @ Name Arguments[?Const]?

        Args:
            const: Whether or not to parse the Const variant
        """
        start = self.expect(At)
        return _ast.Directive(
            name=self.parse_name(),
            arguments=self.parse_arguments(const),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_type_reference(self) -> _ast.Type:
        """
        Type : NamedType | ListType | NonNullType
        """
        start = self.peek()

        if self.skip(BracketOpen):
            inner_type = self.parse_type_reference()
            self.expect(BracketClose)
            type_ = _ast.ListType(
                type=inner_type, loc=self._loc(start), source=self._source
            )  # type: Union[_ast.ListType, _ast.NamedType]
        else:
            type_ = self.parse_named_type()

        if self.skip(ExclamationMark):
            return _ast.NonNullType(
                type=type_, loc=self._loc(start), source=self._source
            )

        return type_

    def parse_named_type(self) -> _ast.NamedType:
        """
        NamedType : Name
        """
        start = self.peek()
        return _ast.NamedType(
            name=self.parse_name(), loc=self._loc(start), source=self._source
        )

    def parse_type_system_definition(self) -> _ast.TypeSystemDefinition:
        """
        TypeSystemDefinition : SchemaDefinition | TypeDefinition | TypeExtension \
        | DirectiveDefinition

        - TypeDefinition : ScalarTypeDefinition | ObjectTypeDefinition \
        | InterfaceTypeDefinition | UnionTypeDefinition | EnumTypeDefinition \
        | InputObjectTypeDefinition
        """
        next_ = self.peek()
        keyword = (
            self.peek(2)
            if (next_.__class__ is String or next_.__class__ is BlockString)
            else next_
        )

        if type(keyword) == Name:
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
            elif keyword.value == "directive":
                return self.parse_directive_definition()

        raise _unexpected(keyword, keyword.start, self._lexer._source)

    def parse_description(self) -> Optional[_ast.StringValue]:
        """
        Description : StringValue
        """
        next_ = self.peek()
        return (
            self.parse_string_literal()
            if (next_.__class__ is String or next_.__class__ is BlockString)
            else None
        )

    def parse_schema_definition(self) -> _ast.SchemaDefinition:
        """
        SchemaDefinition : schema Directives[Const]? { OperationTypeDefinition+ }
        """
        start = self.peek()
        self.expect_keyword("schema")
        return _ast.SchemaDefinition(
            directives=self.parse_directives(True),
            operation_types=self.many(
                CurlyOpen, self.parse_operation_type_definition, CurlyClose
            ),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_operation_type_definition(self) -> _ast.OperationTypeDefinition:
        """
        OperationTypeDefinition : OperationType : NamedType
        """
        start = self.peek()
        operation = self.parse_operation_type()
        self.expect(Colon)
        return _ast.OperationTypeDefinition(
            operation=operation,
            type=self.parse_named_type(),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_scalar_type_definition(self) -> _ast.ScalarTypeDefinition:
        """
        ScalarTypeDefinition : Description? scalar Name Directives[Const]?
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("scalar")
        return _ast.ScalarTypeDefinition(
            description=desc,
            name=self.parse_name(),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_object_type_definition(self) -> _ast.ObjectTypeDefinition:
        """
        ObjectTypeDefinition : Description? type Name ImplementsInterfaces? \
        Directives[Const]? FieldsDefinition?
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
            source=self._source,
        )

    def parse_implements_interfaces(self) -> List[_ast.NamedType]:
        """
        ImplementsInterfaces : implements `&`? NamedType \
        | ImplementsInterfaces & NamedType
        """
        token = self.peek()
        types = []
        if token.value == "implements":
            self.advance()
            self.skip(Ampersand)
            while True:
                types.append(self.parse_named_type())
                if not self.skip(Ampersand):
                    break
        return types

    def parse_fields_definition(self) -> List[_ast.FieldDefinition]:
        """
        FieldsDefinition : { FieldDefinition+ }
        """
        if self.peek().__class__ is CurlyOpen:
            return self.many(CurlyOpen, self.parse_field_definition, CurlyClose)
        return []

    def parse_field_definition(self) -> _ast.FieldDefinition:
        """
        FieldDefinition : \
        Description? Name ArgumentsDefinition? : Type Directives[Const]?
        """
        start = self.peek()
        desc, name = self.parse_description(), self.parse_name()
        args = self.parse_argument_definitions()
        self.expect(Colon)
        return _ast.FieldDefinition(
            description=desc,
            name=name,
            arguments=args,
            type=self.parse_type_reference(),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_argument_definitions(self) -> List[_ast.InputValueDefinition]:
        """
        ArgumentsDefinition : ( InputValueDefinition+ )
        """
        return (
            self.many(ParenOpen, self.parse_input_value_definition, ParenClose)
            if self.peek().__class__ is ParenOpen
            else []
        )

    def parse_input_value_definition(self) -> _ast.InputValueDefinition:
        """
        InputValueDefinition : \
        Description? Name : Type DefaultValue? Directives[Const]?
        """
        start = self.peek()
        desc, name = self.parse_description(), self.parse_name()
        self.expect(Colon)
        return _ast.InputValueDefinition(
            description=desc,
            name=name,
            type=self.parse_type_reference(),
            default_value=(
                cast(_ast.Value, self.parse_value_literal(True))
                if self.skip(Equals)
                else None
            ),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_interface_type_definition(self) -> _ast.InterfaceTypeDefinition:
        """
        InterfaceTypeDefinition : \
        Description? interface Name Directives[Const]? FieldsDefinition?
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
            source=self._source,
        )

    def parse_union_type_definition(self) -> _ast.UnionTypeDefinition:
        """
        UnionTypeDefinition : \
        Description? union Name Directives[Const]? UnionMemberTypes?
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
            source=self._source,
        )

    def parse_union_member_types(self) -> List[_ast.NamedType]:
        """
        UnionMemberTypes : = `|`? NamedType | UnionMemberTypes | NamedType
        """
        if self.skip(Equals):
            return self.delimited_list(Pipe, self.parse_named_type)
        return []

    def parse_enum_type_definition(self) -> _ast.EnumTypeDefinition:
        """
        EnumTypeDefinition : \
        Description? enum Name Directives[Const]? EnumValuesDefinition?
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
            source=self._source,
        )

    def parse_enum_values_definition(self) -> List[_ast.EnumValueDefinition]:
        """
        EnumValuesDefinition : { EnumValueDefinition+ }
        """
        return (
            self.many(CurlyOpen, self.parse_enum_value_definition, CurlyClose)
            if self.peek().__class__ is CurlyOpen
            else []
        )

    def parse_enum_value_definition(self) -> _ast.EnumValueDefinition:
        """
        EnumValueDefinition : Description? EnumValue Directives[Const]?

        - EnumValue : Name
        """
        start = self.peek()
        return _ast.EnumValueDefinition(
            description=self.parse_description(),
            name=self.parse_name(),
            directives=self.parse_directives(True),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_input_object_type_definition(
        self,
    ) -> _ast.InputObjectTypeDefinition:
        """
        InputObjectTypeDefinition : \
        Description? input Name Directives[Const]? InputFieldsDefinition?
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
            source=self._source,
        )

    def parse_input_fields_definition(self) -> List[_ast.InputValueDefinition]:
        """
        InputFieldsDefinition : { InputValueDefinition+ }
        """
        return (
            self.many(CurlyOpen, self.parse_input_value_definition, CurlyClose)
            if self.peek().__class__ is CurlyOpen
            else []
        )

    def parse_type_system_extension(self) -> _ast.TypeSystemExtension:
        """
        TypeSystemExtension : SchemaExtension | TypeExtension

        - TypeExtension : ScalarTypeExtension | ObjectTypeExtension | \
        InterfaceTypeExtension | UnionTypeExtension | EnumTypeExtension | \
        InputObjectTypeDefinition
        """
        keyword = self.peek(2)
        if keyword.__class__ is Name:
            if keyword.value == "schema":
                return self.parse_schema_extension()
            elif keyword.value == "scalar":
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

        raise _unexpected(keyword, keyword.start, self._lexer._source)

    def parse_schema_extension(self) -> _ast.SchemaExtension:
        """
        SchemaExtension : extend schema Directives[Const] \
        { [OperationTypeDefinition] } | extend schema Directives[Const]
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("schema")
        directives = self.parse_directives(True)
        if self.peek().__class__ is CurlyOpen:
            operation_types = self.many(
                CurlyOpen, self.parse_operation_type_definition, CurlyClose
            )
        else:
            operation_types = []
        return _ast.SchemaExtension(
            directives=directives,
            operation_types=operation_types,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_scalar_type_extension(self) -> _ast.ScalarTypeExtension:
        """
        ScalarTypeExtension : extend scalar Name Directives[Const]
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("scalar")
        name = self.parse_name()
        directives = self.parse_directives(True)
        if not directives:
            raise _unexpected(start, start.start, self._lexer._source)
        return _ast.ScalarTypeExtension(
            name=name,
            directives=directives,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_object_type_extension(self) -> _ast.ObjectTypeExtension:
        """
        ObjectTypeExtension : \
        extend type Name ImplementsInterfaces? Directives[Const]? FieldsDefinition \
        | extend type Name ImplementsInterfaces? Directives[Const] \
        | extend type Name ImplementsInterfaces
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
            raise _unexpected(tok, tok.start, self._lexer._source)
        return _ast.ObjectTypeExtension(
            name=name,
            interfaces=interfaces,
            directives=directives,
            fields=fields,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_interface_type_extension(self) -> _ast.InterfaceTypeExtension:
        """
        InterfaceTypeExtension : \
        extend interface Name Directives[Const]? FieldsDefinition \
        | extend interface Name Directives[Const]
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("interface")
        name = self.parse_name()
        directives = self.parse_directives(True)
        fields = self.parse_fields_definition()
        if (not directives) and (not fields):
            tok = self.peek()
            raise _unexpected(tok, tok.start, self._lexer._source)

        return _ast.InterfaceTypeExtension(
            name=name,
            directives=directives,
            fields=fields,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_union_type_extension(self) -> _ast.UnionTypeExtension:
        """
        UnionTypeExtension : \
        | extend union Name Directives[Const]? UnionMemberTypes \
        | extend union Name Directives[Const]
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("union")
        name = self.parse_name()
        directives = self.parse_directives(True)
        types = self.parse_union_member_types()
        if (not directives) and (not types):
            tok = self.peek()
            raise _unexpected(tok, tok.start, self._lexer._source)

        return _ast.UnionTypeExtension(
            name=name,
            directives=directives,
            types=types,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_enum_type_extension(self) -> _ast.EnumTypeExtension:
        """
        EnumTypeExtension : \
        extend enum Name Directives[Const]? EnumValuesDefinition \
        | extend enum Name Directives[Const]
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("enum")
        name = self.parse_name()
        directives = self.parse_directives(True)
        values = self.parse_enum_values_definition()
        if (not directives) and (not values):
            tok = self.peek()
            raise _unexpected(tok, tok.start, self._lexer._source)

        return _ast.EnumTypeExtension(
            name=name,
            directives=directives,
            values=values,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_input_object_type_extension(
        self,
    ) -> _ast.InputObjectTypeExtension:
        """
        InputObjectTypeExtension : \
        extend input Name Directives[Const]? InputFieldsDefinition \
        | extend input Name Directives[Const]
        """
        start = self.peek()
        self.expect_keyword("extend")
        self.expect_keyword("input")
        name = self.parse_name()
        directives = self.parse_directives(True)
        fields = self.parse_input_fields_definition()
        if (not directives) and (not fields):
            raise _unexpected("", start.start, self._lexer._source)

        return _ast.InputObjectTypeExtension(
            name=name,
            directives=directives,
            fields=fields,
            loc=self._loc(start),
            source=self._source,
        )

    def parse_directive_definition(self) -> _ast.DirectiveDefinition:
        """
        DirectiveDefinition : Description? directive @ Name \
        ArgumentsDefinition? on DirectiveLocations
        """
        start = self.peek()
        desc = self.parse_description()
        self.expect_keyword("directive")
        self.expect(At)
        name = self.parse_name()
        args = self.parse_argument_definitions()
        self.expect_keyword("on")
        return _ast.DirectiveDefinition(
            description=desc,
            name=name,
            arguments=args,
            locations=self.parse_directive_locations(),
            loc=self._loc(start),
            source=self._source,
        )

    def parse_directive_locations(self) -> List[_ast.Name]:
        """
        DirectiveLocations : \
        `|`? DirectiveLocation `|` DirectiveLocations `|` DirectiveLocation
        """
        return self.delimited_list(Pipe, self.parse_directive_location)

    def parse_directive_location(self) -> _ast.Name:
        """
        DirectiveLocation : ExecutableDirectiveLocation \
        | TypeSystemDirectiveLocation

        - ExecutableDirectiveLocation : one of QUERY MUTATION SUBSCRIPTION FIELD \
        FRAGMENT_DEFINITION FRAGMENT_SPREAD INLINE_FRAGMENT

        - TypeSystemDirectiveLocation : one of SCHEMA SCALAR OBJECT FIELD_DEFINITION \
        ARGUMENT_DEFINITION INTERFACE UNION ENUM ENUM_VALUE INPUT_OBJECT \
        INPUT_FIELD_DEFINITION

        Returns:
            py_gql.lang.ast.Name:
        """
        start = self.peek()
        name = self.parse_name()
        if name.value in DIRECTIVE_LOCATIONS:
            return name
        raise _unexpected(
            "Unexpected Name %s" % name.value, start.start, self._lexer._source
        )
