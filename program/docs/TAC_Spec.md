# Especificación TAC -- Compiscript

Este documento resume las decisiones de diseño y la implementación del
**código intermedio de tres direcciones (TAC)** para el compilador.

------------------------------------------------------------------------

## 1. Reutilización de temporales

-   Se implementó un **pool LIFO** de temporales (`t1, t2, …`)
    administrado por `TempManager`.
-   Cada vez que un temporal deja de ser necesario, se libera con
    `tm.free(t)` o `tm.free_many(...)`.
-   Al reutilizar se garantiza que la secuencia de TAC no crece
    innecesariamente y se ahorra espacio.

Ejemplo:

``` txt
t1 = 5
t2 = 10
t1 = t1 + t2   # se reusa t1 como acumulador
```

------------------------------------------------------------------------

## 2. Peephole Optimization (copias triviales)

-   Implementado en `_peephole_copy_coalesce`.
-   Detecta instrucciones redundantes del tipo:
    -   `t1 = t2`\
    -   `t1 = 7` sin usos posteriores
-   Si la variable destino se usa una sola vez, se sustituye
    directamente por el RHS y se elimina la línea.
-   También se elimina el patrón inútil `t1 = t1`.

Ejemplo:

``` txt
t1 = x
y = t1
```

Optimizado a:

``` txt
y = x
```

------------------------------------------------------------------------

## 3. Base + Offset

-   Antes de cada función se emiten directivas de **frame** y
    **offsets**:
    -   `.frame FP` → registro de activación con base FP.
    -   `.param nombre, +k` → parámetros a partir de FP+4, FP+8, ...
    -   `.local nombre, -k` → locales a partir de FP-4, FP-8, ...

Ejemplo:

``` txt
func promedioNotas
.frame FP
.param this, +4
.param nota1, +8
.param nota2, +12
.param nota3, +16
.local tmp, -4
...
endfunc promedioNotas
```

-   Para clases se emiten directivas de campos:

``` txt
.class Persona
.field nombre, +0
.field edad, +4
.field color, +8
.endclass
```

Esto hace explícita la correspondencia entre identificadores y
direcciones relativas.

------------------------------------------------------------------------

## 4. Pendientes y decisiones de diseño

-   **Orden de parámetros**: se empujan primero los argumentos y al
    final `this` (convención establecida).\
-   **Shadowing**: la `SymbolTable` maneja scopes anidados; para evitar
    colisiones se puede aplicar name-mangling (ej. `f_x` dentro de
    función `f`).\
-   **Registros de activación**:
    -   FP+0 → dirección de retorno\
    -   FP+4 → this\
    -   FP+8 → primer parámetro\
    -   FP+12 → segundo parámetro ...\
    -   FP-4 → primera variable local\
    -   FP-8 → segunda variable local ...\
-   **Short-circuit lógico**: implementado con saltos y etiquetas
    (`_gen_or_short_circuit`, `_gen_and_short_circuit`).

------------------------------------------------------------------------

## Conclusión

Con estas optimizaciones el TAC de Compiscript cumple los requisitos: 1.
Reuso de temporales\
2. Peephole optimization\
3. Anotación base+offset\
4. Convenciones claras para parámetros, locales, RA y clases
