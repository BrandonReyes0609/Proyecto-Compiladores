# programm/symbol_table.py

class Symbol:
    """Representa una entrada en la tabla (una variable o constante)."""
    def __init__(self, name, type, is_const=False):
        self.name = name
        self.type = type
        self.is_const = is_const

class SymbolTable:
    """Gestiona los símbolos para un ámbito (scope) específico."""
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent # Referencia al ámbito padre

    def insert(self, name, symbol_type, is_const=False):
        """Inserta un símbolo en el ámbito actual. Retorna False si ya existe."""
        if name in self.symbols:
            return False
        self.symbols[name] = Symbol(name, symbol_type, is_const)
        return True

    def lookup(self, name):
        """Busca un símbolo en el ámbito actual y, si no lo encuentra, en los ámbitos padres."""
        symbol = self.symbols.get(name)
        if symbol:
            return symbol
        if self.parent:
            return self.parent.lookup(name)
        return None