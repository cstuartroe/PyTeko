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
        s = "" if self.mutable else "final "
        s += self.visibility + " " + str(self.tekotype)
        return s

NO_FIELD = 0

class Variable:
    def __init__(self, field = NO_FIELD, val=None):
        assert(field is NO_FIELD or type(field) == Field)
        assert(val is None or isinstance(val, TekoObject))
        self.field = field
        self.val = val

    def set(self, val = None, var = None):
        assert((val is None) != (var is None))
        if var:
            assert(isTekoSubtype(var.get_tekotype(),self.get_tekotype()))
            val = var.val
        else:
            assert(isTekoSubtype(val.tekotype, self.get_tekotype()))
        assert(self.field.mutable or self.val is None)
        self.val = val

    def get_tekotype(self):
        if self.field is not NO_FIELD:
            return self.field.tekotype
        elif self.val:
            return self.val.tekotype
        else:
            return None

    def __str__(self):
        if self.field is NO_FIELD:
            lhs = str(self.val.tekotype)
        else:
            lhs = str(self.field)
        if self.val.tekotype is TekoStringType:
            rhs = repr(self.val)
        else:
            rhs = str(self.val)
        return "<%s :: %s>" % (lhs,rhs)

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
        try:
            assert((label in self.tekotype.get_fields()) or (type(self) is TekoModule))
        except AttributeError:
            assert((type(self) is ControlBlock))
        if (not self.is_free_attr(label)) and not (label == "_tostr" and "_tostr" not in self.vars):
            raise ValueError("Label already assigned: " + label) # should be checked by interpreter
        
        var = Variable(field)        
        self.vars[label] = var

        if val:
            self.set(label, Variable(val = val))

    # methods suffixed with _attr only check own ns
    # methods suffixed with _recursive check outer namespaces as well

    # checks whether a label is available to be declared
    def is_free_attr(self, label):
        if label == "_tostr":
            return False
        else:
            return (label not in self.vars)

    def is_free_recursive(self, label):
        if not self.is_free_attr(label):
            return False
    
        for outer in self.outers:
            if not outer.is_free_recursive(label):
                return False
            
        return True

    def var_attr(self, label, default = THROW_ERROR):
        if label == "_tostr" and "_tostr" not in self.vars:
            self.vars["_tostr"] = Variable(field = Field(tekotype = TekoTostrType, mutable = False, visibility = "public"))
        if label == "_tostr" and self.vars["_tostr"].val is None:
            self.vars["_tostr"].val = TekoTostr(defn_context = self)
        
        if self.is_free_attr(label):
            if default is THROW_ERROR:
                raise AttributeError(str(self) + " has no attribute " + label)
            else:
                return default
        else:
            return self.vars[label]

    def var_recursive(self, label, default = THROW_ERROR):
        if self.is_free_recursive(label):
            if default is THROW_ERROR:
                raise AttributeError(str(self) + " does not have scope over a variable called " + label)
            else:
                return default

        if not self.is_free_attr(label):
            return self.vars[label]
        
        for outer in self.outers:
            if not outer.is_free_recursive(label):
                return outer.var_recursive(label)

    def inited_attr(self, label):
        return self.var_attr(label).val is not None

    def val_attr(self, label, default = THROW_ERROR):
        val = self.var_attr(label).val
        if val is None:
            TekoException("Attribute " + label + " of " + repr(self) + " has not been initialized", -1)
        else:
            return val

    def val_recursive(self, label, default = THROW_ERROR):
        val = self.var_recursive(label).val
        if val is None:
            TekoException("Variable " + label + " has not been initialized", -1)
        else:
            return val

    def field_attr(self, label):
        return self.var_attr(label).field

    def field_recursive(self, label):
        return self.var_recursive(label).field

    def set(self, label, var = None, val = None):
        assert((var is None) != (val is None))
        if var:
            assert(type(var) is Variable)
            assert(var.field is NO_FIELD or isTekoSubtype(var.field.tekotype, self.var_recursive(label).field.tekotype))
            val = var.val

        self.var_recursive(label).set(val=val)
        if val.name is None:
            val.name = label

    def printns(self):
        self.val_attr("_tostr")
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
        leftvar = self.eval_expression(asst_stmt.left)
        if leftvar.field is NO_FIELD:
            TekoException("Invalid LHS: " + str(asst_stmt.left), asst_stmt.line_number)
        
        rightvar = self.eval_expression(asst_stmt.right)
        
        if not (isTekoSubtype(leftvar.field.tekotype, rightvar.get_tekotype())):
            TekoException(str(rightvar) + " is not of type " + str(leftvar.get_tekotype()), asst_stmt.line_number)

        if (leftvar.field.mutable is False):
            TekoException(label + " is not mutable", asst_stmt.line_number)
            
        leftvar.set(rightvar.val)

    def exec_if_stmt(self, if_stmt):
        control_block = ControlBlock(outer = self.owner, codeblock = if_stmt.codeblock)

        if self.eval_expression(if_stmt.condition).val._boolval:
            control_block.interpret()
        elif if_stmt.else_stmt:
            self.exec_if_stmt(if_stmt.else_stmt)

    def exec_while(self, while_block):
        control_block = ControlBlock(outer = self.owner, codeblock = while_block.codeblock)
        
        while self.eval_expression(while_block.condition).val._boolval:
            control_block.interpret()

    def exec_for(self, for_block):
        iterable = self.eval_expression(for_block.iterable).val
        assert(isTekoSubtype(iterable.tekotype.tekotype, TekoIterableTypeType))
        
        tekotype = self.eval_expression(for_block.tekotype).val
        assert(isTekoSubtype(tekotype.tekotype, TekoTypeType))
        assert(isTekoSubtype(iterable.tekotype.val_attr("_etype"), tekotype))
        
        label = for_block.label.vals["label"]

        control_block = ControlBlock(outer = self.owner, codeblock = for_block.codeblock)
        control_block.declare(label = label, field = Field(tekotype = tekotype, mutable = False, visibility = "public"))
        for var in iterable.elems:
            control_block.vars[label].val = var.val
            control_block.interpret()

    def exec_class_decl(self, class_decl):
        raise RuntimeError("Not yet implemented!")

    # # # Executing expressions and declarations:

    def eval_expression(self, expression):
        method_name = TekoInterpreter.EXPR_DISPATCH[type(expression)]
        method = getattr(self, method_name)
        var = method(expression)
        assert(type(var) is Variable)
        return var

    def exec_declaration(self, declaration):            
        label = declaration.label.vals["label"]

        if declaration.expression:
            var = self.eval_expression(declaration.expression)
        else:
            var = Variable()
        
        if declaration.tekotype:
            tekotype = self.eval_expression(declaration.tekotype).val
            
            if declaration.struct:
                tekotype = TekoFunctionType(rtype = tekotype, args = self.eval_expression(declaration.struct).val)
        else:
            assert(var.get_tekotype() is not None)
            tekotype = var.get_tekotype()

        if tekotype is TekoVoidType:
            TekoException("Cannot create variable " + label + " of type void", declaration.line_number)
        
        if (var.get_tekotype() is not None) and (not (isTekoSubtype(var.get_tekotype(), tekotype))):
            TekoException(str(var) + " is not of type " + str(tekotype), declaration.line_number)

        self.owner.declare(label = label, field = Field(tekotype = tekotype, mutable = True, visibility = "public"))
        if var.val:
            self.owner.set(label = label, val = var.val)

    def eval_lhs(self, lhs):
        if type(lhs) is SimpleExpression:
            assert lhs.tag.tagType == "LabelTag"
            entity = self.owner
            label = lhs.tag.vals["label"]
        elif type(lhs) is AttrExpression:
            entity = self.eval_expression(lhs.leftexpr).val
            label = lhs.label.vals["label"]
        else:
            TekoException("Invalid LHS: " + str(lhs), lhs.line_number)

        return entity, label

    # # # Evaluating expression types:

    def eval_simple_expr(self, simple_expr):
        tag = simple_expr.tag
        if tag.tagType == "LabelTag":
            label = tag.vals["label"]
            if self.owner.is_free_recursive(label):
                TekoException(repr(self.owner) + " does not have scope over a variable called " + label, simple_expr.line_number)
            else:
                return self.owner.var_recursive(label)
        elif tag.tagType == "StringTag":
            val = TekoString(tag.vals["string"])
        elif tag.tagType == "IntTag":
            val = TekoInt(tag.vals["int"])
        elif tag.tagType == "RealTag":
            val = TekoReal(tag.vals["real"])
        elif tag.tagType == "BoolTag":
            val = TekoBool(tag.vals["bool"])
        else:
            raise RuntimeError("Unknown tagType: " + tag.tagType)
        return Variable(val = val)

    def eval_seq_expr(self, seq_expr):
        varlist = [self.eval_expression(expr) for expr in seq_expr.exprs]
        etype = varlist[0].get_tekotype() # eventualy change to be recursively inclusive
        assert(all(isTekoSubtype(var.get_tekotype(), etype) for var in varlist))

        if seq_expr.brace == "curly":
            val = TekoList(etype, varlist)
        elif seq_expr.brace == "square":
            val = TekoArray(etype, varlist)
        elif seq_expr.brace == "angle":
            val = TekoSet(etype, varlist)

        return Variable(val = val)

    def eval_call_expr(self, call_expr):
        left = self.eval_expression(call_expr.leftexpr)

        evaluated_args = []
        evaluated_kwargs = {}
        on_kwargs = False
        for argnode in call_expr.args:
            var = self.eval_expression(argnode.expr)
            
            kw = argnode.kw.vals["label"] if argnode.kw else None
            if on_kwargs and kw is None:
                TekoException("Positional argument following keyword argument: " + str(argnode), argnode.line_number)
            on_kwargs = (kw is not None)

            if on_kwargs:
                evaluated_kwargs[kw] = var
            else:
                evaluated_args.append(var)
                
        if isinstance(left.get_tekotype(), TekoFunctionType):
            left.val.calling_interpreter = self
            try:
                return left.val.exec(args = evaluated_args, kw_args = evaluated_kwargs)
            except ValueError as e:
                TekoException(str(e), call_expr.line_number)
        
        elif left.get_tekotype() is TekoStructType:
            try:
                s = TekoStructInstance(new_struct = left.val, args = evaluated_args, kw_args = evaluated_kwargs)
            except ValueError as e:
                TekoException(str(e), call_expr.line_number)
            return Variable(val = s)

    def eval_attr_expr(self, attr_expr):
        var = self.eval_expression(attr_expr.leftexpr)
        label = attr_expr.label.vals["label"]
        
        if label not in var.get_tekotype().get_fields():
            TekoException("%s has no attribute %s" % (str(var),label), attr_expr.line_number)
        else:
            return var.val.var_attr(label)

    def eval_binop_expr(self, binop_expr):
        leftvar  = self.eval_expression(binop_expr.leftexpr)
        rightvar = self.eval_expression(binop_expr.rightexpr)
        if not isTekoSubtype(rightvar.get_tekotype(), leftvar.get_tekotype()):
            TekoException("Incompatible types for binary operation: %s, %s" % (leftvar.get_tekotype(), rightvar.get_tekotype()), binop_expr.line_number)

        binop_funcname = TekoInterpreter.BINOP_DISPATCH[binop_expr.binop]
        if binop_funcname not in leftvar.get_tekotype().get_fields():
            TekoException(str(leftvar) + " has no attribute " + binop_funcname, binop_expr.line_number)
        returnvar = leftvar.val.val_attr(binop_funcname).exec([rightvar])

        assert(returnvar.get_tekotype() == leftvar.get_tekotype())
        return returnvar

    def eval_not_expr(self, not_expr):
        var = self.eval_expression(not_expr.expr)
        if var.get_tekotype() is not TekoBool:
            TekoException("! must be used with boolean",not_expr.line_number)

        return Variable(val = TekoBool(not var.val._boolval))

    def eval_comp_expr(self, comp_expr):
        leftvar = self.eval_expression(comp_expr.leftexpr)
        rightvar = self.eval_expression(comp_expr.rightexpr)
        if not isTekoSubtype(rightvar.get_tekotype(), leftvar.get_tekotype()):
            TekoException("Incompatible types for comparison: %s, %s" % (leftvar.get_tekotype(), rightvar.get_tekotype()), comp_expr.line_number)

        if comp_expr.comp == "<:":
            raise RuntimeError("Not yet implemented!")
        
        else:
            if "_compare" not in leftvar.get_tekotype().get_fields():
                if comp_expr.comp not in ["==","!="]:
                    TekoException(str(leftvar) + " has no attribute _compare", comp_expr.line_number)
                    
                comp_result = leftvar.val.val_attr("_eq").exec([rightvar])
                if comp_expr.comp == "==":
                    returnval = comp_result.val
                else:
                    returnval = TekoBool(not comp_result.val._boolval)
                
            else:
                assert("_eq" not in leftvar.get_tekotype().get_fields())
                comp_result = leftvar.val.val_attr("_compare").exec([rightvar])
                assert(comp_result.get_tekotype() is TekoIntType)
                assert(comp_result.val._intval in [-1, 0, 1])
                b = comp_result.val._intval in TekoInterpreter.COMP_DISPATCH[comp_expr.comp]
                returnval = TekoBool(b)            

        assert(type(returnval) is TekoBool)
        return Variable(val = returnval)
    
    def eval_conv_expr(self, conv_expr):
        var = self.eval_expression(conv_expr.leftexpr)

        if conv_expr.conv == "{}":
            assert(isTekoSubtype(var.get_tekotype(), TekoTypeType))
            returnval = TekoListType(etype = var.val)
        elif conv_expr.conv == "[]":
            assert(isTekoSubtype(var.get_tekotype(), TekoTypeType))
            returnval = TekoArrayType(etype = var.val)
        elif conv_expr.conv == "<>":
            assert(isTekoSubtype(var.get_tekotype(), TekoTypeType))
            returnval = TekoSetType(etype = var.val)            

        else:
            conv_funcname = TekoInterpreter.CONV_DISPATCH[conv_expr.conv]
            if conv_funcname in var.get_tekotype().get_fields():
                returnval = var.val.val_attr(conv_funcname).exec([]).val
            else:
                TekoException(str(var) + " has no attribute " + conv_funcname, conv_expr.line_number)
                
        return Variable(val = returnval)

    def eval_new_struct(self, new_struct):
        struct_elems = []
        for elem_node in new_struct.elems:
            tekotype = self.eval_expression(elem_node.tekotype).val
            if not isTekoSubtype(tekotype.tekotype, TekoTypeType):
                TekoException("Invalid type: " + str(tekotype), elem_node.line_number)
                
            label = elem_node.label.vals["label"]
            if label in TekoStructType.get_fields():
                TekoException(label + " is already an attribute of structs", elem_node.line_number)

            if elem_node.default:
                default = self.eval_expression(elem_node.default).val
                if not isTekoSubtype(default.tekotype, tekotype):
                    TekoException(str(default) + " is not an instance of " + str(tekotype), elem_node.line_number)
            else:
                default = None
                
            struct_elems.append(TekoStructElem(tekotype = tekotype, label = label, default = default))
            
        new_struct = TekoNewStruct(struct_elems)
        return Variable(val = new_struct)

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
        return '<%s :: %s>' % (self.tekotype.val_attr("_tostr").exec([]).val._strval, self.val_attr("_tostr").exec([]).val._strval)

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
            self.set("_parent",val = parent)

    def get_fields(self):
        fields = {}
        for label, field in self.fields.items():
            fields[label] = field
        if self.val_attr("_parent") is not self:
            for label, field in self.val_attr("_parent").get_fields().items():
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
    elif sub.val_attr("_parent") is TekoObjectType:
        return False
    else:
        return isTekoSubtype(sub.val_attr("_parent"), sup)

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

    def __eq__(self, other):
        return (self.tekotype == other.tekotype) and (self.default == other.default)

