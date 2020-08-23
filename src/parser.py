from lark import Lark, Tree, Token

with open("teko.lark", "r") as fh:
    grammar = fh.read()

teko_lark_parser = Lark(grammar, parser='earley', lexer='standard')


class TekoAST:

    def __init__(self, file):
        if type(file) is str:
            with open(file, "r") as fh:
                content = fh.read()
        else:
            content = file.read()

        self.tree = teko_lark_parser.parse(content)
        print(self.tree.pretty())
        self.adjust_node(self.tree)
        print('----')
        print(self.tree.pretty())

    def adjust_node(self, node):
        if node.data == "assignment":
            left, setter, right = node.children
            if setter.data.endswith('_equals'):
                node.children[2] = Tree('expression_add_sub', [
                    Tree('expression_atomic', [left]),
                    Tree(setter.data.replace("_equals", ""), []),
                    right
                ])
                setter.data = "equals"

        elif node.data in ["expression_add_sub", "expression_mult_div", "expression_exp"]:
            left, op, right = node.children
            node.data = 'fcall'
            node.children = [
                Tree('attribute', [
                    left, Tree('symbol', [op.data])
                ]),
                Tree('arg', [right])
            ]

        for node in node.children:
            if type(node) is Tree:
                self.adjust_node(node)
