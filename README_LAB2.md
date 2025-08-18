# Laboratorio 2: Verificación de Tipos con ANTLR y Docker

Este laboratorio implementa un verificador de tipos utilizando ANTLR en Python, y se ejecuta dentro de un contenedor Docker.

---

## Estructura del proyecto

```
lab-2/
├── program/
│   ├── Driver.py
│   ├── DriverListener.py
│   ├── SimpleLang.g4
│   ├── type_check_listener.py
│   ├── type_check_visitor.py
│   ├── program_test_pass.txt
│   ├── program_test_no_pass.txt
│   ├── program_test_extra_pass.txt
│   ├── program_test_extra_fail.txt
│   └── ...
├── Dockerfile
├── antlr-4.13.1-complete.jar
├── requirements.txt
└── ...
```

---

## Comandos para ejecutar el laboratorio

### 1.  **Construir la imagen de Docker**

```bash
docker build --rm . -t lab2-image
```

### 2.  **Ejecutar el contenedor**

```bash
docker run --rm -it -v "$(pwd)/program:/program" lab2-image
```

 En Windows con PowerShell, reemplaza `${PWD}` por `$(pwd)` o usa la ruta completa.

---

## Dentro del contenedor

### 3. 🔧 **Generar el parser con ANTLR**

```bash
antlr -Dlanguage=Python3 -visitor SimpleLang.g4
antlr -Dlanguage=Python3 -listener SimpleLang.g4
```

### 4.  **Ejecutar archivos de prueba con Visitor**

```bash
python3 Driver.py program_test_pass.txt
python3 Driver.py program_test_no_pass.txt
python3 Driver.py program_test_extra_pass.txt
python3 Driver.py program_test_extra_fail.txt
```

### 5.  **Ejecutar archivos de prueba con Listener**

```bash
python3 DriverListener.py program_test_pass.txt
python3 DriverListener.py program_test_no_pass.txt
python3 DriverListener.py program_test_extra_pass.txt
python3 DriverListener.py program_test_extra_fail.txt
```

---

## Video de demostración

Puedes ver una demostración completa del laboratorio aquí:
 [https://youtu.be/5vPAefqHda4](https://youtu.be/5vPAefqHda4)

---

## Resultados esperados

- `*_pass.txt` → `Type checking passed`
- `*_fail.txt` → Se muestran los errores de tipo detectados (suma entre tipos incompatibles, comparaciones inválidas, etc.)

---

## Autor

- **Nombre: Brandon Reyes 22992**
- **Curso:** Construcción de Compiladores
- **Año:** 2025

---