class TekoNewStruct(TekoType):
    def __init__(self, struct_elems, **kwargs):
        super().__init__(tekotype = TekoStructType, fields = {}, parent = TekoStructType, **kwargs)

        self.struct_elems = []
        for struct_elem in struct_elems:
            assert(type(struct_elem) == TekoStructElem)
            assert(struct_elem.label not in self.tekotype.get_fields())
            self.struct_elems.append(struct_elem)

    def get_by_index(self, i):
        return self.struct_elems[i]

    def get_by_label(self, label):
        for i in range(len(self.struct_elems)):
            if self.struct_elems[i].label == label:
                return i, self.struct_elems[i]

    def __str__(self):
        return "(%s)" % ", ".join([str(e) for e in self.struct_elems])

    def __eq__(self, other):
        if type(other) is not TekoNewStruct:
            return False
        if len(self.struct_elems) != len(other.struct_elems):
            return False
        return all(self.struct_elems[i] == other.struct_elems[i] for i in range(len(self.struct_elems)))

class TekoStructInstance(TekoObject):
    def __init__(self, new_struct, args, kw_args, **kwargs):
        assert(type(new_struct) == TekoNewStruct)
        
        super().__init__(tekotype = new_struct, **kwargs)

        self.svars = [None]*len(self.tekotype.struct_elems)

        for i, var in enumerate(args):
            assert(type(var) is Variable)
            tekotype = self.tekotype.get_by_index(i).tekotype
            if not isTekoSubtype(var.get_tekotype(), tekotype):
                raise ValueError(str(var) + " is not of type " + str(tekotype))
            
            self.svars[i] = Variable(field = Field(tekotype = tekotype, visibility = "public", mutable = True), val = var.val)

        for kw, var in kw_args.items():
            assert(type(var) is Variable)
            i, elem = self.tekotype.get_by_label(kw)
            tekotype = elem.tekotype
            if not isTekoSubtype(var.get_tekotype(), tekotype):
                raise ValueError(str(var) + " is not of type " + str(tekotype))

            if self.svars[i] is not None:
                raise ValueError("keyword argument passed twice: " + kw)
            self.svars[i] = Variable(field = Field(tekotype = tekotype, visibility = "public", mutable = True), val = var.val)

        for i, svar in enumerate(self.svars):
            if svar is None:
                tekotype = self.tekotype.struct_elems[i].tekotype
                val = self.tekotype.struct_elems[i].default
                if val is None:
                    raise ValueError("no value for argument: " + self.tekotype.struct_elems[i].label)
                self.svars[i] = Variable(field = Field(tekotype = tekotype, visibility = "public", mutable = True), val = val)

    def get_by_index(self, i):
        return self.svars[i]

    def get_by_label(self, label):
        for i in range(len(self.tekotype.struct_elems)):
            if self.tekotype.struct_elems[i].label == label:
                return self.svars[i]

    def var_attr(self, label):
        var = self.get_by_label(label)
        if var: return var
        else:
            return super().var_attr(label)

    def __str__(self):
        s = "("
        for i in range(len(self.tekotype.struct_elems)):
            s += str(self.svars[i].get_tekotype()) + " " + self.tekotype.struct_elems[i].label + " = " + str(self.svars[i].val) + ", "
        s += ")"
        s = s.replace(", )",")")
        return s

