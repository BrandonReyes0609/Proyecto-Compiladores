class Type:
  pass

class _IntType(Type):
  def __str__(self): return "int"

class _FloatType(Type):
  def __str__(self): return "float"

class _StringType(Type):
  def __str__(self): return "string"

class _BoolType(Type):
  def __str__(self): return "bool"

class _NullType(Type):
  def __str__(self): return "null"

class _VoidType(Type):
  def __str__(self): return "void"


class FunctionType(Type):
  def __init__(self, return_type, param_types):
    self.return_type = return_type
    self.param_types = param_types

  def __str__(self):
    params = ", ".join(str(p) for p in self.param_types)
    return f"function<({params}) => {self.return_type}>"

# ===== NUEVO: Tipo para clases (soporta herencia sencilla) =====
class ClassType(Type):
  def __init__(self, name, base=None):
    self.name = name          # "Persona", "Estudiante"
    self.base = base          # otro ClassType o None
    self.fields = {}          # nombre -> Type
    self.methods = {}         # nombre -> FunctionType

  def __str__(self):
    return self.name


# ===== Instancias únicas para primitivos =====
IntType    = _IntType()
FloatType  = _FloatType()
StringType = _StringType()
BoolType   = _BoolType()
NullType   = _NullType()
VoidType   = _VoidType()
