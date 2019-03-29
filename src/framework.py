from .parser import TekoParser
from .parsenode import *
from .general import *

VISIBILITIES = {"public","protected","private"}

class Field:
    def __init__(self, tekotype, visibility, mutable):
        assert(isTekoType(tekotype))
        assert(tekotype is not TekoVoidType)
        assert(visibility in VISIBILITIES)
        self.tekotype = tekotype
        self.visibility = visibility
        self.mutable = mutable

    def __str__(self):
        s = "final " if self.mutable else ""
        s += self.visibility + " " + str(self.tekotype)
        return s

class Variable:
    def __init__(self, field, val=None):
        assert(type(field) == Field)
        self.field = field
        self.val = val

    def set(self, val):
        assert(isTekoInstance(val, self.field.tekotype))
        assert(self.field.mutable or self.val is None)
        self.val = val

    def __str__(self):
        return "<%s :: %s>" % (str(self.field),str(self.val))

    def __repr__(self):
        return str(self)

###

THROW_ERROR = 0

class Namespace:
    def __init__(self, outers = []):
        self.vars = {}
        if outers != []:
            assert(type(self) is TekoModule or isinstance(self, TekoFunction) or type(self) is ControlBlock)
        self.outers = outers

    def declare(self, label, field, val = None):
        assert(type(label) == str)
        if (not self.is_free_attr(label)) and not (label == "_tostr" and "_tostr" not in self.vars):
            raise ValueError("Label already assigned: " + label) # should be checked by interpreter
        
        var = Variable(field)        
        self.vars[label] = var

        if val:
            self.set(label, val)

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
    
        for outer in self.outers:
            if not outer.is_free_var(label):
                return False
            
        return True

    def fetch_attr(self, label):
        if label == "_tostr" and "_tostr" not in self.vars:
            self.vars["_tostr"] = Variable(field = Field(tekotype = TekoTostrType, mutable = False, visibility = "public"))
        if label == "_tostr" and self.vars["_tostr"].val is None:
            self.vars["_tostr"].val = TekoTostr(outer = self)
        
        return self.vars.get(label,None)

    def fetch_var(self, label):
        if self.fetch_attr(label):
            return self.fetch_attr(label)
        
        for outer in self.outers:
            if outer.fetch_var(label):
                return outer.fetch_var(label)

        return None

    def inited_attr(self, label):
        return self.fetch_attr(label).val is not None

    def get_attr(self, label, default = THROW_ERROR):
        if self.is_free_attr(label):
            if default is THROW_ERROR:
                raise AttributeError(str(self) + " has no attribute " + label)
            else:
                return default
        else:
            val = self.fetch_attr(label).val
            if val is None:
                TekoException("Attribute " + label + " of " + repr(self) + " has not been initialized", -1)
            else:
                return val

    def get_var(self, label, default = THROW_ERROR):
        if self.is_free_var(label):
            if default is THROW_ERROR:
                raise AttributeError(str(self) + " does not have scope over a variable called " + label)
            else:
                return default
        else:
            val = self.fetch_var(label).val
            if val is None:
                TekoException("Variable " + label + " has not been initialized", -1)
            else:
                return val

    def field_attr(self, label):
        return self.fetch_attr(label).field

    def field_var(self, label):
        return self.fetch_var(label).field

    def set(self, label, val):
        self.fetch_var(label).set(val)
        if val.name is None:
            val.name = label

    def printns(self):
        self.get_attr("_tostr")
        s = "Teko Namespace:\n---\n"
        m = max([len(label) for label in self.vars.keys()])
        for label, var in self.vars.items():
            s += label.ljust(m," ") + ": " + str(var) + "\n"
        print(s)

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

    CONV_DISPATCH = {"$":"_tostr",
                     ".":"_toreal"}
    
    def __init__(self, owner):
        assert(type(owner) is TekoModule or isinstance(owner, TekoFunction) or type(owner) is ControlBlock)
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
        if entity.is_free_var(label):
            TekoException(repr(entity) + " does not have scope over a variable called " + label, asst_stmt.line_number)
        
        val = self.eval_expression(asst_stmt.right)
        
        if not (isTekoInstance(val, entity.field_var(label).tekotype)):
            TekoException(str(val) + " is not of type " + str(entity.field_var(label).tekotype), asst_stmt.line_number)

        if (entity.field_var(label).mutable is False):
            TekoException(label + " is not mutable", asst_stmt.line_number)
            
        entity.set(label, val)

    def exec_if_stmt(self, if_stmt):
        control_block = ControlBlock(outer = self.owner, codeblock = if_stmt.codeblock)

        if self.eval_expression(if_stmt.condition)._boolval:
            control_block.interpret()
        elif if_stmt.else_stmt:
            self.exec_if_stmt(if_stmt.else_stmt)

    def exec_while(self, while_block):
        control_block = ControlBlock(outer = self.owner, codeblock = while_block.codeblock)
        
        while self.eval_expression(while_block.condition)._boolval:
            control_block.interpret()

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
        label = declaration.label.vals["label"]

        if declaration.expression:
            val = self.eval_expression(declaration.expression)
        else:
            val = None
        
        if declaration.tekotype:
            tekotype = self.eval_expression(declaration.tekotype)
            
            if declaration.struct:
                tekotype = TekoFunctionType(rtype = tekotype, args = self.eval_new_struct(declaration.struct))
        else:
            assert(val is not None)
            tekotype = val.tekotype

        if tekotype is TekoVoidType:
            TekoException("Cannot create variable " + label + " of type void", declaration.line_number)
        
        if (val is not None) and (not (isTekoInstance(val, tekotype))):
            TekoException(str(val) + " is not of type " + str(tekotype), declaration.line_number)

        self.owner.declare(label = label, field = Field(tekotype = tekotype, mutable = True, visibility = "public"), val = val)

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
            label = tag.vals["label"]
            if self.owner.is_free_var(label):
                TekoException(repr(self.owner) + " does not have scope over a variable called " + label, simple_expr.line_number)
            else:
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
        vals = [self.eval_expression(expr) for expr in seq_expr.exprs]
        etype = vals[0].tekotype
        assert(all(isTekoInstance(val, etype) for val in vals))

        if seq_expr.brace == "curly":
            return TekoList(etype, vals)
        elif seq_expr.brace == "square":
            return TekoArray(etype, vals)
        elif seq_expr.brace == "angle":
            return TekoSet(etype, vals)

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
            if leftval.is_free_attr("_compare"):
                if comp_expr.comp not in ["==","!="]:
                    TekoException(str(leftval) + " has no attribute _compare", comp_expr.line_number)
                    
                comp_result = leftval.get_attr("_eq").exec([rightval])
                if comp_expr.comp == "==":
                    returnval = comp_result
                else:
                    returnval = TekoBool(not comp_result._boolval)
                
            else:
                assert(leftval.is_free_attr("_eq"))
                comp_result = leftval.get_attr("_compare").exec([rightval])
                assert(type(comp_result) is TekoInt)
                assert(comp_result._intval in [-1, 0, 1])
                b = comp_result._intval in TekoInterpreter.COMP_DISPATCH[comp_expr.comp]
                returnval = TekoBool(b)            

        assert(type(returnval) is TekoBool)
        return returnval
    
    def eval_conv_expr(self, conv_expr):
        val = self.eval_expression(conv_expr.leftexpr)

        if conv_expr.conv == "{}":
            assert(isTekoType(val))
            return TekoListType(etype = val)
        elif conv_expr.conv == "[]":
            assert(isTekoType(val))
            return TekoArrayType(etype = val)
        elif conv_expr.conv == "<>":
            assert(isTekoType(val))
            return TekoSetType(etype = val)            

        else:
            conv_funcname = TekoInterpreter.CONV_DISPATCH[conv_expr.conv]
            try:
                return TekoString(val.get_attr(conv_funcname).exec([])._strval)
            except AttributeError:
                TekoException(str(val) + " has no attribute " + conv_funcname, conv_expr.line_number)

    def eval_new_struct(self, new_struct):
        raise RuntimeError("Not yet implemented!")