###

class TekoFunctionType(TekoType):
    def __init__(self, rtype, args, **kwargs):
        assert(isTekoType(rtype))
        assert(isinstance(args, TekoNewStruct))
        
        super().__init__(tekotype = TekoFunctionTypeType, fields = {}, **kwargs)
        
        self.set("_args", val = args)
        self.set("_rtype",val = rtype)

    def __str__(self):
        return str(self.val_attr("_rtype")) + str(self.val_attr("_args"))

    def __eq__(self, other):
        return (self.val_attr("_args") == self.val_attr("_args")) and (self.val_attr("_rtype") == self.val_attr("_rtype"))

class TekoFunction(TekoObject):
    def __init__(self, ftype, codeblock, defn_context, **kwargs):
        assert(isinstance(ftype, TekoFunctionType))
        assert(isinstance(defn_context, TekoObject))
        
        self.defn_context = defn_context
        self.outers = [defn_context]
        
        super().__init__(tekotype = ftype, **kwargs)

        assert(codeblock is None or isinstance(codeblock, CodeBlock))
        self.codeblock = codeblock

    def exec(self, args = [], kw_args = {}): # must be overridden if pass_by_val is False
        si = TekoStructInstance(new_struct = self.tekotype.val_attr("_args"), args = args, kw_args = kw_args)
        returnvar = self.interpret(si)
        assert(isTekoSubtype(returnvar.get_tekotype(), self.tekotype.val_attr("_rtype")))
        return returnvar

    def __str__(self):
        return "function %s of %s" % (self.name, repr(self.defn_context))

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
        self.set(label = "_and", val = TekoBoolBinop(op = "_and", defn_context = self))
        self.set(label = "_or",  val = TekoBoolBinop(op = "_or",  defn_context = self))

    def __str__(self):
        return str(self._boolval).lower()

