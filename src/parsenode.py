from .tagger import BRACES, BINOPS, COMPARISONS, CONVERSIONS, OPEN_LITERALS, CLOSE_LITERALS, VISIBILITIES

SIMPLE_EXPR_TAGTYPES = {"IntTag", "RealTag", "BoolTag",
                        "StringTag", "LabelTag"}

# the Node is the basic unit of a parse tree
# each its attributes must be a Node, a list of Nodes, or a Tag

class Node:
    def __init__(self,line_number):
        assert(type(line_number) == int)
        self.line_number = line_number

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
        self.declarations = declarations

    def __str__(self):
        return ", ".join([str(d) for d in self.declarations]) + ";"

class AssignmentStatement(Statement):
    def __init__(self, left, right):
        assert(isinstance(left, Expression))
        assert(isinstance(right, Expression))

        self.left = left
        self.right = right
        self.line_number = self.left.line_number

    def __str__(self):
        return str(self.left) + " = " + str(self.right) + ";"

class ExpressionStatement(Statement):
    def __init__(self, expression):
        assert(isinstance(expression, Expression))
        self.expression = expression

        self.line_number = self.expression.line_number

    def __str__(self):
        return str(self.expression) + ";"

class IfStatement(Statement):
    def __init__(self, line_number, condition, codeblock, else_stmt=None):
        super().__init__(line_number)

        assert(isinstance(condition, Expression))
        assert(isinstance(codeblock, CodeBlock))
        assert(else_stmt is None or isinstance(else_stmt, IfStatement))

        self.condition = condition
        self.codeblock = codeblock
        self.else_stmt = else_stmt

    def __str__(self):
        s = "if (" + str(self.condition) + ") "
        s += str(self.codeblock)
        if self.else_stmt:
            s += " else " + str(self.else_stmt)
        return s

class WhileBlock(Statement):
    def __init__(self, line_number, condition, codeblock):
        super().__init__(line_number)

        assert(isinstance(condition, Expression))
        assert(isinstance(codeblock, CodeBlock))

        self.condition = condition
        self.codeblock = codeblock

    def __str__(self):
        return "while (" + str(self.condition) + ") " + str(self.codeblock)

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

    def __str__(self):
        s = "for (" + str(self.tekotype) + " " + str(self.label)
        s += " in " + str(self.iterable) + ") " + str(self.codeblock)
        return s

class ClassDeclaration(Statement):
    def __init__(self, line_number, label, declaration_dict):
        super().__init__(line_number)

        assert(label.tagType == "LabelTag")
        for vis, decs in declaration_dict.items():
            assert(vis in VISIBILITIES)
            assert(all(isinstance(dec, DeclarationStatement) for dec in decs))

        self.label = label
        self.declaration_dict = declaration_dict

    def __str__(self):
        s = "class " + self.label.vals["label"] + " {\n"
        for vis, decs in self.declaration_dict.items():
            s += vis + ": \n"
            for dec in decs:
                s += "\t" + str(dec) + "\n"
        s += "}"
        return s

# # #

class Declaration(Node):
    def __init__(self, line_number, tekotype, label, struct=None, expression=None):
        super().__init__(line_number)
        
        assert(tekotype is None or isinstance(tekotype, Expression))
        assert(label.tagType == "LabelTag")
        assert(struct is None or isinstance(struct, NewStructNode))
        assert(expression is None or isinstance(expression, Expression))

        self.tekotype = tekotype
        self.label = label
        self.struct = struct
        self.expression = expression

    def __str__(self):
        if self.tekotype:
            s = str(self.tekotype)
        else:
            s = "let"
        s += " " + self.label.vals["label"]
        if self.struct is not None:
            s += str(self.struct)
        if self.expression is not None:
            s += " = " + str(self.expression)
        return s

# # #

class Expression(Node):
    def __init__(self, line_number):
        super().__init__(line_number)

    def evaluate():
        raise ValueError("Not implemented yet!")

class SimpleExpression(Expression):
    def __init__(self, tag):
        assert(tag.tagType in SIMPLE_EXPR_TAGTYPES)
        self.tag = tag

        self.line_number = self.tag.token.line_number

    def __str__(self):
        if self.tag.tagType in ["StringTag", "BoolTag"]:
            return self.tag.token.string
        else:
            return str(self.tag.only_val())