###

class ControlBlock(Namespace):
    def __init__(self, outer, codeblock):
        assert(type(outer) is TekoModule or isinstance(outer, TekoFunction) or type(outer) is ControlBlock)
        assert(type(codeblock) is CodeBlock)
        self.codeblock = codeblock
        self.immutable = False
        super().__init__(outers = [outer])

    def interpret(self):
        ti = TekoInterpreter(self)
        for stmt in self.codeblock.statements:
            ti.exec(stmt)

    def __str__(self):
        return "ControlBlock"

###

class TekoObject(Namespace):
    def __init__(self, tekotype, outers=[], name = None):
        assert(tekotype is None or isTekoType(tekotype)) # tekotype is only None for TekoTypeType
        assert(name is None or type(name) == str)
        self.tekotype = tekotype
        super().__init__(outers)

        self.name = name

        if tekotype is not None:
            for label, field in tekotype.get_fields().items():
                self.declare(label = label, field = field)

    def declare(self, **kwargs):
        super().declare(**kwargs)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s :: %s>' % (self.tekotype.get_attr("_tostr").exec([])._strval, self.get_attr("_tostr").exec([])._strval)

class TekoType(TekoObject):
    def __init__(self, fields, tekotype = None, parent = None, bootstrapping = False, **kwargs):
        assert(type(fields) is dict)
        assert(all(type(label) is str and type(field) is Field for label, field in fields.items()))
        
        if bootstrapping is False:
            tekotype = tekotype or TekoTypeType
            parent = parent or TekoObjectType
        
        super().__init__(tekotype = tekotype, **kwargs)
        self.fields = fields

        if parent:
            self.set("_parent",parent)

    def get_fields(self):
        fields = {}
        for label, field in self.fields.items():
            fields[label] = field
        if self.get_attr("_parent") is not self:
            for label, field in self.get_attr("_parent").get_fields().items():
                assert(label not in fields)
                fields[label] = field
        return fields

    def __eq__(self, other):
        return self is other