class TekoBoolBinop(TekoFunction):
    OP_NAMES = {"_and":"__and__",
                "_or":"__or__"}
    
    def __init__(self, op, **kwargs):
        super().__init__(ftype = TekoBoolBinopType, codeblock=None, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftbool = self.defn_context._boolval
        rightbool = si.get_by_label("other").val._boolval
        python_opname = TekoBoolBinop.OP_NAMES[self.op]

        b = TekoBool(getattr(leftbool,python_opname)(rightbool))
        return Variable(field = NO_FIELD, val = b)

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
        self.set("_add", val = TekoStringAdd(defn_context = self))
        self.set("_eq",  val = TekoStringEq(defn_context = self))

    def __str__(self):
        return self._strval

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

class TekoStringAdd(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringBinopType, codeblock=None, **kwargs)

    def interpret(self, si):
        s = TekoString(self.defn_context._strval + si.get_by_label("other").val._strval)
        return Variable(field = NO_FIELD, val = s)

class TekoStringEq(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringEqType, codeblock=None, **kwargs)

    def interpret(self, si):
        b = TekoBool(self.defn_context._strval == si.get_by_label("other").val._strval)
        return Variable(field = NO_FIELD, val = b)
    
TekoTostrType = TekoFunctionType(TekoStringType, TekoNewStruct([]))
TekoObjectType.fields = {"_tostr": Field(TekoTostrType, mutable = False, visibility = "public")}

class TekoTostr(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTostrType, codeblock = None, **kwargs)
        self.name = "_tostr"

    def interpret(self, si):
        s = TekoString(str(self.defn_context))
        return Variable(field = NO_FIELD, val = s)

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
            self.set(label = teko_opname, val = TekoIntBinop(defn_context = self, op = teko_opname))
        
        self.set(label = "_compare", val = TekoIntComp(defn_context = self))

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
        leftint = self.defn_context._intval
        rightint = si.get_by_label("other").val._intval
        python_opname = TekoIntBinop.OP_NAMES[self.op]
        
        n = TekoInt(getattr(leftint,python_opname)(rightint))
        return Variable(field = NO_FIELD, val = n)

class TekoIntComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoIntCompType, codeblock = None, **kwargs)

    def interpret(self, si):
        leftint = self.defn_context._intval
        rightint = si.get_by_label("other").val._intval

        if leftint == rightint:
            n = 0
        elif leftint < rightint:
            n = -1
        elif leftint > rightint:
            n = 1

        n = TekoInt(n)
        return Variable(field = NO_FIELD, val = n)

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
            self.set(label = teko_opname, val = TekoRealBinop(defn_context = self, op = teko_opname))
        
        self.set(label = "_compare", val = TekoRealComp(defn_context = self))

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
        leftreal = self.defn_context._realval
        rightreal = si.get_by_label("other").val._realval
        python_opname = TekoRealBinop.OP_NAMES[self.op]
        
        x = TekoReal(getattr(leftreal,python_opname)(rightreal))
        return Variable(field = NO_FIELD, val = x)

class TekoRealComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoRealCompType, codeblock=None, **kwargs)

    def interpret(self, si):
        leftreal = self.defn_context._realval
        rightreal = si.get_by_label("other").val._realval

        if leftreal == rightreal:
            n = 0
        elif leftreal < rightreal:
            n = -1
        elif leftreal > rightreal:
            n = 1

        n = TekoInt(n)
        return Variable(field = NO_FIELD, val = n)

###

TekoIterableTypeType = TekoType(parent = TekoTypeType, fields = {"_etype":Field(tekotype = TekoTypeType, mutable = False, visibility = "public")})        
StandardLibrary.declare(label = "iterable", field = Field(tekotype = TekoTypeType, mutable = False, visibility = "public"), val = TekoIterableTypeType)

class TekoIterableType(TekoType):
    def __init__(self, etype, fields = {}):
        assert(isTekoType(etype))
        fields["_size"] = Field(tekotype = TekoIntType,  mutable = False, visibility = "public")
        super().__init__(tekotype = TekoIterableTypeType, fields = fields)
        self.set("_etype", val = etype)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.val_attr("_etype") == other.val_attr("_etype")
        else:
            return False

    def __str__(self):
        return str(self.val_attr("_etype")) + self.braces

class TekoIterable(TekoObject):
    def __init__(self, tekotype, etype, l, **kwargs):
        assert(type(l) == list)
        for var in l:
            assert(isTekoSubtype(var.get_tekotype(), etype))
        self.elems = l
        
        super().__init__(tekotype = tekotype(etype = etype), **kwargs)
        self.set("_size",val=TekoInt(len(l)))

    def __str__(self):
        s = self.tekotype.braces[0]
        for e in self.elems:
            s += str(e.val) + ", "
        s += self.tekotype.braces[1]
        s = s.replace(", " + self.tekotype.braces[1],self.tekotype.braces[1])
        return s

