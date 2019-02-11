from .types import *

class Variable:
    def __init__(self, tekotype):
        assert(isTekoType(tekotype))
        self.tekotype = tekotype
        self.val = None

    def set(self, val):
        assert(isTekoInstance(val, self.tekotype))
        self.val = val

class Namespace:
    def __init__(self, outer_ns = None):
        self.vars = {}
        assert(outer_ns is None or isinstance(outer_ns, Namespace))
        self.outer_ns = outer_ns

    def declare(self, label, tekotype, val = None):
        assert(type(label) == str)
        if not self.is_free(label):
            raise ValueError("Label already assigned: " + label) # should be checked by interpreter
        
        var = Variable(tekotype)
        if val is not None:
            var.set(val)
        self.vars[label] = var

    # checks whether a label is available to be declared
    def is_free(self,label):
        if self.outer_ns:
            return not ((label in self.vars) or outer_ns.is_free(label))
        else:
            return not (label in self.vars)

    def set(self, label, val):
        self.vars[label].set(val)

class StandardNS(Namespace):
    def __init__(self):
        super().__init__(outer_ns = None)

        self.declare("type", TekoType, TekoType)
        self.declare("str",  TekoType, TekoString)
        self.declare("int",  TekoType, TekoInt)
        self.declare("real", TekoType, TekoReal)
        self.declare("bool", TekoType, TekoBool)
