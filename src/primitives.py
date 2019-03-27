from .framework import *

###

TekoIntType = TekoObject(tekotype = TekoType, name = "int", owner = StandardLibrary)
StandardLibrary.declare("int", TekoType, TekoIntType)

class TekoInt(TekoObject):    
    def __init__(self, n, **kwargs):
        assert(type(n) == int)
        super().__init__(TekoIntType, name = str(n), **kwargs)
        self._intval = n

        for teko_opname in TekoIntBinop.OP_NAMES:
            self.declare(label = teko_opname, tekotype = TekoIntBinopType, val = TekoIntBinop(owner = self, op = teko_opname, name = teko_opname))
        
        self.declare(label = "_compare", tekotype = TekoIntCompType, val = TekoIntComp(owner = self, name="_compare"))

TekoIntBinopType = TekoFunctionType(return_type = TekoIntType, arg_struct = TekoNewStruct([TekoStructElem(TekoIntType,"other")]), owner = StandardLibrary)

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
        leftint = self.owner._intval
        rightint = si.get_by_label("other")._intval
        python_opname = TekoIntBinop.OP_NAMES[self.op]
        
        return TekoInt(getattr(leftint,python_opname)(rightint))

TekoIntCompType = TekoFunctionType(return_type = TekoIntType, arg_struct = TekoNewStruct([TekoStructElem(TekoIntType,"other")]), owner = StandardLibrary)

class TekoIntComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoIntCompType, codeblock = None, **kwargs)

    def interpret(self, si):
        leftint = self.owner._intval
        rightint = si.get_by_label("other")._intval

        if leftint == rightint:
            n = 0
        elif leftint < rightint:
            n = -1
        elif leftint > rightint:
            n = 1

        return TekoInt(n)

###

TekoRealType = TekoObject(TekoType, name="real", owner = StandardLibrary)
StandardLibrary.declare("real", TekoType, TekoRealType)

class TekoReal(TekoObject):    
    def __init__(self, x, **kwargs):
        assert(type(x) == float)
        super().__init__(TekoRealType, name = str(x), **kwargs)
        self._realval = x

        for teko_opname in TekoRealBinop.OP_NAMES:
            self.declare(label = teko_opname, tekotype = TekoRealBinopType, val = TekoRealBinop(owner = self, op = teko_opname, name = teko_opname))
        
        self.declare(label = "_compare", tekotype = TekoRealCompType, val = TekoRealComp(owner = self, name="_compare"))

TekoRealBinopType = TekoFunctionType(return_type = TekoRealType, arg_struct = TekoNewStruct([TekoStructElem(TekoRealType,"other")]), owner = StandardLibrary)

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
        leftreal = self.owner._realval
        rightreal = si.get_by_label("other")._realval
        python_opname = TekoRealBinop.OP_NAMES[self.op]
        
        return TekoReal(getattr(leftreal,python_opname)(rightreal))

TekoRealCompType = TekoFunctionType(return_type = TekoIntType, arg_struct = TekoNewStruct([TekoStructElem(TekoRealType,"other")]), owner = StandardLibrary)

class TekoRealComp(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoRealCompType, codeblock=None, **kwargs)

    def interpret(self, si):
        leftreal = self.owner._realval
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

TekoPrintType = TekoFunctionType(return_type = TekoVoidType, arg_struct = TekoNewStruct([TekoStructElem(TekoObjectType,"obj", default=TekoString(""))]), owner = StandardLibrary)
class TekoPrint(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoPrintType, codeblock = None, **kwargs)
        
    def interpret(self, si):
        print(si.get_by_label("obj").get_attr("_tostr").exec([])._strval)
        return TekoVoid
TekoPrint = TekoPrint(name = "print", owner = StandardLibrary)
StandardLibrary.declare("print", TekoPrintType, TekoPrint)

TekoTypeofType = TekoFunctionType(return_type = TekoType, arg_struct = TekoNewStruct([TekoStructElem(TekoObjectType,"obj")]), owner = StandardLibrary)
class TekoTypeof(TekoFunction):
    def __init__(self, **kwargs):
        super().__init__(ftype = TekoTypeofType, codeblock=None, **kwargs)

    def interpret(self,si):
        return si.get_by_label("obj").tekotype
TekoTypeof = TekoTypeof(name = "typeof", owner = StandardLibrary)
StandardLibrary.declare("typeof",  TekoTypeofType, TekoTypeof)