def isTekoType(tekoObj):
    return isinstance(tekoObj, TekoType)

def isTekoSubtype(sub,sup):
    if not isTekoType(sub) or not isTekoType(sup):
        raise ValueError("Not both types: " + str(tt1) + ", " + str(tt2))

    if sup is TekoObjectType:
        return True
    elif sub == sup:
        return True
    elif sub.get_attr("_parent") is TekoObjectType:
        return False
    else:
        return isTekoSubtype(sub.get_attr("_parent"), sup)

def isTekoInstance(tekoObj, tekotype):
    assert(isTekoType(tekotype))
    return isTekoSubtype(tekoObj.tekotype,tekotype)

TekoTypeType   = TekoType(fields = {}, bootstrapping = True, name="type")
TekoObjectType = TekoType(fields = {}, bootstrapping = True, name="obj")
TekoVoidType   = TekoType(fields = {}, bootstrapping = True, name="void")

TekoTypeType.tekotype   = TekoTypeType
TekoObjectType.tekotype = TekoTypeType
TekoVoidType.tekotype   = TekoTypeType

TekoTypeType.vars["_parent"]   = Variable(field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoObjectType)
TekoObjectType.vars["_parent"] = Variable(field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoObjectType)
TekoVoidType.vars["_parent"]   = Variable(field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoObjectType)

TekoTypeType.fields = {"_parent": Field(tekotype = TekoTypeType, mutable = False, visibility = "public")}

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

class TekoNewStruct(TekoType):
    def __init__(self, struct_elems, **kwargs):
        super().__init__(tekotype = TekoStructType, fields = {}, parent = TekoStructType, **kwargs)

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

class TekoFunctionType(TekoType):
    def __init__(self, rtype, args, **kwargs):
        assert(isTekoType(rtype))
        assert(isinstance(args, TekoNewStruct))
        
        super().__init__(tekotype = TekoFunctionTypeType, fields = {}, **kwargs)
        
        self.set("_args", args)
        self.set("_rtype",rtype)

    def __str__(self):
        return str(self.get_attr("_rtype")) + str(self.get_attr("_args"))

