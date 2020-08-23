def isTekoSubtype(subtype, supertype):
    if subtype == supertype:
        return True

    subtype_fields = subtype.get("fields")
    for field_name, tekotype in supertype.get("fields").items():
        if subtype_fields.includes(field_name) and subtype_fields.at(field_name) == tekotype:
            pass
        else:
            return False
    return True


def isTekoInstance(o, tekotype):
    if o is None:
        return True
    return isTekoSubtype(o.get("type").value, tekotype)


class TekoVariable:
    def __init__(self, mutable=False, value=None):
        self.mutable = mutable
        self.value = value

    def set(self, value):
        if self.mutable or (self.value is None):
            self.value = value


class TekoObject:
    def __init__(self, tekotype=None):
        self.members = {"type": TekoVariable(False, tekotype)}
        self.lazy_members = {}

    def get(self, member_name):
        if member_name in self.lazy_members:
            self.set(member_name, self.lazy_members[member_name]())
            del self.lazy_members[member_name]
        if member_name in self.members:
            return self.members[member_name]

    def set(self, member_name, o, mutable=False):
        member_type = self.get("type").value.get("fields").value.at(member_name)
        assert(isTekoInstance(o, member_type))
        if member_name not in self.members:
            self.members[member_name] = TekoVariable(mutable=mutable)
        self.members[member_name].set(o)

    def set_lazy(self, member_name, f):
        self.lazy_members[member_name] = f

    def __eq__(self, other):
        if self is other:
            return True
        elif set(self.members.keys()) != set(other.members.keys()):
            return False
        else:
            return all(self.get(member_name) == other.get(member_name) for member_name in self.members.keys())

    def __hash__(self):
        return hash(repr(self))


TekoTypeType = TekoObject()
TekoTypeType.members["type"].set(TekoTypeType)


def generate_tt_fields():
    fields = TekoMap(TekoStringType, TekoTypeType)
    fields.at(TekoString("fields"), True).set(TekoMap.create_type(TekoStringType, TekoTypeType))
    return fields


TekoTypeType.set_lazy("fields", generate_tt_fields)


class TekoMap(TekoObject):
    def __init__(self, ktype=None, vtype=None):
        TekoObject.__init__(self)
        self.ktype = ktype
        self.vtype= vtype
        self.__items = {}
        self.set_lazy("type", lambda: TekoMap.create_type(ktype, vtype))

    def at(self, key, instantiate=False):
        if key not in self.__items:
            if instantiate:
                self.__items[key] = TekoVariable(mutable=True)
            else:
                raise ValueError
        return self.__items[key]

    @staticmethod
    def create_type(ktype, vtype):
        tt = blankTekoType()
        at_type = TekoFunctionType(
            argtype=ArgCompiler(ArgDef("key", ktype)),
            rtype=vtype
        )
        tt.get("fields").value.at(TekoString("at"), True).set(at_type)


def blankTekoType():
    tt = TekoObject(TekoTypeType)
    tt.set_lazy("fields", lambda: TekoMap(TekoStringType, TekoTypeType))
    return tt


TekoStringType = blankTekoType()


class TekoString(TekoObject):
    def __init__(self, value):
        TekoObject.__init__(self, TekoStringType)
        self.value = value


class ArgDef:
    def __init__(self, name, tekotype, default=None):
        assert(isinstance(name, str))
        assert(isTekoInstance(tekotype, TekoTypeType))
        assert(isTekoInstance(default, tekotype))
        self.name = name
        self.tekotype = tekotype
        self.default = default


class ArgCompiler:
    def __init__(self, *argdefs):
        assert(all(isinstance(argdef, ArgDef) for argdef in argdefs))
        self.argdefs = argdefs

    def rtype(self):
        raise NotImplementedError


class Arg:
    def __init__(self, value, kw=None):
        assert(isinstance(value, TekoObject))
        assert(kw is None or isinstance(kw, str))
        self.value = value
        self.kw = kw


class TekoFunctionType(TekoObject):
    def __init__(self, argtype, rtype=None):
        assert(isinstance(argtype, ArgCompiler))
        if rtype is None:
            rtype = argtype.rtype()
        assert(isTekoInstance(rtype, TekoTypeType))

        TekoObject.__init__(self, TekoTypeType)
        self.set("fields", TekoMap(TekoStringType, TekoTypeType))

        self.set("rtype", rtype)
        self.argtype = argtype


class TekoFunction(TekoObject):
    def __init__(self, ftype, codeblock=None):
        assert(isinstance(ftype, TekoFunctionType))
        TekoObject.__init__(self, ftype)
        self.codeblock = codeblock

    def execute(self, args):
        argso = self.get("type").value.argtype.compile(args)
        raise NotImplementedError

