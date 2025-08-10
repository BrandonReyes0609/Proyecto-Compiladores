carpeta Dockerfile

 Definición del contenedor Docker con las dependencias necesarias. Incluirá por ejemplo:

* Instalación de Java (requerido por la herramienta ANTLR),
* Descarga del *.jar* completo de ANTLR (por ejemplo, `antlr-4.x-complete.jar`) y configuración de alias `antlr4` para invocarlo fácilmente,
* Instalación de Python 3 y la librería runtime de ANTLR para Python (`antlr4-python3-runtime` vía pip),
* Cualquier otro requerimiento descrito en *requerimientos_compilación.md* (p. ej., herramientas adicionales, versiones específicas).