###

class TekoListType(TekoIterableType):
    def __init__(self, etype, **kwargs):
        self.braces = "{}"
        fields = {"_head":Field(tekotype = etype,        mutable = False, visibility = "public"),
                  "_tail":Field(tekotype = self,         mutable = False, visibility = "public")}
        super().__init__(etype = etype, fields = fields, **kwargs)

class TekoList(TekoIterable):
    def __init__(self, etype, l, **kwargs):
        super().__init__(tekotype = TekoListType, etype = etype, l = l, **kwargs)
        if l != []:
            self.set("_head", var = l[0])
            tail = TekoList(etype = etype, l = l[1:], **kwargs)
            self.set("_tail", val = tail)

###

class TekoArrayType(TekoIterableType):
    def __init__(self, etype, **kwargs):
        self.braces = "[]"
        super().__init__(etype = etype, **kwargs)

class TekoArray(TekoIterable):
    def __init__(self, etype, l, **kwargs):
        super().__init__(tekotype = TekoArrayType, etype = etype, l = l, **kwargs)

###

class TekoSetType(TekoIterableType):
    def __init__(self, etype, **kwargs):
        self.braces = "<>"
        super().__init__(etype = etype, **kwargs)

class TekoSet(TekoIterable):
    def __init__(self, etype, l, **kwargs):
        super().__init__(tekotype = TekoSetType, etype = etype, l = l, **kwargs)
        self.elems = set(self.elems)

