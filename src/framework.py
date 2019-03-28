from .parser import TekoParser
from .parsenode import *
from .general import *

class Variable:
    def __init__(self, tekotype, val=None):
        assert(isTekoType(tekotype))
        assert(tekotype is not TekoVoidType)
        self.tekotype = tekotype
        self.val = val

    def get_val(self):
        return self.val

    def get_tekotype(self):
        return self.tekotype

    def set(self, val):
        assert(isTekoInstance(val, self.tekotype))
        self.val = val

    def __str__(self):
        return "<%s :: %s>" % (str(self.tekotype),str(self.val))

    def __repr__(self):
        return str(self)

class Namespace:
    def __init__(self, owner):
        self.vars = {}
        assert(isinstance(owner, TekoObject))
        self.owner = owner

    def outer_namespaces(self):
        return [outer.ns for outer in self.owner.outers]

    def declare(self, label, tekotype, val = None):
        assert(type(label) == str)
        if not self.is_free_attr(label):
            raise ValueError("Label already assigned: " + label) # should be checked by interpreter
        
        var = Variable(tekotype)

        if val:
            var.set(val)
            # assert(val.ns.outer_ns is self)
        
        self.vars[label] = var

    # methods suffixed with _attr only check own ns
    # methods suffixed with _var check outer namespaces as well

    # checks whether a label is available to be declared
    def is_free_attr(self, label):
        if label == "_tostr":
            return False
        else:
            return (label not in self.vars)

    def is_free_var(self, label):
        if not self.is_free_attr(label):
            return False
    
        for outer_namespace in self.outer_namespaces():
            if not outer_namespace.is_free_var(label):
                return False
            
        return True

    def fetch_attr(self, label):
        if label=="_tostr" and "_tostr" not in self.vars:            
            self.vars["_tostr"] = Variable(tekotype = TekoTostrType, val = TekoTostr(outer = self.owner))
        
        return self.vars.get(label,None)

    def fetch_var(self, label):
        if self.fetch_attr(label):
            return self.fetch_attr(label)
        
        for outer_namespace in self.outer_namespaces():
            if outer_namespace.fetch_var(label):
                return outer_namespace.fetch_var(label)

        return None

    def get_attr(self, label):
        return self.fetch_attr(label).get_val()

    def get_var(self, label):
        return self.fetch_var(label).get_val()

    def tekotype_attr(self, label):
        return self.fetch_attr(label).get_tekotype()

    def tekotype_var(self, label):
        return self.fetch_var(label).get_tekotype()

    def set(self, label, val):
        self.fetch_attr(label).set(val)

    def __str__(self):
        s = "Teko Namespace:\n---\n"
        m = max([len(label) for label in self.vars.keys()])
        for label, var in self.vars.items():
            s += label.ljust(m," ") + ": " + str(var) + "\n"
        return s

    def __repr__(self):
        return str(self)

###

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

    def exec_asst_stmt(self, asst_stmt):
        entity, label = self.eval_lhs(asst_stmt.left)
        val = self.eval_expression(asst_stmt.right)

        if entity.immutable:
            TekoException(repr(entity) + " is immutable", -1)
        
        if not (isTekoInstance(val, entity.tekotype_var(label))):
            TekoException(str(val) + " is not of type " + str(entity.tekotype_var(label)), asst_stmt.line_number)
            
        entity.set(label, val)

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

    def exec_declaration(self, declaration):
        if self.owner.immutable:
            TekoException(repr(self.owner) + " is immutable", -1)
            
        label = declaration.label.vals["label"]

        if declaration.expression:
            val = self.eval_expression(declaration.expression)
        else:
            val = None
        
        if declaration.tekotype:
            tekotype = self.eval_expression(declaration.tekotype)
            
            if declaration.struct:
                tekotype = TekoFunctionType(return_type = tekotype, arg_struct = self.eval_new_struct(declaration.struct))
        else:
            assert(val is not None)
            tekotype = val.tekotype

        if tekotype is TekoVoidType:
            TekoException("Cannot create variable " + label + " of type void", declaration.line_number)
        
        if (val is not None) and (not (isTekoInstance(val, tekotype))):
            TekoException(str(val) + " is not of type " + str(tekotype), declaration.line_number)

        self.owner.declare(label = label, tekotype = tekotype, val = val)

    def eval_lhs(self, lhs):
        if type(lhs) is SimpleExpression:
            assert lhs.tag.tagType == "LabelTag"
            entity = self.owner
            label = lhs.tag.vals["label"]
        elif type(lhs) is AttrExpression:
            entity = self.eval_expression(lhs.leftexpr)
            label = lhs.label.vals["label"]
        else:
            TekoException("Invalid LHS: " + str(lhs), lhs.line_number)

        return entity, label

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

