# program/semantic_analyzer.py

from scripts.CompiscriptParser import CompiscriptParser
from scripts.CompiscriptVisitor import CompiscriptVisitor

from custom_types import (
    IntType, FloatType, BoolType, StringType, NullType, VoidType,
    FunctionType, ClassType, ArrayType
)
from symbol_table import SymbolTable


class SemanticAnalyzer(CompiscriptVisitor):
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope

        self.errors = []
        self.current_function_return_type = None

        # ---- Estado para clases ----
        self.classes = {}          # "Persona" -> ClassType
        self.current_class = None  # ClassType o None
        self.in_class_body = False
        self.in_function = False   # distinguir campos vs variables locales

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
        if isinstance(t, ArrayType):
            return f"{self._tname(t.elem_type)}[]"
        if isinstance(t, ClassType):
            return t.name
        if isinstance(t, FunctionType):
            args = ", ".join(self._tname(p) for p in t.param_types)
            return f"fn({args}) -> {self._tname(t.return_type)}"
        return str(t)

    def symbol_tree(self):
        return self._sym_root

    # ===== Helpers de tipos / clases =====
    def _resolve_type_token(self, name: str):
        """Resuelve nombre de tipo ('integer', 'Persona', etc.)."""
        prim = {
            "integer": IntType,
            "float": FloatType,
            "boolean": BoolType,
            "string": StringType,
            "void": VoidType
        }
        return prim.get(name) or self.classes.get(name)

    def _parse_type_text(self, text: str):
        """'integer', 'string[]', 'Persona[][]' -> Type/ArrayType."""
        raw = (text or "").replace(" ", "")
        dims = 0
        while raw.endswith("[]"):
            dims += 1
            raw = raw[:-2]
        base = self._resolve_type_token(raw)
        t = base
        for _ in range(dims):
            t = ArrayType(t)
        return t

    def _compatible(self, expected, actual):
        """Compatibilidad básica (incluye int->float y arrays)."""
        if expected == actual:
            return True
        # numérico: int -> float
        if expected == FloatType and actual == IntType:
            return True
        # arrays
        if isinstance(expected, ArrayType) and isinstance(actual, ArrayType):
            # permitir [] vacío (elem_type == NullType) como cualquier T[]
            if actual.elem_type == NullType:
                return True
            return self._compatible(expected.elem_type, actual.elem_type)
        return False

    def _infer_array_literal_type_from_text(self, txt: str):
        """Inferir tipo de literal de array: [], [1,2], [[1],[2]], etc."""
        s = (txt or "").strip()
        if not (s.startswith("[") and s.endswith("]")):
            return NullType
        inner = s[1:-1].strip()
        if inner == "":
            return ArrayType(NullType)  # array vacío

        # split por comas a nivel superior (soporta anidados y strings)
        parts, buf, depth, in_str = [], [], 0, False
        i = 0
        while i < len(inner):
            ch = inner[i]
            if ch == '"' and (i == 0 or inner[i-1] != "\\"):
                in_str = not in_str
                buf.append(ch)
            elif not in_str and ch == '[':
                depth += 1; buf.append(ch)
            elif not in_str and ch == ']':
                depth -= 1; buf.append(ch)
            elif not in_str and depth == 0 and ch == ',':
                parts.append("".join(buf).strip()); buf = []
            else:
                buf.append(ch)
            i += 1
        if buf: parts.append("".join(buf).strip())

        # tipo por elemento
        elem_types = []
        for p in parts:
            if p.startswith("["):
                elem_types.append(self._infer_array_literal_type_from_text(p))
            elif p.startswith('"'):
                elem_types.append(StringType)
            elif p in ("true", "false"):
                elem_types.append(BoolType)
            elif p == "null":
                elem_types.append(NullType)
            else:
                if "." in p:
                    try:
                        float(p); elem_types.append(FloatType)
                    except:
                        elem_types.append(NullType)
                else:
                    num = p.lstrip("-")
                    elem_types.append(IntType if num.isdigit() else NullType)

        et = elem_types[0]
        for t in elem_types[1:]:
            if et == t:
                continue
            if (et in (IntType, FloatType)) and (t in (IntType, FloatType)):
                et = FloatType
            else:
                et = NullType; break
        return ArrayType(et)

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
            # fallback si difiere la API del contexto
            text = ctx.getText()
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
            if base and ctype.base is None:
                ctype.base = base

        prev_cls, prev_flag = self.current_class, self.in_class_body
        self.current_class = ctype
        self.in_class_body = True

        self._push_scope(f"class {name}", ctx)
        self.visitChildren(ctx)  # dentro registramos campos/métodos
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
        if text.startswith('[') and text.endswith(']'):
            return self._infer_array_literal_type_from_text(text)
        if ctx.Literal():
            literal_text = ctx.Literal().getText()
            if '.' in literal_text:
                return FloatType
            if literal_text.isdigit() or (literal_text.startswith('-') and literal_text[1:].isdigit()):
                return IntType
        return NullType

    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.getText()
        if name == "this":
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

        # tipo explícito (primitivo / clase / array)
        if ctx.typeAnnotation():
            ttxt = ctx.typeAnnotation().type_().getText()
            declared_type = self._parse_type_text(ttxt)

        # CAMPO DE CLASE: let campo: T;  (no insertar en tabla global)
        if self.in_class_body and not self.in_function:
            if declared_type is None:
                self._add_error(f"No se pudo determinar el tipo del campo '{var_name}'.", ctx)
                return
            self.current_class.fields[var_name] = declared_type
            self._record_symbol(var_name, declared_type, False, line, col)
            return

        # Variable local/global normal
        expr_type = None
        if ctx.initializer():
            expr_type = self.visit(ctx.initializer().expression())
            if declared_type is None:
                declared_type = expr_type
            elif expr_type and not self._compatible(declared_type, expr_type):
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

        ttxt = ctx.typeAnnotation().type_().getText()
        declared_type = self._parse_type_text(ttxt)

        if not self.current_scope.insert(const_name, declared_type, is_const=True, line=line, col=col):
            self._add_error(f"Identificador '{const_name}' ya declarado.", ctx); return
        else:
            self._record_symbol(const_name, declared_type, True, line, col)

        expr_type = self.visit(ctx.expression())
        if expr_type and not self._compatible(declared_type, expr_type):
            self._add_error(
                f"Tipo incompatible para constante '{const_name}'. Se esperaba '{declared_type}' pero se obtuvo '{expr_type}'.",
                ctx
            )

    # ===== Funciones y MÉTODOS =====
    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        func_name = ctx.Identifier().getText()

        return_type = VoidType
        if ctx.type_():
            return_type = self._parse_type_text(ctx.type_().getText()) or VoidType

        param_types = []
        if ctx.parameters():
            for pctx in ctx.parameters().parameter():
                param_types.append(self._parse_type_text(pctx.type_().getText()))

        func_type = FunctionType(return_type, param_types)

        # ---- Método en clase ----
        if self.in_class_body and not self.in_function:
            if func_name in self.current_class.methods:
                self._add_error(f"Método '{func_name}' ya ha sido declarado en esta clase.", ctx)
            else:
                self.current_class.methods[func_name] = func_type
                self._record_symbol(func_name, func_type, False, ctx.start.line, ctx.start.column)

            prev_ret = self.current_function_return_type
            prev_in_func = self.in_function
            self.current_function_return_type = return_type
            self.in_function = True

            self._push_scope(f"method {func_name}", ctx)
            try:
                self.current_scope.insert("this", self.current_class, line=ctx.start.line, col=ctx.start.column)
            except Exception:
                pass

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
            return

        # ---- Función global ----
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
        # 1) Texto completo de la llamada desde el PADRE.
        call_text = ""
        try:
            if hasattr(ctx, "parentCtx") and hasattr(ctx.parentCtx, "getText"):
                call_text = ctx.parentCtx.getText() or ""
            else:
                call_text = ctx.getText() or ""
        except Exception:
            call_text = ctx.getText() or ""

        # 2) Callee textual (antes del primer '(').
        callee_text = call_text.split("(", 1)[0].strip()

        # 3) Último recurso
        if not callee_text:
            try:
                callee_text = ctx.parentCtx.primaryAtom().getText().strip()
            except Exception:
                pass

        if not callee_text:
            self._add_error("No se pudo resolver el callee de la llamada.", ctx)
            return NullType

        # ---- Método: obj.metodo(...) ----
        if "." in callee_text:
            recv_name, meth_name = callee_text.split(".", 1)

            if recv_name == "this":
                if not self.current_class:
                    self._add_error("'this' usado fuera de una clase.", ctx)
                    return NullType
                recv_type = self.current_class
            else:
                recv_sym = self.current_scope.lookup(recv_name)
                if recv_sym is None:
                    self._add_error(f"'{recv_name}' no ha sido declarado.", ctx)
                    return NullType
                recv_type = recv_sym.type

            if not isinstance(recv_type, ClassType):
                self._add_error(f"No se puede llamar '{meth_name}' sobre tipo '{recv_type}'.", ctx)
                return NullType

            func_type = self._method_type(recv_type, meth_name, ctx)

        else:
            # ---- Función global id(...) ----
            symbol = self.current_scope.lookup(callee_text)
            if symbol is None:
                self._add_error(f"Función '{callee_text}' no ha sido declarada.", ctx)
                return NullType
            if not isinstance(symbol.type, FunctionType):
                self._add_error(f"'{callee_text}' no es una función y no se puede llamar.", ctx)
                return NullType
            func_type = symbol.type

        # ---- Chequeo de argumentos ----
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

        # new Clase(...)
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

        txt = ctx.getText()

        # literal de array
        if txt.startswith("[") and txt.endswith("]"):
            return self._infer_array_literal_type_from_text(txt)

        # acceso a campo simple: this.x o id.x (no es llamada)
        if "." in txt and "(" not in txt and "[" not in txt:
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

        # indexación: id[expr]  -> tipo del elemento (soporta arrays anidados)
        if "[" in txt and txt.endswith("]") and not txt.startswith("[") and "(" not in txt:
            base = txt.split("[", 1)[0]
            index_text = txt[txt.find("[")+1:-1].strip()

            sym = self.current_scope.lookup(base)
            if sym is None:
                self._add_error(f"'{base}' no ha sido declarado.", ctx)
                return NullType
            arr_t = sym.type
            if not isinstance(arr_t, ArrayType):
                self._add_error(f"No se puede indexar sobre tipo '{arr_t}'.", ctx)
                return NullType

            # tipo del índice
            if index_text.lstrip("-").isdigit():
                idx_t = IntType
            else:
                s = self.current_scope.lookup(index_text)
                idx_t = s.type if s else NullType
            if idx_t != IntType:
                self._add_error(f"El índice de un array debe ser integer, se obtuvo '{idx_t}'.", ctx)

            return arr_t.elem_type

        return self.visitChildren(ctx)
