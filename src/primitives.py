from .framework import *

###

TekoIntType = TekoObject(TekoType, name="int")

class TekoInt(TekoObject):
    OP_NAMES = {"_add":"__add__",
                "_sub":"__sub__",
                "_mul":"__mul__",
                "_div":"__floordiv__",
                "_exp":"__pow__",
                "_mod":"__mod__"}
    
    def __init__(self, n):
        assert(type(n) == int)
        super().__init__(TekoIntType, name = str(n))
        self._intval = n

        for teko_opname, python_opname in TekoInt.OP_NAMES.items():
            self.declare(teko_opname, TekoIntBinopType, TekoIntBinop(int_ns = self.ns, op = python_opname, name=teko_opname))
        
        self.declare("_compare", TekoIntCompType, TekoIntComp(int_ns = self.ns, name="_compare"))

TekoIntBinopType = TekoFunctionType(TekoIntType, TekoNewStruct([TekoStructElem(TekoIntType,"other")]))

class TekoIntBinop(TekoFunction):
    def __init__(self, int_ns, op, **kwargs):
        super().__init__(TekoIntBinopType, codeblock=None, outer_ns=int_ns, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftint = self.ns.outer_ns.owner._intval
        rightint = si.get_by_label("other")._intval
        return TekoInt(getattr(leftint,self.op)(rightint))

TekoIntCompType = TekoFunctionType(TekoIntType, TekoNewStruct([TekoStructElem(TekoIntType,"other")]))

class TekoIntComp(TekoFunction):
    def __init__(self, int_ns, **kwargs):
        super().__init__(TekoIntCompType, codeblock=None, outer_ns=int_ns, **kwargs)

    def interpret(self, si):
        leftint = self.ns.outer_ns.owner._intval
        rightint = si.get_by_label("other")._intval

        if leftint == rightint:
            n = 0
        elif leftint < rightint:
            n = -1
        elif leftint > rightint:
            n = 1

        return TekoInt(n)

###

TekoRealType = TekoObject(TekoType, name="real")

class TekoReal(TekoObject):
    OP_NAMES = {"_add":"__add__",
                "_sub":"__sub__",
                "_mul":"__mul__",
                "_div":"__truediv__",
                "_exp":"__pow__"}
    
    def __init__(self, x):
        assert(type(x) == float)
        super().__init__(TekoRealType, name = str(x))
        self._realval = x

        for teko_opname, python_opname in TekoReal.OP_NAMES.items():
            self.declare(teko_opname, TekoRealBinopType, TekoRealBinop(real_ns = self.ns, op = python_opname, name=teko_opname))
        
        self.declare("_compare", TekoRealCompType, TekoRealComp(real_ns = self.ns, name="_compare"))

TekoRealBinopType = TekoFunctionType(TekoRealType, TekoNewStruct([TekoStructElem(TekoRealType,"other")]))

class TekoRealBinop(TekoFunction):
    def __init__(self, real_ns, op, **kwargs):
        super().__init__(TekoRealBinopType, codeblock=None, outer_ns=real_ns, **kwargs)
        self.op = op
        
    def interpret(self, si):
        leftreal = self.ns.outer_ns.owner._realval
        rightreal = si.get_by_label("other")._realval
        return TekoReal(getattr(leftreal,self.op)(rightreal))

TekoRealCompType = TekoFunctionType(TekoIntType, TekoNewStruct([TekoStructElem(TekoRealType,"other")]))

class TekoRealComp(TekoFunction):
    def __init__(self, real_ns, **kwargs):
        super().__init__(TekoRealCompType, codeblock=None, outer_ns=real_ns, **kwargs)

    def interpret(self, si):
        leftreal = self.ns.outer_ns.owner._realval
        rightreal = si.get_by_label("other")._realval

        if leftreal == rightreal:
            n = 0
        elif leftreal < rightreal:
            n = -1
        elif leftreal > rightreal:
            n = 1

        return TekoInt(n)

###

TekoPrintType = TekoFunctionType(TekoVoidType, TekoNewStruct([TekoStructElem(TekoObjectType,"obj",default=TekoString(""))]))
class TekoPrint(TekoFunction):
    def __init__(self):
        super().__init__(TekoPrintType, name="print", outer_ns=None, codeblock = None)
        
    def interpret(self, si):
        print(si.get_by_label("obj").get_attr("_tostr").exec([])._strval)
        return TekoVoid
TekoPrint = TekoPrint()

TekoTypeofType = TekoFunctionType(TekoType, TekoNewStruct([TekoStructElem(TekoObjectType,"obj")]))
class TekoTypeof(TekoFunction):
    def __init__(self):
        super().__init__(TekoTypeofType, name="typeof", outer_ns=None, codeblock=None)

    def interpret(self,si):
        return si.get_by_label("obj").tekotype
TekoTypeof = TekoTypeof()

###

class StandardNS(Namespace):
    def __init__(self):
        super().__init__(TekoVoid, outer_ns = None)

        # Primitive and complex types:
        self.declare("type",   TekoType, TekoType)
        self.declare("str",    TekoType, TekoStringType)
        self.declare("int",    TekoType, TekoIntType)
        self.declare("real",   TekoType, TekoRealType)
        self.declare("bool",   TekoType, TekoBoolType)
        self.declare("struct", TekoType, TekoStructType)

        # Standard library functions:
        self.declare("print",   TekoPrintType,  TekoPrint)
        self.declare("typeof",  TekoTypeofType, TekoTypeof)
