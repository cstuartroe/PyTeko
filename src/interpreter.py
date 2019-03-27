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
                     NewStructNode:        "eval_new_struct"}

    BINOP_DISPATCH = {"+": "_add",
                      "-": "_sub",
                      "*": "_mul",
                      "/": "_div",
                      "^": "_exp",
                      "%": "_mod",
                      "&&":"_and",
                      "||":"_or",
                      ":": "_link"}

    COMP_DISPATCH = {"==":[0],
                     "!=":[-1,1],
                     "<": [-1],
                     "<=":[-1,0],
                     ">": [1],
                     ">=":[0,1]}
    
    def __init__(self, owner):
        assert(type(owner) is TekoModule or isinstance(owner, TekoFunction))
        self.owner = owner

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
            return self.owner.get_var(tag.vals["label"])
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

    def eval_seq_expr(self, seq_expr):
        raise RuntimeError("Not yet implemented!")

    def eval_call_expr(self, call_expr):
        left = self.eval_expression(call_expr.leftexpr)
        assert(isinstance(left.tekotype, TekoFunctionType))

        evaluated_args = []
        for argnode in call_expr.args:
            arg = self.eval_expression(argnode.expr)
            evaluated_args.append(arg)

        return left.exec(evaluated_args)

    def eval_attr_expr(self, attr_expr):
        obj = self.eval_expression(attr_expr.leftexpr)
        label = attr_expr.label.vals["label"]
        
        if obj.is_free_attr(label):
            TekoException("%s has no attribute %s" % (repr(obj),label), attr_expr.line_number)
        else:
            return obj.get_attr(label)

    def eval_binop_expr(self, binop_expr):
        leftval  = self.eval_expression(binop_expr.leftexpr)
        rightval = self.eval_expression(binop_expr.rightexpr)
        if not isTekoInstance(rightval, leftval.tekotype):
            TekoException("Incompatible types for binary operation: %s, %s" % (leftval.tekotype, rightval.tekotype), binop_expr.line_number)

        binop_funcname = TekoInterpreter.BINOP_DISPATCH[binop_expr.binop]
        returnval = leftval.get_attr(binop_funcname).exec([rightval])

        assert(returnval.tekotype == leftval.tekotype)
        return returnval

    def eval_not_expr(self, not_expr):
        val = self.eval_expression(not_expr.expr)
        if type(val) is not TekoBool:
            TekoException("! must be used with boolean",not_expr.line_number)

        return TekoBool(not val._boolval)

    def eval_comp_expr(self, comp_expr):
        leftval = self.eval_expression(comp_expr.leftexpr)
        rightval = self.eval_expression(comp_expr.rightexpr)
        if not isTekoInstance(rightval, leftval.tekotype):
            TekoException("Incompatible types for comparison: %s, %s" % (leftval.tekotype, rightval.tekotype), comp_expr.line_number)

        if comp_expr.comp == "<:":
            raise RuntimeError("Not yet implemented!")
        
        else:
            if leftval.ns.is_free_attr("_compare"):
                if comp_expr.comp not in ["==","!="]:
                    TekoException(str(leftval) + " has no attribute _compare", comp_expr.line_number)
                    
                comp_result = leftval.get_attr("_eq").exec([rightval])
                if comp_expr.comp == "==":
                    returnval = comp_result
                else:
                    returnval = TekoBool(not comp_result._boolval)
                
            else:
                assert(leftval.ns.is_free_attr("_eq"))
                comp_result = leftval.get_attr("_compare").exec([rightval])
                assert(type(comp_result) is TekoInt)
                assert(comp_result._intval in [-1, 0, 1])
                b = comp_result._intval in TekoInterpreter.COMP_DISPATCH[comp_expr.comp]
                returnval = TekoBool(b)            

        assert(type(returnval) is TekoBool)
        return returnval
    
    def eval_conv_expr(self, conv_expr):
        val = self.eval_expression(conv_expr.leftexpr)

        conv_funcname = TekoInterpreter.CONV_DISPATCH[conv_expr.conv]
        try:
            return TekoString(val.get(conv_funcname).exec([]))
        except AttributeError:
            TekoException(str(val) + " cannot undergo conversion " + conv_expr.conv)

    def eval_codeblock(self, codeblock):
        raise RuntimeError("Not yet implemented!")

    def eval_new_struct(self, new_struct):
        raise RuntimeError("Not yet implemented!")
