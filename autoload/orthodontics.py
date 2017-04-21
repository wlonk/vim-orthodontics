"""
Remember: when accessing a thing in a buffer, the rows are 1-indexed
and the columns are 0-indexed.
"""

import vim
import sys
import os

libs = os.path.join(vim.eval('expand(s:plugin_path)'), 'libs')
sys.path.insert(0, libs)

import grammar  # noqa: E402


DELIMITERS = {
    '(': ')',
    '[': ']',
    '{': '}',
}
REVERSE_DELIMITERS = {v: k for (k, v) in DELIMITERS.items()}

OPENING_DELIMITERS = DELIMITERS.keys()
CLOSING_DELIMITERS = DELIMITERS.values()


def get_char_at(buffer, row, col):
    try:
        return buffer[row - 1][col]
    except IndexError:
        message = "Error at {}, {}".format(row - 1, col)
        raise IndexError(message)


def get_prev_char(buffer, row, col):
    col -= 1
    while col < 0:
        row -= 1
        if row <= 0:
            return None, None, None
        col = len(buffer[row - 1]) - 1
    return get_char_at(buffer, row, col), row, col


def get_next_char(buffer, row, col):
    col += 1
    row_len = len(buffer[row - 1])
    while col >= row_len:
        row += 1
        if row > len(buffer):
            return None, None, None
        col = 0
        row_len = len(buffer[row - 1])
    return get_char_at(buffer, row, col), row, col


def get_text_between(buffer, start_row, start_col, end_row, end_col):
    ret = []
    row = start_row
    col = start_col
    try:
        char = get_char_at(buffer, row, col)
    except IndexError:
        return ''
    while char is not None:
        ret.append(char)
        char, row, col = get_next_char(buffer, row, col)
        excessive_row = row is not None and row > end_row
        excessive_col = col is not None and col > end_col
        if excessive_row or excessive_col:
            break
    return ''.join(ret)


def _find_delimiter(
        buffer, row, col, get_fn, first_delim, second_delim, delim_lookup):
    delimiter_stack = []
    while True:
        char, row, col = get_fn(buffer, row, col)
        if char is None:
            break
        if char in first_delim:
            delimiter_stack.append(char)
        if char in second_delim:
            try:
                top = delimiter_stack[-1]
            except IndexError:
                return char, row, col
            else:
                if top == delim_lookup[char]:
                    delimiter_stack.pop()
                else:
                    return char, row, col
    return None, None, None


def find_opening_delimiter(buffer, row, col):
    return _find_delimiter(
        buffer,
        row,
        col,
        get_prev_char,
        CLOSING_DELIMITERS,
        OPENING_DELIMITERS,
        DELIMITERS,
    )


def find_closing_delimiter(buffer, row, col):
    return _find_delimiter(
        buffer,
        row,
        col,
        get_next_char,
        OPENING_DELIMITERS,
        CLOSING_DELIMITERS,
        REVERSE_DELIMITERS,
    )


buffer = vim.current.buffer
row, col = vim.current.window.cursor
opening_triple = find_opening_delimiter(buffer, row, col)
closing_triple = find_closing_delimiter(buffer, row, col)

# Get characters in range
_, start_row, start_col = opening_triple
_, end_row, end_col = closing_triple

if start_row is None or end_row is None:
    pass
else:
    text = get_text_between(buffer, start_row, start_col, end_row, end_col)

    tree = grammar.Visitor().parse(text)

    # Re-insert in that area.
    replacement_text = tree.outline()

    char, row, col = opening_triple
    vim.command("call cursor({}, {})".format(row, col + 1))
    vim.command("normal ca{}".format(char))
    vim.command("normal l")
    vim.command("normal i{}".format(replacement_text))
