from parsimonious.grammar import Grammar
from parsimonious.nodes import (
    NodeVisitor,
    Node,
)


# TODO: handle escaped quotes.
# TODO: handle kwargs with = as KV nodes, which implies KV nodes can be in any
# surrounders.
g = Grammar(
    r"""
surrounded
    = ( '(' ws expr? ws ')' )
    / ( '[' ws expr? ws ']' )
    / ( '{' ws expr? ws '}' )

expr
    = ( car sep expr )
    / ( car sep? )

car
    = kv
    / number
    / string
    / surrounded
    / fn
    / symb

sep = ( ws "," ws )

kv
    = ( k ws '=' ws v )
    / ( k ws ':' ws v )

k
    = string
    / symb

v
    = number
    / string
    / surrounded
    / fn
    / symb

fn = symb surrounded

symb = ~r"[A-Za-z0-9._-]+"

string
    = ( '"' ~r'[^"]*' '"' )
    / ( "'" ~r"[^']*" "'" )

number = ~r"[0-9]+[.]?[0-9]*"

ws = ~r"[ \t\n\r]*"
    """
)


class FamilyMixin(object):
    parent = None

    def indent(self):
        if self.parent is None:
            return 0
        return self.parent.indent()


class StringNode(object):
    def __init__(self, content):
        self.content = content

    def inline(self):
        return u"{s.content}".format(s=self)

    def outline(self):
        return u"{s.content}".format(s=self)


class ListNode(FamilyMixin):
    def __init__(self, content):
        self.content = [
            el
            for el
            in content
            if el
        ]

    def __add__(self, other):
        return ListNode(content=self.content + other)

    def __iter__(self):
        for el in self.content:
            yield el

    def __len__(self):
        return len(self.content)

    def inline(self):
        return u", ".join(
            node.inline()
            for node
            in self.content
        )

    def outline(self):
        indent = u"    " * self.indent()
        return u",\n".join(
            "{}{}".format(indent, node.outline())
            for node
            in self.content
        ) + ("," if self.content else "")


class SurroundedNode(FamilyMixin):
    def __init__(self, prefix, content, suffix):
        self.prefix = prefix
        self.content = content
        self.suffix = suffix

    def indent(self):
        if self.parent is None:
            return 1
        return self.parent.indent() + 1

    def inline(self):
        return u"{s.prefix}{content}{s.suffix}".format(
            s=self,
            content=self.content.inline(),
        )

    def outline(self):
        content = self.content.outline()
        if not content:
            return u"{s.prefix}{s.suffix}".format(s=self)
        indent = u"    " * (self.indent() - 1)
        return u"{s.prefix}\n{content}\n{indent}{s.suffix}".format(
            s=self,
            content=self.content.outline(),
            indent=indent,
        )


class FnNode(FamilyMixin):
    def __init__(self, symb, surrounded):
        self.symb = symb
        self.surrounded = surrounded

    def inline(self):
        return u"{}{}".format(
            self.symb.inline(),
            self.surrounded.inline(),
        )

    def outline(self):
        return u"{}{}".format(
            self.symb.outline(),
            self.surrounded.outline(),
        )


class KVNode(FamilyMixin):
    def __init__(self, key, sep, val):
        self.key = key
        self.sep = sep
        self.val = val

    def format_sep(self):
        if self.sep == ':':
            return ": "
        return self.sep

    def inline(self):
        return u"{key}{sep}{val}".format(
            key=self.key.inline(),
            sep=self.format_sep(),
            val=self.val.inline(),
        )

    def outline(self):
        return u"{key}{sep}{val}".format(
            key=self.key.outline(),
            sep=self.format_sep(),
            val=self.val.outline(),
        )


class Visitor(NodeVisitor):
    grammar = g
    valid_nodes = (
        SurroundedNode,
        KVNode,
        StringNode,
        FnNode,
    )

    def generic_visit(self, node, visited_children):
        return visited_children or node

    def visit_surrounded(self, node, elements):
        prefix, _, expr, _, suffix = elements[0]
        if isinstance(expr, Node):
            expr = ListNode(content=[])
        else:
            expr = expr[0]
        ret = SurroundedNode(
            prefix=prefix.text,
            content=expr,
            suffix=suffix.text,
        )
        expr.parent = ret
        return ret

    def visit_expr(self, node, elements):
        car = elements[0][0]
        cdr = elements[0][2:]
        if cdr:
            content = [car] + cdr[0].content
        else:
            content = [car]
        ret = ListNode(content=content)
        for el in content:
            el.parent = ret
        return ret

    def visit_car(self, node, elements):
        el = elements[0]
        if isinstance(el, self.valid_nodes):
            return el
        if isinstance(el, Node):
            return StringNode(content=el.text)
        raise ValueError("Invalid el")

    def visit_kv(self, node, elements):
        key, _, sep, _, val = elements[0]
        ret = KVNode(
            key=key,
            sep=sep.text,
            val=val,
        )
        val.parent = ret
        return ret

    def visit_k(self, node, elements):
        el = elements[0]
        if isinstance(el, StringNode):
            return el
        raise ValueError("Somehow, a bad key")

    def visit_v(self, node, elements):
        el = elements[0]
        if isinstance(el, self.valid_nodes):
            return el
        if isinstance(el, Node):
            return StringNode(content=el.text)
        raise ValueError("Invalid el")

    def visit_symb(self, node, elements):
        return StringNode(content=node.text)

    def visit_string(self, node, elements):
        open, txt, close = elements[0]
        return StringNode(content=open.text + txt.text + close.text)

    def visit_fn(self, node, elements):
        symb, surrounded = elements
        ret = FnNode(symb=symb, surrounded=surrounded)
        surrounded.parent = ret
        return ret

    def visit_number(self, node, elements):
        return StringNode(content=node.text)