class SequenceExpression(Expression):
    def __init__(self, line_number, brace, exprs):
        super().__init__(line_number)

        assert(brace in BRACES)
        assert(all(isinstance(expr, Expression) for expr in exprs))

        self.brace = brace
        self.exprs = exprs

    def __str__(self):
        s = OPEN_LITERALS[self.brace]
        s += ", ".join([str(expr) for expr in self.exprs])
        s += CLOSE_LITERALS[self.brace]
        return s

class CallExpression(Expression):
    def __init__(self, leftexpr, args):
        assert(isinstance(leftexpr, Expression))
        assert(isinstance(arg, ArgNode) for arg in args)

        self.leftexpr = leftexpr
        self.args = args

        self.line_number = leftexpr.line_number

    def __str__(self):
        s = str(self.leftexpr) + "("
        s += ", ".join([str(arg) for arg in self.args])
        s += ")"
        return s

class AttrExpression(Expression):
    def __init__(self, leftexpr, label):
        assert(isinstance(leftexpr, Expression))
        assert(label.tagType == "LabelTag")

        self.leftexpr = leftexpr
        self.label = label

        self.line_number = leftexpr.line_number

    def __str__(self):
        return str(self.leftexpr) + "." + self.label.vals["label"]

class BinOpExpression(Expression):
    def __init__(self, binop, leftexpr, rightexpr):
        assert(binop in BINOPS)
        assert(isinstance(leftexpr, Expression))
        assert(isinstance(rightexpr, Expression))

        self.binop = binop
        self.leftexpr = leftexpr
        self.rightexpr = rightexpr

        self.line_number = self.leftexpr.line_number

    def __str__(self):
        return "(" + str(self.leftexpr) + " " + self.binop + " " + str(self.rightexpr) + ")"

class NotExpression(Expression):
    def __init__(self, line_number, expr):
        super().__init__(line_number)
        assert(isinstance(expr, Expression))
        self.expr = expr

    def __str__(self):
        return "!(" + str(self.expr) + ")"

class ComparisonExpression(Expression):
    def __init__(self, comp, leftexpr, rightexpr):
        assert(comp in COMPARISONS)
        assert(isinstance(leftexpr, Expression))
        assert(isinstance(rightexpr, Expression))

        self.comp = comp
        self.leftexpr = leftexpr
        self.rightexpr = rightexpr

        self.line_number = self.leftexpr.line_number

    def __str__(self):
        return "(" + str(self.leftexpr) + " " + self.comp + " " + str(self.rightexpr) + ")"

class ConversionExpression(Expression):
    def __init__(self, leftexpr, conv):
        assert(isinstance(leftexpr, Expression))
        assert(conv in CONVERSIONS)

        self.leftexpr = leftexpr
        self.conv = conv

        self.line_number = leftexpr.line_number

    def __str__(self):
        return str(self.leftexpr) + self.conv

class CodeBlock(Expression):
    def __init__(self, line_number, statements):
        super().__init__(line_number)
        
        assert(type(statements) == list)
        assert(all(isinstance(item,Statement) for item in statements))
        self.statements = statements

    def __str__(self):
        s = "{\n"
        for stmt in self.statements:
            s += "    " + str(stmt) + "\n"
        s += "}"
        return s

class NewStructNode(Expression):
    def __init__(self, line_number, elems):
        super().__init__(line_number)
        
        assert(all(isinstance(elem, StructElem) for elem in elems))
        self.elems = elems

    def __str__(self):
        return "(" + ", ".join([str(elem) for elem in self.elems]) + ")"

# # #

class StructElemNode(Node):
    def __init__(self, tekotype, label, default = None):
        assert(isinstance(tekotype, Expression))
        assert(label.tagType == "LabelTag")
        assert(default is None or isinstance(default, Expression))

        self.tekotype = tekotype
        self.label = label
        self.default = default

        self.line_number = tekotype.line_number

    def __str__(self):
        s = str(self.tekotype) + " " + self.label.vals["label"]
        if self.default:
            s += " ? " + str(self.default)
        return s

class ArgNode(Node):
    def __init__(self, expr, kw = None):
        assert(isinstance(expr, Expression))
        assert(kw is None or kw.tagType == "LabelTag")

        self.expr = expr
        self.kw = kw

        self.line_number = self.kw.token.line_number if self.kw else self.expr.line_number

    def __str__(self):
        if self.kw:
            s = self.kw.vals["label"] + " = "
        else:
            s = ""
        s += str(self.expr)
        return s

# TODO: MapExpression
