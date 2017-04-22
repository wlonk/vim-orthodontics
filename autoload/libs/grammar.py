import six

from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor


# TODO: handle escaped quotes
g = Grammar(
    r"""
expression
    = braces_exp
    / parens_exp
    / brackt_exp
    / tokens

braces_exp = '{' ws expression ws '}'
parens_exp = '(' ws expression ws ')'
brackt_exp = '[' ws expression ws ']'
tokens = token (ws sep ws (expression)?)?

sep = ','

token
    = key_value
    / quoted_string
    / ~r"[0-9A-Za-z_]+"

quoted_string
    = single_quotes
    / double_quotes

key_value
    = k1
    / k2
    / k3
    / k4

k1 = key ws ":" ws braces_exp
k2 = key ws ":" ws parens_exp
k3 = key ws ":" ws brackt_exp
k4 = key ws ":" ws token

key
    = quoted_string
    / ~r"[0-9A-Za-z_]+"

single_quotes = "'" ~"[^']*" "'"
double_quotes = '"' ~'[^"]*' '"'

ws = ~r"[ \t\n\r]*"
    """)


class Expression(object):
    def __init__(self, prefix, suffix, children):
        self.prefix = prefix
        self.suffix = suffix
        self.children = children
        self.parent = None

    @property
    def indent(self):
        if self.parent is None:
            return 0
        return self.parent.indent + 1

    def inline(self):
        return u"{prefix}{content}{suffix}".format(
            prefix=self.prefix,
            content=u", ".join(
                c.inline() for c in self.children
            ),
            suffix=self.suffix,
        )

    def outline(self):
        indent = u"    " * self.indent
        inner_indent = indent + u"    "
        return u"{prefix}\n{content}\n{indent}{suffix}".format(
            indent=indent,
            prefix=self.prefix,
            content=u",\n".join(
                u"{}{}".format(
                    inner_indent,
                    c.outline(),
                ) for c in self.children
            ) + u",",
            suffix=self.suffix,
        )


class KVNode(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.parent = None

    @property
    def indent(self):
        if self.parent is None:
            return 0
        return self.parent.indent + 1

    def inline(self):
        return u"{}: {}".format(
            self.key,
            self.value.inline(),
        )

    def outline(self):
        return u"{}: {}".format(
            self.key,
            self.value.outline(),
        )


class TextNode(object):
    def __init__(self, text):
        self.text = text

    def inline(self):
        return u"{}".format(self.text)

    outline = inline


class Visitor(NodeVisitor):
    grammar = g

    def visit_token(self, node, token):
        token = token[0]
        if isinstance(token, six.string_types):
            return TextNode(token)
        if isinstance(token, KVNode):
            return token
        return TextNode(token.text)

    def visit_tokens(self, node, tokens):
        car, cdr = tokens
        if cdr and isinstance(cdr, list) and len(cdr):
            try:
                cdr = cdr[0][3][0]
            except (TypeError, IndexError):
                return [car]
            else:
                return [car] + cdr
        return [car]

    def visit_expression(self, node, expression):
        return expression[0]

    def handle_visit_surrounded(self, prefix, exp, suffix):
        _, _, exp, _, _ = exp
        if isinstance(exp, Expression):
            exp = [exp]
        ret = Expression(prefix=prefix, children=exp, suffix=suffix)
        if isinstance(exp[0], Expression):
            exp[0].parent = ret
        return ret

    def visit_braces_exp(self, node, braces_exp):
        return self.handle_visit_surrounded("{", braces_exp, "}")

    def visit_parens_exp(self, node, parens_exp):
        return self.handle_visit_surrounded("(", parens_exp, ")")

    def visit_brackt_exp(self, node, brackt_exp):
        return self.handle_visit_surrounded("[", brackt_exp, "]")

    def visit_sep(self, node, sep):
        return

    def handle_kv(self, kv):
        key, _, _, _, value = kv
        if isinstance(value, list):
            value = value[0]
        ret = KVNode(key=key, value=value)
        value.parent = ret
        return ret

    def visit_k1(self, node, k1):
        return self.handle_kv(k1)

    def visit_k2(self, node, k2):
        return self.handle_kv(k2)

    def visit_k3(self, node, k3):
        return self.handle_kv(k3)

    def visit_k4(self, node, k4):
        return self.handle_kv(k4)

    def visit_key_value(self, node, key_value):
        return key_value[0]

    def visit_key(self, node, key):
        key = key[0]
        if isinstance(key, six.string_types):
            return key
        return key.text

    def visit_quoted_string(self, node, quoted_string):
        return quoted_string[0]

    def visit_single_quotes(self, node, single_quotes):
        _, text, _ = single_quotes
        return "'" + text.text + "'"

    def visit_double_quotes(self, node, double_quotes):
        _, text, _ = double_quotes
        return '"' + text.text + '"'

    def visit_ws(self, node, ws):
        return

    def generic_visit(self, node, visited_children):
        return visited_children or node


if __name__ == "__main__":
    # Then run tests

    def single_test(input, inline, outline):
        result = Visitor().parse(input)
        assert result.inline() == inline
        assert result.outline() == outline

    single_test("( test )", "(test)", "(\n    test,\n)")
    single_test("[foo, bar,]", "[foo, bar]", "[\n    foo,\n    bar,\n]")
    single_test(
        "{ 'bim': boo, hi: [there, jim]}",
        "{'bim': boo, hi: [there, jim]}",
        "{\n    'bim': boo,\n    hi: [\n        there,\n        jim,\n    ],\n}"
    )