if __name__ == "__main__":
    # Then run tests

    def single_test(input, inline, outline):
        result = Visitor().parse(input)
        assert result.inline() == inline, repr(result.inline())
        assert result.outline() == outline, repr(result.outline())
        print("Passed: {}".format(input))

    single_test("()", "()", "()")
    single_test("[]", "[]", "[]")
    single_test("{}", "{}", "{}")
    single_test(
        "(foo)",
        "(foo)",
        """
    (
        foo,
    )
        """.strip(),
    )
    single_test(
        "(foo,)",
        "(foo)",
        """
    (
        foo,
    )
        """.strip(),
    )
    single_test(
        "(foo, bar, baz)",
        "(foo, bar, baz)",
        """
    (
        foo,
        bar,
        baz,
    )
        """.strip(),
    )
    single_test(
        "(foo, bar, baz,)",
        "(foo, bar, baz)",
        """
    (
        foo,
        bar,
        baz,
    )
        """.strip(),
    )
    single_test(
        "([], {}, (),)",
        "([], {}, ())",
        """
    (
        [],
        {},
        (),
    )
        """.strip(),
    )
    single_test(
        "{foo: bar}",
        "{foo: bar}",
        """
    {
        foo: bar,
    }
        """.strip(),
    )
    single_test(
        "({foo: bar,},bing,[bong])",
        "({foo: bar}, bing, [bong])",
        """
    (
        {
            foo: bar,
        },
        bing,
        [
            bong,
        ],
    )
        """.strip(),
    )
    single_test(
        "({foo: [],},bing,[bong])",
        "({foo: []}, bing, [bong])",
        """
    (
        {
            foo: [],
        },
        bing,
        [
            bong,
        ],
    )
        """.strip(),
    )
    single_test(
        "{ foo }",
        "{foo}",
        """
    {
        foo,
    }
        """.strip(),
    )
    single_test(
        '{ "foo" }',
        '{"foo"}',
        '''
    {
        "foo",
    }
        '''.strip(),
    )
    single_test(
        "{ 'foo' }",
        "{'foo'}",
        """
    {
        'foo',
    }
        """.strip(),
    )
    single_test(
        "[foo.bar]",
        "[foo.bar]",
        """
    [
        foo.bar,
    ]
        """.strip(),
    )
    single_test(
        "[1]",
        "[1]",
        """
    [
        1,
    ]
        """.strip(),
    )
    single_test(
        "[1.]",
        "[1.]",
        """
    [
        1.,
    ]
        """.strip(),
    )
    single_test(
        "[1.0]",
        "[1.0]",
        """
    [
        1.0,
    ]
        """.strip(),
    )
    single_test(
        "[1, 2.0]",
        "[1, 2.0]",
        """
    [
        1,
        2.0,
    ]
        """.strip(),
    )
    single_test(
        "{ foo: bar }",
        "{foo: bar}",
        """
    {
        foo: bar,
    }
        """.strip(),
    )
    single_test(
        "{ 'foo': bar }",
        "{'foo': bar}",
        """
    {
        'foo': bar,
    }
        """.strip(),
    )
    single_test(
        "{ 'bim': boo, hi: [there, jim]}",
        "{'bim': boo, hi: [there, jim]}",
        """
    {
        'bim': boo,
        hi: [
            there,
            jim,
        ],
    }
        """.strip(),
    )
    single_test(
        "(foo=bar, bim={baz: boo},)",
        "(foo=bar, bim={baz: boo})",
        """
    (
        foo=bar,
        bim={
            baz: boo,
        },
    )
        """.strip(),
    )
    single_test(
        "(foo,bar=baz,[bim,bloo],what={is:this})",
        "(foo, bar=baz, [bim, bloo], what={is: this})",
        """
    (
        foo,
        bar=baz,
        [
            bim,
            bloo,
        ],
        what={
            is: this,
        },
    )
        """.strip(),
    )
    single_test(
        "[foo()]",
        "[foo()]",
        """
    [
        foo(),
    ]
        """.strip(),
    )
    single_test(
        "[foo(bar)]",
        "[foo(bar)]",
        """
    [
        foo(
            bar,
        ),
    ]
        """.strip(),
    )
    single_test(
        """
        (foo, {'kwi': zok.pim,
            'bel': zok.wub,
            'pok': zok.nux,
            'lon': dee(foo),
            'hoi': dee(zok.che.rem('eph', toi=mep))},
        bar='bim', kuh={'rif': tou})
        """.strip(),
        "(foo, {'kwi': zok.pim, 'bel': zok.wub, 'pok': zok.nux, 'lon': dee(foo), 'hoi': dee(zok.che.rem('eph', toi=mep))}, bar='bim', kuh={'rif': tou})",  # NOQA
        """
    (
        foo,
        {
            'kwi': zok.pim,
            'bel': zok.wub,
            'pok': zok.nux,
            'lon': dee(
                foo,
            ),
            'hoi': dee(
                zok.che.rem(
                    'eph',
                    toi=mep,
                ),
            ),
        },
        bar='bim',
        kuh={
            'rif': tou,
        },
    )
        """.strip(),
    )
