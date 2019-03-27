from .parsenode import *
from .general import *

class Variable:
    def __init__(self, tekotype, val=None):
        assert(isTekoType(tekotype))
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

    def outer_ns(self):
        if self.owner.owner:
            return self.owner.owner.ns
        else:
            return None

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
        return (label not in self.vars)

    def is_free_var(self, label):
        if self.is_free_attr(label):
            if self.outer_ns():
                return self.outer_ns().is_free_var(label)
            else:
                return True
        else:
            return False

    def fetch_attr(self, label):
        return self.vars.get(label,None)

    def fetch_var(self, label):
        if self.fetch_attr(label):
            return self.fetch_attr(label)
        elif self.outer_ns():
            return self.outer_ns().fetch_var(label)
        else:
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

THROW_ERROR = 0

class TekoObject:
    def __init__(self, tekotype, owner=None, name="TekoObject", parent=None, bootstrapping=False):
        assert(tekotype is None or isTekoType(tekotype))
        assert(type(name) == str)
        self.tekotype = tekotype
        self.name = name
        
        self.ns = Namespace(self)
        if not bootstrapping:
            if isinstance(self, TekoFunction):
                assert(isinstance(owner, TekoObject))
            #else:
            #    assert(owner is None)
            self.declare("_tostr",TekoTostrType,TekoTostr(owner = self))
            
        self.owner = owner
                   
        if parent is not None:
            self.set_parent(parent)

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
        super().__init__(TekoStructType, **kwargs)

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
        super().__init__(TekoType, **kwargs)
        self.return_type = return_type
        self.arg_struct = arg_struct
        self.declare("_args",TekoStructType,self.arg_struct)
        self.declare("_rtype",TekoType,self.return_type)

    def __str__(self):
        return str(self.return_type) + str(self.arg_struct)

class TekoFunction(TekoObject):
    def __init__(self, ftype, codeblock, name="TekoFunction", **kwargs):
        assert(isinstance(ftype, TekoFunctionType))
        super().__init__(tekotype = ftype, name=name, **kwargs)

        assert(codeblock is None or isinstance(codeblock, CodeBlock))
        self.codeblock = codeblock

    def exec(self, args):
        si = TekoStructInstance(self.tekotype.arg_struct, args)
        returnval = self.interpret(si)
        assert(isTekoInstance(returnval, self.tekotype.return_type))
        return returnval

    def __str__(self):
        return "function %s of %s" % (self.name, repr(self.owner))

    def interpret(self, si):
        ti = TekoInterpreter(self.ns)
        for stmt in self.codeblock.statements:
            ti.exec(stmt)
        raise RuntimeError("Returning not yet implemented")

###

class TekoString(TekoObject):
    def __init__(self, s, **kwargs):
        assert(type(s) == str)
        super().__init__(TekoStringType, name = s, **kwargs)
        self._strval = s
        self.declare(label = "_add", tekotype = TekoStringBinopType, val = TekoStringAdd(owner = self))
        self.declare(label = "_eq",  tekotype = TekoStringEqType,    val = TekoStringEq(owner = self))

    def __str__(self):
        return self._strval

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

class TekoStringAdd(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringBinopType, codeblock=None, name="_add", **kwargs)

    def interpret(self, si):
        return TekoString(self.owner._strval + si.get_by_label("other")._strval)

class TekoStringEq(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoStringEqType, codeblock=None, name="_eq", **kwargs)

    def interpret(self, si):
        return TekoBool(self.owner._strval == si.get_by_label("other")._strval)

class TekoTostr(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTostrType, codeblock = None, name="_tostr", bootstrapping=True, **kwargs)

    def get_attr(self, label):
        if label=="_tostr":
            return TekoTostr(owner = self)
        else:
            return super().get_attr(label)

    def interpret(self, si):
        return TekoString(str(self.owner))

###

