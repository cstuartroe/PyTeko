from collections import namedtuple

from .general import TekoException
from .tokenizer import Tokenizer
from .tagger import *
from .types import *
from .parsenode import*

class Precedence:
    COMPARE  = 0
    ADD_SUB  = 1
    MULT_DIV = 2
    EXP      = 3

    BINOP_PRECS = {"+":ADD_SUB,  "-":ADD_SUB,
                   "*":MULT_DIV, "/":MULT_DIV,
                   "%":MULT_DIV, "^":EXP}

class TekoParser:
    def __init__(self, filename):
        with open(filename,"r",encoding="utf-8") as fh:
            source = fh.read()

        tk = Tokenizer()
        tokens = tk.tokenize(source)
        
        self.tags = list(get_tags(tokens))
        #self.tags = [Tag("OpenTag",{"brace":"curly"})] + list(tags) + [Tag("CloseTag",{"brace":"curly"})]

    def more(self):
        return self.i < len(self.tags)

    def step(self):
        print(self.next().token.string)
        self.i += 1

    def next(self,n=1):
        assert(type(n) == int and n>0)
        if len(self.tags) < self.i+n:
            TekoException("Unexpected EOF",self.tags[-1].token.line_number)
        else:
            if n == 1:
                return self.tags[self.i] # returns a single tag if n=1
            else:
                return self.tags[self.i:self.i+n] # returns a list of tags if n>1

    def expect(self,tagType,vals={}):
        if self.next().tagType != tagType:
            TekoException("Expected %s instead of %s" % (tagType, self.next().tagType), self.next().token.line_number)
        elif self.next().vals != vals:
            TekoException("Expected %s instead of %s" % (str(vals), str(self.next().vals)), self.next().token.line_number)
        self.step()

    def parse(self):
        self.i = 0
        cb = self.grab_codeblock()
        return cb

    def grab_codeblock(self):
        stmts = []
        while self.i < len(self.tags) and self.next().tagType != "CloseTag":
            stmt = self.grab_statement()
            stmts.append(stmt)
                
        cb = CodeBlock(statements=stmts)
        return cb

    def grab_statement(self):
        if self.next().tagType == "IfTag":
            return self.grab_if()
        elif self.next().tagType == "ForTag":
            return self.grab_for()
        elif self.next().tagType == "WhileTag":
            return self.grab_while()
        elif self.next().tagType == "LetTag":
            line_number = self.next().token.line_number
            self.step()
            return self.grab_declaration(tekotype = None, line_number = line_number)

        expr = self.grab_expression()
        
        if self.next().tagType == "SetterTag":
            return self.grab_assignment(left = expr)
        elif self.next().tagType == "LabelTag":
            return self.grab_declarations(tekotype = expr)
        else:
            return ExpressionStatement(expression=expr)

    def grab_expression(self, prec = -1):
        if self.next().tagType == "OpenTag":
            expr = self.grab_sequence()
        elif self.next().tagType in SIMPLE_EXPR_TAGTYPES:
            expr = SimpleExpression(self.next())
            self.step()
        else:
            TekoException("Illegal start to expression: " + self.next().token.string,
                          self.next().token.line_number)
            
        return self.check_postfix(expr, prec)

    def check_postfix(self, expr, prec):
        new_expr = None
        
        if self.next().tagType == "BinOpTag":
            binop = self.next().vals["binop"]
            new_prec = Precedence.BINOP_PRECS[binop]
            if new_prec > prec:
                self.step()
                rightexpr = self.grab_expression(prec = new_prec)
                new_expr = BinOpExpression(binop, leftexpr = expr, rightexpr = rightexpr)
            else:
                return expr

        if self.next().tagType == "ComparisonTag":
            comp = self.next().vals["comparison"]
            new_prec = Precedence.COMPARE
            if new_prec > prec:
                self.step()
                rightexpr = self.grab_expression(prec = new_prec)
                new_expr = ComparisonExpression(comp, leftexpr = expr, rightexpr = rightexpr)
            else:
                return expr

        if self.next().tagType == "OpenTag" and self.next().vals["brace"] == "paren":
            self.step()
            args = self.grab_args()
            self.expect("CloseTag",{"brace":"paren"})

            new_expr = CallExpression(leftexpr = expr, args = args)

        if self.next().tagType == "DotTag":
            nextnext = self.next(2)[1]
            if nextnext.tagType == "LabelTag":
                new_expr = AttrExpression(leftexpr = expr, label = nextnext)
            else:
                self.tags[self.i] = Tag("ConversionTag",self.next().token,{"conversion":"."})

        if self.next().tagType == "ConversionTag":
            conv = self.next().vals["conversion"]
            self.step()
            new_expr = ConversionExpression(leftexpr = expr, conv = conv)

        if not new_expr:
            return expr

        return self.check_postfix(new_expr, prec)

    def grab_sequence(self):
        brace = self.next().vals["brace"]
        self.step()
        
    def grab_if(self):
        line_number = self.next().token.line_number
        
        self.expect("IfTag")
        self.expect("OpenTag",{"brace":"paren"})
        
        cond = self.grab_expression()
        if not cond.tekotype is TekoBool:
            TekoException("Must be a boolean expression",self.next().token.line_number)
            
        self.expect("CloseTag",{"brace":"paren"})
        self.expect("OpenTag",{"brace":"curly"})

        cb = self.grab_codeblock()

        self.expect("CloseTag",{"brace":"curly"})

        if self.more() and self.next().tagType == "ElseTag":
            self.step()
            if self.next().tagType == "IfTag":
                else_stmt = self.grab_if()
            else:
                self.expect("OpenTag",{"brace":"curly"})
                cb = self.grab_codeblock()
                self.expect("CloseTag",{"brace":"curly"})
                raise BaseException("Not implemented!")
        else:
            else_stmt = None

        return IfStatement(line_number = line_number, condition = cond, codeblock = cb, else_stmt = else_stmt)

    def grab_declarations(self, tekotype, line_number = None):
        declarations = []
        if tekotype is not None:
            line_number = tekotype.line_number
        assert(line_number is not None)
        
        cont = True
        while cont:
            cont = False
            
            if self.next().tagType != "LabelTag":
                TekoException("Invalid variable label: " + self.next().token.string, self.next().token.line_number)              
            label = self.next()
            self.step()

            if self.next().tagType == "OpenTag" and self.next().vals["brace"] == "paren":
                struct = self.grab_struct()
            else:
                struct = None

            if self.next().tagType == "SetterTag":
                if self.next().vals["setter"] != "=":
                    TekoException('Must use basic setter "=" in a declaration',self.next().token.line_number)
                self.step()

                expr = self.grab_expression()
            else:
                expr = None

            declaration = Declaration(tekotype, label, struct, expr)
            declarations.append(declaration)

            if self.next().tagType == "CommaTag":
                cont = True
                self.step()

        self.expect("SemicolonTag")
        return DeclarationStatement(line_number, declarations)
