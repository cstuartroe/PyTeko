from .framework import *

###

# Structs and functions need to be defined first because other primitives have function attributes

TekoStructType = TekoObject(TekoType, name="struct",parent=TekoType)

class TekoStructElem:
    def __init__(self, tekotype, label, default=None):
        assert(isTekoType(tekotype))
        assert(type(label) == str)
        assert(default is None or isTekoInstance(default, tekotype))
               
        self.tekotype = tekotype
        self.label = label
        self.default = default

class TekoNewStruct(TekoObject):
    def __init__(self, struct_elems):
        super().__init__(TekoStructType)

        self.struct_elems = []
        for struct_elem in struct_elems:
            assert(type(struct_elem) == TekoStructElem)
            self.struct_elems.append(struct_elem)

class TekoStructInstance(TekoObject):
    def __init__(self, new_struct, args):
        assert(type(new_struct) == TekoNewStruct)
        
        super().__init__(new_struct)

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
    def __init__(self, return_type, arg_struct):
        assert(return_type is None or isTekoType(return_type))
        assert(isinstance(arg_struct, TekoNewStruct))
        super().__init__(TekoType)
        self.return_type = return_type
        self.arg_struct = arg_struct

    def __str__(self):
        return str(self.return_type) + str(self.arg_struct)

class TekoFunction(TekoObject):
    def __init__(self, ftype, codeblock, outer_ns=None):
        assert(isinstance(ftype, TekoFunctionType))
        assert(codeblock is None or isinstance(codeblock, CodeBlock))
        super().__init__(ftype, name="TekoFunction")
        self.codeblock = codeblock
        self.ns = Namespace(outer_ns = outer_ns)

    def exec(self, args):
        si = TekoStructInstance(self.tekotype.arg_struct, args)
        returnval = self.interpret(si)
        if self.tekotype.return_type is None:
            assert(returnval is None)
        else:
            assert(isTekoInstance(returnval, self.tekotype.return_type))
        return returnval

    def interpret(self, si):
        ti = TekoInterpreter(self.ns)
        for stmt in self.codeblock.statements:
            ti.exec(stmt)
        raise RuntimeError("Returning not yet implemented")

###

TekoStringType = TekoObject(TekoType, name="str")

class TekoString(TekoObject):
    def __init__(self, s):
        assert(type(s) == str)
        super().__init__(TekoStringType, name = s)
        self._strval = s
        self.declare("_val", TekoStringType, self)
        self.declare("_add", TekoStringBinopType, TekoStringAdd(str_ns = self.ns))

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

TekoStringBinopType = TekoFunctionType(TekoStringType, TekoNewStruct([TekoStructElem(TekoStringType,"other")]))

class TekoStringAdd(TekoFunction):
    def __init__(self, str_ns):
        super().__init__(TekoStringBinopType, codeblock=None, outer_ns=str_ns)

    def interpret(self, si):
        return TekoString(self.ns.get("_val")._strval + si.get_by_label("other")._strval)

###

TekoIntType = TekoObject(TekoType, name="int")

class TekoInt(TekoObject):
    def __init__(self, n):
        assert(type(n) == int)
        super().__init__(TekoIntType, name = str(n))
        self._intval = n
        self.declare("_val", TekoIntType, self)
        self.declare("_add", TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = "__add__"))
        self.declare("_sub", TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = "__sub__"))
        self.declare("_mul", TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = "__mul__"))
        self.declare("_div", TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = "__floordiv__"))
        self.declare("_exp", TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = "__pow__"))
        self.declare("_mod", TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = "__mod__"))

TekoIntBinopType = TekoFunctionType(TekoIntType, TekoNewStruct([TekoStructElem(TekoIntType,"other")]))

class TekoIntBinop(TekoFunction):
    def __init__(self, int_ns, op):
        super().__init__(TekoIntBinopType, codeblock=None, outer_ns=int_ns)
        self.op = op
        
    def interpret(self, si):
        leftint = self.ns.get("_val")._intval
        rightint = si.get_by_label("other")._intval
        return TekoInt(getattr(leftint,self.op)(rightint))

###

TekoRealType = TekoObject(TekoType, name="real")

class TekoReal(TekoObject):
    def __init__(self, x):
        assert(type(x) == float)
        super().__init__(TekoRealType, name = str(x))
        self._realval = x
        self.declare("_val", TekoRealType, self)
        self.declare("_add", TekoRealBinopType, TekoRealBinop(real_ns = self.ns, op = "__add__"))
        self.declare("_sub", TekoRealBinopType, TekoRealBinop(real_ns = self.ns, op = "__sub__"))
        self.declare("_mul", TekoRealBinopType, TekoRealBinop(real_ns = self.ns, op = "__mul__"))
        self.declare("_div", TekoRealBinopType, TekoRealBinop(real_ns = self.ns, op = "__truediv__"))
        self.declare("_exp", TekoRealBinopType, TekoRealBinop(real_ns = self.ns, op = "__pow__"))

TekoRealBinopType = TekoFunctionType(TekoRealType, TekoNewStruct([TekoStructElem(TekoRealType,"other")]))

class TekoRealBinop(TekoFunction):
    def __init__(self, real_ns, op):
        super().__init__(TekoRealBinopType, codeblock=None, outer_ns=real_ns)
        self.op = op
        
    def interpret(self, si):
        leftreal = self.ns.get("_val")._realval
        rightreal = si.get_by_label("other")._realval
        return TekoReal(getattr(leftreal,self.op)(rightreal))

###

TekoBoolType = TekoObject(TekoType, name="bool")

class TekoBool(TekoObject):
    def __init__(self, b):
        assert(type(b) == bool)
        super().__init__(TekoBoolType, name = str(b).lower())
        self._boolval = b
        self.declare("_val", TekoBoolType, self)
        self.declare("_and", TekoBoolBinopType, TekoRealBinop(bool_ns = self.ns, op = "__and__"))
        self.declare("_or",  TekoBoolBinopType, TekoRealBinop(bool_ns = self.ns, op = "__or__"))

TekoBoolBinopType = TekoFunctionType(TekoBoolType, TekoNewStruct([TekoStructElem(TekoBoolType,"other")]))

class TekoBoolBinop(TekoFunction):
    def __init__(self, bool_ns, op):
        super().__init__(TekoBoolBinopType, codeblock=None, outer_ns=bool_ns)
        self.op = op
        
    def interpret(self, si):
        leftbool = self.ns.get("_val")._boolval
        rightbool = si.get_by_label("other")._boolval
        return TekoBool(getattr(leftbool,self.op)(rightbool))

###

TekoPrintType = TekoFunctionType(None, TekoNewStruct([TekoStructElem(TekoObjectType,"arg")]))
class TekoPrint(TekoFunction):
    def __init__(self):
        super().__init__(TekoPrintType, codeblock = None)
        
    def interpret(self, si):
        print(str(si.get_by_label("arg")))
        return None
TekoPrint = TekoPrint()

###

class StandardNS(Namespace):
    def __init__(self):
        super().__init__(outer_ns = None)

        # Primitive and complex types:
        self.declare("type",   TekoType, TekoType)
        self.declare("str",    TekoType, TekoStringType)
        self.declare("int",    TekoType, TekoIntType)
        self.declare("real",   TekoType, TekoRealType)
        self.declare("bool",   TekoType, TekoBoolType)
        self.declare("struct", TekoType, TekoStructType)

        # Standard library functions:
        self.declare("print",  TekoPrintType, TekoPrint)
