# -*- coding: utf-8 -*-
""" Work with strings """

import re

import six

from ._utils import OrderedDict


LINE_SEPARATOR = re.compile(r"\r\n|[\n\r]")
LEADING_WS = re.compile(r"^[\t\s]*")


def ensure_unicode(string):
    if isinstance(string, six.binary_type):
        return string.decode("utf8")
    return string


def leading_whitespace(string):
    r"""
    :type string: str
    :rtype: int

    >>> leading_whitespace('  \t  foo')
    5
    >>> leading_whitespace('\tfoo')
    1
    >>> leading_whitespace('   foo')
    3
    """
    return len(string) - len(LEADING_WS.sub("", string))


def is_blank(string):
    """
    :type string: str
    :rtype: bool
    """
    return not string.strip()


def parse_block_string(
    raw_string, strip_trailing_newlines=True, strip_leading_newlines=True
):
    r""" Parse a raw string according to the GraphQL spec's BlockStringValue()
    http://facebook.github.io/graphql/draft/#BlockStringValue() static
    algorithm. Similar to Coffeescript's block string, Python's docstring trim
    or Ruby's strip_heredoc.

    See https://github.com/facebook/graphql/pull/327 and
    http://facebook.github.io/graphql/draft/#sec-String-Value for information
    on the implementation as this is not in the published spec at the time
    of writing (in the Draft though).

    :type raw_string: str
    :rtype: str
    """
    lines = LINE_SEPARATOR.split(raw_string)
    common_indent = None

    for i, line in enumerate(lines):
        if i == 0:
            continue
        indent = leading_whitespace(line)
        if indent < len(line) and (
            common_indent is None or indent < common_indent
        ):
            common_indent = indent

    if common_indent:
        lines = [
            line[common_indent:]
            if (len(line) >= common_indent and i > 0)
            else line
            for i, line in enumerate(lines)
        ]

    while strip_leading_newlines and lines and is_blank(lines[0]):
        lines.pop(0)

    while strip_trailing_newlines and lines and is_blank(lines[-1]):
        lines.pop()

    return "\n".join(lines)


dedent = lambda s: parse_block_string(s, strip_trailing_newlines=False)


def index_to_loc(body, position):
    r""" Get the (lineno, col) tuple from a zero-indexed offset.

    :type body: py_gql.lang.source.Source|str
    :type index: int
    :rtype: tuple(int, int)

    >>> index_to_loc("ab\ncd\ne", 0)
    (1, 1)

    >>> index_to_loc("ab\ncd\ne", 3)
    (2, 1)

    >>> index_to_loc("", 0)
    (1, 1)

    >>> index_to_loc("{", 1)
    (1, 2)

    >>> index_to_loc("", 42)
    Traceback (most recent call last):
        ...
    IndexError: 42
    """
    if not body and not position:
        return (1, 1)

    if position > len(body):
        raise IndexError(position)

    lines, cols = 0, 0
    for offset, char in enumerate(body):
        if offset == position:
            return (lines + 1, cols + 1)
        elif char == "\n":
            lines += 1
            cols = 0
        else:
            cols += 1
    return (lines + 1, cols + 1)


def loc_to_index(body, loc):
    r""" Get the zero-indexed offset from a (lineno, col) tuple.

    :type body: py_gql.lang.source.Source|str
    :type loc: tuple(int, int)
    :rtype: int

    >>> loc_to_index("ab\ncd\ne", (1, 1))
    0

    >>> loc_to_index("", (1, 1))
    0

    >>> loc_to_index("ab\ncd\ne", (2, 1))
    3

    >>> loc_to_index("{", (1, 2))
    1

    >>> loc_to_index("ab\ncd\ne", (6, 7))
    Traceback (most recent call last):
        ...
    IndexError: 6:7
    """
    if not body and loc == (1, 1):
        return 0

    lineo, col = loc
    lines = 0
    for index, char in enumerate(body):
        if lines == lineo - 1:
            if len(body) >= index + col - 1:
                return index + col - 1
            break
        if char == "\n":
            lines += 1
    raise IndexError("%s:%s" % (lineo, col))


