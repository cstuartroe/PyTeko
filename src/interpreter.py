from .parsenode import *
from .framework import *
from .primitives import *

class TekoInterpreter:
    STMT_DISPATCH = {ExpressionStatement:  "exec_expr_stmt",
                     DeclarationStatement: "exec_decl_stmt",
                     AssignmentStatement:  "exec_asst_stmt",
                     IfStatement:          "exec_if_stmt",
                     WhileBlock:           "exec_while",
                     ForBlock:             "exec_for",
                     ClassDeclaration:     "exec_class_decl"}
    
    EXPR_DISPATCH = {SimpleExpression:     "eval_simple_expr",
                     SequenceExpression:   "eval_seq_expr",
                     CallExpression:       "eval_call_expr",
                     AttrExpression:       "eval_attr_expr",
                     BinOpExpression:      "eval_binop_expr",
                     NotExpression:        "eval_not_expr",
                     ComparisonExpression: "eval_comp_expr",
                     ConversionExpression: "eval_conv_expr",
                     CodeBlock:            "eval_codeblock",
                     NewStruct:            "eval_new_struct"}
    
    def __init__(self, base_ns = StandardNS()):
        self.ns = Namespace(base_ns)

    def exec(self, statement):
        method_name = TekoInterpreter.STMT_DISPATCH[type(statement)]
        method = getattr(self, method_name)
        method(statement)

    # # # Executing statements:

    def exec_expr_stmt(self, expr_stmt):
        self.eval_expression(expr_stmt.expression)

    def exec_decl_stmt(self, decl_stmt):
        for decl in decl_stmt.declarations:
            self.exec_declaration(decl)

    def exec_asst_stmt(self, asst):
        raise RuntimeError("Not yet implemented!")

    def exec_if_stmt(self, if_stmt):
        raise RuntimeError("Not yet implemented!")

    def exec_while(self, while_block):
        raise RuntimeError("Not yet implemented!")

    def exec_for(self, for_block):
        raise RuntimeError("Not yet implemented!")

    def exec_class_decl(self, class_decl):
        raise RuntimeError("Not yet implemented!")

    # # # Executing expressions and declarations:

    def eval_expression(self, expression):
        method_name = TekoInterpreter.EXPR_DISPATCH[type(expression)]
        method = getattr(self, method_name)
        return method(expression)

    def exec_declaration(self, expression):
        raise RuntimeError("Not yet implemented!")

    # # # Evaluating expression types:

    def eval_simple_expr(self, simple_expr):
        tag = simple_expr.tag
        if tag.tagType == "LabelTag":
            return self.ns.get(tag.vals["label"])
        elif tag.tagType == "StringTag":
            return TekoString(tag.vals["string"])
        elif tag.tagType == "IntTag":
            return TekoInt(tag.vals["int"])
        elif tag.tagType == "RealTag":
            return TekoReal(tag.vals["real"])
        elif tag.tagType == "BoolTag":
            return TekoBool(tag.vals["bool"])
        else:
            raise RuntimeError("Unknown tagType: " + tag.tagType)

    def eval_call_expr(self, call_expr):
        left = self.eval_expression(call_expr.leftexpr)
        assert(isinstance(left.tekotype, TekoFunctionType))

        evaluated_args = []
        for argnode in call_expr.args:
            arg = self.eval_expression(argnode.expr)
            evaluated_args.append(arg)

        left.exec(evaluated_args)
