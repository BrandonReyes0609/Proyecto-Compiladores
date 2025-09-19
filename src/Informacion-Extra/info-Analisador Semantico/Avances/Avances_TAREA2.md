# ✅ Tarea 2: Compilación con ANTLR y Generación del Parser

## 📌 Descripción

En esta tarea se utilizó la gramática validada `Compiscript.g4` para generar los analizadores léxico y sintáctico del lenguaje Compiscript, usando ANTLR con destino a Python3.

También se ejecutó el parser sobre un archivo `.cps` para validar que el árbol sintáctico se genera correctamente.

---

## 🧱 Archivos generados

Después de compilar la gramática, se generaron los siguientes archivos dentro de la carpeta `scripts/`:

- `CompiscriptLexer.py`
- `CompiscriptParser.py`
- `CompiscriptVisitor.py`
- `Compiscript.tokens`
- `CompiscriptLexer.tokens`
- `Compiscript.interp`
- `CompiscriptLexer.interp`

---

## 🧰 Comandos utilizados

### 1. Iniciar contenedor Docker (desde PowerShell):

```bash
docker run --rm -ti -v "${PWD}:/program" csp-image
```

### 2. Compilar la gramática (dentro del contenedor):

```bash
cd /program/grammar
java -jar /usr/local/lib/antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor Compiscript.g4 -o ../scripts
```

### 3. Ejecutar el parser (dentro del contenedor):

```bash
cd /program
python3 Driver.py
```

---

## ✅ Validación: Árbol sintáctico generado

La ejecución imprimió exitosamente un árbol como el siguiente:

```plaintext
(program (statement (variableDeclaration let a (typeAnnotation : (type (baseType integer))) ... <EOF>)
```

---

## 📄 Ejemplo de entrada (`program.cps`)

```cps
let a: integer = 5 + 3 * 2;
let b: string = "hola";
const PI: integer = 314;

function saludar(nombre: string): string {
  return "Hola " + nombre;
}

let mensaje = saludar("Mundo");
```

Este archivo fue leído y analizado correctamente por el parser generado.

---

## ✅ Conclusión

La gramática fue compilada con éxito, los analizadores fueron generados, y el árbol sintáctico fue producido correctamente desde un archivo de entrada.

La tarea 2 se considera **completada**.