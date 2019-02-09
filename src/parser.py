from collections import namedtuple

from .general import TekoException
from .tokenizer import Tokenizer
from .tagger import *

CodeBlock = namedtuple("CodeBlock", ["statements"])

DeclarationStatement = namedtuple("DeclarationStatement",["declarations"])
AssignmentStatement  = namedtuple("AssignmentStatement", ["label","value"])
ExpressionStatement  = namedtuple("ExpressionStatement", ["expression"])
IfStatement          = namedtuple("IfStatement",         ["condition","codeblock"])
WhileBlock           = namedtuple("WhileBlock",          ["condition","codeblock"])
ForBlock             = namedtuple("ForBlock",            ["label","iterable","codeblock"])

StatementTypes = {DeclarationStatement, AssignmentStatement, ExpressionStatement,
                  IfStatement, WhileBlock, ForBlock}

class TekoParser:
    def __init__(self, filename):
        with open(filename,"r",encoding="utf-8") as fh:
            source = fh.read()

        tk = Tokenizer()
        tokens = tk.tokenize(source)
        
        self.tags = list(get_tags(tokens))
        #self.tags = [Tag("OpenTag",{"brace":"curly"})] + list(tags) + [Tag("CloseTag",{"brace":"curly"})]

    def next(self,n=1):
        assert(type(n) == int and n>0)
        if len(self.tags) < self.i+n:
            return None
        else:
            if n == 1:
                return self.tags[self.i] # returns a single tag if n=1
            else:
                return self.tags[self.i:self.i+n] # returns a list of tags if n>1

    def parse(self):
        self.i = 0
        cb = self.grab_codeblock()
        return cb

    def grab_codeblock(self):
        stmts = []
        while self.i < len(self.tags):
            stmt = self.grab_statement()
            stmts.append(stmt)
                
        cb = CodeBlock(statements=stmts)
        return cb

    def grab_statement(self):
        start = self.i + 0
        while self.next().tagType != "SemicolonTag":
            if self.next().tagType == "OpenTag":
                self.grab_brace()
            elif self.next().tagType == "CloseTag":
                TekoException("closing %s brace without corresponding opening brace" % self.next().vals["brace"],
                              self.next().token.line_number)
            else:
                self.i += 1
            if self.next() is None:
                TekoException("EOF while parsing statement",self.tags[-1].token.line_number)

        stmt = self.tags[start:self.i]
        self.i += 1 # skip semicolon - its only value is statement demarcation
        return stmt

    def grab_brace(self):
        assert(self.next().tagType == "OpenTag")
        open_brace = self.next().vals["brace"]
        start = self.i + 0
        self.i += 1
        
        while self.tags[self.i].tagType != "CloseTag":
            if self.tags[self.i].tagType == "OpenTag":
                self.grab_brace()
            else:
                self.i += 1
            if self.next() is None:
                TekoException("Unterminated %s brace" % self.tags[start].vals["brace"],
                              self.tags[start].token.line_number)
                
                
        close_brace = self.tags[self.i].vals["brace"]
        if open_brace != close_brace:
            TekoException("mismatched braces", self.tags[self.i].token.line_number)
        else:
            self.i += 1
            return self.tags[start:self.i]
