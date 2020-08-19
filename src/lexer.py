import string

alphabet = set(string.ascii_letters) | {'_'}
digits = set(string.digits)
punctuation = set(string.punctuation) - {'_'}
whitespace = set(' \t\r')


def getlines(file):
    if type(file) is str:
        with open(file, "r") as fh:
            return fh.read().split('\n')
    else:
        return file.read().split('\n')


class TekoLexer:
    LINE_COMMENT_START = '//'
    ESCAPES = {
        '\\n': '\n',
        '\\r': '\r',
        '\\t': '\t',
        '\\\\': '\\',
        '\\"': '"'
    }
    TOKEN_LABELS = {'symbol', 'integer', 'float', 'string'}

    def __init__(self, lexer_file='lexer'):
        rule_lines = getlines(lexer_file)
        assert (len(rule_lines) == 3)
        assert (rule_lines[2] == '')

        KEYWORDS, kwlist = rule_lines[0].split(': ')
        assert (KEYWORDS == 'KEYWORDS')
        self.keywords = set(kwlist.split(' '))

        PUNCT, plist = rule_lines[1].split(': ', 1)
        assert (PUNCT == 'PUNCT')
        self.punct_seqs = set(plist.split(' '))
        assert (all(all(c in punctuation for c in ps) for ps in self.punct_seqs))

    def lex(self, file):
        self.lines = getlines(file)
        self.tokens = []
        self.row = 0
        self.col = 0

        for _ in self.lines:
            self.parse_line()

        return self.tokens

    def next(self, i=1):
        line = self.lines[self.row]
        return line[self.col:min(self.col + i, len(line))]

    def issue_error(self, message):
        s = f"Line {self.row + 1}, column {self.col + 1}"
        s += '\n' + self.lines[self.row]
        s += '\n' + ' ' * self.col + '^'
        s += '\n' + message
        raise ValueError(s)

    def parse_line(self):
        self.pass_whitespace()
        while self.col < len(self.lines[self.row]) and self.next(2) != TekoLexer.LINE_COMMENT_START:
            self.tokens.append(self.grab_token())
            self.pass_whitespace()
        self.row += 1

    def pass_whitespace(self):
        while self.next() in whitespace:
            self.col += 1

    def grab_token(self):
        if self.next() in alphabet:
            return self.grab_symbol()
        elif self.next() in digits:
            return self.grab_number()
        elif self.next() == '"':
            return self.grab_string()
        elif self.next() in punctuation:
            return self.grab_punctuation()
        else:
            self.issue_error("Unknown start to token")

    def grab_symbol(self):
        start_col = self.col
        s = ""
        while self.next() in (alphabet | digits):
            s += self.next()
            self.col += 1

        if s in self.keywords:
            return s, None, self.row, start_col
        else:
            return "symbol", s, self.row, start_col

    def grab_number(self):
        start_col = self.col
        s = ""

        while self.next() in digits:
            s += self.next()
            self.col += 1

        if self.next() != '.':
            return "integer", int(s), self.row, start_col

        s += '.'
        self.col += 1

        while self.next() in digits:
            s += self.next()
            self.col += 1

        return "float", float(s), self.row, start_col

    def grab_punctuation(self):
        start_col = self.col
        s = self.next()
        self.col += 1

        c = self.next()
        while c in punctuation and (s + c) in self.punct_seqs:
            s += c
            self.col += 1
            c = self.next()

        return s, None, self.row, start_col

    def grab_string(self):
        start_col = self.col
        assert(self.next() == '"')
        self.col += 1
        s = ""

        while self.next() != '"':
            if self.col == len(self.lines[self.row]):
                self.issue_error("EOL while parsing string")

            s += self.grab_character()

        self.col += 1

        return "string", s, self.row, start_col

    def grab_character(self):
        if self.next() == '\\':
            c = TekoLexer.ESCAPES.get(self.next(2),
                                      self.issue_error("Invalid escape sequence"))
            self.col += 2
        else:
            c = self.next()
            self.col += 1
        return c



