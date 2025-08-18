# program/symbol_table.py

class Symbol:
    """Entrada en la tabla (variable, constante o parámetro)."""
    def __init__(self, name, type, is_const=False, line=None, col=None):
        self.name = name
        self.type = type
        self.is_const = is_const
        self.line = line
        self.col = col

class SymbolTable:
    """Ámbito (scope) con jerarquía para exportar al IDE."""
    def __init__(self, parent=None, name="global", level=0):
        self.symbols = {}      # name -> Symbol
        self.parent = parent   # scope padre
        self.children = []     # sub-scopes
        self.name = name
        self.level = level

    def insert(self, name, symbol_type, is_const=False, line=None, col=None):
        """Inserta en el scope actual. False si ya existía."""
        if name in self.symbols:
            return False
        self.symbols[name] = Symbol(name, symbol_type, is_const, line, col)
        return True

    def lookup(self, name):
        """Busca en este scope y, si no, recursivo en padres."""
        s = self.symbols.get(name)
        if s:
            return s
        return self.parent.lookup(name) if self.parent else None
