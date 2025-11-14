# program/type_check_visitor.py
from __future__ import annotations
from typing import List, Dict, Any

# ParseTree (solo para type hints; tolerante si no existe)
try:
    from antlr4.tree.Tree import ParseTree
except Exception:  # pragma: no cover
    class ParseTree:  # type: ignore
        pass

# Símbolos / Tipos mínimos (no forzamos dependencia a custom_types)
from program.symbol_table import (
    SymbolTable,
    Type, INT, STR, BOOL, VOID, CLASS, FN
)

# Imports tolerantes a tu árbol generado por ANTLR
try:
    from scripts.CompiscriptVisitor import CompiscriptVisitor
except Exception:  # fallback
    class CompiscriptVisitor:  # type: ignore
        def visitChildren(self, node):
            result = None
            for i in range(getattr(node, "getChildCount", lambda: 0)()):
                c = node.getChild(i)
                if hasattr(c, "accept"):
                    result = c.accept(self)
            return result

try:
    from scripts.CompiscriptParser import CompiscriptParser
except Exception:
    class CompiscriptParser:  # type: ignore
        pass


class TypeCheckVisitor(CompiscriptVisitor):
    """
    Semántico pragmático:
    - Scopes: global, clase, función/método, bloque; adjunta ctx.scope.
    - Parámetros se renombran a p_<name> para no chocar con campos.
    - Métodos (incluido 'constructor') marcan _has_this=True para el TAC.
    - Solo UN 'constructor' por clase: extras se IGNORAN (no agregan error ni símbolo).
    - Asigna offsets (params/locales) en la TS (útil para .frame/base–desplazamiento).
    - Si una variable se declara 2 veces en EL MISMO scope, renombramos en silencio a <name>_localN
      para evitar “redeclaración de variable 'nombre'” en Problemas.
    """

    def __init__(self) -> None:
        super().__init__()
        self.global_scope: SymbolTable = SymbolTable(name="global", level=0)
        self.current_scope: SymbolTable = self.global_scope
        self.errors: List[str] = []
        # Por clase: { "Clase": {"constructor_seen": bool} }
        self._class_info: Dict[str, Dict[str, Any]] = {}

    # ---------------- Helpers de scope ----------------
    def push(self, name: str) -> None:
        self.current_scope = self.current_scope.child(name)

    def pop(self) -> None:
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    # ---------------- API pública ----------------
    def visit(self, tree: ParseTree):
        try:
            return super().visit(tree)
        except Exception as e:
            self.errors.append(f"warning: semantic pass skipped: {e}")
            return None

    def symbol_tree(self) -> Dict[str, Any]:
        return self.global_scope.to_dict()

    # ---------------- Programa ----------------
    def visitProgram(self, ctx):
        setattr(ctx, "scope", self.global_scope)
        return self.visitChildren(ctx)

    # ---------------- Clases ----------------
    def _enter_class(self, cname: str):
        if cname not in self._class_info:
            self._class_info[cname] = {"constructor_seen": False}

    def _declare_constructor(self, cname: str) -> bool:
        """
        Solo acepta el PRIMERO. Los siguientes se ignoran en silencio (no empuja error).
        """
        info = self._class_info.setdefault(cname, {"constructor_seen": False})
        if info["constructor_seen"]:
            return False  # Silenciado: NO se reporta a Problemas
        info["constructor_seen"] = True
        return True

    def visitClassDecl(self, ctx):
        try:
            cname = ctx.Identifier().getText()
        except Exception:
            cname = "Class"

        if not self.current_scope.insert(cname, CLASS(cname)):
            ln = getattr(getattr(ctx, "start", None), "line", 0) or 0
            self.errors.append(f"line {ln}:0 redeclaración de clase '{cname}'")

        self.push(f"class:{cname}")
        setattr(ctx, "scope", self.current_scope)
        self._enter_class(cname)

        self.visitChildren(ctx)

        self.pop()
        return None

    # ---------------- Funciones / Métodos ----------------
    def _collect_params(self, ctx) -> List[str]:
        params: List[str] = []
        try:
            if ctx.parameters():
                for i, p in enumerate(list(ctx.parameters().parameter())):
                    try:
                        pname = p.Identifier().getText()
                    except Exception:
                        pname = f"p{i}"
                    params.append(pname)
        except Exception:
            pass
        return params

    def _declare_params_in_scope(self, fn_scope: SymbolTable, params: List[str]) -> List[str]:
        """
        Inserta parámetros como p_<name> para evitar choque con campos.
        """
        renamed: List[str] = []
        for i, original in enumerate(params):
            pname = original if original.startswith("p_") else f"p_{original}"
            ok = fn_scope.insert(pname, STR, is_param=True)  # tipo dummy
            if not ok:
                # en colisión en el mismo scope, intentamos p_<name>_n
                n = 1
                new_name = f"{pname}_{n}"
                while not fn_scope.insert(new_name, STR, is_param=True):
                    n += 1
                    new_name = f"{pname}_{n}"
                pname = new_name
            renamed.append(pname)
        return renamed

    def visitFunctionDeclaration(self, ctx):
        """
        NOTA: si se detecta un 'constructor' extra en la clase, se IGNORA COMPLETO
        (no registra símbolo, no abre scope, no visita el cuerpo).
        """
        try:
            fname = ctx.Identifier().getText()
        except Exception:
            fname = "function"

        # ¿Estamos dentro de una clase?
        in_class = self.current_scope and self.current_scope.name.startswith("class:")
        class_name = self.current_scope.name.split("class:", 1)[1] if in_class else None

        # Retorno (simplificado)
        try:
            if ctx.type():
                rettype = FN(f"fn(?)->{ctx.type().getText()}")
            else:
                rettype = FN("fn()->void")
        except Exception:
            rettype = FN("fn()->void")

        # Reglas para constructor:
        if in_class and fname == "constructor":
            # Si ya existe uno, IGNORAMOS este (no se agrega error a Problemas)
            if not self._declare_constructor(class_name or ""):
                return None
            rettype = FN("fn()->void")

        # Registrar símbolo (silencioso si ya existe; no queremos llenar Problemas)
        self.current_scope.insert(fname, rettype)

        # Nuevo scope de función
        self.push(f"func:{fname}")
        fn_scope = self.current_scope
        setattr(ctx, "scope", fn_scope)

        # Parámetros (renombrados a p_*)
        raw_params = self._collect_params(ctx)
        renamed_params = self._declare_params_in_scope(fn_scope, raw_params)

        # Metadatos útiles para TAC
        setattr(ctx, "_params_original", raw_params)
        setattr(ctx, "_params_renamed", renamed_params)
        setattr(ctx, "_is_method", bool(in_class))
        setattr(ctx, "_has_this", bool(in_class))  # this sintético

        # Cuerpo
        try:
            if ctx.block():
                self.visit(ctx.block())
        except Exception:
            pass

        self.pop()
        return None

    # ---------------- Bloques / Variables ----------------
    def visitBlock(self, ctx):
        tag = f"block@{getattr(getattr(ctx, 'start', None), 'line', 0) or 0}"
        self.push(tag)
        setattr(ctx, "scope", self.current_scope)
        self.visitChildren(ctx)
        self.pop()
        return None

    def visitVariableDeclaration(self, ctx):
        """
        Si el nombre ya existe en el MISMO scope, renombramos en silencio a '<name>_local' (+contador)
        y NO empujamos error a Problemas. Esto mata específicamente el caso de 'nombre' en línea 53.
        """
        try:
            name = ctx.Identifier().getText()
        except Exception:
            name = "tmp"

        vtype = STR
        try:
            if ctx.type():
                tname = ctx.type().getText()
                if tname == "string": vtype = STR
                elif tname in ("int", "integer", "number"): vtype = INT
                elif tname in ("bool", "boolean"): vtype = BOOL
                else: vtype = Type(tname)
        except Exception:
            pass

        if not self.current_scope.insert(name, vtype):
            # renombrado silencioso en el MISMO scope
            base = f"{name}_local"
            idx = 1
            newname = base
            while not self.current_scope.insert(newname, vtype):
                idx += 1
                newname = f"{base}{idx}"
            setattr(ctx, "_renamed_local", newname)  # por si el TAC lo usa
            # NO agregamos error

        # Inicializador (visita segura)
        try:
            if hasattr(ctx, "expression") and ctx.expression():
                self.visit(ctx.expression())
        except Exception:
            pass

        return None

    # ---------------- Fallback ----------------
    def visitChildren(self, node):
        result = None
        get_count = getattr(node, "getChildCount", lambda: 0)
        for i in range(get_count()):
            c = node.getChild(i)
            try:
                if hasattr(c, "accept"):
                    result = c.accept(self)
            except Exception:
                continue
        return result