###

THROW_ERROR = 0

class TekoObject:
    def __init__(self, tekotype, name="TekoObject", parent=None, immutable=False):
        assert(tekotype is None or isTekoType(tekotype))
        assert(type(name) == str)
        self.tekotype = tekotype
        self.name = name
        self.ns = Namespace(self)
                   
        if parent is not None:
            self.set_parent(parent)
            
        self.immutable = immutable

    def declare(self, label, tekotype, val = None):
        self.ns.declare(label, tekotype, val)

    def is_free_attr(self, label):
        return self.ns.is_free_attr(label)

    def is_free_var(self, label):
        return self.ns.is_free_var(label)

    def get_attr(self,label,default=THROW_ERROR):
        if self.ns.is_free_attr(label):
            if default is THROW_ERROR:
                raise AttributeError(str(self) + " has no attribute " + label)
            else:
                return default
        else:
            return self.ns.get_attr(label)

    def get_var(self,label,default=THROW_ERROR):
        if self.ns.is_free_var(label):
            if default is THROW_ERROR:
                raise AttributeError(str(self) + " does not have scope over a variable called " + label)
            else:
                return default
        else:
            return self.ns.get_var(label)

    def tekotype_attr(self, label):
        return self.ns.tekotype_attr(label)

    def tekotype_var(self, label):
        return self.ns.tekotype_var(label)

    def set(self,label,val):
        self.ns.set(label, val)

    def get_parent(self):
        assert(isTekoType(self))
        return self.get_attr("_parent",None)

    def set_parent(self,parent):
        self.declare("_parent",TekoType,parent)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s :: %s>' % (str(self.tekotype), self.get_attr("_tostr").exec([])._strval)

def isTekoType(tekoObj):
    if tekoObj is TekoType:
        return True
    else:
        return isTekoSubtype(tekoObj.tekotype,TekoType)

def isTekoSubtype(sub,sup):
    if not isTekoType(sub) or not isTekoType(sup):
        raise ValueError("Not both types: " + str(tt1) + ", " + str(tt2))

    if sup is TekoObjectType:
        return True
    elif sub is sup:
        return True
    elif sub.get_parent() is None:
        return False
    else:
        return isTekoSubtype(sub.get_parent(), sup)

def isTekoInstance(tekoObj, tekotype):
    assert(isTekoType(tekotype))
    return isTekoSubtype(tekoObj.tekotype,tekotype)

TekoType            = TekoObject(None,     name="type", immutable = True)
TekoType.tekotype   = TekoType

TekoObjectType      = TekoObject(TekoType, name="obj",  immutable = True)

###

# Structs and functions need to be defined first because other primitives have function attributes

class TekoStructElem:
    def __init__(self, tekotype, label, default=None):
        assert(isTekoType(tekotype))
        assert(type(label) == str)
        assert(default is None or isTekoInstance(default, tekotype))
               
        self.tekotype = tekotype
        self.label = label
        self.default = default

    def __str__(self):
        s = str(self.tekotype) + " " + self.label
        if self.default:
            s += " ? " + repr(self.default)
        return s

class TekoNewStruct(TekoObject):
    def __init__(self, struct_elems, **kwargs):
        super().__init__(TekoStructType, immutable = True, **kwargs)

        self.struct_elems = []
        for struct_elem in struct_elems:
            assert(type(struct_elem) == TekoStructElem)
            self.struct_elems.append(struct_elem)

    def __str__(self):
        return "(%s)" % ", ".join([str(e) for e in self.struct_elems])

