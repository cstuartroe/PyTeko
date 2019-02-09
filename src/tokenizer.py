import re

alpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
nums = "0123456789"
white = " \t\n"
punct = "!\"#$%&'()*+,-./:;<=>?@[\\]^`|{|}~"
punct_combos = ["==","<=",">=","!=","<:","+=",
                "-=","*=","/=","^=","%%=","{}","[]","<>"]
esc_punct = [re.escape(p) for p in (list(punct) + punct_combos)]

TOKEN_RES = {"comment":"//.*\n",
             "str":"\"(?!\")\"",
             "label":"(%s)(%s)*" % ("|".join(alpha),"|".join(alpha+nums)),
             "num":"(%s)+\.?(%s)*" % ("|".join(nums),"|".join(nums)),
             "punct":"(%s)" % "|".join(esc_punct),
             "white":"\s+"}

def grab(s,regex_name):
    s += "\n"
    regex = TOKEN_RES[regex_name]
    m = re.match(regex,s)
    try:
        start, end = m.span()
    except AttributeError:
        print(s,regex_name)
    return s[end:],s[:end]

def tokenize(s):
    tokens = []
    while len(s) > 0:
        new = None
        if len(s) >= 2 and s[:2] == "//":
            s, _ = grab(s,"comment")
        elif s[0] == '"':
            s, new = grab(s,"str")
        elif s[0] in alpha:
            s, new = grab(s,"label")
        elif s[0] in nums:
            s, new = grab(s,"num")
        elif s[0] in punct:
            s, new = grab(s,"punct")
        elif s[0] in white:
            s, _ = grab(s,"white")
        else:
            raise ValueError("unknown character " + s[0])
        if new:
            tokens.append(new)
    return tokens
    
