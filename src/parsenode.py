from .tagger import BRACES, BINOPS, COMPARISONS, CONVERSIONS

# the Node is the basic unit of a parse tree
# each its attributes must be a Node, a list of Nodes, or a Tag

class Node:
    def __init__(line_number):
        assert(type(line_number) == int)
        self.line_number = line_number

# a codeblock is just a series of statements
# a file is a codeblock, as is the body of a function or block

class CodeBlock(Node):
    def __init__(self,statements):        
        assert(type(statements) == list)
        assert(all(isinstance(item,Statement) for item in statements))
        self.statements = statements

        self.line_number = self.statements[0].line_number

# statements - single instructions that can be executed
# include declarations, assignments, expressions, ifs, fors, whiles

class Statement(Node):
    def __init__(self, line_number):
        super().__init__(line_number)

class DeclarationStatement(Statement):
    def __init__(self, line_number, declarations):
        super().__init__(line_number)

        assert(type(declarations) == list)
        assert(all(isinstance(item,Declaration) for item in declarations))
        self.declaration = declarations

class AssignmentStatement(Statement):
    def __init__(self, label, expression):
        assert(label.tagType == "LabelTag")
        assert(isinstance(expression, Expression))

        self.label = label
        self.expression = expression

        self.line_number = self.label.token.line_number

class ExpressionStatement(Statement):
    def __init__(self, expression):
        assert(isinstance(expression, Expression))
        self.expression = expression

        self.line_number = self.expression.line_number

class IfStatement(Statement):
    def __init__(self, line_number, condition, codeblock, else_stmt):
        super().__init__(line_number)

        assert(isinstance(condition, Expression))
        assert(isinstance(codeblock, CodeBlock))
        assert(else_stmt is None or isinstance(else_stmt, IfStatement))

        self.condition = condition
        self.codeblock = codeblock
        self.else_stmt = else_stmt

class WhileBlock(Statement):
    def __init__(self, line_number, condition, codeblock):
        super().__init__(line_number)

        assert(isinstance(condition, Expression))
        assert(isinstance(codeblock, CodeBlock))

        self.condition = condition
        self.codeblock = codeblock

class ForBlock(Statement):
    def __init__(self, line_number, tekotype, label, iterable, codeblock):
        super().__init__(line_number)

        assert(isinstance(tekotype, Expression))
        assert(label.tagType == "LabelTag")
        assert(isinstance(iterable, Expression))
        assert(isinstance(codeblock, CodeBlock))

        self.tekotype = tekotype
        self.label = label
        self.iterable = iterable
        self.codeblock = codeblock

# # #

class Declaration(Node):
    def __init__(self, tekotype, label, struct=None, expression=None, codeblock=None):
        assert(isinstance(tekotype, Expression))
        assert(label.tagType == "LabelTag")
        assert(struct is None or isinstance(struct, StructExpression))
        assert(expression is None or isinstance(expression, Expression))
        assert(codeblock is None or isinstance(codeblock, CodeBlock))

        # a variable can only be set to a codeblock if it is a function
        # it is a function if and only if it has a struct
        if struct is None:
            assert(codeblock is None)

        # the variable can only be set to either an expression or a codeblock
        if expression:
            assert(codeblock is None)
        # but it could be neither - not initialized at all

        self.tekotype = tekotype
        self.label = label
        self.struct = struct
        self.expression = expression
        self.codeblock = codeblock

        self.line_number = self.tekotype.line_number

class Assignment(Node):
    def __init__(self, label, expression=None, codeblock=None):
        assert(label.tagType == "LabelTag")
        assert(expression is None or isinstance(expression, Expression))
        assert(codeblock is None or isinstance(codeblock, CodeBlock))

        # the variable must be set to either an expression or a codeblock
        assert((expression is None) != (codeblock is None))

        self.label = label
        self.exression = expression
        self.codeblock = codeblock

        self.line_number = label.token.line_number

# # #

class Expression(Node):
    def __init__(self, line_number):
        super().__init__(line_number)

class SimpleExpression(Expression):
    SIMPLE_TAGTYPES = {"IntTag", "RealTag", "BoolTag", "StringTag", "LabelTag"}

    def __init__(self, tag):
        assert(tag.tagType in SimpleExpression.SIMPLE_TAGTYPES)
        self.tag = tag

        self.line_number = self.tag.token.line_number

class SequenceExpression(Expression):
    def __init__(self, line_number, brace, exprs):
        super().__init__(line_number)

        assert(brace in BRACES)
        assert(all(isinstance(expr) for expr in exprs))

        self.brace = brace
        self.exprs = exprs

class CallExpression(Expression):
    def __init__(self, leftexpr, args):
        assert(isinstance(leftexpr, Expression))
        assert(isinstance(arg, ArgNode) for arg in args)

        self.line_number = leftexpr.line_number

class AttrExpression(Expression):
    def __init__(self, leftexpr, label):
        assert(isinstance(leftexpr, Expression))
        assert(label.tagType == "LabelTag")

        self.line_number = leftexpr.line_number

class BinOpExpression(Expression):
    def __init__(self, binop, leftexpr, rightexpr):
        assert(binop in BINOPS)
        assert(isinstance(leftexpr, Expression))
        assert(isinstance(rightexpr, Expression))

        self.binop = binop
        self.leftexpr = leftexpr
        self.rightexpr = rightexpr

        self.line_number = self.leftexpr.line_number

class ComparisonExpression(Expression):
    def __init__(self, comp, leftexpr, rightexpr):
        assert(comp in COMPARISON)
        assert(isinstance(leftexpr, Expression))
        assert(isinstance(rightexpr, Expression))

        self.comp = comp
        self.leftexpr = leftexpr
        self.rightexpr = rightexpr

        self.line_number = self.leftexpr.line_number

class ConversionExpression(Expression):
    def __init__(self, leftexpr, conv):
        assert(isinstance(leftexpr, Expression))
        assert(conv in CONVERSIONS)

        self.leftexpr = leftexpr
        self.conv = conv

        self.line_number = leftexpr.line_number

# TODO: MapExpression, ArgNode, NewStruct
