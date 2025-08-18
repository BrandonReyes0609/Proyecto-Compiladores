# program/Driver.py
from __future__ import annotations
import sys, time, re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ---------- Rutas robustas ----------
HERE   = Path(__file__).resolve().parent              # .../program
ROOT   = HERE.parent                                  # repo raíz
SCRIPTS= ROOT / "scripts"                             # .../scripts
for p in (ROOT, SCRIPTS, HERE):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# ---------- Carga segura de ANTLR ----------
def _import_antlr_modules():
    """
    Importa CompiscriptLexer/Parser/Visitor desde scripts.
    Si no existen, lanza un error claro con instrucción de regeneración.
    """
    try:
        from scripts.CompiscriptLexer import CompiscriptLexer
        from scripts.CompiscriptParser import CompiscriptParser
        try:
            from scripts.CompiscriptVisitor import CompiscriptVisitor  # opcional
        except Exception:
            CompiscriptVisitor = object
        return CompiscriptLexer, CompiscriptParser, CompiscriptVisitor
    except Exception as e:
        missing = (
            "No se encontró CompiscriptLexer/Parser. "
            "Genera los archivos ANTLR en /scripts con:\n\n"
            "  java -jar antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor -o scripts grammar/Compiscript.g4\n"
        )
        raise ImportError(f"{missing}\nDetalle: {e}")

# Importa ahora (a nivel módulo) para el modo CLI y para validarlo temprano
CompiscriptLexer, CompiscriptParser, _ = _import_antlr_modules()

# ---------- ANTLR runtime ----------
from antlr4 import InputStream, CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener

# ---------- Semántica ----------
# semantic_analyzer.py está en program/
from program.semantic_analyzer import SemanticAnalyzer


# ---------- Listener de errores sintácticos ----------
class CollectingErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors: List[Dict[str, Any]] = []
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append({"sev": "error", "line": int(line), "col": int(column), "msg": str(msg)})


# ---------- Utilidades ----------
_ERR_PAT = [
    re.compile(r".*?linea\s+(\d+)\s*:\s*(\d+)\s*:\s*(.+)", re.IGNORECASE),
    re.compile(r".*?linea\s+(\d+)\s*:\s*(\d+)\s*(.+)", re.IGNORECASE),
    re.compile(r".*?línea\s+(\d+)\s*:\s*(\d+)\s*(.+)", re.IGNORECASE),
    re.compile(r".*?line\s+(\d+)\s*:\s*(\d+)\s*(.+)", re.IGNORECASE),
    re.compile(r".*?line\s+(\d+)\s*,\s*col\s*(\d+)\s*[:\-]?\s*(.+)", re.IGNORECASE),
]

def _semantic_str_to_struct(errs: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in errs or []:
        s = s.strip()
        m = next((p.match(s) for p in _ERR_PAT if p.match(s)), None)
        if m:
            out.append({"sev":"error","line":int(m.group(1)),"col":int(m.group(2)),"msg":m.group(3).strip()})
        else:
            out.append({"sev":"error","line":None,"col":None,"msg":s})
    return out

def _format_messages(errors: List[Dict[str, Any]]) -> str:
    if not errors: return "OK"
    return "\n".join(f"line {e.get('line','-')}:{e.get('col','-')} {e.get('msg','')}" for e in errors)


# ---------- API para el IDE ----------
def parse_code_from_string(source: str) -> Dict[str, Any]:
    """
    Analiza `source` y devuelve un dict con:
      parse_tree, messages, actions, ir, asm, errors, timings
    """
    t0 = time.perf_counter()

    # Lexer / Parser desde STRING
    lexer = CompiscriptLexer(InputStream(source))
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)

    syn = CollectingErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(syn)

    tree = parser.program()  # regla inicial
    parse_tree_str = tree.toStringTree(recog=parser)

    t1 = time.perf_counter()

    # Semántico si no hubo errores sintácticos
    sem_struct: List[Dict[str, Any]] = []
    if not syn.errors:
        analyzer = SemanticAnalyzer()
        analyzer.visit(tree)
        sem_struct = _semantic_str_to_struct(analyzer.errors)

    t2 = time.perf_counter()

    # (ganchos para IR/ASM si los generas)
    ir = ""
    asm = ""

    all_errors = syn.errors + sem_struct
    messages = _format_messages(all_errors)

    return {
        "parse_tree": parse_tree_str,
        "messages": messages,
        "actions": "",
        "ir": ir,
        "asm": asm,
        "errors": all_errors,
        "timings": {
            "parse_ms":    round((t1 - t0) * 1000),
            "semantic_ms": round((t2 - t1) * 1000),
            "ir_ms":       0,
            "asm_ms":      0,
        },
    }


# ---------- Modo consola (se mantiene tu flujo) ----------
def main(argv):
    input_stream = FileStream(str(ROOT / "program.cps"), encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(token_stream)

    tree = parser.program()
    print(f"--- Análisis Semántico del archivo: {input_stream.fileName} ---")

    analyzer = SemanticAnalyzer()
    analyzer.visit(tree)

    if analyzer.errors:
        print("Se encontraron los siguientes errores semánticos:")
        for error in analyzer.errors:
            print(error)
        print(f"\nTotal: {len(analyzer.errors)} errores.")
    else:
        print("El análisis semántico finalizó sin errores.")

if __name__ == '__main__':
    main(sys.argv)
