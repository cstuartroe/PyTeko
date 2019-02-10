from .general import TekoException
from .tokenizer import Tokenizer, Token
from .tagger import *
from .types import *
from .parsenode import *

class Precedence:
    COMPARE  = 0
    ADD_SUB  = 1
    MULT_DIV = 2
    EXP      = 3

    BINOP_PRECS = {"+":ADD_SUB,  "-":ADD_SUB,
                   "&&":ADD_SUB, "||":ADD_SUB,
                   "*":MULT_DIV, "/":MULT_DIV,
                   "%":MULT_DIV, "^":EXP,
                   ":":EXP}

EMPTY_SEQUENCES = {"{}":"curly","[]":"square","<>":"angle"}

class TekoParser:
    def __init__(self, filename):
        with open(filename,"r",encoding="utf-8") as fh:
            source = fh.read()

        tk = Tokenizer()
        tokens = tk.tokenize(source)
        
        self.tags = list(get_tags(tokens))
        
    def more(self):
        return self.i < len(self.tags)

    def step(self):
        #print(self.next().token.string)
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
        while self.more():
            yield self.grab_statement()

    def grab_statement(self):
        if self.next().tagType == "IfTag":
            return self.grab_if()
        elif self.next().tagType == "ForTag":
            return self.grab_for()
        elif self.next().tagType == "WhileTag":
            return self.grab_while()
        elif self.next().tagType == "ClassTag":
            return self.grab_class()
        elif self.next().tagType == "LetTag":
            line_number = self.next().token.line_number
            self.step()
            return self.grab_declarations(tekotype = None, line_number = line_number)

        expr = self.grab_expression()
        
        if self.next().tagType == "SetterTag":
            return self.grab_assignment(left = expr)
        elif self.next().tagType == "LabelTag":
            return self.grab_declarations(tekotype = expr)
        else:
            expr_stmt = ExpressionStatement(expression=expr)
            self.expect("SemicolonTag")
            return expr_stmt

    def grab_expression(self, prec = -1):
        if self.next().tagType == "OpenTag":
            expr = self.grab_sequence()
        elif self.next().tagType in SIMPLE_EXPR_TAGTYPES:
            expr = SimpleExpression(self.next())
            self.step()
        elif self.next().tagType == "BangTag":
            line_number = self.next().token.line_number
            self.step()
            expr = self.grab_expression()
            return NotExpression(line_number, expr)
        elif self.next().tagType == "ConversionTag" and self.next().vals["conversion"] in ["{}","[]","<>"]:
            brace = EMPTY_SEQUENCES[self.next().vals["conversion"]]
            line_number = self.next().token.line_number
            expr = SequenceExpression(line_number, brace, [])
            self.step()
        else:
            TekoException("Illegal start to expression: " + self.next().token.string,
                          self.next().token.line_number)
            
        return self.check_postfix(expr, prec)

    def check_postfix(self, expr, prec):
        new_expr = None

        # some tokens have ambiguous syntactic function, which can only be determined during parsing:

        if self.next().tagType == "DotTag":
            nextnext = self.next(2)[1]
            if nextnext.tagType == "LabelTag":
                new_expr = AttrExpression(leftexpr = expr, label = nextnext)
                self.step()
                self.step()
            else:
                self.tags[self.i] = Tag("ConversionTag",self.next().token,{"conversion":"."})

        if self.next().tagType == "ColonTag":
            self.tags[self.i] = Tag("BinOpTag",self.next().token,{"binop":":"})

        if self.next().tagType == "LAngleTag":
            self.tags[self.i] = Tag("ComparisonTag",self.next().token,{"comparison":"<"})

        if self.next().tagType == "RAngleTag":
            self.tags[self.i] = Tag("ComparisonTag",self.next().token,{"comparison":">"})

        # this is actual postfix checking:
        
        if self.next().tagType == "BinOpTag":
            binop = self.next().vals["binop"]
            new_prec = Precedence.BINOP_PRECS[binop]
            if new_prec > prec:
                self.step()
                rightexpr = self.grab_expression(prec = new_prec)
                new_expr = BinOpExpression(binop, leftexpr = expr, rightexpr = rightexpr)
            else:
                return expr

        elif self.next().tagType == "ComparisonTag":
            comp = self.next().vals["comparison"]
            new_prec = Precedence.COMPARE
            if new_prec > prec:
                self.step()
                rightexpr = self.grab_expression(prec = new_prec)
                new_expr = ComparisonExpression(comp, leftexpr = expr, rightexpr = rightexpr)
            else:
                return expr

        elif self.next().tagType == "OpenTag" and self.next().vals["brace"] == "paren":
            args = self.grab_args()
            new_expr = CallExpression(leftexpr = expr, args = args)

        elif self.next().tagType == "ConversionTag":
            conv = self.next().vals["conversion"]
            self.step()
            new_expr = ConversionExpression(leftexpr = expr, conv = conv)

        if not new_expr:
            # print(expr)
            return expr

        return self.check_postfix(new_expr, prec)

    # this method is unsafe with regard to what type of Expression it returns
    # it may return a SequenceExpression, a CodeBlock, a NewStruct
    # or any type of Expression with (expr)
    def grab_sequence(self):        
        start = self.i
        brace = self.next().vals["brace"]
        
        if brace == "curly" and self.codeblock_forensic():
            return self.grab_codeblock()
        
        line_number = self.next().token.line_number
        self.step()
        exprs = []
        
        cont = (self.next().tagType != "CloseTag")
        while cont:
            cont = False
            expr = self.grab_expression()
            exprs.append(expr)
            if self.next().tagType == "CommaTag":
                cont = True
                self.step()
            elif self.next().tagType == "LabelTag":
                self.i = start
                return self.grab_struct()
                
        self.expect("CloseTag",{"brace":brace})
        if brace == "paren" and len(exprs) == 1:
            return exprs[0]
        else:
            return SequenceExpression(line_number, brace, exprs)
        
    def grab_if(self):
        line_number = self.next().token.line_number
        
        self.expect("IfTag")
        self.expect("OpenTag",{"brace":"paren"})
        cond = self.grab_expression()
        self.expect("CloseTag",{"brace":"paren"})
        cb = self.grab_codeblock()

        if self.more() and self.next().tagType == "ElseTag":
            self.step()
            if self.next().tagType == "IfTag":
                else_stmt = self.grab_if()
            else:
                else_line_number = self.next().token.line_number
                nonce_token = Token(string="true",position=None,line_number=else_line_number)
                else_cond = SimpleExpression(Tag("BoolTag",nonce_token,{"bool":True}))
                else_cb = self.grab_codeblock()
                else_stmt = IfStatement(line_number = else_line_number, condition = else_cond, codeblock = else_cb)
        else:
            else_stmt = None

        return IfStatement(line_number = line_number, condition = cond, codeblock = cb, else_stmt = else_stmt)

    def grab_while(self):
        line_number = self.next().token.line_number
        
        self.expect("WhileTag")
        self.expect("OpenTag",{"brace":"paren"})
        cond = self.grab_expression()
        self.expect("CloseTag",{"brace":"paren"})
        cb = self.grab_codeblock()

        return WhileBlock(line_number, cond, cb)        

    def grab_for(self):
        line_number = self.next().token.line_number

        self.expect("ForTag")
        self.expect("OpenTag",{"brace":"paren"})

        tekotype = self.grab_expression()
        if self.next().tagType != "LabelTag":
            TekoException("Expecting a label",self.next().token.line_number)
        label = self.next()
        self.step()
        self.expect("InTag")
        iterable = self.grab_expression()
        self.expect("CloseTag",{"brace":"paren"})

        cb = self.grab_codeblock()

        return ForBlock(line_number, tekotype, label, iterable, cb)

    def grab_assignment(self, left):
        setter = self.next().vals["setter"]
        self.step()
        right = self.grab_expression()
        self.expect("SemicolonTag")

        if setter == "=":
            return AssignmentStatement(left, right)
        else:
            binop = setter[0]
            binop_expr = BinOpExpression(binop, leftexpr = left, rightexpr = right)
            return AssignmentStatement(left = left, right = binop_expr)

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

            declaration = Declaration(line_number, tekotype, label, struct, expr)
            declarations.append(declaration)

            if self.next().tagType == "CommaTag":
                cont = True
                self.step()

        self.expect("SemicolonTag")
        return DeclarationStatement(line_number, declarations)

    # the toughest node to identify is the codeblock
    # so I needed a method to specifically look ahead and tell whether a codeblock is coming
    def codeblock_forensic(self):
        local_i = self.i + 0
        assert(self.tags[local_i].tagType == "OpenTag" and self.tags[local_i].vals["brace"] == "curly")
        local_i += 1

        while self.tags[local_i].tagType != "CloseTag":
            if self.tags[local_i].tagType == "OpenTag":
                local_i = self.resolve_brace(local_i)
            elif self.tags[local_i].tagType == "SemicolonTag":
                return True # a semicolon can only occur inside a codeblock, never a list or map
            else:
                local_i += 1

        if self.tags[local_i].vals["brace"] != "curly":
            TekoException("mismatched braces", self.tags[local_i].token.line_number)

        return False

    # makes sure that braces match, and returns position after closure of start brace
    def resolve_brace(self, local_i):
        assert(self.tags[local_i].tagType == "OpenTag")
        open_brace = self.tags[local_i].vals["brace"]
        local_i += 1
        
        while self.tags[local_i].tagType != "CloseTag":
            if self.tags[local_i].tagType == "OpenTag":
                self.resolve_brace(local_i)
            else:
                local_i += 1
            if local_i >= len(self.tags):
                TekoException("Unterminated %s brace" % self.tags[local_i].vals["brace"],
                              self.tags[local_i].token.line_number)
                
                
        close_brace = self.tags[local_i].vals["brace"]
        if open_brace != close_brace:
            TekoException("mismatched braces", self.tags[local_i].token.line_number)
        else:
            return local_i + 1

    def grab_codeblock(self):
        line_number = self.next().token.line_number
        self.expect("OpenTag", {"brace":"curly"})
        stmts = []
        
        while self.next().tagType != "CloseTag":
            stmt = self.grab_statement()
            stmts.append(stmt)

        self.expect("CloseTag", {"brace":"curly"})              
        cb = CodeBlock(line_number=line_number, statements=stmts)
        return cb

    def grab_args(self):
        self.expect("OpenTag",{"brace":"paren"})
        args = []
        cont = not (self.next().tagType == "CloseTag" and self.next().vals["brace"] == "paren") # if arglist is empty, next tag is a CloseTag )
        
        while cont:
            cont = False
            one, two = tuple(self.next(2))
            if one.tagType == "LabelTag" and two.tagType == "SetterTag" and two.vals["setter"] == "=":
                self.step()
                self.step()
                kw = one
            else:
                kw = None

            expr = self.grab_expression()
            arg = ArgNode(expr, kw)
            args.append(arg)

            if self.next().tagType == "CommaTag":
                cont = True
                self.step()

        self.expect("CloseTag",{"brace":"paren"})
        return args

    def grab_struct(self):
        elems = []
        line_number = self.next().token.line_number
        self.expect("OpenTag",{"brace":"paren"})
        cont = (self.next().tagType != "CloseTag")
        while cont:
            cont = False
            tekotype = self.grab_expression()
            if self.next().tagType != "LabelTag":
                TekoException("Expected LabelTag instead of " + str(self.next()), self.next().token.line_number)
            label = self.next()
            self.step()
            
            if self.next().tagType == "QMarkTag":
                self.step()
                default = self.grab_expression()
            else:
                default = None

            elem = StructElem(tekotype, label, default)
            elems.append(elem)
            
            if self.next().tagType == "CommaTag":
                cont = True
                self.step()

        self.expect("CloseTag",{"brace":"paren"})
        struct = NewStruct(line_number, elems)
        return struct

    # def grab_map

    def grab_class(self):
        line_number = self.next().token.line_number
        self.expect("ClassTag")
        classname = self.next()
        self.step()
        self.expect("OpenTag",{"brace":"curly"})
        
        current_vis = "protected" # default visibility level
        vis_sections = []
        declaration_dict = {}

        while self.next().tagType != "CloseTag":
            if self.next().tagType == "VisibilityTag":
                vis = self.next().vals["visibility"]
                if vis in vis_sections:
                    TekoException("Two %s visibility sections in class %s" % (vis, classname.vals["label"]), self.next().token.line_number)
                current_vis = vis
                vis_sections.append(vis)
                self.step()
                self.expect("ColonTag")
            else:
                if self.next().tagType == "LetTag":
                    tekotype = None
                    dec_line_number = self.next().token.line_number
                    self.step()
                else:
                    tekotype = self.grab_expression()
                    dec_line_number = None
                dec = self.grab_declarations(tekotype, dec_line_number)
                declaration_dict[current_vis] = declaration_dict.get(current_vis,[]) + [dec]

        self.expect("CloseTag",{"brace":"curly"})
        return ClassDeclaration(line_number, classname, declaration_dict)
