from .parsenode import *

class Variable:
    def __init__(self, tekotype):
        assert(isTekoType(tekotype))
        self.tekotype = tekotype
        self.val = None

    def get(self):
        return self.val

    def get_tekotype(self):
        return self.tekotype

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

    def fetchvar(self, label):
        outer_var = self.outer_ns.fetchvar(label) if self.outer_ns else None
        if outer_var:
            return outer_var
        else:
            return self.vars.get(label, None)

    def get(self, label):
        return self.fetchvar(label).get()

    def get_tekotype(self, label):
        return self.fetchvar(label).get_tekotype()

    def set(self, label, val):
        self.fetchvar(label).set(val)

class TekoObject:
    def __init__(self,tekotype,name="TekoObject"):
        assert(tekotype is None or isTekoType(tekotype))
        assert(type(name) == str)
        self.tekotype = tekotype
        self.ns = Namespace()
        self.name = name

    def declare(self, label, tekotype, val = None):
        self.ns.declare(label, tekotype, val)

    def get(self,label):
        return self.ns.get(label)

    def get_tekotype(self, label):
        return self.ns.get_tekotype(label)

    def set(self,label,val):
        self.ns.set(label, val)

    def parent(self):
        assert(isTekoType(self))
        return self.get("_parent",None)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s :: %s>' % (str(self.tekotype), str(self))

TekoType = TekoObject(None)
TekoType.tekotype = TekoType

def isTekoType(tekoObj):
    if tekoObj is TekoType:
        return True
    else:
        return isTekoSubtype(tekoObj.tekotype,TekoType)

def isTekoSubtype(sub,sup):
    if not isTekoType(sub) or not isTekoType(sup):
        raise ValueError("Not both types: " + str(tt1) + ", " + str(tt2))
    if sub is sup:
        return True
    elif sub.parent() is None:
        return False
    else:
        return isTekoSubtype(sub.parent(), sup)

def isTekoInstance(tekoObj, tekotype):
    assert(isTekoType(tekotype))
    return isTekoSubtype(tekoObj.tekotype,tekotype)