def highlight_location(body, position, delta=2):
    """ Nicely format a position in a source string.

    :type body: py_gql.lang.source.Source|str
    :type position: int
    :type delta: int
    :rtype: str

    >>> print(highlight_location('''{
    ...     query {
    ...         Node (search: "foo") {
    ...             id
    ...             name
    ...         }
    ...     }
    ... }''', 40))
    (3:27):
      1:{
      2:    query {
      3:        Node (search: "foo") {
                                  ^
      4:            id
      5:            name
    """
    # [REVIEW] Hackish for now, but There mist be a more readable way to write
    # this
    line, col = index_to_loc(body, position)
    line_index = line - 1
    lines = LINE_SEPARATOR.split(body)
    min_line = max(0, line_index - delta)
    max_line = min(line_index + delta, len(lines) - 1)
    pad_len = len(str(max_line + 1))

    def ws(len_):
        return "".join((" " for _ in range(len_)))

    def lineno(l):
        return " ".join(range(pad_len - len(str(l + 1)))) + str(l + 1)

    output = ["(%d:%d):" % (line, col)]
    output.extend(
        [
            ws(2) + lineno(l) + ":" + lines[l]
            for l in range(min_line, line_index)
        ]
    )
    output.append(ws(2) + lineno(line_index) + ":" + lines[line_index])
    output.append(ws(2) + ws(len(str(max_line + 1)) + col) + "^")
    output.extend(
        [
            ws(2) + lineno(l) + ":" + lines[l]
            for l in range(line_index + 1, max_line + 1)
        ]
    )
    return "\n".join(output)


def _split_words_with_boundaries(string, word_boundaries):
    """
    >>> list(_split_words_with_boundaries("ab cd -ef_gh", " -_"))
    ['ab', ' ', 'cd', ' ', '-', 'ef', '_', 'gh']
    """
    stack = []
    for char in string:
        if char in word_boundaries:
            if stack:
                yield "".join(stack)
            yield char
            stack[:] = []
        else:
            stack.append(char)

    if stack:
        yield "".join(stack)


def wrapped_lines(lines, max_len, word_boundaries=" -_"):
    """ Generator of wrapped strings in a source iterator to a given length.
    """
    for line in lines:
        if len(line) <= max_len:
            yield line
            continue

        wrapped = ""

        for entry in _split_words_with_boundaries(line, word_boundaries):
            if len(wrapped + entry) > max_len:
                yield wrapped
                wrapped = ""
            if entry != " " or wrapped:
                wrapped += entry

        if wrapped:
            yield wrapped


def levenshtein(s1, s2):
    """ Compute the Levenshtein edit distance between 2 strings.

    :type s1: str
    :param s1:

    :type s2: str
    :param s2:

    :rtype: int
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def infer_suggestions(candidate, options, distance=levenshtein):
    """ Extract the most similar entries to an input string from multiple options

    :type candidate: str
    :param candidate:

    :type options: List[str]
    :param options:

    :type distance: (str, str) -> int
    :param distance:

    :rtype: List[str]
    """
    distances = OrderedDict()
    half = len(candidate) / 2
    for option in options:
        distance = levenshtein(candidate, option)
        threshold = max(half, len(option) / 2, 1)
        if distance <= threshold:
            distances[option] = distance
    return sorted(distances.keys(), key=distances.get)


def quoted_options_list(options):
    """ Quote a list of strings

    :type options: List[str]
    :param options:

    :rtype: str

    >>> quoted_options_list([])
    ''

    >>> quoted_options_list(['foo'])
    '"foo"'

    >>> quoted_options_list(['foo', 'bar'])
    '"foo" or "bar"'

    >>> quoted_options_list(['foo', 'bar', 'baz'])
    '"foo", "bar" or "baz"'
    """
    if not options:
        return ""

    if len(options) == 1:
        return '"%s"' % options[0]

    return "%s or %s" % (
        ", ".join(('"%s"' % option for option in options[:-1])),
        '"%s"' % options[-1],
    )
