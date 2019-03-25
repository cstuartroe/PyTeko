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
        return self.interpret(si)

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

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

TekoIntType = TekoObject(TekoType, name="int")

TekoIntAddType = TekoFunctionType(TekoIntType, TekoNewStruct([TekoStructElem(TekoIntType,"other")]))
class TekoIntAdd(TekoFunction):
    def __init__(self, int_ns):
        super().__init__(TekoIntAddType, codeblock=None, outer_ns=int_ns)

    def interpret(self, si):
        return TekoInt(self.ns.get("_val")._intval + si.get_by_label("other")._intval)

class TekoInt(TekoObject):
    def __init__(self, n):
        assert(type(n) == int)
        super().__init__(TekoIntType, name = str(n))
        self._intval = n
        self.declare("_val", TekoIntType, self)
        self.declare("_add", TekoIntAddType, TekoIntAdd(int_ns = self.ns))

TekoRealType = TekoObject(TekoType, name="real")

class TekoReal(TekoObject):
    def __init__(self, x):
        assert(type(x) == float)
        super().__init__(TekoRealType, name = str(x))        
        self._realval = x 

TekoBoolType = TekoObject(TekoType, name="bool")

class TekoBool(TekoObject):
    def __init__(self, b):
        assert(type(b) == bool)
        super().__init__(TekoBoolType, name = str(b))
        self._boolval = b

TekoPrintType = TekoFunctionType(None, TekoNewStruct([TekoStructElem(TekoObjectType,"arg")]))
class TekoPrint(TekoFunction):
    def __init__(self):
        super().__init__(TekoPrintType, codeblock = None)
        
    def interpret(self, si):
        print(str(si.get_by_label("arg")))
        return None
TekoPrint = TekoPrint()

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
