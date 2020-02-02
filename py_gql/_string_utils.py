# -*- coding: utf-8 -*-
""" Work with strings """

import re
import sys
import textwrap
from typing import (
    Callable,
    Container,
    Iterable,
    Iterator,
    List,
    Sequence,
    Tuple,
    Union,
)

LINE_SEPARATOR = re.compile(r"\r\n|[\n\r]")

ResponsePath = Sequence[Union[int, str]]


def ensure_unicode(string: Union[str, bytes]) -> str:
    if isinstance(string, bytes):
        return string.decode("utf8")
    return string


def is_blank(string: str) -> bool:
    """
    Args:
        string (str): Input value

    Returns:
        bool: Whether the string is blank
    """
    return not string.strip()


def parse_block_string(raw_string: str) -> str:
    """ Parse a raw string according to the GraphQL spec's BlockStringValue()
    http://facebook.github.io/graphql/draft/#BlockStringValue() static
    algorithm. Similar to Coffeescript's block string, Python's inspect.cleandoc
    or Ruby's strip_heredoc.

    Compared to Python's default behaviour, this does not remove leading
    whitespace from the first line.
    """
    lines = raw_string.splitlines()

    common_indent = sys.maxsize

    for line in lines[1:]:
        inner_len = len(line.lstrip())
        if inner_len:
            common_indent = min(common_indent, len(line) - inner_len)

    if common_indent < sys.maxsize:
        for i, line in enumerate(lines[1:]):
            lines[i + 1] = line[common_indent:]

    while lines and (not lines[0].lstrip()):
        lines.pop(0)

    while lines and (not lines[-1].lstrip()):
        lines.pop()

    return "\n".join(lines)


# Kept for compatibility (only used in tests)
def dedent(raw_string: str) -> str:
    return textwrap.dedent(raw_string).lstrip()


def index_to_loc(body: str, position: int) -> Tuple[int, int]:
    r""" Get the (line number, column number) tuple from a zero-indexed offset.

    Args:
        body (str): Source string
        position (int): 0-indexed position of the character

    Returns:
        Tuple[int, int]: (line number, column number)

    Raises:
        :py:class:`IndexError`: if ``position`` is out of bounds

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

    if position > len(body) or position < 0:
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


def loc_to_index(body: str, loc: Tuple[int, int]) -> int:
    r""" Get the zero-indexed offset from a (lineno, col) tuple.

    Args:
        body: Source string
        loc: (line number, column number)

    Returns:
        int: 0-indexed position of the character

    Raises:
        :py:class:`IndexError`: if ``loc`` is out of bounds

    >>> loc_to_index("ab\ncd\ne", (1, 1))
    0

    >>> loc_to_index("", (1, 1))
    0

    >>> loc_to_index("ab\ncd\ne", (2, 1))
    3

    >>> loc_to_index("{", (1, 2))
    1

    >>> loc_to_index("{       ", (1, 3))
    2

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


def highlight_location(body: str, position: int, delta: int = 2) -> str:
    """ Nicely format a highlited view of a position into a source string.

    Args:
        body (str): Source string
        position (int): 0-indexed position of the character
        delta (int): How many lines around the position should this conserve

    Returns:
        str: Formatted view
    """
    # REVIEW: There must be a more readable way to write this
    line, col = index_to_loc(body, position)
    line_index = line - 1
    lines = LINE_SEPARATOR.split(body)
    min_line = max(0, line_index - delta)
    max_line = min(line_index + delta, len(lines) - 1)
    pad_len = len(str(max_line + 1))

    def ws(len_):
        return "".join((" " for _ in range(len_)))

    def lineno(l):
        m = l + 1
        return " ".join(str(x) for x in range(pad_len - len(str(m)))) + str(m)

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
    return "\n".join(output) + "\n"


def _split_words_with_boundaries(
    string: str, word_boundaries: Container[str]
) -> Iterator[str]:
    """
    >>> list(_split_words_with_boundaries("ab cd -ef_gh", " -_"))
    ['ab', ' ', 'cd', ' ', '-', 'ef', '_', 'gh']
    """
    stack = []  # type: List[str]
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


def wrapped_lines(
    lines: Iterable[str], max_len: int, word_boundaries: Container[str] = " -_"
) -> Iterator[str]:
    """ Wrap provided lines to a given length.

    Lines that are under ``max_len`` are left as is, otherwise this splits
    them based on the specified word boundaries and yields parts of the line
    that under ``max_len`` until the line has been exhausted,

    Args:
        lines (Iterator[str]): Source lines
        max_len (int): Maximum line length
        word_boundaries (Iterator[str]): Which charcaters are used to split lines

    Yields:
        str: The next wrapped line
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


def levenshtein(s1: str, s2: str) -> int:
    """ Compute the Levenshtein edit distance between 2 strings.

    Args:
        s1 (str): First string
        s2 (str): Second string

    Returns:
        int: Computed edit distance
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def infer_suggestions(
    candidate: str,
    options: Iterable[str],
    distance: Callable[[str, str], int] = levenshtein,
) -> List[str]:
    """ Extract the most similar entries to an input string given multiple
    options and a distance function.

    Args:
        candidate (str): Input string
        options (Iterator[str]): Possible options
        distance (callable):
            Distance function, must have the signature ``(s1, s2) -> int``
            where the more similar the inputs are, the lower the result is.

    Returns:
        Most similar options sorted by similarity (most similar to least similar)
    """
    distances = []
    half = len(candidate) / 2
    for option in options:
        dist = distance(candidate, option)
        threshold = max(half, len(option) / 2, 1)
        if dist <= threshold:
            distances.append((option, dist))
    return [opt for opt, _ in sorted(distances, key=lambda s: s[1])]


def quoted_options_list(options: Sequence[str]) -> str:
    """ Quote a list of possible strings.

    Args:
        options (Iterator[str]): Possible options

    Returns:
        str: Quoted options

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


def stringify_path(path: ResponsePath) -> str:
    """ Concatenate traversal path into a string.

    >>> stringify_path(['foo', 0, 'bar'])
    'foo[0].bar'

    >>> stringify_path(['foo'])
    'foo'

    >>> stringify_path([1, 'foo'])
    '[1].foo'

    >>> stringify_path([])
    ''
    """
    path_str = ""
    for entry in path:
        if isinstance(entry, int):
            path_str += "[%s]" % entry
        else:
            path_str += ".%s" % entry
    return path_str.lstrip(".")


def snakecase_to_camelcase(value: str) -> str:
    """
    >>> snakecase_to_camelcase('')
    ''

    >>> snakecase_to_camelcase('foo')
    'foo'

    >>> snakecase_to_camelcase('foo_bar_baz')
    'fooBarBaz'

    >>> snakecase_to_camelcase('fooBarBaz')
    'fooBarBaz'
    """
    if not value:
        return value

    head, *tail = value.split("_")
    return head[0].lower() + head[1:] + "".join(s.title() for s in tail)


def camelcase_to_snakecase(value: str) -> str:
    """
    >>> camelcase_to_snakecase('')
    ''

    >>> camelcase_to_snakecase('foo')
    'foo'

    >>> camelcase_to_snakecase('fooBarBaz')
    'foo_bar_baz'

    >>> camelcase_to_snakecase('foo_bar_baz')
    'foo_bar_baz'
    """
    value = re.sub(r"[\-\.\s]", "_", value)

    if not value:
        return value

    return value[0].lower() + re.sub(
        r"[A-Z]", lambda matched: "_" + matched.group(0).lower(), value[1:]
    )
