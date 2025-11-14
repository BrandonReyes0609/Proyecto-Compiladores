# program/type_check_visitor.py
from __future__ import annotations
from typing import List, Optional
from program.symbol_table import SymbolTable, INT, STR, BOOL, VOID, CLASS, FN

# Import seguro del Visitor de ANTLR (si no existe, usamos objeto base)
try:
    from scripts.CompiscriptVisitor import CompiscriptVisitor
except Exception:
    class CompiscriptVisitor: pass

# Import seguro del Parser para acceder a métodos si hace falta
try:
    from scripts.CompiscriptParser import CompiscriptParser
except Exception:
    class CompiscriptParser:
        pass

class TypeCheckVisitor(CompiscriptVisitor):
    """
    - Construye scopes (global, clase, función, bloque).
    - Asigna offsets (params/locales) en cada scope.
    - Adjunta 'scope' a nodos de clase/función para que el TAC pueda emitir .frame.
    - Registra errores simples (nombres duplicados, etc.).
    """
    def __init__(self):
        super().__init__()
        self.global_scope = SymbolTable(name="global", level=0)
        self.current_scope = self.global_scope
        self.errors: List[str] = []

    # Helpers
    def push(self, name: str):
        self.current_scope = self.current_scope.child(name)

    def pop(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    # --- Programa ---
    def visitProgram(self, ctx):
        # Visita hijos
        for ch in getattr(ctx, "children", []) or []:
            if hasattr(ch, "accept"):
                self.visit(ch)
        return None

    # --- Clases ---
    def visitClassDecl(self, ctx):
        # Nombre de clase
        try:
            cname = ctx.Identifier().getText()
        except Exception:
            cname = "Class"

        # Inserta símbolo de clase en global
        ok = self.current_scope.insert(cname, CLASS(cname))
        if not ok:
            self.errors.append(f"linea {getattr(ctx, 'start', None).line}:0: redeclaración de clase '{cname}'")

        # scope de clase
        self.push(f"class:{cname}")
        setattr(ctx, "scope", self.current_scope)

        # Campos/métodos
        for ch in getattr(ctx, "children", []) or []:
            if hasattr(ch, "accept"):
                self.visit(ch)

        self.pop()
        return None

    # --- Funciones/métodos ---
    def visitFunctionDeclaration(self, ctx):
        # nombre
        try:
            fname = ctx.Identifier().getText()
        except Exception:
            fname = "function"

        # firma simplificada: asumimos retorno por la gramática o VOID
        rettype = VOID
        try:
            if ctx.type():
                rettype = FN(f"fn(?)->{ctx.type().getText()}")
            else:
                rettype = FN("fn()->void")
        except Exception:
            rettype = FN("fn()->void")

        # registra símbolo en scope actual
        if not self.current_scope.insert(fname, rettype):
            self.errors.append(f"linea {getattr(ctx, 'start', None).line}:0: redeclaración de función '{fname}'")

        # abre scope de función
        self.push(f"func:{fname}")
        fn_scope = self.current_scope
        setattr(ctx, "scope", fn_scope)

        # parámetros (si existen)
        params = []
        try:
            if ctx.parameters():
                params = list(ctx.parameters().parameter())
        except Exception:
            params = []

        for i, p in enumerate(params):
            try:
                pname = p.Identifier().getText()
            except Exception:
                pname = f"p{i}"
            # decláralo como parámetro (offset en zona de params)
            fn_scope.insert(pname, STR, is_param=True)  # tipo dummy (STR) para no fallar

        # cuerpo
        try:
            if ctx.block():
                self.visit(ctx.block())
        except Exception:
            pass

        self.pop()
        return None

    # --- Variables (let) con inicializador ---
    def visitVariableDeclaration(self, ctx):
        # Muchas gramáticas: 'let' Identifier ':' type ('=' expr)? ';'
        try:
            name = ctx.Identifier().getText()
        except Exception:
            name = "tmp"

        # tipo dummy para no depender de custom_types
        vtype = STR
        try:
            if ctx.type():
                vtype = STR if ctx.type().getText() == "string" else INT
        except Exception:
            pass

        if not self.current_scope.insert(name, vtype):
            self.errors.append(f"linea {getattr(ctx, 'start', None).line}:0: redeclaración de variable '{name}'")

        # Visitar inicializador si existe (no hace nada semántico, pero no rompe)
        try:
            if ctx.expression():
                self.visit(ctx.expression())
        except Exception:
            pass

        return None

    # Fallback
    def visitChildren(self, node):
        result = None
        for i in range(getattr(node, "getChildCount", lambda: 0)()):
            c = node.getChild(i)
            if hasattr(c, "accept"):
                result = c.accept(self)
        return result
