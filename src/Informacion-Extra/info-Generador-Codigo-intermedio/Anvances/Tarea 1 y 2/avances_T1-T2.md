Según los **README** y  **Tareas fase 2** :

* **Objetivo:** Transformar el **AST + tabla de símbolos** en  **Código de Tres Direcciones (TAC)** .
* **Formato:** cuádruplas o lineal con temporales (`t1, t2, …`).
* **Salidas esperadas:**
  1. Un archivo `.tac` generado a partir de un `.cps`.
  2. Tabla de símbolos extendida con offsets, temporales, funciones.
  3. Tests con casos correctos y fallidos.
  4. Documentación del TAC diseñado.

---

## 👤 Tus tareas asignadas

Según **README_FASE2_TAC (1).md** y  **Tareas fase 2.pdf** , te corresponde:

### 🔹 **Persona 1: Expresiones y Operaciones Básicas (TAC Frontend)**

1. Diseñar la estructura del TAC (ej. cuádruplas: `(op, arg1, arg2, result)`).
2. Crear `TACGeneratorVisitor.py`.
3. Implementar generación TAC para:
   * Literales: enteros, booleanos, strings, `null`.
   * Operaciones aritméticas básicas: `+`, `-`.
   * Operaciones aritméticas avanzadas: `*`, `/`, `%`.
   * Expresiones agrupadas: `(a + b) * c`.
4. Manejo de asignaciones:
   * Simples (`x = y`).
   * Con operación (`x = y + z`).
5. Generar temporales (`t1, t2, …`) y logs.
6. Validar con ejemplos de expresiones simples.

---

### 🔹 **Persona 2: Operaciones Lógicas y Comparaciones**

1. TAC para operaciones lógicas (`&&`, `||`, `!`) con cortocircuito.
2. Comparaciones (`<`, `<=`, `>`, `>=`, `==`, `!=`).
3. Generar etiquetas (`L1, L2`) para control de flujo.
4. Integrar con los temporales de Persona 1.
5. Validar con ejemplos tipo: `if (a < b && c > d)`.

---

## 📂 Estructura esperada del proyecto (fase 2)

<pre class="overflow-visible!" data-start="1718" data-end="2094"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>compiscript/
├── program/
│   ├── Compiscript</span><span>.g4</span><span>
│   ├── Driver</span><span>.py</span><span>
│   ├── tac_generator/
│   │   └── TACVisitor</span><span>.py</span><span>   👈 aquí irí</span><span>a</span><span> tu implementación
│   └── tests/
│       ├── test_valid_01</span><span>.cps</span><span>
│       ├── test_valid_01</span><span>.tac</span><span>
│       └── ...
├── docs/
│   ├── TAC_Spec</span><span>.md</span><span>         👈 documentación </span><span>del</span><span> diseño de TAC
│   ├── SymbolTable</span><span>.md</span><span>
│   └── README_TAC_GENERATION</span><span>.md</span><span>
</span></span></code></div></div></pre>

---

## 🚀 Plan de acción para ti

1. **Crear base del visitor TAC**
   * Nuevo archivo: `program/tac_generator/TACVisitor.py`
   * Heredar de `CompiscriptVisitor`.
   * Usar una clase `TempManager` para manejar `t1, t2…`.
2. **Implementar generación TAC de expresiones aritméticas**
   * Literales → devolver temporal con valor directo.
   * Binarias (`+`, `-`, `*`, `/`, `%`) → generar temporales intermedios.
   * Ejemplo:

     <pre class="overflow-visible!" data-start="2528" data-end="2567"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cps"><span>let z = x + y * 2;
     </span></code></div></div></pre>

     TAC:

     <pre class="overflow-visible!" data-start="2583" data-end="2640"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>t1</span><span> = y * </span><span>2</span><span>
     </span><span>t2</span><span> = x + t1
     </span><span>z</span><span> = t2
     </span></span></code></div></div></pre>
3. **Asignaciones**
   * `x = y;` → `x = y`
   * `x = y + z;` → usar temporales si es necesario.
4. **Validar con pruebas**
   * Crear `tests/test_expresiones.cps` y su esperado `.tac`.

---

📌 En resumen:

Tú tienes que levantar **el frontend de TAC (expresiones + operaciones básicas)** y en paralelo tu compañero (Persona 2) hará lo mismo con  **operaciones lógicas y comparaciones** , para luego integrarse.
