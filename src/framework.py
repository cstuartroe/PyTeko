from .parsenode import *

class Variable:
    def __init__(self, tekotype, val=None):
        assert(isTekoType(tekotype))
        self.tekotype = tekotype
        self.val = val

    def get(self):
        return self.val

    def get_tekotype(self):
        return self.tekotype

    def set(self, val):
        assert(isTekoInstance(val, self.tekotype))
        self.val = val

    def __str__(self):
        return "Variable(%s,%s)" % (str(self.tekotype),str(self.val))

    def __repr__(self):
        return str(self)

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
            return self.vars[label]

    def get(self, label):
        return self.fetchvar(label).get()

    def get_tekotype(self, label):
        return self.fetchvar(label).get_tekotype()

    def set(self, label, val):
        self.fetchvar(label).set(val)

    def __str__(self):
        s = "Teko Namespace:\n\n"
        for label, var in self.vars.items():
            s += label + ": " + str(var)
        return s

    def __repr__(self):
        return str(self)

THROW_ERROR = 0

class TekoObject:
    def __init__(self,tekotype,name="TekoObject",parent=None):
        assert(tekotype is None or isTekoType(tekotype))
        assert(type(name) == str)
        self.tekotype = tekotype
        self.ns = Namespace()
        self.name = name
        if parent is not None:
            self.set_parent(parent)

    def declare(self, label, tekotype, val = None):
        self.ns.declare(label, tekotype, val)

    def get(self,label,default=THROW_ERROR):
        if self.ns.is_free(label):
            if default is THROW_ERROR:
                raise RuntimeError("No default specified")
            else:
                return default
        else:
            return self.ns.get(label)

    def get_tekotype(self, label):
        return self.ns.get_tekotype(label)

    def set(self,label,val):
        self.ns.set(label, val)

    def get_parent(self):
        assert(isTekoType(self))
        return self.get("_parent",None)

    def set_parent(self,parent):
        self.declare("_parent",TekoType,parent)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s :: %s>' % (str(self.tekotype), str(self))

TekoType = TekoObject(None,name="type")
TekoType.tekotype = TekoType

def isTekoType(tekoObj):
    if tekoObj is TekoType:
        return True
    else:
        return isTekoSubtype(tekoObj.tekotype,TekoType)

TekoObjectType = TekoObject(TekoType)

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
