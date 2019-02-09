class TekoObject:
    def __init__(self,tekoType,tekoVal=None,tekoAttrs = {}):
        self.tekoType = tekoType
        self.tekoVal = tekoVal
        self.tekoAttrs = tekoAttrs

    def to_tekostr():
        raise Exception("Not implemented yet")

    def get_tekoAttr(name):
        return self.tekoAttrs[name]

    def parent(self):
        assert(isTekoType(self))
        return self.tekoAttrs.get("parent",None)

TekoType = TekoObject(None)
TekoType.tekoType = TekoType

def isTekoType(tekoObj):
    if tekoObj is TekoType:
        return True
    else:
        return isTekoSubtype(tekoObj.tekoType,TekoType)

def isTekoSubtype(sub,sup):
    if not isTekoType(sub) or not isTekoType(sup):
        raise ValueError("Not both types: " + str(tt1) + ", " + str(tt2))
    if sub is sup:
        return True
    elif sub.parent() is None:
        return False
    else:
        return isTekoSubtype(sub.parent(), sup)

def isTekoInstance(tekoObj, tekoType):
    assert(isTekoType(tekoType))
    return isTekoSubtype(tekoObj.tekoType,tekoType)

TekoString = TekoObject(TekoType)
TekoInt    = TekoObject(TekoType)
TekoReal   = TekoObject(TekoType)
TekoBool   = TekoObject(TekoType)

if __name__ == "__main__":
    # some subtyping tests
    s = TekoObject(TekoString)
    sup = TekoObject(TekoType)
    sub = TekoObject(TekoType,tekoAttrs = {"parent":sup})
    print(sub.parent() is sup) # true
    print(sub.parent() is TekoType) # false
    print(isTekoType(sub)) # true
    print(isTekoInstance(s, TekoString)) # true
    print(isTekoInstance(s, TekoType)) # false
