from collections import namedtuple

from .tokenizer import Tokenizer
from .tagger import *

CodeBlock = namedtuple("CodeBlock", ["lines"])

DeclarationLine = namedtuple("DeclarationLine",["declarations"])
AssignmentLine  = namedtuple("AssignmentLine", ["label","value"])
ExpressionLine  = namedtuple("ExpressionLine", ["expression"])
IfStatement     = namedtuple("IfStatement",    ["condition","codeblock"])
WhileBlock      = namedtuple("WhileBlock",     ["condition","codeblock"])
ForBlock        = namedtuple("ForBlock",       ["label","iterable","codeblock"])

LineTypes = {DeclarationLine, AssignmentLine, ExpressionLine,
             IfStatement, WhileBlock, ForBlock}

class TekoParser:
    def __init__(self, filename):
        with open(filename,"r",encoding="utf-8") as fh:
            source = fh.read()

        tk = Tokenizer()
        tokens = tk.tokenize(source)
        
        tags = get_tags(tokens)
        self.tags = [Tag("OpenTag",{"brace":"curly"})] + list(tags) + [Tag("CloseTag",{"brace":"curly"})]

    def parse(self):
        self.i = 0
        cb = self.grab_codeblock()
        return cb

    def grab_codeblock(self):
        try:
            assert(self.tags[self.i] == Tag("OpenTag",{"brace":"curly"}))
        except AssertionError:
            print(self.i,str(self.tags[self.i]))
        self.i += 1
        end = False

        lines = []
        while not end:
            tag = self.tags[self.i]
            if tag == Tag("CloseTag",{"brace":"curly"}):
                self.i += 1
                end = True
            else:
                line = self.grab_line()
                lines.append(line)
                
        cb = CodeBlock(lines=lines)
        return cb

    def grab_line(self):
        start = self.i + 0
        while self.tags[self.i] != Tag("SemicolonTag"):
            if self.tags[self.i] == Tag("OpenTag",{"brace":"curly"}):
                cb = self.grab_codeblock()
            else:
                self.i += 1

        line = self.tags[start:self.i]
        self.i += 1 # skip semicolon - its only value is line demarcation
        return line
