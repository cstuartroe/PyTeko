import re

from .general import TekoException

ALPHA = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
NUMS = set("0123456789")
WHITE = set(" \t\n")
PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^`|{|}~")

def is_alpha(c):
    return c in ALPHA

def is_num(c):
    return c in NUMS

def is_white(c):
    return c in WHITE

def is_punct(c):
    return c in PUNCT

class Tokenizer:
    PUNCT_COMBOS = ["==","<=",">=","!=","<:","+=","-=","*=",
                    "/=","^=","%%=","{}","[]","<>"]
    
    def __init__(self):
        pass

    def tokenize(self,s):
        self.s = s
        self.i = 0
        self.tokens = []
        
        while self.i < len(self.s):
            if self.next(2) == "//":
                self.pass_line_comment()
                
            elif self.next(2) == "/*":
                self.pass_multiline_comment()
                
            elif self.next() == "\"":
                self.grab_string()
                
            elif is_alpha(self.next()):
                self.grab_label()
                
            elif is_num(self.next()):
                self.grab_num()
                
            elif is_punct(self.next()):
                self.grab_punct()
                
            elif is_white(self.next()):
                self.i += 1
                
            else:
                TekoException("Unknown character: " + self.next())

        return self.tokens

    def next(self,n=1):
        if len(self.s) < self.i+n:
            return None
        else:
            return self.s[self.i:self.i+n]

    def pass_line_comment(self):
        assert(self.next(2) == "//")
        while self.next is not None and self.next() != "\n":
            self.i += 1       

    def pass_multiline_comment(self):
        assert(self.next(2) == "/*")
        while self.next(2) != "*/":
            self.i += 1
            if self.next(2) is None:
                TekoException("EOF while parsing multiline comment")
        self.i += 2

    def grab_string(self):
        assert(self.next() == '"')
        self.i += 1
        token = ""
        
        while self.next() != '"':
            if self.next(2) == r'\"':
                token += '"'
                self.i += 2
            elif self.next(2) == r'\n':
                token += "\n"
                self.i += 2
            elif self.next(2) == r'\t':
                token += "\t"
                self.i += 2
            else:
                c = self.next()
                if c is None:
                    TekoException("EOF while parsing string")
                token += c
                self.i += 1
                
        self.i += 1                
        self.tokens.append(token)

    def grab_label(self):
        assert(is_alpha(self.next()))
        token = self.next()
        self.i += 1
        
        while is_alpha(self.next()) or is_num(self.next()):
            token += self.next()
            self.i += 1
            
        self.tokens.append(token)

    def grab_num(self):
        assert(is_num(self.next()))
        token = self.next()
        self.i += 1
        
        while is_num(self.next()):
            token += self.next()
            self.i += 1
            
        if self.next() == ".":
            token += self.next()
            self.i += 1
            while is_num(self.next()):
                token += self.next()
                self.i += 1
            
        self.tokens.append(token)

    def grab_punct(self):
        assert(is_punct(self.next()))
        token = self.next()
        self.i += 1

        while self.next() is not None and (token + self.next()) in Tokenizer.PUNCT_COMBOS:
            token += self.next()
            self.i += 1

        self.tokens.append(token)            