class TekoBool(TekoObject):
    def __init__(self, b):
        assert(type(b) == bool)
        super().__init__(TekoBoolType, name = str(b).lower())
        self._boolval = b
        self.declare(label = "_and", tekotype = TekoBoolBinopType, val = TekoBoolBinop(bool_ns = self.ns, op = "_and", name="_and", owner = self))
        self.declare(label = "_or",  tekotype = TekoBoolBinopType, val = TekoBoolBinop(bool_ns = self.ns, op = "_or",  name="_or", owner = self))

class TekoBoolBinop(TekoFunction):
    OP_NAMES = {"_and":"__and__",
                "_or":"__or__"}
    
    def __init__(self, bool_ns, op, **kwargs):
        super().__init__(TekoBoolBinopType, codeblock=None, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftbool = self.owner._boolval
        rightbool = si.get_by_label("other")._boolval
        python_opname = TekoBoolBinop.OP_NAMES[self.op]
        
        return TekoBool(getattr(leftbool,python_opname)(rightbool))

###

TekoType            = TekoObject(None,         name="type",   bootstrapping=True)
TekoType.tekotype   = TekoType

TekoObjectType      = TekoObject(TekoType,     name="obj",    bootstrapping=True)
            
TekoVoidType        = TekoObject(TekoType,     name="void",   bootstrapping=True)
TekoVoid            = TekoObject(TekoVoidType,                bootstrapping=True)

TekoStructType      = TekoObject(TekoType,     name="struct", bootstrapping=True, parent=TekoType)

TekoBoolType        = TekoObject(TekoType,     name="bool",   bootstrapping=True)
TekoBoolBinopType   = TekoFunctionType(TekoBoolType,   TekoNewStruct([TekoStructElem(TekoBoolType,"other")],   bootstrapping=True), bootstrapping=True)

TekoStringType      = TekoObject(TekoType,     name="str",    bootstrapping=True)
TekoStringBinopType = TekoFunctionType(TekoStringType, TekoNewStruct([TekoStructElem(TekoStringType,"other")], bootstrapping=True), bootstrapping=True)
TekoStringEqType    = TekoFunctionType(TekoBoolType,   TekoNewStruct([TekoStructElem(TekoStringType,"other")], bootstrapping=True), bootstrapping=True)
TekoTostrType       = TekoFunctionType(TekoStringType, TekoNewStruct([],                                       bootstrapping=True), bootstrapping=True)

###

TekoModuleType = TekoObject(TekoType, name="module", bootstrapping=True)

class TekoModule(TekoObject):
    def __init__(self, name, **kwargs):
        super().__init__(TekoModuleType, name=name, **kwargs)

StandardLibrary = TekoModule(name="stdlib", bootstrapping=True)

TekoType.owner = StandardLibrary
StandardLibrary.declare("type",   TekoType, TekoType)
TekoObjectType.owner = StandardLibrary
StandardLibrary.declare("obj",    TekoType, TekoObjectType)
TekoVoidType.owner = StandardLibrary
StandardLibrary.declare("void",   TekoType, TekoVoidType)
TekoStringType.owner = StandardLibrary
StandardLibrary.declare("str",    TekoType, TekoStringType)
TekoBoolType.owner = StandardLibrary
StandardLibrary.declare("bool",   TekoType, TekoBoolType)
TekoStructType.owner = StandardLibrary
StandardLibrary.declare("struct", TekoType, TekoStructType)
TekoModuleType.owner = StandardLibrary
StandardLibrary.declare("module", TekoType, TekoModuleType)

###

BOOTSTRAPPING_OBJECTS = [StandardLibrary, TekoType, TekoObjectType, TekoVoidType, TekoVoid, TekoStructType, TekoBoolType, TekoBoolBinopType, TekoBoolBinopType.arg_struct, TekoStringType,
                         TekoStringBinopType, TekoStringBinopType.arg_struct, TekoStringEqType, TekoStringEqType.arg_struct, TekoTostrType, TekoTostrType.arg_struct, TekoModuleType]

for obj in BOOTSTRAPPING_OBJECTS:
    obj.declare("_tostr",TekoTostrType,TekoTostr(owner = obj))