###

# These classes are only declared so that interpret can be overridden

TekoPrintType = TekoFunctionType(rtype = TekoVoidType, args = TekoNewStruct([TekoStructElem(TekoObjectType,"obj", default=TekoString("\n"))]))

class TekoPrint(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoPrintType, codeblock = None, **kwargs)
        
    def interpret(self, si):
        print(si.get_by_label("obj").val.val_attr("_tostr").exec([]).val._strval, end='')
        return Variable(field = NO_FIELD, val = TekoVoid)
    
TekoPrint = TekoPrint(defn_context = StandardLibrary)
StandardLibrary.declare(label = "print", field = Field(tekotype = TekoPrintType, mutable = False, visibility = "public"), val = TekoPrint)

TekoTypeofType = TekoFunctionType(rtype = TekoTypeType, args = TekoNewStruct([TekoStructElem(TekoObjectType,"obj")]))

class TekoTypeof(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTypeofType, codeblock=None, **kwargs)

    def exec(self, args, kw_args = {}):
        t = args[0].get_tekotype()
        return Variable(val = t)
    
TekoTypeof = TekoTypeof(defn_context = StandardLibrary)
StandardLibrary.declare(label = "typeof", field = Field(tekotype = TekoTypeofType, mutable = False, visibility = "public"), val = TekoTypeof)

TekoAssertType = TekoFunctionType(rtype = TekoVoidType, args = TekoNewStruct([TekoStructElem(TekoBoolType,"statement")]))

class TekoAssert(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoAssertType, codeblock = None, **kwargs)

    def interpret(self, si):
        b = si.get_by_label("statement").val._boolval
        if not b:
            TekoException("Assertion failed", -1)
        return Variable(field = NO_FIELD, val = TekoVoid)
    
TekoAssert = TekoAssert(defn_context = StandardLibrary)
StandardLibrary.declare(label = "assert", field = Field(tekotype = TekoAssertType, mutable = False, visibility = "public"), val = TekoAssert)

TekoInputType = TekoFunctionType(rtype = TekoStringType, args = TekoNewStruct([]))

class TekoInput(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoInputType, codeblock = None, **kwargs)

    def interpret(self, si):
        s = input()
        return Variable(field = NO_FIELD, val = TekoString(s))

TekoInput = TekoInput(defn_context = StandardLibrary)
StandardLibrary.declare(label = "input", field = Field(tekotype = TekoInputType, mutable = False, visibility = "public"), val = TekoInput)
