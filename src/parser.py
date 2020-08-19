import re

from .lexer import getlines, alphabet, punctuation, TekoLexer


def caps(c):
    assert (len(c) == 1)
    return c.lower() != c or c == '_'


class GrammarParser:
    MODIFIERS = set('*+?')

    def __init__(self, file="grammar"):
        self.lines = getlines(file)
        assert(self.lines[-1] == '')
        self.row = 0
        self.rules = {}
        while self.row < len(self.lines) - 1:
            self.grab_rule()

    def grab_rule(self):
        assert(all(caps(c) for c in self.lines[self.row]))
        rulename = self.lines[self.row]
        self.row += 1
        outcomes = []

        while self.lines[self.row].startswith('  '):
            outcomes.append(self.grab_outcome())

        assert(len(outcomes)) > 0
        self.rules[rulename] = outcomes

    def grab_outcome(self):
        terms = self.lines[self.row][2:].split(' ')
        outcome = []
        for term in terms:
            if all(c in punctuation for c in term):
                outcome.append((term, None))
            elif term[0] in alphabet:
                if term[-1] in GrammarParser.MODIFIERS:
                    symbol, modifier = term[:-1], term[-1]
                else:
                    symbol, modifier = term, None

                assert((symbol in TekoLexer.TOKEN_LABELS) or all(caps(c) for c in symbol))
                outcome.append((symbol, modifier))
            else:
                raise ValueError
        assert(len(outcome) > 0)
        self.row += 1
        return outcome