class TekoStructInstance(TekoObject):
    def __init__(self, new_struct, args, **kwargs):
        assert(type(new_struct) == TekoNewStruct)
        
        super().__init__(tekotype = new_struct, **kwargs)

        self.values = []

        for i, arg in enumerate(args):
            assert(isTekoInstance(arg, self.tekotype.struct_elems[i].tekotype))
            self.values.append((self.tekotype.struct_elems[i].label,arg))

        for i in range(len(args),len(self.tekotype.struct_elems)):
            self.values.append((self.tekotype.struct_elems[i].label,self.tekotype.struct_elems[i].default))

    def get_by_index(self, i):
        return self.values[i][1]

    def get_by_label(self, label):
        for l, v in self.values:
            if l == label:
                return v

###

class TekoFunctionType(TekoObject):
    def __init__(self, return_type, arg_struct, **kwargs):
        assert(isTekoType(return_type))
        assert(isinstance(arg_struct, TekoNewStruct))
        super().__init__(TekoType, immutable = True, **kwargs)
        self.return_type = return_type
        self.arg_struct = arg_struct
        self.declare("_args",TekoStructType,self.arg_struct)
        self.declare("_rtype",TekoType,self.return_type)

    def __str__(self):
        return str(self.return_type) + str(self.arg_struct)

class TekoFunction(TekoObject):
    def __init__(self, ftype, codeblock, outer, name="TekoFunction", **kwargs):
        assert(isinstance(ftype, TekoFunctionType))
        assert(isinstance(outer,TekoObject))
        self.outer = outer
        self.outers = [outer]
        super().__init__(tekotype = ftype, name=name, **kwargs)

        assert(codeblock is None or isinstance(codeblock, CodeBlock))
        self.codeblock = codeblock

    def exec(self, args):
        si = TekoStructInstance(self.tekotype.arg_struct, args)
        returnval = self.interpret(si)
        assert(isTekoInstance(returnval, self.tekotype.return_type))
        return returnval

    def __str__(self):
        return "function %s of %s" % (self.name, repr(self.outer))

    def interpret(self, si):
        ti = TekoInterpreter(self.ns)
        for stmt in self.codeblock.statements:
            ti.exec(stmt)
        raise RuntimeError("Returning not yet implemented")
            
TekoVoidType   = TekoObject(TekoType, name="void",   immutable=True)
TekoVoid       = TekoObject(TekoVoidType)
TekoStructType = TekoObject(TekoType, name="struct", immutable=True, parent=TekoType)

###

TekoModuleType = TekoObject(TekoType, name="module", immutable=True)

class TekoModule(TekoObject):
    def __init__(self, name, filename, outers = [], **kwargs):
        super().__init__(TekoModuleType, name=name, **kwargs)
        self.filename = filename
        self.outers = outers

    def interpret(self):
        tp = TekoParser(self.filename)
        stmts = list(tp.parse())
        ti = TekoInterpreter(self)
        for stmt in stmts:
            ti.exec(stmt)

StandardLibrary = TekoModule(name="stdlib", filename = None, immutable=True)

StandardLibrary.declare("type",   TekoType, TekoType)
StandardLibrary.declare("obj",    TekoType, TekoObjectType)
StandardLibrary.declare("module", TekoType, TekoModuleType)
StandardLibrary.declare("void",   TekoType, TekoVoidType)
StandardLibrary.declare("struct", TekoType, TekoStructType)

###

TekoBoolType = TekoObject(TekoType, name="bool", immutable=True)
StandardLibrary.declare("bool", TekoType, TekoBoolType)

class TekoBool(TekoObject):
    def __init__(self, b):
        assert(type(b) == bool)
        super().__init__(TekoBoolType, name = str(b).lower(), immutable=True)
        self._boolval = b
        self.declare(label = "_and", tekotype = TekoBoolBinopType, val = TekoBoolBinop(bool_ns = self.ns, op = "_and", name="_and", outer = self))
        self.declare(label = "_or",  tekotype = TekoBoolBinopType, val = TekoBoolBinop(bool_ns = self.ns, op = "_or",  name="_or", outer = self))

