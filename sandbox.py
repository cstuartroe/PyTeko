from lark.exceptions import UnexpectedToken

from src.parser import TekoAST
from src.basics import *

# ast = TekoAST("simple.to")

s = TekoString("s")
t = s.get("type").value
print(t is TekoStringType)
f = t.get("fields").value
