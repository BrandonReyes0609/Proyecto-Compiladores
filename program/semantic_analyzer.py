# program/semantic_analyzer.py

# Importa los archivos generados por ANTLR desde la carpeta 'scripts'
from scripts.CompiscriptParser import CompiscriptParser
from scripts.CompiscriptVisitor import CompiscriptVisitor

# Tipos y tabla de símbolos
from custom_types import (
    IntType, FloatType, BoolType, StringType, NullType, VoidType, FunctionType
)
from symbol_table import SymbolTable


class SemanticAnalyzer(CompiscriptVisitor):
    """
    Analizador semántico con:
      - Comprobación de tipos y ámbitos (tu lógica original, corregida)
      - Estructura de scopes y símbolos exportable para el IDE (symbol_tree())
        * No depende de que SymbolTable tenga children/name/level.
    """
    def __init__(self):
        # Tabla de símbolos para búsquedas semánticas
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope

        # Errores recolectados
        self.errors = []

        # Retorno esperado en la función actual
        self.current_function_return_type = None

        # ---- Árbol de símbolos para el IDE (independiente de SymbolTable) ----
        self._sym_root = {
            "name": "global",
            "level": 0,
            "symbols": [],   # [{name,type,const,line,col}]
            "children": []   # nodos de scopes
        }
        self._sym_stack = [self._sym_root]  # pila paralela al scope semántico

    # ================= Utilidades de reporte / scopes =================
    def _add_error(self, message, ctx):
        line = ctx.start.line
        column = ctx.start.column
        self.errors.append(f"Error en linea {line}:{column}: {message}")

    def _push_scope(self, label, ctx=None):
        """Crea un scope semántico + un nodo de scope para el IDE."""
        # scope semántico
        self.current_scope = SymbolTable(parent=self.current_scope)

        # nodo para el IDE
        parent_node = self._sym_stack[-1]
        node = {
            "name": str(label),
            "level": parent_node["level"] + 1,
            "symbols": [],
            "children": []
        }
        parent_node["children"].append(node)
        self._sym_stack.append(node)

    def _pop_scope(self):
        """Sale del scope semántico + nodo del IDE."""
        # scope semántico
        self.current_scope = self.current_scope.parent
        # nodo IDE
        if len(self._sym_stack) > 1:
            self._sym_stack.pop()

    def _record_symbol(self, name, sym_type, is_const, line, col):
        """Registra el símbolo en el nodo de scope actual (para el IDE)."""
        node = self._sym_stack[-1]
        node["symbols"].append({
            "name": name,
            "type": self._tname(sym_type),
            "const": bool(is_const),
            "line": int(line) if line is not None else None,
            "col": int(col) if col is not None else None,
        })

    def _tname(self, t):
        """Nombre de tipo amigable para el IDE."""
        if t is IntType: return "integer"
        if t is FloatType: return "float"
        if t is BoolType: return "boolean"
        if t is StringType: return "string"
        if t is NullType: return "null"
        if t is VoidType: return "void"
        if isinstance(t, FunctionType):
            args = ", ".join(self._tname(p) for p in t.param_types)
            return f"fn({args}) -> {self._tname(t.return_type)}"
        return str(t)

    def symbol_tree(self):
        """Devuelve el árbol de símbolos jerárquico (para el IDE)."""
        return self._sym_root

    # ================= Scopes de bloque =================
    def enter_scope(self, label="block"):
        """Compat con tu código existente: crea sub-scope genérico."""
        self._push_scope(label)

    def exit_scope(self):
        self._pop_scope()

    def visitBlock(self, ctx: CompiscriptParser.BlockContext):
        self._push_scope(f"block@{ctx.start.line}:{ctx.start.column}", ctx)
        self.visitChildren(ctx)
        self._pop_scope()

    # ================= Expresiones base =================
    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        text = ctx.getText()
        if text == 'true' or text == 'false':
            return BoolType
        if text.startswith('"'):
            return StringType
        if text == 'null':
            return NullType
        if ctx.Literal():
            literal_text = ctx.Literal().getText()
            if '.' in literal_text:
                return FloatType
            if literal_text.isdigit() or (literal_text.startswith('-') and literal_text[1:].isdigit()):
                return IntType
        return NullType

    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.getText()
        symbol = self.current_scope.lookup(name)
        if symbol is None:
            self._add_error(f"'{name}' no ha sido declarado.", ctx)
            return NullType
        return symbol.type

    # ================= Declaraciones =================
    # Variables (con inferencia y chequeos)
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        var_name = ctx.Identifier().getText()
        declared_type = None
        line, col = ctx.start.line, ctx.start.column

        type_map = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType}
        if ctx.typeAnnotation():
            declared_type_str = ctx.typeAnnotation().type_().baseType().getText()
            declared_type = type_map.get(declared_type_str)

        if ctx.initializer():
            expr_type = self.visit(ctx.initializer().expression())
            if declared_type is None:
                declared_type = expr_type
            elif expr_type and expr_type != declared_type and not (declared_type == FloatType and expr_type == IntType):
                self._add_error(
                    f"No se puede asignar tipo '{expr_type}' a variable de tipo '{declared_type}'.", ctx
                )

        if declared_type is None:
            self._add_error(f"No se pudo determinar el tipo de la variable '{var_name}'.", ctx)
            return

        if not self.current_scope.insert(var_name, declared_type, is_const=False, line=line, col=col):
            self._add_error(f"Identificador '{var_name}' ya ha sido declarado en este ámbito.", ctx)
        else:
            self._record_symbol(var_name, declared_type, False, line, col)

    # Constantes
    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        if not ctx.expression():
            self._add_error(
                f"La constante '{ctx.Identifier().getText()}' debe ser inicializada.", ctx
            ); return

        const_name = ctx.Identifier().getText()
        line, col = ctx.start.line, ctx.start.column

        if not ctx.typeAnnotation():
            self._add_error(
                f"La constante '{const_name}' debe tener una anotación de tipo explícita.", ctx
            ); return

        type_map = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType}
        declared_type_str = ctx.typeAnnotation().type_().baseType().getText()
        declared_type = type_map.get(declared_type_str)

        if not self.current_scope.insert(const_name, declared_type, is_const=True, line=line, col=col):
            self._add_error(f"Identificador '{const_name}' ya declarado.", ctx); return
        else:
            self._record_symbol(const_name, declared_type, True, line, col)

        expr_type = self.visit(ctx.expression())
        if expr_type and expr_type != declared_type and not (declared_type == FloatType and expr_type == IntType):
            self._add_error(
                f"Tipo incompatible para constante '{const_name}'. Se esperaba '{declared_type}' pero se obtuvo '{expr_type}'.",
                ctx
            )

    # Funciones y parámetros
    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        func_name = ctx.Identifier().getText()
        type_map = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType, "void": VoidType}

        return_type = VoidType
        if ctx.type_():
            return_type_str = ctx.type_().baseType().getText()
            return_type = type_map.get(return_type_str, VoidType)

        param_types = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                p = param_ctx.type_().baseType().getText()
                param_types.append(type_map.get(p))

        func_type = FunctionType(return_type, param_types)

        # Declaramos el símbolo de la función en el scope actual
        if not self.current_scope.insert(func_name, func_type, line=ctx.start.line, col=ctx.start.column):
            self._add_error(f"Función o variable '{func_name}' ya ha sido declarada en este ámbito.", ctx)
        else:
            self._record_symbol(func_name, func_type, False, ctx.start.line, ctx.start.column)

        # Entramos al scope de la función
        previous_return_type = self.current_function_return_type
        self.current_function_return_type = return_type

        self._push_scope(f"fn {func_name}", ctx)

        # Parámetros como símbolos del scope de la función
        if ctx.parameters():
            for i, param_ctx in enumerate(ctx.parameters().parameter()):
                pname = param_ctx.Identifier().getText()
                ptype = param_types[i]
                # Insertar en tabla real
                self.current_scope.insert(pname, ptype, line=param_ctx.start.line, col=param_ctx.start.column)
                # Registrar en árbol para IDE
                self._record_symbol(pname, ptype, False, param_ctx.start.line, param_ctx.start.column)

        # Cuerpo
        self.visit(ctx.block())

        # Salir del scope de la función
        self._pop_scope()
        self.current_function_return_type = previous_return_type

    # ================= Expresiones aritméticas/lógicas =================
    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        if ctx.getChildCount() < 3:
            return self.visit(ctx.unaryExpr(0))
        left_type  = self.visit(ctx.unaryExpr(0))
        right_type = self.visit(ctx.unaryExpr(1))
        if not (left_type in (IntType, FloatType) and right_type in (IntType, FloatType)):
            self._add_error(
                "Operación aritmética ('*', '/', '%') solo válida entre integers/floats. "
                f"Se obtuvo '{left_type}' y '{right_type}'.", ctx
            )
            return NullType
        return FloatType if left_type == FloatType or right_type == FloatType else IntType

    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        if ctx.getChildCount() < 3:
            return self.visit(ctx.multiplicativeExpr(0))
        left_type  = self.visit(ctx.multiplicativeExpr(0))
        right_type = self.visit(ctx.multiplicativeExpr(1))
        op = ctx.getChild(1).getText()
        if op == '+':
            if left_type == StringType and right_type == StringType:
                return StringType
        if not (left_type in (IntType, FloatType) and right_type in (IntType, FloatType)):
            self._add_error(
                f"Operación aritmética ('{op}') solo válida entre números. "
                f"Se obtuvo '{left_type}' y '{right_type}'.", ctx
            )
            return NullType
        return FloatType if left_type == FloatType or right_type == FloatType else IntType

    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        if ctx.getChildCount() < 3:
            return self.visit(ctx.additiveExpr(0))
        left_type  = self.visit(ctx.additiveExpr(0))
        right_type = self.visit(ctx.additiveExpr(1))
        if not (left_type in (IntType, FloatType) and right_type in (IntType, FloatType)):
            self._add_error(
                "Operadores relacionales (<, <=, >, >=) solo aplican a números. "
                f"Se obtuvo '{left_type}' y '{right_type}'.", ctx
            )
        return BoolType

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        if ctx.getChildCount() < 3:
            return self.visit(ctx.relationalExpr(0))
        left_type  = self.visit(ctx.relationalExpr(0))
        right_type = self.visit(ctx.relationalExpr(1))
        compatible = (
            (left_type == right_type) or
            (left_type in (IntType, FloatType) and right_type in (IntType, FloatType))
        )
        if not compatible:
            self._add_error(
                f"Comparación '==' o '!=' entre tipos incompatibles: '{left_type}' y '{right_type}'.", ctx
            )
        return BoolType

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        if ctx.getChildCount() < 3:
            return self.visit(ctx.equalityExpr(0))
        left_type  = self.visit(ctx.equalityExpr(0))
        right_type = self.visit(ctx.equalityExpr(1))
        if not (left_type == BoolType and right_type == BoolType):
            self._add_error(
                f"Operador '&&' requiere operandos boolean. Se obtuvo '{left_type}' y '{right_type}'.", ctx
            )
        return BoolType

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        if ctx.getChildCount() < 3:
            return self.visit(ctx.logicalAndExpr(0))
        left_type  = self.visit(ctx.logicalAndExpr(0))
        right_type = self.visit(ctx.logicalAndExpr(1))
        if not (left_type == BoolType and right_type == BoolType):
            self._add_error(
                f"Operador '||' requiere operandos boolean. Se obtuvo '{left_type}' y '{right_type}'.", ctx
            )
        return BoolType

    def visitConditionalExpr(self, ctx: CompiscriptParser.ConditionalExprContext):
        # Por ahora, solo pasamos el control
        return self.visit(ctx.logicalOrExpr())

    # ================= Sentencias =================
    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        condition_type = self.visit(ctx.expression())
        if condition_type != BoolType:
            self._add_error(
                f"La condición de un 'if' debe ser de tipo boolean, pero se obtuvo '{condition_type}'.", ctx
            )
        self.visit(ctx.block(0))
        if ctx.block(1):
            self.visit(ctx.block(1))

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        if self.current_function_return_type is None:
            self._add_error("Declaración 'return' encontrada fuera de una función.", ctx)
            return
        if ctx.expression():
            returned_type = self.visit(ctx.expression())
            if self.current_function_return_type == VoidType:
                self._add_error("Una función de tipo 'void' no puede retornar un valor.", ctx)
            elif returned_type != self.current_function_return_type and not (
                self.current_function_return_type == FloatType and returned_type == IntType
            ):
                self._add_error(
                    f"El tipo de retorno no coincide. Se esperaba '{self.current_function_return_type}' "
                    f"pero se retornó '{returned_type}'.", ctx
                )
        elif self.current_function_return_type != VoidType:
            self._add_error(
                f"Una función de tipo '{self.current_function_return_type}' debe retornar un valor.", ctx
            )

    # Llamadas a funciones
    def visitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
        # El identificador está en el primaryAtom del leftHandSide padre.
        callee_name = ctx.parentCtx.primaryAtom().getText()
        symbol = self.current_scope.lookup(callee_name)

        if symbol is None:
            self._add_error(f"Función '{callee_name}' no ha sido declarada.", ctx.parentCtx.primaryAtom())
            return NullType

        if not isinstance(symbol.type, FunctionType):
            self._add_error(f"'{callee_name}' no es una función y no se puede llamar.", ctx.parentCtx.primaryAtom())
            return NullType

        func_type = symbol.type
        arg_expressions = ctx.arguments().expression() if ctx.arguments() else []

        if len(func_type.param_types) != len(arg_expressions):
            self._add_error(
                f"La función '{callee_name}' esperaba {len(func_type.param_types)} argumentos, "
                f"pero recibió {len(arg_expressions)}.", ctx
            )
            # Devolvemos el tipo esperado para no encadenar más errores
            return func_type.return_type

        for i, arg_expr in enumerate(arg_expressions):
            arg_type = self.visit(arg_expr)
            expected_type = func_type.param_types[i]
            if arg_type != expected_type and not (expected_type == FloatType and arg_type == IntType):
                self._add_error(
                    f"Argumento {i+1} de '{callee_name}' es incorrecto. "
                    f"Se esperaba '{expected_type}', pero se obtuvo '{arg_type}'.",
                    arg_expr
                )

        return func_type.return_type

    # ================= Pasarelas genéricas =================
    def visitExpression(self, ctx: CompiscriptParser.ExpressionContext):
        return self.visitChildren(ctx)

    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.getChildCount() == 3 and ctx.getChild(0).getText() == '(':
            return self.visit(ctx.expression())
        return self.visitChildren(ctx)
