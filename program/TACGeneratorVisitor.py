"""
TACGeneratorVisitor.py
----------------------
Generación de Código Intermedio (TAC) para Compiscript.

Incluye las tareas de:
- Persona 1: Literales, identificadores, aritmética (+,-,*,/,%), asignaciones.
- Persona 2: Comparaciones (==, !=, <, <=, >, >=) y lógica (&&, ||, !) con cortocircuito + etiquetas.

El visitor es tolerante a variantes de gramática: prueba varios nombres
de subreglas y tiene fallbacks para evitar errores como
"Context object has no attribute 'expr'".
"""

import os
import sys
from typing import List, Optional, Sequence

# Asegura importar los módulos generados por ANTLR desde la raíz del repo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.CompiscriptVisitor import CompiscriptVisitor  # type: ignore
from antlr4 import TerminalNode  # type: ignore


class TACGeneratorVisitor(CompiscriptVisitor):
    # =========================================================
    # Infraestructura
    # =========================================================
    def __init__(self) -> None:
        super().__init__()
        self.code: List[str] = []
        self.temp_count: int = 0
        self.label_count: int = 0

    def emit(self, line: str) -> None:
        self.code.append(line)

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def get_code(self) -> str:
        return "\n".join(self.code)

    # =========================================================
    # Utilidades internas
    # =========================================================
    def _try_get_list(self, ctx, method_names: Sequence[str]) -> Optional[List]:
        """
        Intenta llamar a ctx.<method>() para varios nombres candidatos y
        devuelve la lista de sub-nodos si existe y no está vacía.
        """
        for name in method_names:
            fn = getattr(ctx, name, None)
            if fn is None or not callable(fn):
                continue
            try:
                res = fn()  # ANTLR en Python: sin argumento -> lista
            except TypeError:
                continue
            if isinstance(res, list) and len(res) > 0:
                return res
        return None

    def _child_op_between(self, ctx, left_term_index: int, right_term_index: int) -> str:
        """
        Heurística: intenta localizar el token operador textual que se encuentra
        entre dos términos. Si no lo logra, devuelve '?'.
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

    def _fold_binary(self, ctx, subrule_candidates: Sequence[str], allowed_ops: Sequence[str]) -> str:
        """
        Plegado genérico para expresiones binarias asociativas (p.ej. a+b-c).
        NO aplica cortocircuito. Para lógica, usar las variantes short-circuit.
        """
        terms = self._try_get_list(ctx, subrule_candidates)
        if not terms:
            # Fallback: recorrer hijos "aceptables"
            children_rules = [ctx.getChild(i) for i in range(ctx.getChildCount())]
            children_rules = [c for c in children_rules if hasattr(c, "accept")]
            if not children_rules:
                tmp = self.new_temp()
                self.emit(f"{tmp} = {ctx.getText()}")
                return tmp
            acc = self.visit(children_rules[0])
            for i in range(1, len(children_rules)):
                op = self._child_op_between(ctx, i - 1, i)
                if op not in allowed_ops:
                    op = allowed_ops[0] if allowed_ops else op
                right = self.visit(children_rules[i])
                t = self.new_temp()
                self.emit(f"{t} = {acc} {op} {right}")
                acc = t
            return acc

        # Caso "normal": term op term op term ...
        acc = self.visit(terms[0])
        expected = 2 * len(terms) - 1
        for i in range(1, len(terms)):
            right = self.visit(terms[i])
            op = None
            if ctx.getChildCount() >= expected:
                try:
                    op = ctx.getChild(2 * i - 1).getText()
                except Exception:
                    op = None
            if op not in allowed_ops:
                op = allowed_ops[0] if allowed_ops else op or "?"
            t = self.new_temp()
            self.emit(f"{t} = {acc} {op} {right}")
            acc = t
        return acc

    # ======== Utilidades para lógica con cortocircuito ========
    def _gen_or_short_circuit(self, terms: List) -> str:
        """
        Genera TAC para a || b || c con CORTOCIRCUITO.
        tmp = 0
        if a goto Ltrue
        if b goto Ltrue
        if c goto Ltrue
        goto Lend
        Ltrue:
        tmp = 1
        Lend:
        """
        result = self.new_temp()
        self.emit(f"{result} = 0")
        l_true = self.new_label()
        l_end = self.new_label()

        for term in terms:
            v = self.visit(term)
            # 'if v goto Ltrue'
            self.emit(f"if {v} goto {l_true}")

        self.emit(f"goto {l_end}")
        self.emit(f"{l_true}:")
        self.emit(f"{result} = 1")
        self.emit(f"{l_end}:")
        return result

    def _gen_and_short_circuit(self, terms: List) -> str:
        """
        Genera TAC para a && b && c con CORTOCIRCUITO.
        tmp = 1
        ifFalse a goto Lfalse
        ifFalse b goto Lfalse
        ifFalse c goto Lfalse
        goto Lend
        Lfalse:
        tmp = 0
        Lend:
        """
        result = self.new_temp()
        self.emit(f"{result} = 1")
        l_false = self.new_label()
        l_end = self.new_label()

        for term in terms:
            v = self.visit(term)
            # no asumimos 'ifFalse' nativo; usamos comparación == 0
            self.emit(f"if {v} == 0 goto {l_false}")

        self.emit(f"goto {l_end}")
        self.emit(f"{l_false}:")
        self.emit(f"{result} = 0")
        self.emit(f"{l_end}:")
        return result

    # =========================================================
    # Persona 1: Literales, identificadores, aritmética, asignación
    # =========================================================
    def visitIdentifierExpr(self, ctx):
        # id
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
        # ( expr )
        try:
            return self.visit(ctx.getChild(1))
        except Exception:
            return self.visitChildren(ctx)

    def visitPrimaryExpr(self, ctx):
        # por si la gramática usa primary -> '(' expr ')' | literal | id
        if ctx.getChildCount() == 3 and str(ctx.getChild(0).getText()) == "(":
            return self.visit(ctx.getChild(1))
        text = ctx.getText()
        if ctx.getChildCount() == 1:
            return text
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

    # Asignación (id = expr)
    def visitAssignment(self, ctx):
        try:
            left_text = ctx.Identifier().getText()
            right = None
            if hasattr(ctx, "expr"):
                try:
                    right = self.visit(ctx.expr())
                except Exception:
                    try:
                        right = self.visit(ctx.expr(0))
                    except Exception:
                        right = None
            if right is None:
                right = self.visit(ctx.getChild(2))
            self.emit(f"{left_text} = {right}")
            return left_text
        except Exception:
            try:
                left_text = ctx.getChild(0).getText()
                right_node = ctx.getChild(2)
                right = self.visit(right_node)
                self.emit(f"{left_text} = {right}")
                return left_text
            except Exception:
                return self.visitChildren(ctx)

    def visitAssignmentStmt(self, ctx):
        return self.visitAssignment(ctx)

    # =========================================================
    # Persona 2: Comparaciones y lógica (con cortocircuito)
    # =========================================================
    # Igualdad: ==, !=  (sin cortocircuito; devuelven 0/1)
    def visitEqualityExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=["relationalExpr", "additiveExpr", "expr"],
            allowed_ops=["==", "!="],
        )

    # Relacionales: <, <=, >, >=  (sin cortocircuito; devuelven 0/1)
    def visitRelationalExpr(self, ctx):
        return self._fold_binary(
            ctx,
            subrule_candidates=["additiveExpr", "expr"],
            allowed_ops=["<", "<=", ">", ">="],
        )

    # Lógica OR con cortocircuito
    def visitLogicalOrExpr(self, ctx):
        # Obtenemos lista de términos OR: logicalAndExpr | equalityExpr | ...
        terms = self._try_get_list(ctx, [
            "logicalAndExpr", "equalityExpr", "relationalExpr", "additiveExpr", "expr"
        ])
        if terms and len(terms) > 1:
            return self._gen_or_short_circuit(terms)
        # si no se detectó múltiple, plegado normal (aunque OR sin cortocircuito pierde semántica)
        return self._fold_binary(ctx,
                                 subrule_candidates=["logicalAndExpr", "equalityExpr", "relationalExpr", "additiveExpr", "expr"],
                                 allowed_ops=["||", "or"])

    # Lógica AND con cortocircuito
    def visitLogicalAndExpr(self, ctx):
        terms = self._try_get_list(ctx, [
            "equalityExpr", "relationalExpr", "additiveExpr", "expr"
        ])
        if terms and len(terms) > 1:
            return self._gen_and_short_circuit(terms)
        return self._fold_binary(ctx,
                                 subrule_candidates=["equalityExpr", "relationalExpr", "additiveExpr", "expr"],
                                 allowed_ops=["&&", "and"])

    # Negación lógica: !expr  (se produce 0/1)
    def visitUnaryExpr(self, ctx):
        try:
            if ctx.getChildCount() >= 2 and str(ctx.getChild(0).getText()) == "!":
                val = self.visit(ctx.getChild(1))
                t = self.new_temp()
                self.emit(f"{t} = ! {val}")
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


