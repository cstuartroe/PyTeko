from .framework import *
from .interpreter import *

TekoStringType = TekoObject(TekoType, name="str")

class TekoString(TekoObject):
    def __init__(self, s):
        assert(type(s) == str)
        super().__init__(TekoStringType, name = s)
        self._strval = s

    def __repr__(self):
        return '<str :: %s>' % self._strval.__repr__()

TekoIntType = TekoObject(TekoType, name="int")

class TekoInt(TekoObject):
    def __init__(self, n):
        assert(type(n) == int)
        super().__init__(TekoIntType, name = str(n))
        self._intval = n

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
    def __init__(self, ftype, codeblock, outer_ns):
        assert(isinstance(ftype, TekoFunctionType))
        assert(isinstance(codeblock, CodeBlock))
        super().__init__(ftype, name="TekoFunction")
        self.codeblock = codeblock
        self.ns = Namespace(outer_ns = outer_ns)

    def exec(self, args):
        ti = TekoInterpreter(self.ns)
        for stmt in self.codeblock.statements:
            ti.exec(stmt)

TekoStructType = TekoObject(TekoType, name="struct")

class TekoNewStruct(TekoObject):
    def __init__(self):
        pass

TekoPrintType = TekoFunctionType(None, TekoNewStruct())
empty_cb = CodeBlock(-1,[])
TekoPrint = TekoFunction(TekoPrintType, empty_cb, None)
TekoPrint.exec = lambda s: print(s[0])

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
