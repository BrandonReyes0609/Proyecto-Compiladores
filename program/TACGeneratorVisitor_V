"""
TACGeneratorVisitor.py
----------------------
Generación de Código Intermedio (TAC) para Compiscript.

Incluye implementación de las tareas asignadas a:
- Persona 1: Expresiones y Operaciones Básicas
- Persona 2: Operaciones Lógicas y Comparaciones

Extiende CompiscriptVisitor generado por ANTLR.
"""

import sys
import os

# 🔧 Hack para asegurar que Python encuentre la carpeta "scripts"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.CompiscriptVisitor import CompiscriptVisitor


class TACGeneratorVisitor(CompiscriptVisitor):
    def __init__(self):
        self.code = []        # Lista de instrucciones TAC
        self.temp_count = 0   # Contador de temporales
        self.label_count = 0  # Contador de etiquetas

    # =====================
    # Utilidades
    # =====================
    def new_temp(self):
        """Genera un nuevo temporal único"""
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        """Genera una nueva etiqueta única"""
        self.label_count += 1
        return f"L{self.label_count}"

    # =====================
    # Persona 1: Expresiones y Operaciones Básicas
    # =====================
    def visitLiteralExpr(self, ctx):
        """Genera TAC para un literal (número, string, booleano)"""
        value = ctx.getText()
        temp = self.new_temp()
        self.code.append(f"{temp} = {value}")
        return temp

    def visitAdditiveExpr(self, ctx):
        """Genera TAC para suma y resta"""
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        op = ctx.getChild(1).getText()  # '+' o '-'
        temp = self.new_temp()
        self.code.append(f"{temp} = {left} {op} {right}")
        return temp

    def visitMultiplicativeExpr(self, ctx):
        """Genera TAC para multiplicación, división, módulo"""
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        op = ctx.getChild(1).getText()  # '*', '/', '%'
        temp = self.new_temp()
        self.code.append(f"{temp} = {left} {op} {right}")
        return temp

    def visitAssignment(self, ctx):
        """Genera TAC para asignaciones"""
        left = ctx.Identifier().getText()
        right = self.visit(ctx.expr())
        self.code.append(f"{left} = {right}")
        return left

    # =====================
    # Persona 2: Operaciones Lógicas y Comparaciones
    # =====================
    def visitLogicalAndExpr(self, ctx):
        """Genera TAC para AND lógico"""
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        temp = self.new_temp()
        self.code.append(f"{temp} = {left} && {right}")
        return temp

    def visitLogicalOrExpr(self, ctx):
        """Genera TAC para OR lógico"""
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        temp = self.new_temp()
        self.code.append(f"{temp} = {left} || {right}")
        return temp

    def visitUnaryExpr(self, ctx):
        """Genera TAC para negación lógica"""
        if ctx.getChild(0).getText() == "!":
            expr = self.visit(ctx.expr())
            temp = self.new_temp()
            self.code.append(f"{temp} = !{expr}")
            return temp
        return self.visitChildren(ctx)

    def visitRelationalExpr(self, ctx):
        """Genera TAC para comparaciones (<, <=, >, >=)"""
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        op = ctx.getChild(1).getText()
        temp = self.new_temp()
        self.code.append(f"{temp} = {left} {op} {right}")
        return temp

    def visitEqualityExpr(self, ctx):
        """Genera TAC para igualdad y desigualdad (==, !=)"""
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        op = ctx.getChild(1).getText()
        temp = self.new_temp()
        self.code.append(f"{temp} = {left} {op} {right}")
        return temp

    # =====================
    # Utilidad: obtener TAC final
    # =====================
    def get_code(self):
        """Devuelve el código TAC generado como string"""
        return "\n".join(self.code)
