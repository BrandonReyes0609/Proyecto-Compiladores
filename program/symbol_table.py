# program/symbol_table.py
import json
from typing import Optional, Dict, Any, List, Callable

class Type:
    def __init__(self, name: str):
        self.name = name
    def __str__(self): return self.name
    def __repr__(self): return self.name

# Exponemos un "constructor" de tipos por nombre para reutilizar
def TYPE(name: str) -> Type:
    return Type(name)

INT    = Type("integer")
STR    = Type("string")
BOOL   = Type("boolean")
VOID   = Type("void")
CLASS  = lambda n: Type(f"class<{n}>")
FN     = lambda sig: Type(sig)  # ej: "fn(integer)->string"

class Symbol:
    def __init__(self,
                 name: str,
                 type: Type,
                 is_const: bool = False,
                 line: Optional[int] = None,
                 col: Optional[int] = None,
                 offset: Optional[int] = None,
                 label: Optional[str] = None,
                 is_param: bool = False):
        self.name = name
        self.type = type
        self.is_const = is_const
        self.line = line
        self.col = col
        self.offset = offset
        self.label = label
        self.is_param = is_param

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": str(self.type),
            "const": self.is_const,
            "line": self.line,
            "col": self.col,
            "offset": self.offset,
            "label": self.label,
            "is_param": self.is_param,
        }

class SymbolTable:
    def __init__(self, parent: Optional['SymbolTable']=None, name: str="global", level: int=0):
        self.symbols: Dict[str, Symbol] = {}
        self.parent = parent
        self.children: List['SymbolTable'] = []
        self.name = name
        self.level = level
        self.next_local = 0
        self.next_param = 0

    def insert(self, name: str, symbol_type: Type, is_const: bool=False,
               line: Optional[int]=None, col: Optional[int]=None,
               is_param: bool=False, label: Optional[str]=None) -> bool:
        if name in self.symbols:
            return False
        if is_param:
            off = self.next_param
            self.next_param += 1
        else:
            off = self.next_local
            self.next_local += 1
        self.symbols[name] = Symbol(name, symbol_type, is_const, line, col, offset=off, label=label, is_param=is_param)
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        s = self.symbols.get(name)
        if s: return s
        return self.parent.lookup(name) if self.parent else None

    def child(self, name: str) -> 'SymbolTable':
        kid = SymbolTable(parent=self, name=name, level=self.level+1)
        self.children.append(kid)
        return kid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.name,
            "level": self.level,
            "symbols": [s.to_dict() for s in self.symbols.values()],
            "children": [c.to_dict() for c in self.children]
        }

    def export_json(self, path: str="symbol_table.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
