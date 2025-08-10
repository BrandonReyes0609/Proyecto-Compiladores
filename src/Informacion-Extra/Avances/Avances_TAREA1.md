# 🧩 Tarea 1: Preparación de la Gramática – Compiscript

Este documento describe los avances y pasos realizados en la **Tarea 1 del proyecto de compiladores**, centrada en la preparación y validación de la gramática del lenguaje **Compiscript**.

---

## ✅ ¿Qué se hizo?

1. **Revisión y limpieza de la gramática `Compiscript.g4`**:
   - Se verificó que todas las reglas estuvieran bien estructuradas y sin ambigüedades.
   - Se definió la regla inicial como: `program`.
   - Se usaron anotaciones claras y se organizó por bloques: declaraciones, tipos, expresiones, funciones, clases, etc.

2. **Generación de archivos del parser con ANTLR 4.13.1**:
   - Se compiló la gramática con `antlr` dentro de un contenedor Docker.
   - Se generaron los siguientes archivos en la carpeta `/scripts`:
     - `CompiscriptLexer.py`
     - `CompiscriptParser.py`
     - `CompiscriptVisitor.py`
     - `CompiscriptListener.py`
     - `Compiscript.tokens`, `Compiscript.interp`

3. **Archivo de prueba creado (`program.cps`)**:
   - Contiene declaraciones válidas del lenguaje Compiscript (variables, constantes, función, llamada).

4. **Archivo `Driver.py`** funcional:
   - Permite ejecutar el parser sobre el archivo `program.cps` y muestra el árbol sintáctico generado.

---

## ⚙️ ¿Qué se necesita para ejecutar el proyecto?

### 1. 📁 Estructura del proyecto relevante

```
Proyecto-Compiladores/
├── grammar/
│   └── Compiscript.g4
├── scripts/
│   └── [Archivos generados por ANTLR]
├── program.cps
├── Driver.py
├── antlr-4.13.1-complete.jar
├── Dockerfile
```

---

## 🚀 Ejecución paso a paso (desde PowerShell / terminal)

### 1. Construir la imagen de Docker (una vez)

```powershell
docker build -t csp-image .
```

### 2. Ejecutar el contenedor y montar el proyecto

```powershell
docker run --rm -ti -v "${PWD}:/program" csp-image
```

> Esto te dejará dentro del contenedor en la ruta `/program`.

---

## 🔁 Dentro del contenedor

### 1. Compilar la gramática con ANTLR

```bash
cd /program/grammar
antlr -Dlanguage=Python3 -visitor -o ../scripts Compiscript.g4
```

### 2. Verificar que se generaron los archivos

```bash
ls /program/scripts
```

### 3. Ejecutar el parser sobre `program.cps`

```bash
cd /program
python3 Driver.py
```

> Deberías ver el árbol sintáctico como resultado.

---

## 📄 Ejemplo de código en `program.cps`

```cps
let a: integer = 5 + 3 * 2;
let b: string = "hola";
const PI: integer = 314;

function saludar(nombre: string): string {
  return "Hola " + nombre;
}

let mensaje = saludar("Mundo");
```

---

## ✅ Resultado final esperado

Al ejecutar `Driver.py`, el árbol sintáctico se genera correctamente sin errores, lo que demuestra que:

- La gramática es válida.
- El lexer y parser funcionan correctamente.
- La entrada de prueba `program.cps` cumple con la gramática definida.

---

## 📌 Siguiente paso

Pasar a la **Tarea 2: Compilación con ANTLR y generación del análisis semántico**, que incluye:

- Implementar un Listener o Visitor.
- Crear una tabla de símbolos.
- Validar tipos, errores semánticos y estructuras del lenguaje.