# -*- coding: utf-8 -*-
"""
TACGeneratorVisitor.py
----------------------
Generación de Código Intermedio (TAC) para Compiscript.

Incluye (resumen de características):
- Pool LIFO de temporales + peephole para eliminar copias triviales (tA = tB, tA uso único).
- Llamadas robustas a funciones y métodos, aunque la gramática no dispare reglas específicas.
- Separación formal/reales: en funciones se usan 'LoadParam i' para formales,
  mientras que el paso de argumentos reales usa 'param ...' antes de 'call ...'.
- Soporte de 'new Clase(args...)' -> 't = Clase new N' y (opcional) llamada al 'constructor'.
- Acceso a propiedades: getprop/setprop; LHS estrictamente asignable (id, obj.prop, arr[idx]).
- Control de flujo: if/else, while, do-while, for, break/continue, lógica con cortocircuito (&&, ||).
- Anotaciones de frame con base–desplazamiento si la TS trae offsets (params/locales).
- Etiquetas y utilidades para generación de TAC legible y estable.

Esta versión está pensada como drop-in para tu proyecto actual.
"""

from __future__ import annotations

import os
import sys
import re
from typing import List, Optional, Sequence, Dict, Any

# ------------------------------------------------------------
# Rutas: asegurar carga de módulos generados por ANTLR
# ------------------------------------------------------------
_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_SCRIPTS = os.path.join(_REPO_ROOT, "scripts")
for _p in (_REPO_ROOT, _SCRIPTS, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Ajusta el nombre del Visitor a tu gramática real
from scripts.CompiscriptVisitor import CompiscriptVisitor  # type: ignore
from antlr4 import TerminalNode  # type: ignore


# =========================================================
# TempManager: Pool LIFO de t# para reutilización de temporales
# =========================================================
class TempManager:
    def __init__(self) -> None:
        self._cnt = 0
        self._free: List[str] = []

    def new(self) -> str:
        if self._free:
            return self._free.pop()
        self._cnt += 1
        return f"t{self._cnt}"

    def free(self, t: Optional[str]) -> None:
        if isinstance(t, str) and t.startswith("t"):
            self._free.append(t)

    def free_many(self, *temps: Optional[str]) -> None:
        for t in temps:
            self.free(t)


# =========================================================
# Generador TAC
# =========================================================
class TACGeneratorVisitor(CompiscriptVisitor):
    # -----------------------------------------------------
    # Infraestructura
    # -----------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.code: List[str] = []
        self.label_count: int = 0
        self.break_stack: List[str] = []
        self.continue_stack: List[str] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.return_seen: bool = False
        self.tm = TempManager()

    # ---- utilidades base
    def emit(self, line: str) -> None:
        self.code.append(line)

    def new_temp(self) -> str:
        return self.tm.new()

    def new_label(self, prefix: str = "L") -> str:
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    # ---- Peephole: elimina copias triviales y coalesce de temps
    def _peephole_copy_coalesce(self, lines: List[str]) -> List[str]:
        """
        Elimina copias triviales:
          tA = <RHS_simple>   # y tA se usa 1 sola vez -> inlining
        RHS_simple := (t#, id, literal)
        """
        temp_pat = re.compile(r"\bt\d+\b")
        assign_pat = re.compile(
            r"^\s*(t\d+)\s*=\s*([A-Za-z_]\w*|t\d+|\".*?\"|\'.*?\'|\d+(?:\.\d+)?)\s*$"
        )

        # Conteo de usos
        use_count: Dict[str, int] = {}
        for ln in lines:
            if ln.strip().endswith(":"):
                continue
            for tok in temp_pat.findall(ln):
                use_count[tok] = use_count.get(tok, 0) + 1

        to_delete = set()
        replacements: Dict[str, str] = {}

        # Detectar candidates (uso único)
        for idx, ln in enumerate(lines):
            s = ln.strip()
            if not s or s.endswith(":"):
                continue
            m = assign_pat.match(ln)
            if not m:
                continue
            dst, rhs = m.group(1), m.group(2)
            if dst == rhs:
                to_delete.add(idx)
                continue
            if use_count.get(dst, 0) == 1:
                replacements[dst] = rhs
                to_delete.add(idx)

        def replace_safe(s: str, repl: Dict[str, str]) -> str:
            if not repl:
                return s
            for k, v in repl.items():
                s = re.sub(rf"\b{re.escape(k)}\b", v, s)
            return s

        out: List[str] = []
        for i, ln in enumerate(lines):
            if i in to_delete:
                continue
            if ln.strip().endswith(":"):
                out.append(ln)
                continue
            out.append(replace_safe(ln, replacements))
        return out

    def get_code(self) -> str:
        return "\n".join(self._peephole_copy_coalesce(self.code))

    # =========================================================
    # Utilidades internas (parsing y helpers)
    # =========================================================
    @staticmethod
    def _is_temp(name: Optional[str]) -> bool:
        return isinstance(name, str) and name.startswith("t")

    @staticmethod
    def _looks_like_call_text(text: str) -> bool:
        return "(" in text and text.endswith(")")

    def _try_get_list(self, ctx, method_names: Sequence[str]) -> Optional[List]:
        """
        Devuelve la primera lista no vacía que encuentre llamando a
        cualquiera de los métodos indicados en method_names.
        """
        for name in method_names:
            fn = getattr(ctx, name, None)
            if fn is None or not callable(fn):
                continue
            try:
                res = fn()
            except TypeError:
                continue
            if isinstance(res, list) and len(res) > 0:
                return res
        return None

    def _child_op_between(self, ctx, left_term_index: int, right_term_index: int) -> str:
        """
        Recupera el operador textual entre dos subnodos hermanos.
        """
        try:
            pos = 2 * (left_term_index + 1) - 1
            if 0 <= pos < ctx.getChildCount():
                return ctx.getChild(pos).getText()
        except Exception:
            pass
        try:
            txt = ctx.getText()
            for tok in ["||", "&&", "==", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/", "%"]:
                if tok in txt:
                    return tok
        except Exception:
            pass
        return "?"

    # ---------- props y llamadas ----------
    def gen_getprop(self, base: str, prop: str) -> str:
        t = self.new_temp()
        self.emit(f"{t} = getprop {base}, {prop}")
        return t

    def gen_setprop(self, base: str, prop: str, val: str) -> None:
        self.emit(f"setprop {base}, {prop}, {val}")

    # ---------- recolectar argumentos desde el ctx (si la regla existe) ----------
    def _collect_args_from_ctx(self, ctx) -> List:
        cand = [
            ("arguments", "expression"),
            ("argumentList", "expression"),
            ("args", "expression"),
        ]
        for getter, _ in cand:
            g = getattr(ctx, getter, None)
            if not g:
                continue
            try:
                node = g()
                if not node:
                    continue
                try:
                    items = node.expression()
                    if isinstance(items, list):
                        return items
                    if items is not None:
                        return [items]
                except Exception:
                    pass
            except Exception:
                pass
        return []

    # ---------- Emisores de llamadas (mejorados) ----------
    def _emit_function_call(self, name: str, arg_nodes: List) -> str:
        """
        Llamada a función global:
          param argN
          ...
          t = call name, N
        """
        vals: List[str] = [self.visit(n) for n in arg_nodes]
        for v in reversed(vals):
            self.emit(f"param {v}")
            self.tm.free(v)
        t = self.new_temp()
        self.emit(f"{t} = call {name}, {len(vals)}")
        return t

    def _emit_method_call(self, recv: str, meth: str, arg_nodes: List) -> str:
        """
        Llamada a método (this como último param):
          param argN
          ...
          param recv
          t = call method meth, N+1
        """
        vals: List[str] = [self.visit(n) for n in arg_nodes]
        for v in reversed(vals):
            self.emit(f"param {v}")
            self.tm.free(v)
        self.emit(f"param {recv}")
        t = self.new_temp()
        self.emit(f"{t} = call method {meth}, {len(vals)+1}")
        return t

    def _split_args_text(self, inner: str) -> List[str]:
        """
        Parte 'a, b, c' en argumentos a nivel tope.
        Respeta paréntesis y comillas.
        """
        args, buf = [], []
        depth = 0
        in_str: Optional[str] = None
        i = 0
        while i < len(inner):
            ch = inner[i]
            if in_str:
                buf.append(ch)
                if ch == in_str:
                    in_str = None
                elif ch == "\\" and i + 1 < len(inner):
                    i += 1
                    buf.append(inner[i])
            else:
                if ch in ("'", '"'):
                    in_str = ch
                    buf.append(ch)
                elif ch == "(":
                    depth += 1
                    buf.append(ch)
                elif ch == ")":
                    depth = max(0, depth - 1)
                    buf.append(ch)
                elif ch == "," and depth == 0:
                    arg = "".join(buf).strip()
                    if arg:
                        args.append(arg)
                    buf = []
                else:
                    buf.append(ch)
            i += 1
        last = "".join(buf).strip()
        if last:
            args.append(last)
        return args

    def _normalize_value_from_node(self, node, text_value: str) -> str:
        """
        Si text_value parece 'foo(...)' o 'obj.m(...)', generar param/call.
        Intenta obtener args desde el nodo; si no, cae a split textual.
        """
        if not isinstance(text_value, str):
            return text_value
        if not self._looks_like_call_text(text_value):
            return text_value

        callee = text_value.split("(", 1)[0]
        # NEW: detectar 'new Clase(...)'
        if callee.strip().startswith("new "):
            try:
                class_name = callee.strip()[len("new "):].strip()
                args_nodes = self._collect_args_from_ctx(node)
                if not args_nodes:
                    inner_text = text_value[text_value.find("(") + 1:text_value.rfind(")")]
                    arg_texts = [a for a in self._split_args_text(inner_text) if a]
                    # materializar args textuales
                    args_nodes = []
                    for a in arg_texts:
                        tmp = self.new_temp()
                        self.emit(f"{tmp} = {a}")
                        args_nodes.append(tmp)
                return self._emit_new_object(class_name, args_nodes)
            except Exception:
                pass

        args_nodes = self._collect_args_from_ctx(node)

        # Camino normal con nodos de argumentos
        if args_nodes:
            if "." in callee:
                recv, meth = callee.split(".", 1)
                return self._emit_method_call(recv, meth, args_nodes)
            return self._emit_function_call(callee, args_nodes)

        # Fallback textual
        try:
            inner_text = text_value[text_value.find("(") + 1:text_value.rfind(")")]
        except Exception:
            inner_text = ""
        arg_texts = [a for a in self._split_args_text(inner_text) if a]

        is_method = False
        recv = meth = None
        if "." in callee:
            recv, meth = callee.split(".", 1)
            is_method = True

        # Emitir params
        for a in reversed(arg_texts):
            tmp = self.new_temp()
            self.emit(f"{tmp} = {a}")
            self.emit(f"param {tmp}")
            self.tm.free(tmp)

        if is_method:
            self.emit(f"param {recv}")

        out = self.new_temp()
        argc = len(arg_texts) + (1 if is_method else 0)
        if is_method:
            self.emit(f"{out} = call method {meth}, {argc}")
        else:
            self.emit(f"{out} = call {callee}, {argc}")
        return out

    # ---------- NEW: Soporte de 'new Clase(...)' ----------
    def _emit_new_object(self, class_name: str, arg_nodes: List) -> str:
        """
        t_obj = Clase new N
        (opcional) t_dummy = call method constructor, N+1  (param this al final)
        """
        t_obj = self.new_temp()
        self.emit(f"{t_obj} = {class_name} new {len(arg_nodes)}")
        if arg_nodes:
            vals = [self.visit(n) for n in arg_nodes]
            for v in reversed(vals):
                self.emit(f"param {v}")
                self.tm.free(v)
            self.emit(f"param {t_obj}")
            t_dummy = self.new_temp()
            self.emit(f"{t_dummy} = call method constructor, {len(vals)+1}")
            self.tm.free(t_dummy)
        return t_obj

    # =========================================================
    # Plegado binario + actualización in-place del acumulador
    # =========================================================
    def _acc_init(self, first_val: str) -> str:
        if self._is_temp(first_val):
            return first_val
        acc = self.new_temp()
        self.emit(f"{acc} = {first_val}")
        return acc

    def _fold_binary(self, ctx, subrule_candidates: Sequence[str], allowed_ops: Sequence[str]) -> str:
        terms = self._try_get_list(ctx, subrule_candidates)

        def _op_inplace(acc: str, op: str, right: str) -> str:
            if self._is_temp(acc):
                self.emit(f"{acc} = {acc} {op} {right}")
                self.tm.free(right)
                return acc
            t = self.new_temp()
            self.emit(f"{t} = {acc} {op} {right}")
            self.tm.free(right)
            return t

        # Fallback: recorrer hijos con accept
        if not terms:
            children_rules = [ctx.getChild(i) for i in range(ctx.getChildCount())]
            children_rules = [c for c in children_rules if hasattr(c, "accept")]
            if not children_rules:
                tmp = self.new_temp()
                self.emit(f"{tmp} = {ctx.getText()}")
                return tmp

            first_node = children_rules[0]
            first_raw = self.visit(first_node)
            first = self._normalize_value_from_node(first_node, first_raw)
            acc = self._acc_init(first)

            for i in range(1, len(children_rules)):
                op = self._child_op_between(ctx, i - 1, i)
                if op not in allowed_ops:
                    op = allowed_ops[0] if allowed_ops else op
                right_node = children_rules[i]
                right_raw = self.visit(right_node)
                right = self._normalize_value_from_node(right_node, right_raw)
                acc = _op_inplace(acc, op, right)
            return acc

        # Caso "normal": términos explícitos
        first_node = terms[0]
        first_raw = self.visit(first_node)
        first = self._normalize_value_from_node(first_node, first_raw)
        acc = self._acc_init(first)

        expected = 2 * len(terms) - 1
        for i in range(1, len(terms)):
            right_node = terms[i]
            right_raw = self.visit(right_node)
            right = self._normalize_value_from_node(right_node, right_raw)

            op = None
            if ctx.getChildCount() >= expected:
                try:
                    op = ctx.getChild(2 * i - 1).getText()
                except Exception:
                    op = None
            if op not in allowed_ops:
                op = allowed_ops[0] if allowed_ops else op or "?"
            acc = _op_inplace(acc, op, right)
        return acc

    # =========================================================
    # Lógica con cortocircuito
    # =========================================================
    def _gen_or_short_circuit(self, terms: List) -> str:
        result = self.new_temp()
        self.emit(f"{result} = 0")
        l_true = self.new_label("L")
        l_end = self.new_label("L")
        for term in terms:
            v = self.visit(term)
            v = self._normalize_value_from_node(term, v)
            self.emit(f"if {v} goto {l_true}")
            self.tm.free(v)
        self.emit(f"goto {l_end}")
        self.emit(f"{l_true}:")
        self.emit(f"{result} = 1")
        self.emit(f"{l_end}:")
        return result

    def _gen_and_short_circuit(self, terms: List) -> str:
        result = self.new_temp()
        self.emit(f"{result} = 1")
        l_false = self.new_label("L")
        l_end = self.new_label("L")
        for term in terms:
            v = self.visit(term)
            v = self._normalize_value_from_node(term, v)
            self.emit(f"if {v} == 0 goto {l_false}")
            self.tm.free(v)
        self.emit(f"goto {l_end}")
        self.emit(f"{l_false}:")
        self.emit(f"{result} = 0")
        self.emit(f"{l_end}:")
        return result

    # =========================================================
    # Literales, identificadores, paréntesis, etc.
    # =========================================================
    def visitIdentifierExpr(self, ctx):
        return ctx.getText()

    def visitIdPrimary(self, ctx):
        return ctx.getText()

    def visitId(self, ctx):
        return ctx.getText()

    def visitPrimaryIdentifier(self, ctx):
        return ctx.getText()

    def visitLiteralExpr(self, ctx):
        value = ctx.getText()
        t = self.new_temp()
        self.emit(f"{t} = {value}")
        return t

    def visitNumberLiteral(self, ctx):
        value = ctx.getText()
        t = self.new_temp()
        self.emit(f"{t} = {value}")
        return t

    def visitStringLiteral(self, ctx):
        value = ctx.getText()
        t = self.new_temp()
        self.emit(f"{t} = {value}")
        return t

    def visitBooleanLiteral(self, ctx):
        value = ctx.getText()
        t = self.new_temp()
        self.emit(f"{t} = {value}")
        return t

    def visitParenExpr(self, ctx):
        try:
            return self.visit(ctx.getChild(1))
        except Exception:
            return self.visitChildren(ctx)

    def visitPrimaryExpr(self, ctx):
        """
        Soporta:
          - (expr)
          - literales e id simples
          - obj.prop     -> getprop
          - llamadas     -> param/call (func o método)
          - new Clase()  -> new + opcional constructor
        """
        if ctx.getChildCount() == 3 and str(ctx.getChild(0).getText()) == "(":
            return self.visit(ctx.getChild(1))

        text = ctx.getText()

        def _looks_str(s: str) -> bool:
            return (len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")))

        def _looks_num(s: str) -> bool:
            try:
                float(s)
                return True
            except Exception:
                return False

        if ctx.getChildCount() == 1:
            if _looks_str(text) or _looks_num(text):
                t = self.new_temp()
                self.emit(f"{t} = {text}")
                return t
            # obj.prop directo
            if "." in text and "(" not in text and "[" not in text:
                base, prop = text.split(".", 1)
                return self.gen_getprop(base, prop)
            return text

        # new Clase(args)
        if text.startswith("new "):
            try:
                header, tail = text.split("(", 1)
                class_name = header.replace("new", "", 1).strip()
                arg_nodes = self._collect_args_from_ctx(ctx)
                if not arg_nodes and ")" in tail:
                    inner = tail[:tail.rfind(")")]
                    arg_texts = [a for a in self._split_args_text(inner) if a]
                    arg_nodes = []
                    for a in arg_texts:
                        tmp = self.new_temp()
                        self.emit(f"{tmp} = {a}")
                        arg_nodes.append(tmp)
                return self._emit_new_object(class_name, arg_nodes)
            except Exception:
                pass

        # llamadas (función o método)
        if "(" in text and text.endswith(")"):
            args_nodes = self._collect_args_from_ctx(ctx)
            callee = text.split("(", 1)[0]
            if "." in callee:
                recv, meth = callee.split(".", 1)
                return self._emit_method_call(recv, meth, args_nodes)
            return self._emit_function_call(callee, args_nodes)

        # acceso obj.prop detectado por texto (evitar literales)
        if "." in text and "(" not in text and "[" not in text and not _looks_str(text):
            base, prop = text.split(".", 1)
            return self.gen_getprop(base, prop)

        t = self.new_temp()
        self.emit(f"{t} = {text}")
        return t

    # =========================================================
    # Aritmética y lógica
    # =========================================================
    def visitAdditiveExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=["multiplicativeExpr", "term", "unaryExpr", "factor", "primaryExpr", "expr"],
            allowed_ops=["+", "-"],
        )

    def visitMultiplicativeExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=["unaryExpr", "factor", "primaryExpr", "powerExpr", "expr"],
            allowed_ops=["*", "/", "%"],
        )

    def visitEqualityExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=["relationalExpr", "additiveExpr", "expr"],
            allowed_ops=["==", "!="],
        )

    def visitRelationalExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=["additiveExpr", "expr"],
            allowed_ops=["<", "<=", ">", ">="],
        )

    def visitLogicalOrExpr(self, ctx):
        terms = self._try_get_list(ctx, [
            "logicalAndExpr", "equalityExpr", "relationalExpr", "additiveExpr", "expr"
        ])
        if terms and len(terms) > 1:
            return self._gen_or_short_circuit(terms)
        return self._fold_binary(
            ctx,
            subrule_candidates=["logicalAndExpr", "equalityExpr", "relationalExpr", "additiveExpr", "expr"],
            allowed_ops=["||", "or"]
        )

    def visitLogicalAndExpr(self, ctx):
        terms = self._try_get_list(ctx, [
            "equalityExpr", "relationalExpr", "additiveExpr", "expr"
        ])
        if terms and len(terms) > 1:
            return self._gen_and_short_circuit(terms)
        return self._fold_binary(
            ctx,
            subrule_candidates=["equalityExpr", "relationalExpr", "additiveExpr", "expr"],
            allowed_ops=["&&", "and"]
        )

    def visitUnaryExpr(self, ctx):
        try:
            if ctx.getChildCount() >= 2 and str(ctx.getChild(0).getText()) == "!":
                val = self.visit(ctx.getChild(1))
                t = self.new_temp()
                self.emit(f"{t} = ! {val}")
                self.tm.free(val)
                return t
        except Exception:
            pass
        try:
            for i in range(ctx.getChildCount()):
                ch = ctx.getChild(i)
                if hasattr(ch, "accept"):
                    return self.visit(ch)
        except Exception:
            pass
        return self.visitChildren(ctx)

    # =========================================================
    # Asignación
    # =========================================================
    def visitAssignment(self, ctx):
        # RHS
        if hasattr(ctx, "expr"):
            try:
                right_node = ctx.expr()
            except Exception:
                try:
                    right_node = ctx.expr(0)
                except Exception:
                    right_node = ctx.getChild(2)
        else:
            right_node = ctx.getChild(2)
        right_raw = self.visit(right_node)
        right = self._normalize_value_from_node(right_node, right_raw)

        # LHS id directo
        try:
            if hasattr(ctx, "Identifier") and ctx.Identifier() is not None:
                left_text = ctx.Identifier().getText()
                self.emit(f"{left_text} = {right}")
                self.tm.free(right)
                return left_text
        except Exception:
            pass

        # LHS textual
        lhs_text = ctx.getChild(0).getText()

        # obj.prop
        if "." in lhs_text and "[" not in lhs_text and "(" not in lhs_text:
            base, prop = lhs_text.split(".", 1)
            self.gen_setprop(base, prop, right)
            self.tm.free(right)
            return lhs_text

        # arr[idx] (placeholder)
        if "[" in lhs_text and "]" in lhs_text:
            base_name = lhs_text.split("[", 1)[0]
            idx_t = self.new_temp()
            self.emit(f"{idx_t} = /*idx*/")
            self.emit(f"setelem {base_name}, {idx_t}, {right}")
            self.tm.free_many(idx_t, right)
            return lhs_text

        # no asignable
        if "(" in lhs_text or ")" in lhs_text:
            raise RuntimeError("LHS no asignable (llamada/expresión)")

        # id simple
        self.emit(f"{lhs_text} = {right}")
        self.tm.free(right)
        return lhs_text

    def visitAssignmentStmt(self, ctx):
        return self.visitAssignment(ctx)

    # =========================================================
    # Control de flujo
    # =========================================================
    def visitIfStatement(self, ctx):
        cond = self.visit(ctx.expression())
        cond = self._normalize_value_from_node(ctx.expression(), cond)
        l_else = self.new_label()
        l_end = self.new_label()

        self.emit(f"if {cond} == 0 goto {l_else}")
        self.tm.free(cond)

        self.visit(ctx.block(0))

        if ctx.block(1):
            self.emit(f"goto {l_end}")
            self.emit(f"{l_else}:")
            self.visit(ctx.block(1))
            self.emit(f"{l_end}:")
        else:
            self.emit(f"{l_else}:")

    def visitDoWhileStatement(self, ctx):
        l_begin = self.new_label()
        self.emit(f"{l_begin}:")
        self.visit(ctx.block())
        cond = self.visit(ctx.expression())
        cond = self._normalize_value_from_node(ctx.expression(), cond)
        self.emit(f"if {cond} != 0 goto {l_begin}")
        self.tm.free(cond)

    def visitForStatement(self, ctx):
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())

        l_begin = self.new_label()
        l_end = self.new_label()

        self.emit(f"{l_begin}:")
        if ctx.expression(0):
            cond = self.visit(ctx.expression(0))
            cond = self._normalize_value_from_node(ctx.expression(0), cond)
            self.emit(f"if {cond} == 0 goto {l_end}")
            self.tm.free(cond)

        self.visit(ctx.block())

        if ctx.expression(1):
            inc_v = self.visit(ctx.expression(1))
            inc_v = self._normalize_value_from_node(ctx.expression(1), inc_v)
            self.tm.free(inc_v)

        self.emit(f"goto {l_begin}")
        self.emit(f"{l_end}:")

    def visitBreakStatement(self, ctx):
        if not self.break_stack:
            return
        self.emit(f"goto {self.break_stack[-1]}")

    def visitContinueStatement(self, ctx):
        if not self.continue_stack:
            return
        self.emit(f"goto {self.continue_stack[-1]}")

    def visitWhileStatement(self, ctx):
        l_begin = self.new_label()
        l_end = self.new_label()
        self.continue_stack.append(l_begin)
        self.break_stack.append(l_end)

        self.emit(f"{l_begin}:")
        cond = self.visit(ctx.expression())
        cond = self._normalize_value_from_node(ctx.expression(), cond)
        self.emit(f"if {cond} == 0 goto {l_end}")
        self.tm.free(cond)
        self.visit(ctx.block())
        self.emit(f"goto {l_begin}")
        self.emit(f"{l_end}:")
        self.continue_stack.pop()
        self.break_stack.pop()

    # =========================================================
    # Funciones / Métodos / Clases
    # =========================================================
    def _emit_frame_if_available(self, ctx):
        """
        Imprime .frame/.endframe si el semántico dejó offsets en ctx.scope.symbols.
        Se asume convención: params [bp+], locales [bp-].
        """
        fn_scope = getattr(ctx, "scope", None)
        if not fn_scope or not hasattr(fn_scope, "symbols"):
            return
        try:
            symbols = list(getattr(fn_scope, "symbols").values())
        except Exception:
            symbols = []
        if not symbols:
            return

        self.emit(".frame")
        for s in symbols:
            name = getattr(s, "name", "sym")
            off = getattr(s, "offset", None)
            is_param = getattr(s, "is_param", False)
            if off is None:
                continue
            # convención simple: + para params, - para locals (palabras*4)
            base = "+{}".format((off + 1) * 4) if is_param else "-{}".format((off + 1) * 4)
            tag = "param" if is_param else "local"
            self.emit(f".{tag} {name}, [bp{base}]")
        self.emit(".endframe")
    def visitFunctionDeclaration(self, ctx):
        """
        Prologo de función/método con:
        - p_* = LoadParam i
        - this = LoadParam arity-1 (si es método; el receptor se pasa AL FINAL)
        - Inyección en constructor: setprop this, campo, p_campo (evita 'nombre = nombre')
        """
        # nombre
        try:
            fname = ctx.Identifier().getText()
        except Exception:
            fname = "function"

        # ¿es método? preferimos flag del semántico; si no, usamos current_class
        is_method = bool(getattr(ctx, "_has_this", False)) or (self.current_class is not None)
        qual = f"{self.current_class}.{fname}" if is_method and self.current_class else fname

        # parámetros crudos (por si necesitamos los nodos)
        params = []
        try:
            if ctx.parameters():
                params = list(ctx.parameters().parameter())
        except Exception:
            params = []

        # aridad (+1 por this si es método)
        arity = len(params) + (1 if is_method else 0)

        self.current_function = fname
        self.return_seen = False

        self.emit(f"FUNC {qual}_START:")
        self.emit(f"BeginFunc {fname} {arity}")
        self.emit(f"ActivationRecord {fname}")

        # Cargar parámetros p_* = LoadParam i
        renameds = []
        for i, p in enumerate(params):
            try:
                pname = p.Identifier().getText()
            except Exception:
                pname = f"p{i}"
            if not pname.startswith("p_"):
                pname = f"p_{pname}"
            self.emit(f"{pname} = LoadParam {i}")
            renameds.append(pname)

        # this desde el último índice si es método
        if is_method:
            self.emit(f"this = LoadParam {arity - 1}")

        # Inyección especial para constructor: mapear p_<x> -> this.<x>
        if fname == "constructor" and is_method and renameds:
            for rp in renameds:
                base = rp[2:] if rp.startswith("p_") else rp
                self.emit(f"setprop this, {base}, {rp}")

        # (opcional) frame con offsets
        try:
            self._emit_frame_if_available(ctx)
        except Exception:
            pass

        # cuerpo
        self.visit(ctx.block())

        # return implícito si no hubo
        if not self.return_seen:
            self.emit("return")

        self.emit(f"FUNC {qual}_END:")
        self.emit(f"EndFunc {fname}")

        self.current_function = None
        self.return_seen = False
        return None

    def visitCallExpr(self, ctx):
        """
        Soporta:
          - foo(a,b)
          - obj.m(a,b)
        """
        full = ctx.getText()
        callee = full.split("(", 1)[0]
        args = ctx.arguments().expression() if ctx.arguments() else []

        arg_vals: List[str] = [self.visit(arg) for arg in args]

        if "." in callee:
            recv, meth = callee.split(".", 1)
            for v in reversed(arg_vals):
                self.emit(f"param {v}")
                self.tm.free(v)
            self.emit(f"param {recv}")
            tmp = self.new_temp()
            self.emit(f"{tmp} = call method {meth}, {len(arg_vals)+1}")
            return tmp

        for v in reversed(arg_vals):
            self.emit(f"param {v}")
            self.tm.free(v)
        tmp = self.new_temp()
        self.emit(f"{tmp} = call {callee}, {len(arg_vals)}")
        return tmp

    def visitClassDecl(self, ctx):
        """
        Envuelve los miembros de clase con etiquetas.
        Si el semántico dejó offsets de campos en ctx.scope.symbols,
        puedes imprimirlos como .field (+offset) aquí.
        """
        try:
            cname = ctx.Identifier().getText()
        except Exception:
            cname = "Class"

        # etiqueta de clase (opcional)
        self.emit(f"CLASS_{cname}_START:")

        # (Opcional) listar campos con offsets si existen
        class_scope = getattr(ctx, "scope", None)
        if class_scope and hasattr(class_scope, "symbols"):
            try:
                fields = []
                for sym in class_scope.symbols.values():
                    off = getattr(sym, "offset", None)
                    if isinstance(off, int) and off >= 0:
                        fields.append(sym)
                if fields:
                    fields.sort(key=lambda s: s.offset)
                    for s in fields:
                        self.emit(f".field {s.name}, +{s.offset * 4}")
            except Exception:
                pass

        prev = self.current_class
        self.current_class = cname
        for ch in ctx.children or []:
            if hasattr(ch, "accept"):
                self.visit(ch)
        self.current_class = prev

        self.emit(f"CLASS_{cname}_END:")
        return None

    # =========================================================
    # Return
    # =========================================================
    def visitReturnStatement(self, ctx):
        self.return_seen = True
        if ctx.expression():
            val_raw = self.visit(ctx.expression())
            try:
                val = self._normalize_value_from_node(ctx.expression(), val_raw)
            except Exception:
                val = val_raw
            self.emit(f"return {val}")
            if isinstance(val, str) and val.startswith("t"):
                self.tm.free(val)
        else:
            self.emit("return")
        return None

    # =========================================================
    # Terminal (fallback)
    # =========================================================
    def visitTerminal(self, node: TerminalNode):
        return node.getText()
