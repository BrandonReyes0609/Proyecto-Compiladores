# program/semantic_analyzer.py

from scripts.CompiscriptParser import CompiscriptParser
from scripts.CompiscriptVisitor import CompiscriptVisitor

from custom_types import (
    IntType, FloatType, BoolType, StringType, NullType, VoidType,
    FunctionType, ClassType   # <<< AÑADIDO ClassType
)
from symbol_table import SymbolTable


class SemanticAnalyzer(CompiscriptVisitor):
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope

        self.errors = []
        self.current_function_return_type = None

        # <<< AÑADIDO: estado para clases >>>
        self.classes = {}          # "Persona" -> ClassType
        self.current_class = None  # ClassType o None
        self.in_class_body = False
        self.in_function = False   # para distinguir campos vs variables locales

        # ---- Árbol de símbolos para el IDE ----
        self._sym_root = {
            "name": "global",
            "level": 0,
            "symbols": [],
            "children": []
        }
        self._sym_stack = [self._sym_root]

    # ================= Utilidades =================
    def _add_error(self, message, ctx):
        line = ctx.start.line
        column = ctx.start.column
        self.errors.append(f"Error en linea {line}:{column}: {message}")

    def _push_scope(self, label, ctx=None):
        self.current_scope = SymbolTable(parent=self.current_scope)
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
        self.current_scope = self.current_scope.parent
        if len(self._sym_stack) > 1:
            self._sym_stack.pop()

    def _record_symbol(self, name, sym_type, is_const, line, col):
        node = self._sym_stack[-1]
        node["symbols"].append({
            "name": name,
            "type": self._tname(sym_type),
            "const": bool(is_const),
            "line": int(line) if line is not None else None,
            "col": int(col) if col is not None else None,
        })

    def _tname(self, t):
        if t is IntType: return "integer"
        if t is FloatType: return "float"
        if t is BoolType: return "boolean"
        if t is StringType: return "string"
        if t is NullType: return "null"
        if t is VoidType: return "void"
        if isinstance(t, ClassType):  # <<< nombre legible para clases
            return t.name
        if isinstance(t, FunctionType):
            args = ", ".join(self._tname(p) for p in t.param_types)
            return f"fn({args}) -> {self._tname(t.return_type)}"
        return str(t)

    def symbol_tree(self):
        return self._sym_root

    # ===== Helpers de clases =====
    def _resolve_type_token(self, name: str):
        """Resuelve nombre de tipo ('integer', 'Persona', etc.)"""
        prim = {"integer": IntType, "float": FloatType, "boolean": BoolType, "string": StringType, "void": VoidType}
        return prim.get(name) or self.classes.get(name)

    def _field_type(self, ctype: ClassType, field: str, ctx):
        t = ctype
        while t:
            if field in t.fields:
                return t.fields[field]
            t = t.base
        self._add_error(f"Campo '{field}' no existe en '{ctype.name}'.", ctx)
        return NullType

    def _method_type(self, ctype: ClassType, name: str, ctx):
        t = ctype
        while t:
            if name in t.methods:
                return t.methods[name]
            t = t.base
        self._add_error(f"Método '{name}' no existe en '{ctype.name}'.", ctx)
        return FunctionType(VoidType, [])

    # ================= Scopes de bloque =================
    def enter_scope(self, label="block"):
        self._push_scope(label)

    def exit_scope(self):
        self._pop_scope()

    def visitBlock(self, ctx: CompiscriptParser.BlockContext):
        self._push_scope(f"block@{ctx.start.line}:{ctx.start.column}", ctx)
        self.visitChildren(ctx)
        self._pop_scope()

    # ================= CLASES =================
    # Nota: asumo regla 'ClassDeclaration'; si tu regla se llama distinto,
    # cambia el nombre del método al que corresponda.
    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        # class Nombre [: Base]? { ... }
        name = None
        base = None
        try:
            name = ctx.Identifier(0).getText()
            if ctx.Identifier(1):  # herencia opcional
                base_name = ctx.Identifier(1).getText()
                base = self.classes.get(base_name)
                if base is None:
                    self._add_error(f"Clase base '{base_name}' no ha sido declarada.", ctx)
        except Exception:
            # Fallback por si la API del contexto difiere
            text = ctx.getText()
            # classNombre{...} o classNombre:Base{...}
            try:
                header = text.split("{", 1)[0]
                header = header.replace("class", "", 1)
                if ":" in header:
                    nm, bs = header.split(":", 1)
                    name = nm.strip()
                    base = self.classes.get(bs.strip())
                else:
                    name = header.strip()
            except Exception:
                name = "<anon-class>"

        ctype = self.classes.get(name)
        if not ctype:
            ctype = ClassType(name, base)
            self.classes[name] = ctype
        else:
            # si ya existía, actualiza base si procede
            if base and ctype.base is None:
                ctype.base = base

        prev_cls, prev_flag = self.current_class, self.in_class_body
        self.current_class = ctype
        self.in_class_body = True

        self._push_scope(f"class {name}", ctx)
        self.visitChildren(ctx)  # aquí caerán let/func members y se registran abajo
        self._pop_scope()

        self.current_class = prev_cls
        self.in_class_body = prev_flag
        return None

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
        if name == "this":  # <<< soporte de 'this'
            if self.current_class:
                return self.current_class
            self._add_error("'this' usado fuera de una clase.", ctx)
            return NullType
        symbol = self.current_scope.lookup(name)
        if symbol is None:
            self._add_error(f"'{name}' no ha sido declarado.", ctx)
            return NullType
        return symbol.type

    # ================= Declaraciones =================
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        var_name = ctx.Identifier().getText()
        declared_type = None
        line, col = ctx.start.line, ctx.start.column

        # tipo explícito (primitivo o clase)
        if ctx.typeAnnotation():
            declared_type_str = ctx.typeAnnotation().type_().baseType().getText()
            declared_type = self._resolve_type_token(declared_type_str)

        # CAMPO DE CLASE: let campo: T;  (no insertar en tabla global)
        if self.in_class_body and not self.in_function:
            if declared_type is None:
                self._add_error(f"No se pudo determinar el tipo del campo '{var_name}'.", ctx)
                return
            # registra campo en la clase actual
            self.current_class.fields[var_name] = declared_type
            self._record_symbol(var_name, declared_type, False, line, col)
            return

        # Variable local/global normal
        expr_type = None
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

        declared_type_str = ctx.typeAnnotation().type_().baseType().getText()
        declared_type = self._resolve_type_token(declared_type_str)

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

    # ===== Funciones y MÉTODOS =====
    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        func_name = ctx.Identifier().getText()
        # tipos primitivos + void + clases
        return_type = VoidType
        if ctx.type_():
            return_type_str = ctx.type_().baseType().getText()
            return_type = self._resolve_type_token(return_type_str) or VoidType

        param_types = []
        if ctx.parameters():
            for pctx in ctx.parameters().parameter():
                p = pctx.type_().baseType().getText()
                param_types.append(self._resolve_type_token(p))

        func_type = FunctionType(return_type, param_types)

        # ---- Caso método dentro de clase ----
        if self.in_class_body and not self.in_function:
            # Registrar método en la clase (no contaminar el global)
            if func_name in self.current_class.methods:
                self._add_error(f"Método '{func_name}' ya ha sido declarado en esta clase.", ctx)
            else:
                self.current_class.methods[func_name] = func_type
                self._record_symbol(func_name, func_type, False, ctx.start.line, ctx.start.column)

            # Entrar al scope del método
            prev_ret = self.current_function_return_type
            prev_in_func = self.in_function
            self.current_function_return_type = return_type
            self.in_function = True

            self._push_scope(f"method {func_name}", ctx)
            # (Opcional) insertar 'this' en el scope
            try:
                self.current_scope.insert("this", self.current_class, line=ctx.start.line, col=ctx.start.column)
            except Exception:
                pass

            # Parámetros
            if ctx.parameters():
                for i, pctx in enumerate(ctx.parameters().parameter()):
                    pname = pctx.Identifier().getText()
                    ptype = param_types[i]
                    self.current_scope.insert(pname, ptype, line=pctx.start.line, col=pctx.start.column)
                    self._record_symbol(pname, ptype, False, pctx.start.line, pctx.start.column)

            # Cuerpo
            self.visit(ctx.block())

            self._pop_scope()
            self.in_function = prev_in_func
            self.current_function_return_type = prev_ret
            return

        # ---- Función global normal (tu lógica original) ----
        if not self.current_scope.insert(func_name, func_type, line=ctx.start.line, col=ctx.start.column):
            self._add_error(f"Función o variable '{func_name}' ya ha sido declarada en este ámbito.", ctx)
        else:
            self._record_symbol(func_name, func_type, False, ctx.start.line, ctx.start.column)

        prev_ret = self.current_function_return_type
        prev_in_func = self.in_function
        self.current_function_return_type = return_type
        self.in_function = True

        self._push_scope(f"fn {func_name}", ctx)

        if ctx.parameters():
            for i, pctx in enumerate(ctx.parameters().parameter()):
                pname = pctx.Identifier().getText()
                ptype = param_types[i]
                self.current_scope.insert(pname, ptype, line=pctx.start.line, col=pctx.start.column)
                self._record_symbol(pname, ptype, False, pctx.start.line, pctx.start.column)

        self.visit(ctx.block())
        self._pop_scope()

        self.in_function = prev_in_func
        self.current_function_return_type = prev_ret

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

    # ================= Llamadas (funciones y métodos) =================
    def visitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
        callee_text = ctx.parentCtx.primaryAtom().getText()

        # ---- Caso método: obj.metodo(...) ----
        if "." in callee_text:
            recv_name, meth_name = callee_text.split(".", 1)

            # tipo del receptor
            if recv_name == "this":
                if not self.current_class:
                    self._add_error("'this' usado fuera de una clase.", ctx)
                    return NullType
                recv_type = self.current_class
            else:
                sym = self.current_scope.lookup(recv_name)
                if sym is None:
                    self._add_error(f"'{recv_name}' no ha sido declarado.", ctx.parentCtx.primaryAtom())
                    return NullType
                recv_type = sym.type

            if not isinstance(recv_type, ClassType):
                self._add_error(f"No se puede llamar '{meth_name}' sobre tipo '{recv_type}'.", ctx)
                return NullType

            func_type = self._method_type(recv_type, meth_name, ctx)

        else:
            # ---- Función libre id(...) ----
            callee_name = callee_text
            symbol = self.current_scope.lookup(callee_name)
            if symbol is None:
                self._add_error(f"Función '{callee_name}' no ha sido declarada.", ctx.parentCtx.primaryAtom())
                return NullType
            if not isinstance(symbol.type, FunctionType):
                self._add_error(f"'{callee_name}' no es una función y no se puede llamar.", ctx.parentCtx.primaryAtom())
                return NullType
            func_type = symbol.type

        # Chequeo de argumentos (igual que ya tenías)
        arg_expressions = ctx.arguments().expression() if ctx.arguments() else []
        if len(func_type.param_types) != len(arg_expressions):
            self._add_error(
                f"La función '{callee_text}' esperaba {len(func_type.param_types)} argumentos, "
                f"pero recibió {len(arg_expressions)}.", ctx
            )
            return func_type.return_type

        for i, arg_expr in enumerate(arg_expressions):
            arg_type = self.visit(arg_expr)
            expected_type = func_type.param_types[i]
            if arg_type != expected_type and not (expected_type == FloatType and arg_type == IntType):
                self._add_error(
                    f"Argumento {i+1} de '{callee_text}' es incorrecto. "
                    f"Se esperaba '{expected_type}', pero se obtuvo '{arg_type}'.",
                    arg_expr
                )
        return func_type.return_type

    # ================= Pasarelas genéricas =================
    def visitExpression(self, ctx: CompiscriptParser.ExpressionContext):
        return self.visitChildren(ctx)

    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        # ( expr )
        if ctx.getChildCount() == 3 and ctx.getChild(0).getText() == '(':
            return self.visit(ctx.expression())

        # <<< NEW: new Clase(...) devuelve ClassType (sin chequear ctor aquí) >>>
        try:
            if ctx.getChildCount() >= 2 and ctx.getChild(0).getText() == 'new':
                cname = ctx.getChild(1).getText()
                c = self.classes.get(cname)
                if not c:
                    self._add_error(f"Clase '{cname}' no ha sido declarada.", ctx)
                    return NullType
                return c
        except Exception:
            pass

        # <<< NEW: acceso a campo simple: this.x o id.x (no es llamada) >>>
        txt = ctx.getText()
        if "." in txt and "(" not in txt:
            base, attr = txt.split(".", 1)
            if base == "this":
                if not self.current_class:
                    self._add_error("'this' usado fuera de una clase.", ctx)
                    return NullType
                return self._field_type(self.current_class, attr, ctx)
            else:
                sym = self.current_scope.lookup(base)
                if sym is None:
                    self._add_error(f"'{base}' no ha sido declarado.", ctx)
                    return NullType
                if not isinstance(sym.type, ClassType):
                    self._add_error(f"No se puede acceder a '.{attr}' sobre tipo '{sym.type}'.", ctx)
                    return NullType
                return self._field_type(sym.type, attr, ctx)

        return self.visitChildren(ctx)
