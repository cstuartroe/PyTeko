from .tokenizer import is_alpha, is_num, Token
from .general import TekoException

BRACES = {"paren","curly","square","angle"}
BINOPS = {"+","-","*","/","^","%","&&","||",":"}
SETTERS = {"=","+=","-=","*=","/=","^=","%="}
COMPARISONS = {"==","!=","<","<=",">",">=","<:"}
CONVERSIONS = {".","$","[]","{}","<>"}
VISIBILITIES = {"public","protected","private","readonly"}
ENUM_TAGTYPES = {"OpenTag":BRACES,"CloseTag":BRACES,"SetterTag":SETTERS,
                 "ComparisonTag":COMPARISONS,"ConversionTag":CONVERSIONS}
STATIC_TAGS = {";":"SemicolonTag",",":"CommaTag","?":"QMarkTag", ":":"ColonTag",
               "!":"BangTag","if":"IfTag","else":"ElseTag","for":"ForTag",
               "while":"WhileTag","in":"InTag","let":"LetTag","class":"ClassTag"}

OPEN_LITERALS  = {"paren":"(","curly":"{","square":"[","angle":"<"}
CLOSE_LITERALS = {"paren":")","curly":"}","square":"]","angle":">"}

ESCAPE_SEQS = {r"\"":'"',r"\n":'\n',r"\'":"'",r"\t":'\t'}

def digest_char(s, i):
    if s[i] == "\\":
        if s[i:i+2] in ESCAPE_SEQS:
            c = ESCAPE_SEQS[s[i:i+2]]
            return c, i+2
    else:
        return s[i], i+1

# takes a string escaped according to Teko syntax, and returns the literal string it represents
def digest_string(token):
    escaped_s = token.string
    assert(escaped_s[0] == '"' and escaped_s[-1] == '"')
    
    i = 1
    literal_s = ""
    while i < len(escaped_s) - 1:
        try:
            c, i = digest_char(escaped_s, i)
        except BaseException:
            TekoException("Error while parsing string",token.line_number)
        literal_s += c

    return literal_s

class Tag:
    tagTypes = {"LabelTag":{"label"}, "StringTag":{"string"},
                "IntTag":{"int"}, "RealTag":{"real"},
                "BoolTag":{"bool"}, "IfTag":set(), "ElseTag":set(),
                "ForTag":set(),"WhileTag":set(), "InTag":set(), "LetTag":set(),
                "ClassTag":set(), "VisibilityTag":{"visibility"},
                "SemicolonTag":set(),"ColonTag":set(), "CommaTag":set(),
                "QMarkTag":set(), "BangTag":set(),"DotTag":set(),
                "OpenTag":{"brace"},"CloseTag":{"brace"},
                "LAngleTag":set(),"RAngleTag":set(), "BinOpTag":{"binop"},
                "SetterTag":{"setter"},"ComparisonTag":{"comparison"},
                "ConversionTag":{"conversion"}, "AttrTag":set()}

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
            s = OPEN_LITERALS[ self.vals["brace"] ]
        elif self.tagType == "CloseTag":
            s = CLOSE_LITERALS[ self.vals["brace"] ]
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

        elif s == "public":    yield Tag("VisibilityTag",token,{"visibility":s})
        elif s == "protected": yield Tag("VisibilityTag",token,{"visibility":s})
        elif s == "private":   yield Tag("VisibilityTag",token,{"visibility":s})
        elif s == "readonly":  yield Tag("VisibilityTag",token,{"visibility":s})

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

        elif s[0] == '"': yield Tag("StringTag",token,{"string":digest_string(token)})
        elif is_alpha(s[0]): yield Tag("LabelTag",token,{"label":s})
        elif is_num(s[0]):
            if "." in s:
                yield Tag("RealTag",token,{"real":eval(s+"0")})
            else:
                yield Tag("IntTag",token,{"int":eval(s)})

        else:
            raise ValueError("Unreadable token: " + token.string)
