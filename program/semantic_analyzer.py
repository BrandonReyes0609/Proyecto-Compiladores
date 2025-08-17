# programm/semantic_analyzer.py

# Importa los archivos generados por ANTLR desde la carpeta 'scripts'
from scripts.CompiscriptParser import CompiscriptParser
from scripts.CompiscriptVisitor import CompiscriptVisitor

# Importa los módulos auxiliares desde la misma carpeta 'programm'
from custom_types import IntType, FloatType, BoolType, StringType, NullType, VoidType, FunctionType
from symbol_table import SymbolTable

class SemanticAnalyzer(CompiscriptVisitor):
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.errors = []
        self.current_function_return_type = None

    def _add_error(self, message, ctx):
        line = ctx.start.line
        column = ctx.start.column
        self.errors.append(f"Error en linea {line}:{column}: {message}")

    def enter_scope(self):
        self.current_scope = SymbolTable(parent=self.current_scope)

    def exit_scope(self):
        self.current_scope = self.current_scope.parent

    def visitBlock(self, ctx:CompiscriptParser.BlockContext):
        self.enter_scope()
        self.visitChildren(ctx)
        self.exit_scope()

    def visitLiteralExpr(self, ctx:CompiscriptParser.LiteralExprContext):
        text = ctx.getText()
        if text == 'true' or text == 'false': return BoolType
        if text.startswith('"'): return StringType
        if text == 'null': return NullType
        if ctx.Literal():
            literal_text = ctx.Literal().getText()
            if '.' in literal_text: return FloatType
            if literal_text.isdigit() or (literal_text.startswith('-') and literal_text[1:].isdigit()): return IntType
        return NullType

    def visitIdentifierExpr(self, ctx:CompiscriptParser.IdentifierExprContext):
        name = ctx.getText()
        symbol = self.current_scope.lookup(name)
        if symbol is None:
            self._add_error(f"'{name}' no ha sido declarado.", ctx)
            return NullType
        return symbol.type

    # --- CORREGIDO: Lógica de declaración con inferencia de tipos ---
    def visitVariableDeclaration(self, ctx:CompiscriptParser.VariableDeclarationContext):
        var_name = ctx.Identifier().getText()
        declared_type = None
        type_map = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType}
        if ctx.typeAnnotation():
            declared_type_str = ctx.typeAnnotation().type_().baseType().getText()
            declared_type = type_map.get(declared_type_str)
        if ctx.initializer():
            expr_type = self.visit(ctx.initializer().expression())
            if declared_type is None: declared_type = expr_type
            elif expr_type and expr_type != declared_type and not (declared_type == FloatType and expr_type == IntType):
                self._add_error(f"No se puede asignar tipo '{expr_type}' a variable de tipo '{declared_type}'.", ctx)
        if declared_type is None:
            self._add_error(f"No se pudo determinar el tipo de la variable '{var_name}'.", ctx); return
        if not self.current_scope.insert(var_name, declared_type, is_const=False):
            self._add_error(f"Identificador '{var_name}' ya ha sido declarado en este ámbito.", ctx)

    def visitConstantDeclaration(self, ctx:CompiscriptParser.ConstantDeclarationContext):
        # ... (La lógica anterior para constantes era correcta, se mantiene)
        if not ctx.expression(): self._add_error(f"La constante '{ctx.Identifier().getText()}' debe ser inicializada.", ctx); return
        const_name = ctx.Identifier().getText()
        if not ctx.typeAnnotation(): self._add_error(f"La constante '{const_name}' debe tener una anotación de tipo explícita.", ctx); return
        type_map = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType}
        declared_type_str = ctx.typeAnnotation().type_().baseType().getText()
        declared_type = type_map.get(declared_type_str)
        if not self.current_scope.insert(const_name, declared_type, is_const=True): self._add_error(f"Identificador '{const_name}' ya declarado.", ctx); return
        expr_type = self.visit(ctx.expression())
        if expr_type and expr_type != declared_type and not (declared_type == FloatType and expr_type == IntType): self._add_error(f"Tipo incompatible para constante '{const_name}'. Se esperaba '{declared_type}' pero se obtuvo '{expr_type}'.", ctx)

    # --- CORREGIDO: Lógica de Funciones y Parámetros ---
    def visitFunctionDeclaration(self, ctx:CompiscriptParser.FunctionDeclarationContext):
        func_name = ctx.Identifier().getText()
        type_map = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType, "void": VoidType}
        return_type = VoidType
        if ctx.type_():
            return_type_str = ctx.type_().baseType().getText()
            return_type = type_map.get(return_type_str, VoidType)

        param_types = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                param_type_str = param_ctx.type_().baseType().getText()
                param_types.append(type_map.get(param_type_str))
        
        func_type = FunctionType(return_type, param_types)
        if not self.current_scope.insert(func_name, func_type):
            self._add_error(f"Función o variable '{func_name}' ya ha sido declarada en este ámbito.", ctx)

        previous_return_type = self.current_function_return_type
        self.current_function_return_type = return_type
        self.enter_scope()

        if ctx.parameters():
            for i, param_ctx in enumerate(ctx.parameters().parameter()):
                param_name = param_ctx.Identifier().getText()
                self.current_scope.insert(param_name, param_types[i])

        self.visit(ctx.block())
        self.exit_scope()
        self.current_function_return_type = previous_return_type

    # --- CORREGIDO: Lógica de Expresiones con el bug de `isinstance` solucionado ---
    def visitMultiplicativeExpr(self, ctx:CompiscriptParser.MultiplicativeExprContext):
        if ctx.getChildCount() < 3: return self.visit(ctx.unaryExpr(0))
        left_type = self.visit(ctx.unaryExpr(0))
        right_type = self.visit(ctx.unaryExpr(1))
        if not (left_type in (IntType, FloatType) and right_type in (IntType, FloatType)):
            self._add_error(f"Operación aritmética ('*', '/', '%') solo válida entre integers/floats. Se obtuvo '{left_type}' y '{right_type}'.", ctx)
            return NullType
        return FloatType if left_type == FloatType or right_type == FloatType else IntType
    
        # --- NUEVO: Lógica para validar llamadas a funciones ---
    def visitReturnStatement(self, ctx:CompiscriptParser.ReturnStatementContext):
        if self.current_function_return_type is None:
            self._add_error("Declaración 'return' encontrada fuera de una función.", ctx); return
        if ctx.expression():
            returned_type = self.visit(ctx.expression())
            if self.current_function_return_type == VoidType: self._add_error(f"Una función de tipo 'void' no puede retornar un valor.", ctx)
            elif returned_type != self.current_function_return_type and not (self.current_function_return_type == FloatType and returned_type == IntType):
                self._add_error(f"El tipo de retorno no coincide. Se esperaba '{self.current_function_return_type}' pero se retornó '{returned_type}'.", ctx)
        elif self.current_function_return_type != VoidType:
            self._add_error(f"Una función de tipo '{self.current_function_return_type}' debe retornar un valor.", ctx)        
        
        
    def visitCallExpr(self, ctx:CompiscriptParser.CallExprContext):
        # El 'leftHandSide' del padre es la expresión completa, ej: 'saludar(...)'
        # El 'primaryAtom' de ese LHS es 'saludar'
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
            self._add_error(f"La función '{callee_name}' esperaba {len(func_type.param_types)} argumentos, pero recibió {len(arg_expressions)}.", ctx)
            return func_type.return_type # Devolver tipo esperado para no encadenar errores

        for i, arg_expr in enumerate(arg_expressions):
            arg_type = self.visit(arg_expr)
            expected_type = func_type.param_types[i]
            if arg_type != expected_type and not (expected_type == FloatType and arg_type == IntType):
                self._add_error(f"Argumento {i+1} de '{callee_name}' es incorrecto. Se esperaba '{expected_type}', pero se obtuvo '{arg_type}'.", arg_expr)

        return func_type.return_type
    

    def visitAdditiveExpr(self, ctx:CompiscriptParser.AdditiveExprContext):
        if ctx.getChildCount() < 3: return self.visit(ctx.multiplicativeExpr(0))
        left_type = self.visit(ctx.multiplicativeExpr(0))
        right_type = self.visit(ctx.multiplicativeExpr(1))
        op = ctx.getChild(1).getText()
        if op == '+':
            if left_type == StringType and right_type == StringType: return StringType
        if not (left_type in (IntType, FloatType) and right_type in (IntType, FloatType)):
            self._add_error(f"Operación aritmética ('{op}') solo válida entre números. Se obtuvo '{left_type}' y '{right_type}'.", ctx)
            return NullType
        return FloatType if left_type == FloatType or right_type == FloatType else IntType

    def visitRelationalExpr(self, ctx:CompiscriptParser.RelationalExprContext):
        if ctx.getChildCount() < 3: return self.visit(ctx.additiveExpr(0))
        left_type = self.visit(ctx.additiveExpr(0))
        right_type = self.visit(ctx.additiveExpr(1))
        if not (left_type in (IntType, FloatType) and right_type in (IntType, FloatType)):
            self._add_error(f"Operadores relacionales (<, <=, >, >=) solo aplican a números. Se obtuvo '{left_type}' y '{right_type}'.", ctx)
        return BoolType
        
    def visitEqualityExpr(self, ctx:CompiscriptParser.EqualityExprContext):
        if ctx.getChildCount() < 3: return self.visit(ctx.relationalExpr(0))
        left_type = self.visit(ctx.relationalExpr(0))
        right_type = self.visit(ctx.relationalExpr(1))
        compatible = (left_type == right_type) or (left_type in (IntType, FloatType) and right_type in (IntType, FloatType))
        if not compatible: self._add_error(f"Comparación '==' o '!=' entre tipos incompatibles: '{left_type}' y '{right_type}'.", ctx)
        return BoolType

    def visitLogicalAndExpr(self, ctx:CompiscriptParser.LogicalAndExprContext):
        if ctx.getChildCount() < 3: return self.visit(ctx.equalityExpr(0))
        left_type = self.visit(ctx.equalityExpr(0))
        right_type = self.visit(ctx.equalityExpr(1))
        if not (left_type == BoolType and right_type == BoolType):
            self._add_error(f"Operador '&&' requiere operandos boolean. Se obtuvo '{left_type}' y '{right_type}'.", ctx)
        return BoolType
        
    def visitLogicalOrExpr(self, ctx:CompiscriptParser.LogicalOrExprContext):
        if ctx.getChildCount() < 3: return self.visit(ctx.logicalAndExpr(0))
        left_type = self.visit(ctx.logicalAndExpr(0))
        right_type = self.visit(ctx.logicalAndExpr(1))
        if not (left_type == BoolType and right_type == BoolType):
            self._add_error(f"Operador '||' requiere operandos boolean. Se obtuvo '{left_type}' y '{right_type}'.", ctx)
        return BoolType

    def visitConditionalExpr(self, ctx: CompiscriptParser.ConditionalExprContext):
        return self.visit(ctx.logicalOrExpr()) # Por ahora, solo pasamos el control

    def visitIfStatement(self, ctx:CompiscriptParser.IfStatementContext):
        condition_type = self.visit(ctx.expression())
        if condition_type != BoolType:
            self._add_error(f"La condición de un 'if' debe ser de tipo boolean, pero se obtuvo '{condition_type}'.", ctx)
        self.visit(ctx.block(0))
        if ctx.block(1): self.visit(ctx.block(1))

    # --- Métodos Genéricos para Completar ---
    def visitExpression(self, ctx:CompiscriptParser.ExpressionContext):
        return self.visitChildren(ctx)

    def visitPrimaryExpr(self, ctx:CompiscriptParser.PrimaryExprContext):
        if ctx.getChildCount() == 3 and ctx.getChild(0).getText() == '(':
            return self.visit(ctx.expression())
        return self.visitChildren(ctx)