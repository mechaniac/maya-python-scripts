"""KV3 (KeyValues3) text format parser.

Parses Valve's KV3 text encoding into Python dicts and lists.
Used to read .vmdl, .vmdl_prefab, and decompiled .vmat files.
"""

import re


def parse(text):
    """Parse KV3 text into a Python object (dict, list, or scalar)."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    tokens = _tokenize(text)
    pos = [0]
    result = _parse_value(tokens, pos)
    return result


_TOKEN_SPEC = [
    ('COMMENT_LINE',  r'//[^\n]*'),
    ('COMMENT_BLOCK', r'/\*.*?\*/'),
    ('RESOURCE',      r'resource:"(?:[^"\\]|\\.)*"'),
    ('MSTRING',       r'"""[\s\S]*?"""'),
    ('STRING',        r'"(?:[^"\\]|\\.)*"'),
    ('NUMBER',        r'-?\d+\.?\d*(?:[eE][+-]?\d+)?'),
    ('BOOL',          r'\b(?:true|false)\b'),
    ('NULL',          r'\bnull\b'),
    ('IDENT',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('LBRACE',        r'\{'),
    ('RBRACE',        r'\}'),
    ('LBRACKET',      r'\['),
    ('RBRACKET',      r'\]'),
    ('EQUALS',        r'='),
    ('COMMA',         r','),
    ('WS',            r'[ \t\n\r]+'),
]

_TOK_RE = re.compile(
    '|'.join(f'(?P<{name}>{pat})' for name, pat in _TOKEN_SPEC)
)

_SKIP = frozenset(('WS', 'COMMENT_LINE', 'COMMENT_BLOCK'))


def _tokenize(text):
    tokens = []
    for m in _TOK_RE.finditer(text):
        kind = m.lastgroup
        if kind not in _SKIP:
            tokens.append((kind, m.group()))
    return tokens


def _peek(tokens, pos):
    return tokens[pos[0]] if pos[0] < len(tokens) else (None, None)


def _unescape(s):
    return (s.replace("\\'", "'")
             .replace('\\"', '"')
             .replace('\\\\', '\\')
             .replace('\\n', '\n')
             .replace('\\t', '\t'))


def _parse_value(tokens, pos):
    kind, val = _peek(tokens, pos)
    if kind is None:
        return None
    if kind == 'LBRACE':
        return _parse_object(tokens, pos)
    if kind == 'LBRACKET':
        return _parse_array(tokens, pos)
    if kind == 'STRING':
        pos[0] += 1
        return _unescape(val[1:-1])
    if kind == 'MSTRING':
        pos[0] += 1
        return val[3:-3]
    if kind == 'RESOURCE':
        pos[0] += 1
        return _unescape(val[len('resource:') + 1:-1])
    if kind == 'NUMBER':
        pos[0] += 1
        return float(val) if ('.' in val or 'e' in val.lower()) else int(val)
    if kind == 'BOOL':
        pos[0] += 1
        return val == 'true'
    if kind == 'NULL':
        pos[0] += 1
        return None
    raise ValueError(f"Unexpected token: {kind}={val!r} at index {pos[0]}")


def _parse_object(tokens, pos):
    pos[0] += 1  # skip {
    obj = {}
    while True:
        kind, val = _peek(tokens, pos)
        if kind == 'RBRACE' or kind is None:
            break
        if kind == 'IDENT':
            key = val
        elif kind == 'STRING':
            key = _unescape(val[1:-1])
        else:
            raise ValueError(f"Expected key, got {kind}={val!r}")
        pos[0] += 1
        eq_kind, _ = _peek(tokens, pos)
        if eq_kind != 'EQUALS':
            raise ValueError(f"Expected '=', got {eq_kind}")
        pos[0] += 1
        obj[key] = _parse_value(tokens, pos)
    if _peek(tokens, pos)[0] == 'RBRACE':
        pos[0] += 1
    return obj


def _parse_array(tokens, pos):
    pos[0] += 1  # skip [
    arr = []
    while True:
        kind, _ = _peek(tokens, pos)
        if kind == 'RBRACKET' or kind is None:
            break
        arr.append(_parse_value(tokens, pos))
        if _peek(tokens, pos)[0] == 'COMMA':
            pos[0] += 1
    if _peek(tokens, pos)[0] == 'RBRACKET':
        pos[0] += 1
    return arr
