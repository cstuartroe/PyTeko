from .tokenizer import alpha, nums

BRACES = {"paren","curly","square","angle"}
BINOPS = {"+","-","*","/","^","%","&&","||"}
SETTERS = {"=","+=","-=","*=","/=","^=","%="}
COMPARISONS = {"==","!=","<","<=",">",">=","<:"}
CONVERSIONS = {".","$","[]","{}","<>"}
ENUM_TAGTYPES = {"OpenTag":BRACES,"CloseTag":BRACES,"SetterTag":SETTERS,
                 "ComparisonTag":COMPARISONS,"ConversionTag":CONVERSIONS}

class Tag:
    tagTypes = {"LabelTag":{"label"}, "StringTag":{"string"},
                "IntTag":{"int"}, "RealTag":{"real"},
                "BoolTag":{"bool"}, "IfTag":set(), "ElseTag":set(),
                "ForTag":set(),"WhileTag":set(), "InTag":set(), "LetTag":set(),
                "SemicolonTag":set(),"ColonTag":set(), "CommaTag":set(),
                "QMarkTag":set(), "BangTag":set(),"AttrTag":set(),
                "OpenTag":{"brace"},"CloseTag":{"brace"},
                "LAngleTag":set(),"RAngleTag":set(), "BinOpTag":{"binop"},
                "SetterTag":{"setter"},"ComparisonTag":{"comparison"},
                "ConversionTag":{"conversion"}}

    def __init__(self,tagType,vals={}):
        assert(tagType in Tag.tagTypes)
        try:
            assert(set(vals.keys()) == Tag.tagTypes[tagType])
        except AssertionError as e:
            print(tagType, vals, set(vals.keys()), Tag.tagTypes[tagType])
            raise e
        self.tagType = tagType
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
        return self.tagType + " " + s

def get_tags(tokens):
    for token in tokens:
        if token == ";": yield Tag("SemicolonTag")
        elif token == ":": yield Tag("ColonTag")
        elif token == ",": yield Tag("CommaTag")
        elif token == "?": yield Tag("QMarkTag")
        elif token == "!": yield Tag("BangTag")

        elif token == "if": yield Tag("IfTag")
        elif token == "else": yield Tag("ElseTag")
        elif token == "for": yield Tag("ForTag")
        elif token == "while": yield Tag("WhileTag")
        elif token == "in": yield Tag("InTag")
        elif token == "let": yield Tag("LetTag")

        elif token == "(": yield Tag("OpenTag",{"brace":"paren"})
        elif token == ")": yield Tag("CloseTag",{"brace":"paren"})
        elif token == "{": yield Tag("OpenTag",{"brace":"curly"})
        elif token == "}": yield Tag("CloseTag",{"brace":"curly"})
        elif token == "[": yield Tag("OpenTag",{"brace":"square"})
        elif token == "]": yield Tag("CloseTag",{"brace":"square"})
        elif token == "<": yield Tag("LAngleTag")
        elif token == ">": yield Tag("RAngleTag")

        elif token in BINOPS: yield Tag("BinOpTag",{"binop":token})
        elif token in SETTERS: yield Tag("SetterTag",{"setter":token})
        elif token in COMPARISONS: yield Tag("ComparisonTag",{"comparison":token})
        elif token in CONVERSIONS: yield Tag("ConversionTag",{"conversion":token})

        elif token == "true": yield Tag("BoolTag",{"bool":True})
        elif token == "false": yield Tag("BoolTag",{"bool":False})

        elif token[0] == '"': yield Tag("StringTag",{"string":eval(token)})
        elif token[0] in alpha: yield Tag("LabelTag", {"label":token})
        elif token[0] in nums:
            if "." in token:
                yield Tag("RealTag",{"real":eval(token+"0")})
            else:
                yield Tag("IntTag",{"int":eval(token)})
