# program/symbol_table.py
import json

class Symbol:
    """Entrada en la tabla (variable, constante, parámetro o función)."""
    def __init__(self, name, type, is_const=False, line=None, col=None, offset=None, label=None):
        self.name = name
        self.type = type
        self.is_const = is_const
        self.line = line
        self.col = col
        self.offset = offset      # dirección relativa en RA
        self.label = label        # etiqueta TAC (para funciones / globales)

    def to_dict(self):
        return {
            "name": self.name,
            "type": str(self.type),
            "const": self.is_const,
            "line": self.line,
            "col": self.col,
            "offset": self.offset,
            "label": self.label,
        }


class SymbolTable:
    """Ámbito (scope) con jerarquía para exportar al IDE."""
    def __init__(self, parent=None, name="global", level=0):
        self.symbols = {}      # name -> Symbol
        self.parent = parent   # scope padre
        self.children = []     # sub-scopes
        self.name = name
        self.level = level
        self.offset_counter = 0  # nuevo: asignar offsets a locales

    def insert(self, name, symbol_type, is_const=False, line=None, col=None, label=None):
        """Inserta en el scope actual. False si ya existía."""
        if name in self.symbols:
            return False
        offset = self.offset_counter
        self.offset_counter += 1
        self.symbols[name] = Symbol(name, symbol_type, is_const, line, col, offset=offset, label=label)
        return True

    def lookup(self, name):
        """Busca en este scope y, si no, recursivo en padres."""
        s = self.symbols.get(name)
        if s:
            return s
        return self.parent.lookup(name) if self.parent else None

    def to_dict(self):
        return {
            "name": self.name,
            "level": self.level,
            "symbols": [s.to_dict() for s in self.symbols.values()],
            "children": [c.to_dict() for c in self.children]
        }

    def export_json(self, path="symbol_table.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class TempManager:
    def __init__(self):
        self.counter = 0
        self.free = []

    def new_temp(self) -> str:
        if self.free:
            return self.free.pop()
        self.counter += 1
        return f"t{self.counter}"

    def free_temp(self, t: str):
        self.free.append(t)


class LabelManager:
    def __init__(self):
        self.counter = 0

    def new_label(self) -> str:
        self.counter += 1
        return f"L{self.counter}"