class TekoFunction(TekoObject):
    def __init__(self, ftype, codeblock, outer, **kwargs):
        assert(isinstance(ftype, TekoFunctionType))
        assert(isinstance(outer, TekoObject))
        
        self.outer = outer
        self.outers = [outer]
        
        super().__init__(tekotype = ftype, **kwargs)

        assert(codeblock is None or isinstance(codeblock, CodeBlock))
        self.codeblock = codeblock

    def exec(self, args):
        si = TekoStructInstance(self.tekotype.get_attr("_args"), args)
        returnval = self.interpret(si)
        assert(isTekoInstance(returnval, self.tekotype.get_attr("_rtype")))
        return returnval

    def __str__(self):
        return "function %s of %s" % (self.name, repr(self.outer))

    def interpret(self, si):
        ti = TekoInterpreter(self)
        for stmt in self.codeblock.statements:
            ti.exec(stmt)
        raise RuntimeError("Returning not yet implemented")

TekoVoid             = TekoObject(tekotype = TekoVoidType)
TekoStructType       = TekoType(parent = TekoTypeType, fields = {}, name="struct")
TekoFunctionTypeType = TekoType(parent = TekoTypeType,
                                fields = {"_args": Field(tekotype = TekoStructType, visibility = "public", mutable = False),
                                          "_rtype":Field(tekotype = TekoTypeType,   visibility = "public", mutable = False)})

###

TekoModuleType = TekoType(fields = {})

class TekoModule(TekoObject):
    def __init__(self, name, filename = None, outers = [], only_stdlib = False, **kwargs):
        super().__init__(tekotype = TekoModuleType, name=name, **kwargs)
        self.filename = filename
        self.outers = outers

        if not only_stdlib:
            assert(type(filename) is str)
            self.outers = [StandardLibrary] + self.outers

    def interpret(self):
        tp = TekoParser(self.filename)
        stmts = list(tp.parse())
        ti = TekoInterpreter(self)
        for stmt in stmts:
            ti.exec(stmt)

StandardLibrary = TekoModule(name="stdlib", only_stdlib = True)

StandardLibrary.declare(label = "type",   field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoTypeType)
StandardLibrary.declare(label = "obj",    field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoObjectType)
StandardLibrary.declare(label = "module", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoModuleType)
StandardLibrary.declare(label = "void",   field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoVoidType)
StandardLibrary.declare(label = "struct", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoStructType)

###

TekoBoolType = TekoType(fields = {}, name="bool")
TekoBoolBinopType = TekoFunctionType(TekoBoolType, TekoNewStruct([TekoStructElem(TekoBoolType,"other")]))

TekoBoolType.fields = {"_and":Field(tekotype = TekoBoolBinopType, mutable = False, visibility = "public"),
                       "_or": Field(tekotype = TekoBoolBinopType, mutable = False, visibility = "public")}
StandardLibrary.declare(label = "bool", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoBoolType)

class TekoBool(TekoObject):
    def __init__(self, b):
        assert(type(b) == bool)
        self._boolval = b
        super().__init__(tekotype = TekoBoolType)
        self.set(label = "_and", val = TekoBoolBinop(op = "_and", outer = self))
        self.set(label = "_or",  val = TekoBoolBinop(op = "_or",  outer = self))

    def __str__(self):
        return str(self._boolval).lower()

