from src.lexer import TekoLexer
from src.parser import GrammarParser

for t in TekoLexer().lex("simple.to"):
    print(t)

print(GrammarParser().rules)