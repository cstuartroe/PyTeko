from .tokenizer import is_alpha, is_num, Token

BRACES = {"paren","curly","square","angle"}
BINOPS = {"+","-","*","/","^","%","&&","||"}
SETTERS = {"=","+=","-=","*=","/=","^=","%="}
COMPARISONS = {"==","!=","<","<=",">",">=","<:"}
CONVERSIONS = {".","$","[]","{}","<>"}
ENUM_TAGTYPES = {"OpenTag":BRACES,"CloseTag":BRACES,"SetterTag":SETTERS,
                 "ComparisonTag":COMPARISONS,"ConversionTag":CONVERSIONS}
STATIC_TAGS = {";":"SemicolonTag",":":"ColonTag",",":"CommaTag","?":"QMarkTag",
               "!":"BangTag","if":"IfTag","else":"ElseTag","for":"ForTag",
               "while":"WhileTag","in":"InTag","let":"LetTag"}

class Tag:
    tagTypes = {"LabelTag":{"label"}, "StringTag":{"string"},
                "IntTag":{"int"}, "RealTag":{"real"},
                "BoolTag":{"bool"}, "IfTag":set(), "ElseTag":set(),
                "ForTag":set(),"WhileTag":set(), "InTag":set(), "LetTag":set(),
                "SemicolonTag":set(),"ColonTag":set(), "CommaTag":set(),
                "QMarkTag":set(), "BangTag":set(),"DotTag":set(),
                "OpenTag":{"brace"},"CloseTag":{"brace"},
                "LAngleTag":set(),"RAngleTag":set(), "BinOpTag":{"binop"},
                "SetterTag":{"setter"},"ComparisonTag":{"comparison"},
                "ConversionTag":{"conversion"}}

    def __init__(self,tagType,token,vals={}):
        assert(tagType in Tag.tagTypes)
        assert(type(token) == Token)
        assert(set(vals.keys()) == Tag.tagTypes[tagType])
        
        self.tagType = tagType
        self.token = token
        self.vals = vals
        
        if self.tagType in ENUM_TAGTYPES:
            assert(self.only_val() in ENUM_TAGTYPES[self.tagType])

    def only_val(self):
        vall = list(self.vals.values())
        assert(len(vall) == 1)
        return vall[0]

    def __str__(self):
        simple_tagTypes = {"LabelTag","IntTag","RealTag","BoolTag",
                    "BinOpTag","SetterTag","ComparisonTag","ConversionTag"}
        if self.tagType in simple_tagTypes:
            s = str(self.only_val())
        elif self.tagType == "StringTag":
            s = '"%s"' % self.vals["string"]
        elif self.tagType == "OpenTag":
            brace = self.vals["brace"]
            if brace == "paren": s = "("
            elif brace == "curly": s = "{"
            elif brace == "square": s = "["
            elif brace == "angle": s = "<"
        elif self.tagType == "CloseTag":
            brace = self.vals["brace"]
            if brace == "paren": s = ")"
            elif brace == "curly": s = "}"
            elif brace == "square": s = "]"
            elif brace == "angle": s = ">"
        else:
            s = ""
        return "<" + self.tagType + " " + s + " >"

    def __repr__(self):
        return str(self)

    def __eq__(self,other):
        return self.tagType == other.tagType and self.vals == other.vals

def get_tags(tokens):    
    for token in tokens:
        s = token.string
        
        if s in STATIC_TAGS: yield Tag(STATIC_TAGS[s],token)

        elif s == "(": yield Tag("OpenTag",token,{"brace":"paren"})
        elif s == ")": yield Tag("CloseTag",token,{"brace":"paren"})
        elif s == "{": yield Tag("OpenTag",token,{"brace":"curly"})
        elif s == "}": yield Tag("CloseTag",token,{"brace":"curly"})
        elif s == "[": yield Tag("OpenTag",token,{"brace":"square"})
        elif s == "]": yield Tag("CloseTag",token,{"brace":"square"})
        elif s == "<": yield Tag("LAngleTag",token)
        elif s == ">": yield Tag("RAngleTag",token)
        elif s == ".": yield Tag("DotTag",token)

        elif s in BINOPS: yield Tag("BinOpTag",token,{"binop":s})
        elif s in SETTERS: yield Tag("SetterTag",token,{"setter":s})
        elif s in COMPARISONS: yield Tag("ComparisonTag",token,{"comparison":s})
        elif s in CONVERSIONS: yield Tag("ConversionTag",token,{"conversion":s})

        elif s == "true": yield Tag("BoolTag",token,{"bool":True})
        elif s == "false": yield Tag("BoolTag",token,{"bool":False})

        elif s[0] == '"': yield Tag("StringTag",token,{"string":s})
        elif is_alpha(s[0]): yield Tag("LabelTag",token,{"label":s})
        elif is_num(s[0]):
            if "." in s:
                yield Tag("RealTag",token,{"real":eval(s+"0")})
            else:
                yield Tag("IntTag",token,{"int":eval(s)})