class TekoBoolBinop(TekoFunction):
    OP_NAMES = {"_and":"__and__",
                "_or":"__or__"}
    
    def __init__(self, op, **kwargs):
        super().__init__(ftype = TekoBoolBinopType, codeblock=None, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftbool = self.outer._boolval
        rightbool = si.get_by_label("other")._boolval
        python_opname = TekoBoolBinop.OP_NAMES[self.op]
        
        return TekoBool(getattr(leftbool,python_opname)(rightbool))

###

TekoStringType = TekoType(fields = {}, name="str")
TekoStringBinopType = TekoFunctionType(TekoStringType, TekoNewStruct([TekoStructElem(TekoStringType,"other")]))
TekoStringEqType    = TekoFunctionType(TekoBoolType,   TekoNewStruct([TekoStructElem(TekoStringType,"other")]))

TekoStringType.fields = {"_add":Field(TekoStringBinopType, mutable = False, visibility = "public"),
                         "_eq": Field(TekoStringEqType,    mutable = False, visibility = "public")}                  
StandardLibrary.declare(label = "str", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoStringType)

class TekoString(TekoObject):
    def __init__(self, s, **kwargs):
        assert(type(s) == str)
        self._strval = s
        super().__init__(tekotype = TekoStringType, **kwargs)
        self.set("_add", TekoStringAdd(outer = self))
        self.set("_eq",  TekoStringEq(outer = self))

    def __str__(self):
        return self._strval

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

class TekoStringAdd(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringBinopType, codeblock=None, **kwargs)

    def interpret(self, si):
        return TekoString(self.outer._strval + si.get_by_label("other")._strval)

class TekoStringEq(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringEqType, codeblock=None, **kwargs)

    def interpret(self, si):
        return TekoBool(self.outer._strval == si.get_by_label("other")._strval)
    
TekoTostrType = TekoFunctionType(TekoStringType, TekoNewStruct([]))
TekoObjectType.fields = {"_tostr": Field(TekoTostrType, mutable = False, visibility = "public")}

class TekoTostr(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTostrType, codeblock = None, **kwargs)
        self.name = "_tostr"

    def interpret(self, si):
        return TekoString(str(self.outer))

###

TekoIntType = TekoType(fields = {}, name="int")
TekoIntBinopType = TekoFunctionType(rtype = TekoIntType, args = TekoNewStruct([TekoStructElem(TekoIntType,"other")]))
TekoIntCompType  = TekoFunctionType(rtype = TekoIntType, args = TekoNewStruct([TekoStructElem(TekoIntType,"other")]))

TekoIntType.fields = {"_add":    Field(tekotype = TekoIntBinopType, mutable = False, visibility = "public"),
                      "_sub":    Field(tekotype = TekoIntBinopType, mutable = False, visibility = "public"),
                      "_mul":    Field(tekotype = TekoIntBinopType, mutable = False, visibility = "public"),
                      "_div":    Field(tekotype = TekoIntBinopType, mutable = False, visibility = "public"),
                      "_exp":    Field(tekotype = TekoIntBinopType, mutable = False, visibility = "public"),
                      "_mod":    Field(tekotype = TekoIntBinopType, mutable = False, visibility = "public"),
                      "_compare":Field(tekotype = TekoIntCompType,  mutable = False, visibility = "public")}
StandardLibrary.declare(label = "int", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoIntType)

class TekoInt(TekoObject):    
    def __init__(self, n, **kwargs):
        assert(type(n) == int)
        self._intval = n
        super().__init__(tekotype = TekoIntType, **kwargs)

        for teko_opname in TekoIntBinop.OP_NAMES:
            self.set(label = teko_opname, val = TekoIntBinop(outer = self, op = teko_opname))
        
        self.set(label = "_compare", val = TekoIntComp(outer = self))

    def __str__(self):
        return str(self._intval)

class TekoIntBinop(TekoFunction):
    OP_NAMES = {"_add":"__add__",
                "_sub":"__sub__",
                "_mul":"__mul__",
                "_div":"__floordiv__",
                "_exp":"__pow__",
                "_mod":"__mod__"}
    
    def __init__(self, op, **kwargs):
        super().__init__(ftype = TekoIntBinopType, codeblock = None, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftint = self.outer._intval
        rightint = si.get_by_label("other")._intval
        python_opname = TekoIntBinop.OP_NAMES[self.op]
        
        return TekoInt(getattr(leftint,python_opname)(rightint))

class TekoIntComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoIntCompType, codeblock = None, **kwargs)

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

TekoRealType = TekoType(fields = {}, name="real")
TekoRealBinopType = TekoFunctionType(rtype = TekoRealType, args = TekoNewStruct([TekoStructElem(TekoRealType,"other")]))
TekoRealCompType  = TekoFunctionType(rtype = TekoIntType,  args = TekoNewStruct([TekoStructElem(TekoRealType,"other")]))

TekoRealType.fields = {"_add":    Field(tekotype = TekoRealBinopType, mutable = False, visibility = "public"),
                       "_sub":    Field(tekotype = TekoRealBinopType, mutable = False, visibility = "public"),
                       "_mul":    Field(tekotype = TekoRealBinopType, mutable = False, visibility = "public"),
                       "_div":    Field(tekotype = TekoRealBinopType, mutable = False, visibility = "public"),
                       "_exp":    Field(tekotype = TekoRealBinopType, mutable = False, visibility = "public"),
                       "_compare":Field(tekotype = TekoRealCompType,  mutable = False, visibility = "public")}
StandardLibrary.declare(label = "real", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoRealType)

class TekoReal(TekoObject):    
    def __init__(self, x, **kwargs):
        assert(type(x) == float)
        self._realval = x
        super().__init__(TekoRealType, name = str(x), **kwargs)

        for teko_opname in TekoRealBinop.OP_NAMES:
            self.set(label = teko_opname, val = TekoRealBinop(outer = self, op = teko_opname))
        
        self.set(label = "_compare", val = TekoRealComp(outer = self))

    def __str__(self):
        return str(self._realval)

class TekoRealBinop(TekoFunction):
    OP_NAMES = {"_add":"__add__",
                "_sub":"__sub__",
                "_mul":"__mul__",
                "_div":"__truediv__",
                "_exp":"__pow__"}
    
    def __init__(self, op, **kwargs):
        super().__init__(ftype = TekoRealBinopType, codeblock=None, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftreal = self.outer._realval
        rightreal = si.get_by_label("other")._realval
        python_opname = TekoRealBinop.OP_NAMES[self.op]
        
        return TekoReal(getattr(leftreal,python_opname)(rightreal))

class TekoRealComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoRealCompType, codeblock=None, **kwargs)

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

TekoIterableType = TekoType(parent = TekoTypeType, fields = {"_etype":Field(tekotype = TekoTypeType, mutable = False, visibility = "public")})
StandardLibrary.declare(label = "iterable", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoIterableType)

class TekoListType(TekoType):
    def __init__(self, etype, **kwargs):
        assert(isTekoType(etype))
        
        fields = {"_head":Field(tekotype = etype, mutable = True, visibility = "public"),
                  "_tail":Field(tekotype = self,  mutable = True, visibility = "public")}
                  
        super().__init__(tekotype = TekoIterableType, fields = fields, **kwargs)
        self.set("_etype",etype)

    def __eq__(self, other):
        if type(other) is TekoListType:
            return self.get_attr("_etype") == other.get_attr("_etype")
        else:
            return False

    def __str__(self):
        return str(self.get_attr("_etype")) + "{}"

class TekoList(TekoObject):
    def __init__(self, etype, l, **kwargs):
        assert(type(l) == list)
        super().__init__(tekotype = TekoListType(etype = etype), **kwargs)
        
        if l != []:
            assert(isTekoInstance(l[0], etype))
            self.set("_head",l[0])
            tail = TekoList(etype = etype, l = l[1:], **kwargs)
            self.set("_tail",tail)

    def __str__(self):
        if self.inited_attr("_head"):
            s = "{" + str(self.get_attr("_head")) + ", " + str(self.get_attr("_tail"))[1:]
            s = s.replace(", }","}")
        else:
            s = "{}"
        return s

###

class TekoArrayType(TekoType):
    def __init__(self, etype, **kwargs):
        assert(isTekoType(etype))

        fields = {"_len":Field(tekotype = TekoIntType, mutable = False, visibility = "public")}

        super().__init__(tekotype = TekoIterableType, fields = fields, **kwargs)
        self.set("_etype",etype)

    def __eq__(self, other):
        if type(other) is TekoArrayType:
            return self.get_attr("_etype") == other.get_attr("_etype")
        else:
            return False

    def __str__(self):
        return str(self.get_attr("_etype")) + "[]"

class TekoArray(TekoObject):
    def __init__(self, etype, l, **kwargs):
        assert(type(l) == list)
        super().__init__(tekotype = TekoArrayType(etype = etype), **kwargs)

        self.set("_len", TekoInt(len(l)))
        self.elems = l

    def __str__(self):
        s = "["
        for e in self.elems:
            s += str(e) + ", "
        s += "]"
        s = s.replace(", ]","]")
        return s

###

class TekoSetType(TekoType):
    def __init__(self, etype, **kwargs):
        assert(isTekoType(etype))

        fields = {"_size":Field(tekotype = TekoIntType, mutable = False, visibility = "public")}

        super().__init__(tekotype = TekoIterableType, fields = fields, **kwargs)
        self.set("_etype",etype)

    def __eq__(self, other):
        if type(other) is TekoSetType:
            return self.get_attr("_etype") == other.get_attr("_etype")
        else:
            return False

    def __str__(self, other):
        return str(self.get_attr("_etype")) + "<>"

class TekoSet(TekoObject):
    def __init__(self, etype, l, **kwargs):
        assert(type(l) == list)
        super().__init__(tekotype = TekoSetType(etype = etype), **kwargs)

        self.set("_size", TekoInt(len(l)))
        self.elems = set(l)

    def __str__(self):
        s = "<"
        for e in self.elems:
            s += str(e) + ", "
        s += ">"
        s = s.replace(", >",">")
        return s

###

# These classes are only declared so that interpret can be overridden

TekoPrintType = TekoFunctionType(rtype = TekoVoidType, args = TekoNewStruct([TekoStructElem(TekoObjectType,"obj", default=TekoString("\n"))]))

class TekoPrint(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoPrintType, codeblock = None, **kwargs)
        
    def interpret(self, si):
        print(si.get_by_label("obj").get_attr("_tostr").exec([])._strval, end='')
        return TekoVoid
    
TekoPrint = TekoPrint(outer = StandardLibrary)
StandardLibrary.declare(label = "print", field = Field(tekotype = TekoPrintType, mutable = False, visibility = "public"), val = TekoPrint)

TekoTypeofType = TekoFunctionType(rtype = TekoTypeType, args = TekoNewStruct([TekoStructElem(TekoObjectType,"obj")]))

class TekoTypeof(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTypeofType, codeblock=None, **kwargs)

    def interpret(self,si):
        return si.get_by_label("obj").tekotype
    
TekoTypeof = TekoTypeof(outer = StandardLibrary)
StandardLibrary.declare(label = "typeof", field = Field(tekotype = TekoTypeofType, mutable = False, visibility = "public"), val = TekoTypeof)

TekoAssertType = TekoFunctionType(rtype = TekoVoidType, args = TekoNewStruct([TekoStructElem(TekoBoolType,"statement")]))

class TekoAssert(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoAssertType, codeblock = None, **kwargs)

    def interpret(self, si):
        b = si.get_by_label("statement")._boolval
        if not b:
            TekoException("Assertion failed", -1)
        return TekoVoid
    
TekoAssert = TekoAssert(outer = StandardLibrary)
StandardLibrary.declare(label = "assert", field = Field(tekotype = TekoAssertType, mutable = False, visibility = "public"), val = TekoAssert)

TekoInputType = TekoFunctionType(rtype = TekoStringType, args = TekoNewStruct([]))

class TekoInput(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoInputType, codeblock = None, **kwargs)

    def interpret(self, si):
        s = input()
        return TekoString(s)

TekoInput = TekoInput(outer = StandardLibrary)
StandardLibrary.declare(label = "input", field = Field(tekotype = TekoInputType, mutable = False, visibility = "public"), val = TekoInput)
