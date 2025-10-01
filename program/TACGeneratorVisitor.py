"""
TACGeneratorVisitor.py
----------------------
Generación de Código Intermedio (TAC) para Compiscript.

Incluye:
- (1) Reutilización de temporales (pool LIFO + actualización in-place del acumulador).
- (2) Reutilización de variables temporales vía peephole (elimina copias triviales tA=tB).
- Expansión robusta de llamadas (funciones y métodos) aunque la gramática no dispare visitCallExpr.
- Acceso a propiedades con getprop/setprop.
- LHS estrictamente asignable (id, obj.prop, arr[i]).
"""

import os
import sys
import re
from typing import List, Optional, Sequence

# Asegura importar los módulos generados por ANTLR desde la raíz del repo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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


class TACGeneratorVisitor(CompiscriptVisitor):
    # =========================================================
    # Infraestructura
    # =========================================================
    def __init__(self) -> None:
        super().__init__()
        self.code: List[str] = []
        self.temp_count: int = 0     # (delegamos en self.tm)
        self.label_count: int = 0
        self.break_stack: List[str] = []
        self.continue_stack: List[str] = []
        self.current_function: Optional[str] = None
        self.return_seen: bool = False
        self.tm = TempManager()
        self.current_class: Optional[str] = None  # clase actual (si aplica)

    def emit(self, line: str) -> None:
        self.code.append(line)

    def new_temp(self) -> str:
        return self.tm.new()

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    # ---- Peephole (punto 2) ----
    def _peephole_copy_coalesce(self, lines: List[str]) -> List[str]:
        """
        Elimina copias triviales: si hay 'tA = <RHS_simple>' y tA se usa una sola vez,
        sustituye ese uso por <RHS_simple> y borra la línea.
        - No toca definiciones de etiqueta 'Lx:' ni líneas vacías.
        - RHS_simple = un solo token (t#, id, literal).
        """
        temp_pat = re.compile(r"\bt\d+\b")
        assign_pat = re.compile(r"^\s*(t\d+)\s*=\s*([A-Za-z_]\w*|t\d+|\".*?\"|\'.*?\'|\d+(?:\.\d+)?)\s*$")

        # 1) Cuenta de usos por temp (en todas las líneas)
        use_count = {}
        for ln in lines:
            # ignora etiquetas
            if ln.strip().endswith(":"):
                continue
            for tok in temp_pat.findall(ln):
                use_count[tok] = use_count.get(tok, 0) + 1

        # 2) Detecta copias triviales candidatas
        to_delete = set()
        replacements = {}  # tA -> RHS

        for idx, ln in enumerate(lines):
            if ln.strip().endswith(":") or not ln.strip():
                continue
            m = assign_pat.match(ln)
            if not m:
                continue
            dst, rhs = m.group(1), m.group(2)
            if dst == rhs:
                # tA = tA => inútil
                to_delete.add(idx)
                continue

            # Si el destino aparece exactamente 1 vez (esta misma línea),
            # entonces la asignación no tiene consumidores: intentar inline del RHS.
            # Nota: use_count incluye esta línea (la aparición de dst), así que 1 significa solo aquí.
            if use_count.get(dst, 0) == 1:
                # Reemplazar apariciones futuras de dst por rhs (no habrá, pero por seguridad)
                replacements[dst] = rhs
                to_delete.add(idx)

        # 3) Aplica reemplazos de manera segura (token a token) solo en líneas posteriores
        def replace_tokenwise(s: str, repl_map: dict) -> str:
            if not repl_map:
                return s
            # Reemplazo por límites de palabra para t#
            for k, v in repl_map.items():
                s = re.sub(rf"\b{re.escape(k)}\b", v, s)
            return s

        new_lines: List[str] = []
        for i, ln in enumerate(lines):
            if i in to_delete:
                continue
            # No tocar etiquetas
            if ln.strip().endswith(":"):
                new_lines.append(ln)
                continue
            new_lines.append(replace_tokenwise(ln, replacements))

        return new_lines

    def get_code(self) -> str:
        # Ejecuta peephole antes de devolver
        optimized = self._peephole_copy_coalesce(self.code)
        return "\n".join(optimized)

    # =========================================================
    # Utilidades internas
    # =========================================================
    @staticmethod
    def _is_temp(name: Optional[str]) -> bool:
        return isinstance(name, str) and name.startswith("t")

    @staticmethod
    def _looks_like_call_text(text: str) -> bool:
        return "(" in text and text.endswith(")")

    def _try_get_list(self, ctx, method_names: Sequence[str]) -> Optional[List]:
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

    # ---------- helpers de props y llamadas ----------
    def gen_getprop(self, base: str, prop: str) -> str:
        t = self.new_temp()
        self.emit(f"{t} = getprop {base}, {prop}")
        return t

    def gen_setprop(self, base: str, prop: str, val: str) -> None:
        self.emit(f"setprop {base}, {prop}, {val}")

    def gen_call_method(self, class_and_name: str, this_val: str, arg_values: List[str]) -> str:
        for v in reversed(arg_values):
            self.emit(f"param {v}")
            self.tm.free(v)
        self.emit(f"param {this_val}")
        r = self.new_temp()
        self.emit(f"{r} = call method {class_and_name}, {len(arg_values)+1}")
        return r

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

    def _emit_function_call(self, name: str, arg_nodes: List) -> str:
        vals: List[str] = []
        for n in arg_nodes:
            v = self.visit(n)
            vals.append(v)
        for v in reversed(vals):
            self.emit(f"param {v}")
            self.tm.free(v)
        t = self.new_temp()
        self.emit(f"{t} = call {name}, {len(vals)}")
        return t

    def _emit_method_call(self, recv: str, meth: str, arg_nodes: List) -> str:
        vals: List[str] = []
        for n in arg_nodes:
            v = self.visit(n)
            vals.append(v)
        for v in reversed(vals):
            self.emit(f"param {v}")
            self.tm.free(v)
        self.emit(f"param {recv}")
        t = self.new_temp()
        self.emit(f"{t} = call method {meth}, {len(vals)+1}")
        return t

    def _split_args_text(self, inner: str) -> list[str]:
        """
        Divide 'a, b, c' en argumentos a nivel tope.
        Respeta paréntesis y comillas para no partir dentro de ellos.
        """
        args, buf = [], []
        depth = 0
        in_str = None  # '"', "'" o None
        i = 0
        while i < len(inner):
            ch = inner[i]
            if in_str:
                buf.append(ch)
                if ch == in_str:
                    in_str = None
                elif ch == "\\" and i + 1 < len(inner):
                    # escapa siguiente
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
        Si text_value parece una llamada cruda ('foo(...)'),
        conviértela a TAC con 'param/call'. Intenta obtener args desde el nodo.
        Si no hay nodos de args, hace fallback textual robusto (split por comas a nivel tope).
        """
        if not isinstance(text_value, str):
            return text_value
        if not self._looks_like_call_text(text_value):
            return text_value

        callee = text_value.split("(", 1)[0]
        args_nodes = self._collect_args_from_ctx(node)

        # Camino normal con nodos de argumentos
        if args_nodes:
            if "." in callee:
                recv, meth = callee.split(".", 1)
                return self._emit_method_call(recv, meth, args_nodes)
            return self._emit_function_call(callee, args_nodes)

        # --- Fallback textual: partir "a, b, c" a nivel tope y emitir params uno por uno ---
        try:
            inner_text = text_value[text_value.find("(")+1:text_value.rfind(")")]
        except Exception:
            inner_text = ""

        arg_texts = [a for a in self._split_args_text(inner_text) if a]

        # Si es método: separar receptor y método
        is_method = False
        recv = meth = None
        if "." in callee:
            recv, meth = callee.split(".", 1)
            is_method = True

        # 1) Emitir params de derecha a izquierda como hacemos en el camino normal
        #    Materializamos cada arg textual en un temp para no romper semántica.
        for a in reversed(arg_texts):
            tmp = self.new_temp()
            self.emit(f"{tmp} = {a}")
            self.emit(f"param {tmp}")
            self.tm.free(tmp)

        # 2) Param 'this' si es método
        if is_method:
            self.emit(f"param {recv}")

        # 3) Hacer la llamada con aridad correcta
        out = self.new_temp()
        argc = len(arg_texts) + (1 if is_method else 0)
        if is_method:
            self.emit(f"{out} = call method {meth}, {argc}")
        else:
            self.emit(f"{out} = call {callee}, {argc}")
        return out

    # =========================================================
    # Plegado binario con optimización in-place y normalización de llamadas
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

        # Fallback: recorrer hijos aceptables
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

        # Caso "normal"
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
        l_true = self.new_label()
        l_end = self.new_label()

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
        l_false = self.new_label()
        l_end = self.new_label()

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
    # Persona 1: Literales, identificadores, aritmética, asignación
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
        # '(' expr ')'
        if ctx.getChildCount() == 3 and str(ctx.getChild(0).getText()) == "(":
            return self.visit(ctx.getChild(1))

        text = ctx.getText()

        # Helpers para reconocer literales cuando no entran por reglas de literal
        def _looks_str(s: str) -> bool:
            return (len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")))
        def _looks_num(s: str) -> bool:
            try:
                float(s)
                return True
            except Exception:
                return False

        # id simple o literal aislado
        if ctx.getChildCount() == 1:
            # Si es literal -> materializa en temp (evita confundirlo con obj.prop)
            if _looks_str(text) or _looks_num(text):
                t = self.new_temp()
                self.emit(f"{t} = {text}")
                return t
            # ¿obj.prop sin subregla explícita?
            if "." in text and "(" not in text and "[" not in text:
                base, prop = text.split(".", 1)
                return self.gen_getprop(base, prop)
            return text

        # llamadas (función o método) aunque no venga por visitCallExpr
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

        # Fallback
        t = self.new_temp()
        self.emit(f"{t} = {text}")
        return t

    # Aritmética: +, -
    def visitAdditiveExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=[
                "multiplicativeExpr", "term", "unaryExpr", "factor", "primaryExpr", "expr"
            ],
            allowed_ops=["+", "-"],
        )

    # Aritmética: *, /, %
    def visitMultiplicativeExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=[
                "unaryExpr", "factor", "primaryExpr", "powerExpr", "expr"
            ],
            allowed_ops=["*", "/", "%"],
        )

    # Asignación: id = expr | obj.prop = expr | arr[i] = expr
    def visitAssignment(self, ctx):
        # RHS (normaliza llamadas si vienen como texto)
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

        # 1) Identifier
        try:
            if hasattr(ctx, "Identifier") and ctx.Identifier() is not None:
                left_text = ctx.Identifier().getText()
                self.emit(f"{left_text} = {right}")
                self.tm.free(right)
                return left_text
        except Exception:
            pass

        # 2) Texto genérico del LHS
        lhs_text = ctx.getChild(0).getText()

        # 2.1) member access: base.prop
        if "." in lhs_text and "[" not in lhs_text and "(" not in lhs_text:
            base, prop = lhs_text.split(".", 1)
            self.gen_setprop(base, prop, right)
            self.tm.free(right)
            return lhs_text

        # 2.2) array access: base[idx]  (placeholder de índice)
        if "[" in lhs_text and "]" in lhs_text:
            base_name = lhs_text.split("[", 1)[0]
            idx_t = self.new_temp()
            self.emit(f"{idx_t} = /*idx*/")
            self.emit(f"setelem {base_name}, {idx_t}, {right}")
            self.tm.free_many(idx_t, right)
            return lhs_text

        # 2.3) LHS no asignable (llamada/expresión)
        if "(" in lhs_text or ")" in lhs_text:
            raise RuntimeError("LHS no asignable (llamada/expresión)")

        # 2.4) Fallback id simple
        self.emit(f"{lhs_text} = {right}")
        self.tm.free(right)
        return lhs_text

    def visitAssignmentStmt(self, ctx):
        return self.visitAssignment(ctx)

    # =========================================================
    # Persona 2: Comparaciones y lógica (con cortocircuito)
    # =========================================================
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

    # ===== Terminales =====
    def visitTerminal(self, node: TerminalNode):
        return node.getText()

    # =========================================================
    # Persona 3: Control de flujo
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
    # Persona 4: Funciones / Métodos / Clases
    # =========================================================
    def visitFunctionDeclaration(self, ctx):
        fname = ctx.Identifier().getText()
        self.current_function = fname
        self.return_seen = False

        # ¿Es método (estamos dentro de una clase)?
        is_method = self.current_class is not None
        if is_method:
            qual = f"{self.current_class}.{fname}"
            self.emit(f"method {qual}")
        else:
            self.emit(f"func {fname}:")

        # ----- parámetros “lógicos” (mantener formato previo)
        if ctx.parameters():
            for p in ctx.parameters().parameter():
                pname = p.Identifier().getText()
                self.emit(f"param {pname}")

        # ======== NUEVO: .frame con base+desplazamiento ========
        # Si el analizador semántico adjuntó un 'scope' con offsets de símbolos:
        fn_scope = getattr(ctx, "scope", None)
        if fn_scope and hasattr(fn_scope, "symbols"):
            # Normalizamos a lista (ajusta si tu TS usa otra estructura)
            try:
                symbols = list(getattr(fn_scope, "symbols").values())
            except Exception:
                # por si fuera ya lista/dict-like
                symbols = list(fn_scope.symbols) if hasattr(fn_scope, "symbols") else []

            # Si tus offsets están en “slots/palabras”, pásalos a bytes (x4).
            # Si ya están en bytes, elimina el '* 4'.
            def off_bytes(sym):
                off = getattr(sym, "offset", None)
                return off * 4 if isinstance(off, int) else None

            self.emit(".frame")
            for s in symbols:
                ob = off_bytes(s)
                if ob is None:
                    continue
                tag = "param" if getattr(s, "is_param", False) else "local"
                # Convención ilustrativa: params [bp+X], locals [bp-X].
                # Aquí solo mostramos el desplazamiento con signo para propósitos de IC.
                sign = "+" if ob >= 0 else "-"
                self.emit(f".{tag} {getattr(s, 'name', 'sym')}, [bp{sign}{abs(ob)}]")
            self.emit(".endframe")
        # ======== FIN NUEVO ========

        # Cuerpo de la función
        self.visit(ctx.block())

        # return implícito si no se vio ninguno
        if not self.return_seen:
            self.emit("return")

        # Cierre
        if is_method:
            self.emit("endmethod")
        else:
            self.emit(f"endfunc {fname}")

        self.current_function = None


    def visitCallExpr(self, ctx):
        full = ctx.getText()
        callee = full.split("(", 1)[0]
        args = ctx.arguments().expression() if ctx.arguments() else []

        arg_vals: List[str] = []
        for arg in args:
            arg_vals.append(self.visit(arg))

        if "." in callee:
            recv, meth = callee.split(".", 1)
            qual = f"{meth}"
            return self.gen_call_method(qual, recv, arg_vals)

        for v in reversed(arg_vals):
            self.emit(f"param {v}")
            self.tm.free(v)
        tmp = self.new_temp()
        self.emit(f"{tmp} = call {callee}, {len(arg_vals)}")
        return tmp

    # ---------- Declaración de clases (ajusta el nombre de regla si difiere) ----------
    def visitClassDecl(self, ctx):
        try:
            cname = ctx.Identifier().getText()
        except Exception:
            cname = "Class"
        prev = self.current_class
        self.current_class = cname
        for ch in ctx.children or []:
            if hasattr(ch, "accept"):
                self.visit(ch)
        self.current_class = prev
        return None

    # =========================================================
    # Returns
    # =========================================================
    def visitReturnStatement(self, ctx):
        self.return_seen = True
        if ctx.expression():
            val = self.visit(ctx.expression())
            val = self._normalize_value_from_node(ctx.expression(), val)

            # 🔹 Si es un temporal o un nombre de variable, retorna directo
            if isinstance(val, str) and (val.startswith("t") or val.isidentifier()):
                self.emit(f"return {val}")
                return

            # 🔹 Si es un literal crudo, materialízalo
            if isinstance(val, str) and (val.startswith('"') or val.isdigit()):
                tmp = self.new_temp()
                self.emit(f"{tmp} = {val}")
                self.emit(f"return {tmp}")
                return

            # 🔹 En cualquier otro caso
            self.emit(f"return {val}")
        else:
            self.emit("return")

    # =========================================================
    # Clases (.class/.field con offsets si hay TS)
    # =========================================================
    def visitClassDecl(self, ctx):
        try:
            cname = ctx.Identifier().getText()
        except Exception:
            cname = "Class"

        # Anotación de clase y (si hay) offsets de campos
        self.emit(f".class {cname}")

        class_scope = getattr(ctx, "scope", None)
        if class_scope:
            # Si la TS trae offsets de campos, los ordenamos por offset
            fields = []
            for sym in class_scope.symbols.values():
                off = getattr(sym, "offset", None)
                # muchos analizadores asignan offsets >=0 a campos
                if isinstance(off, int) and off >= 0:
                    fields.append(sym)
            if fields:
                fields.sort(key=lambda s: s.offset)
                for s in fields:
                    self.emit(f".field {s.name}, +{s.offset*4}")

        self.emit(".endclass")

        # Procesar miembros de la clase (métodos, etc.)
        prev = self.current_class
        self.current_class = cname
        for ch in ctx.children or []:
            if hasattr(ch, "accept"):
                self.visit(ch)
        self.current_class = prev
        return None
