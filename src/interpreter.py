from .types import *
from .namespace import *
from .parsenode import ExpressionStatement, DeclarationStatement, \
     AssignmentStatement, IfStatement, WhileBlock, ForBlock, \
     ClassDeclaration 

class TekoInterpreter:
    DISPATCH = {ExpressionStatement:"exec_expr",
                DeclarationStatement:"exec_decl",
                AssignmentStatement:"exec_asst",
                IfStatement:"exec_if",
                WhileBlock:"exec_while",
                ForBlock:"exec_for",
                ClassDeclaration:"exec_class"} 
    
    def __init__(self, base_ns = StandardNS()):
        self.ns = Namespace(base_ns)

    def exec(self, statement):
        method_name = TekoInterpreter.DISPATCH[type(statement)]
        method = getattr(self, method_name)
        method(statement)

    def exec_expr(self, expr):
        print(expr)

    def exec_decl(self, decl):
        print(decl)

    def exec_asst(self, asst):
        print(asst)

    def exec_if(self, if_stmt):
        print(if_stmt)

    def exec_while(self, while_block):
        print(while_block)

    def exec_for(self, for_block):
        print(for_block)

    def exec_class(self, class_decl):
        print(class_decl)
