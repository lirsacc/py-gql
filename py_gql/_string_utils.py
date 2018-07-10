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
    r""" Detect of leading whitespace in a string.

    Args:
        string (str): Input value

    Returns:
        int: Length of leading whitespace

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
    Args:
        string (str): Input value

    Returns:
        bool: Whether the string is blank
    """
    return not string.strip()


def parse_block_string(
    raw_string, strip_trailing_newlines=True, strip_leading_newlines=True
):
    """ Parse a raw string according to the GraphQL spec's BlockStringValue()
    http://facebook.github.io/graphql/draft/#BlockStringValue() static
    algorithm. Similar to Coffeescript's block string, Python's docstring trim
    or Ruby's strip_heredoc.

    Args:
        raw_string (str): Input value
        strip_trailing_newlines (bool): Remove trailing newlines
        strip_leading_newlines (bool): Remove leading newlines

    Returns:
        str: Block string value
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


def loc_to_index(body, loc):
    r""" Get the zero-indexed offset from a (lineno, col) tuple.

    Args:
        body (str): Source string
        loc (Tuple[int, int]): (line number, column number)

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
    """ Nicely format a highlited view of a position into a source string.

    Args:
        body (str): Source string
        position (int): 0-indexed position of the character
        delta (int): How many lines around the position should this conserve

    Returns:
        str: Formatted view

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


def levenshtein(s1, s2):
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
    """ Extract the most similar entries to an input string given multiple
    options and a distance function.

    Args:
        candidate (str): Input string
        options (Iterator[str]): Possible options
        distance (callable):
            Distance function, must have the signature ``(s1, s2) -> int``
            where the more similar the inputs are, the lower the result is.

    Returns:
        List[str]: Most similar options sorted by similarity (most similar to
        least similar)
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


def stringify_path(path):
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
