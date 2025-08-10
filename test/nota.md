* **`tests/`** – Pruebas automatizadas del proyecto:
  * `tests/test_parser.py` – Pruebas unitarias para asegurar que el analizador léxico/sintáctico reconoce correctamente distintas construcciones de Compiscript.
  * `tests/test_semantics.py` – Pruebas para el análisis semántico (p. ej., verificar que el visitor de tipos detecta correctamente errores de tipo, variables no declaradas, etc.).
  * (Se puede usar un framework como `unittest` o **PyTest** para ejecutar estas pruebas dentro del contenedor).
