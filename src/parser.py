from collections import namedtuple

from .general import TekoException
from .tokenizer import Tokenizer
from .tagger import *
from .types import *
from .parsenode import*

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
        e = Tag(tagType,None,vals)
        n = self.next()
        if n != e:
            TekoException("Expected %s instead of %s" % (str(e), n.token.string), n.token.line_number())
        self.i += 1

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
        start = self.i + 0

        if self.next().tagType == "IfTag":
            return self.grab_if()
        elif self.next().tagType == "ForTag":
            return self.grab_for()
        elif self.next().tagType == "WhileTag":
            return self.grab_while()
        elif self.next().tagType == "LetTag":
            return self.grab_declaration()

        next2 = self.next(2)
        one, two = tuple(next2)
        
        if one.tagType == "LabelTag" and two.tagType == "LabelTag":
            return self.grab_declarations()

        expr = self.grab_expression()
        if self.next().tagType == "SetterTag":
            raise BaseException("Not implemented!")
        else:
            return ExpressionStatement(expression=expr)

    def grab_expression(self):
        pass

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
            self.i += 1
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

    def grab_declarations(self):
        declarations = []
        
        if self.next().tagType == "LetTag":
            tekotype = None
        else:
            tekotype = self.grab_expression()

        cont = True
        while cont:
            cont = False
            if self.next().tagType != "LabelTag":
                TekoException("Invalid variable label: " + self.next().token.string, self.next().token.line_number)
                              
            label = self.next().vals["label"]
            self.i += 1

            if self.next().tagType == "OpenTag" and self.next().vals["brace"] == "paren":
                args = self.grab_args()
            else:
                args = None

            
