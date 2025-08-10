
* **`src/`** – Código fuente principal del compilador e intérprete:
  * `src/main.py` – Punto de entrada opcional para ejecutar el compilador o hacer pruebas manuales (por ejemplo, leer un archivo de código Compiscript, ejecutar el parser y aplicar el visitor semántico).
  * **`src/visitor/`** – Implementaciones de visitantes personalizados para análisis semántico. Por ejemplo, un archivo `TypeChecker.py` aquí podría definir una clase `TypeChecker` que extiende `CompiscriptVisitor` para recorrer el árbol sintáctico y verificar tipos o realizar otras validaciones semánticas.
  * **`src/ast/`** – (Opcional, para futuras fases) Definiciones de clases de Árbol de Sintaxis Abstracta (AST). Si en etapas posteriores se traduce el parse tree a un AST para análisis semántico o generación de código, este módulo contendrá los nodos AST y posiblemente funciones para construirlos.
  * *(Otros submódulos)* – Podrían incluirse otros módulos como `src/symbol_table.py` (para gestionar la tabla de símbolos durante el análisis semántico), u otros componentes necesarios (p.ej., generación de código intermedio en fases futuras).
