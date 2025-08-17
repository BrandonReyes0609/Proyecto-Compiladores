class Type:
  pass

class IntType(Type):
  def __str__(self):
    return "int"

class FloatType(Type):
  def __str__(self):
    return "float"

class StringType(Type):
  def __str__(self):
    return "string"

class BoolType(Type):
  def __str__(self):
    return "bool"

class NullType(Type):
  def __str__(self):
    return "null"
  
class VoidType(Type):
  def __str__(self):
    return "void"


# --- NUEVO: Clase para representar el tipo de una función, siguiendo tu estilo ---
class FunctionType(Type):
  def __init__(self, return_type, param_types):
    self.return_type = return_type
    self.param_types = param_types

  def __str__(self):
    # Creamos un nombre descriptivo, ej: "(string) => string"
    param_str = ", ".join(str(p) for p in self.param_types)
    return f"function<({param_str}) => {self.return_type}>"
  
  # --- NUEVO: Instancias únicas de los tipos ---
# Esto es una MEJORA. En lugar de crear un nuevo objeto cada vez (ej. IntType()),
# usaremos siempre la misma instancia. Esto hace que las comparaciones (type_a == type_b)
# sean más rápidas y seguras.
IntType = IntType()
FloatType = FloatType()
StringType = StringType()
BoolType = BoolType()
NullType = NullType()
VoidType = VoidType()