import os
import sys
import shutil
import subprocess

# Verificar si el comando 'antlr4' está disponible (alias para el .jar de ANTLR)
antlr_cmd = shutil.which("antlr4")
antlr_jar = os.environ.get("ANTLR_JAR")  # Ruta alternativa del jar, configurable vía variable de entorno

if antlr_cmd:
    # Usar alias antlr4 si existe (configurado en Dockerfile)
    antlr_tool = "antlr4"
elif antlr_jar and os.path.isfile(antlr_jar):
    # Usar java -jar con la ruta proporcionada
    antlr_tool = f"java -jar \"{antlr_jar}\""
else:
    print("ERROR: No se encontró ANTLR. Asegúrate de tener el alias 'antlr4' en PATH o la variable ANTLR_JAR definida.")
    sys.exit(1)

# Definir paths de entrada/salida
GRAMMAR_FILE = "grammar/Compiscript.g4"
OUTPUT_DIR = "antlr"

# Asegurarse de que el directorio de salida existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Construir el comando completo para ANTLR
# -Dlanguage=Python3: generar código Python
# -visitor: generar la clase base Visitor (CompiscriptVisitor.py):contentReference[oaicite:0]{index=0}
# -no-listener: opcional, si no se necesita la funcionalidad de Listener
antlr_command = [
    *antlr_tool.split(),           # Puede ser ["antlr4"] o ["java","-jar","..."]
    "-Dlanguage=Python3",
    "-visitor",
    "-no-listener",
    "-o", OUTPUT_DIR,
    GRAMMAR_FILE
]

print(f"Compilando gramática ANTLR: {GRAMMAR_FILE} ...")
result = subprocess.run(antlr_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if result.returncode != 0:
    print("ERROR al ejecutar ANTLR:")
    print(result.stderr.decode('utf-8') or "<stderr vacío>")
    sys.exit(result.returncode)

# Verificar generación de archivos principales
expected_files = ["CompiscriptLexer.py", "CompiscriptParser.py", "CompiscriptVisitor.py"]
missing = [f for f in expected_files if not os.path.isfile(os.path.join(OUTPUT_DIR, f))]
if missing:
    print(f"ADVERTENCIA: Los siguientes archivos no se generaron: {missing}")
else:
    print("Gramática compilada con éxito. Archivos generados en carpeta 'antlr/'")