TekoBoolBinopType = TekoFunctionType(TekoBoolType, TekoNewStruct([TekoStructElem(TekoBoolType,"other")]))

class TekoBoolBinop(TekoFunction):
    OP_NAMES = {"_and":"__and__",
                "_or":"__or__"}
    
    def __init__(self, bool_ns, op, **kwargs):
        super().__init__(TekoBoolBinopType, codeblock=None, immutable=True, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftbool = self.outer._boolval
        rightbool = si.get_by_label("other")._boolval
        python_opname = TekoBoolBinop.OP_NAMES[self.op]
        
        return TekoBool(getattr(leftbool,python_opname)(rightbool))

###

TekoStringType = TekoObject(TekoType, name="str", immutable=True)
StandardLibrary.declare("str", TekoType, TekoStringType)

class TekoString(TekoObject):
    def __init__(self, s, **kwargs):
        assert(type(s) == str)
        super().__init__(TekoStringType, name = s, immutable=True, **kwargs)
        self._strval = s
        self.immutable = True
        self.declare(label = "_add", tekotype = TekoStringBinopType, val = TekoStringAdd(outer = self))
        self.declare(label = "_eq",  tekotype = TekoStringEqType,    val = TekoStringEq(outer = self))

    def __str__(self):
        return self._strval

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

TekoStringBinopType = TekoFunctionType(TekoStringType, TekoNewStruct([TekoStructElem(TekoStringType,"other")]))

class TekoStringAdd(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringBinopType, codeblock=None, name="_add", immutable=True, **kwargs)

    def interpret(self, si):
        return TekoString(self.outer._strval + si.get_by_label("other")._strval)
    
TekoStringEqType = TekoFunctionType(TekoBoolType,   TekoNewStruct([TekoStructElem(TekoStringType,"other")]))

class TekoStringEq(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringEqType, codeblock=None, name="_eq", immutable=True, **kwargs)

    def interpret(self, si):
        return TekoBool(self.outer._strval == si.get_by_label("other")._strval)
    
TekoTostrType = TekoFunctionType(TekoStringType, TekoNewStruct([]))

class TekoTostr(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTostrType, codeblock = None, name="_tostr", immutable=True, **kwargs)

    def interpret(self, si):
        return TekoString(str(self.outer))

###

TekoIntType = TekoObject(tekotype = TekoType, name = "int", immutable=True)
StandardLibrary.declare("int", TekoType, TekoIntType)

class TekoInt(TekoObject):    
    def __init__(self, n, **kwargs):
        assert(type(n) == int)
        super().__init__(TekoIntType, name = str(n), immutable=True, **kwargs)
        self._intval = n

        for teko_opname in TekoIntBinop.OP_NAMES:
            self.declare(label = teko_opname, tekotype = TekoIntBinopType, val = TekoIntBinop(outer = self, op = teko_opname, name = teko_opname))
        
        self.declare(label = "_compare", tekotype = TekoIntCompType, val = TekoIntComp(outer = self, name="_compare"))

TekoIntBinopType = TekoFunctionType(return_type = TekoIntType, arg_struct = TekoNewStruct([TekoStructElem(TekoIntType,"other")]))

class TekoIntBinop(TekoFunction):
    OP_NAMES = {"_add":"__add__",
                "_sub":"__sub__",
                "_mul":"__mul__",
                "_div":"__floordiv__",
                "_exp":"__pow__",
                "_mod":"__mod__"}
    
    def __init__(self, op, **kwargs):
        super().__init__(ftype = TekoIntBinopType, codeblock = None, immutable=True, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftint = self.outer._intval
        rightint = si.get_by_label("other")._intval
        python_opname = TekoIntBinop.OP_NAMES[self.op]
        
        return TekoInt(getattr(leftint,python_opname)(rightint))

TekoIntCompType = TekoFunctionType(return_type = TekoIntType, arg_struct = TekoNewStruct([TekoStructElem(TekoIntType,"other")]))

class TekoIntComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoIntCompType, codeblock = None, immutable=True, **kwargs)

    def interpret(self, si):
        leftint = self.outer._intval
        rightint = si.get_by_label("other")._intval

        if leftint == rightint:
            n = 0
        elif leftint < rightint:
            n = -1
        elif leftint > rightint:
            n = 1

        return TekoInt(n)

###

TekoRealType = TekoObject(TekoType, name="real", immutable=True)
StandardLibrary.declare("real", TekoType, TekoRealType)

class TekoReal(TekoObject):    
    def __init__(self, x, **kwargs):
        assert(type(x) == float)
        super().__init__(TekoRealType, name = str(x), immutable=True, **kwargs)
        self._realval = x

        for teko_opname in TekoRealBinop.OP_NAMES:
            self.declare(label = teko_opname, tekotype = TekoRealBinopType, val = TekoRealBinop(outer = self, op = teko_opname, name = teko_opname))
        
        self.declare(label = "_compare", tekotype = TekoRealCompType, val = TekoRealComp(outer = self, name="_compare"))

TekoRealBinopType = TekoFunctionType(return_type = TekoRealType, arg_struct = TekoNewStruct([TekoStructElem(TekoRealType,"other")]))

class TekoRealBinop(TekoFunction):
    OP_NAMES = {"_add":"__add__",
                "_sub":"__sub__",
                "_mul":"__mul__",
                "_div":"__truediv__",
                "_exp":"__pow__"}
    
    def __init__(self, op, **kwargs):
        super().__init__(ftype = TekoRealBinopType, codeblock=None, immutable=True, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftreal = self.outer._realval
        rightreal = si.get_by_label("other")._realval
        python_opname = TekoRealBinop.OP_NAMES[self.op]
        
        return TekoReal(getattr(leftreal,python_opname)(rightreal))

TekoRealCompType = TekoFunctionType(return_type = TekoIntType, arg_struct = TekoNewStruct([TekoStructElem(TekoRealType,"other")]))

class TekoRealComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoRealCompType, codeblock=None, immutable=True, **kwargs)

    def interpret(self, si):
        leftreal = self.outer._realval
        rightreal = si.get_by_label("other")._realval

        if leftreal == rightreal:
            n = 0
        elif leftreal < rightreal:
            n = -1
        elif leftreal > rightreal:
            n = 1

        return TekoInt(n)

###

# These classes are only declared so that interpret can be overridden

TekoPrintType = TekoFunctionType(return_type = TekoVoidType, arg_struct = TekoNewStruct([TekoStructElem(TekoObjectType,"obj", default=TekoString(""))]))

class TekoPrint(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoPrintType, codeblock = None, **kwargs)
        
    def interpret(self, si):
        print(si.get_by_label("obj").get_attr("_tostr").exec([])._strval)
        return TekoVoid
    
TekoPrint = TekoPrint(name = "print", outer = StandardLibrary, immutable=True)
StandardLibrary.declare("print", TekoPrintType, TekoPrint)

TekoTypeofType = TekoFunctionType(return_type = TekoType, arg_struct = TekoNewStruct([TekoStructElem(TekoObjectType,"obj")]))

class TekoTypeof(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTypeofType, codeblock=None, **kwargs)

    def interpret(self,si):
        return si.get_by_label("obj").tekotype
    
TekoTypeof = TekoTypeof(name = "typeof", outer = StandardLibrary, immutable=True)
StandardLibrary.declare("typeof",  TekoTypeofType, TekoTypeof)

TekoAssertType = TekoFunctionType(return_type = TekoVoidType, arg_struct = TekoNewStruct([TekoStructElem(TekoBoolType,"statement")]))

class TekoAssert(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoAssertType, codeblock = None, **kwargs)

    def interpret(self, si):
        b = si.get_by_label("statement")._boolval
        if not b:
            TekoException("Assertion failed", -1)
        return TekoVoid
    
TekoAssert = TekoAssert(name = "assert", outer = StandardLibrary, immutable=True)
StandardLibrary.declare("assert", TekoAssertType, TekoAssert)
