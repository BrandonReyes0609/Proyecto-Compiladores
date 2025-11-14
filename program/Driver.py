# program/Driver.py
from __future__ import annotations
import sys, time, re, json
from pathlib import Path
from typing import List, Dict, Any

# --- Rutas robustas ---
HERE    = Path(__file__).resolve().parent          # .../program
ROOT    = HERE.parent                               # repo raíz
SCRIPTS = ROOT / "scripts"                          # .../scripts
for p in (ROOT, SCRIPTS, HERE):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# --- Import seguro de ANTLR/gramática ---
def _import_antlr_modules():
    try:
        from scripts.CompiscriptLexer import CompiscriptLexer
        from scripts.CompiscriptParser import CompiscriptParser
        try:
            from scripts.CompiscriptVisitor import CompiscriptVisitor  # opcional
        except Exception:
            class CompiscriptVisitor: pass
        return CompiscriptLexer, CompiscriptParser, CompiscriptVisitor
    except Exception as e:
        msg = (
            "No se encontró CompiscriptLexer/Parser en /scripts.\n"
            "Genera los archivos con:\n\n"
            "  java -jar antlr-4.13.1-complete.jar "
            "-Dlanguage=Python3 -visitor -o scripts grammar/Compiscript.g4\n"
        )
        raise ImportError(msg + f"\nDetalle: {e}")

CompiscriptLexer, CompiscriptParser, _ = _import_antlr_modules()

from antlr4 import InputStream, CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener

# --- Núcleo semántico/TAC (nuestros) ---
from program.symbol_table import SymbolTable
from program.type_check_visitor import TypeCheckVisitor
from program.TACGeneratorVisitor import TACGeneratorVisitor


# ---------- Listener de errores sintácticos ----------
class CollectingErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors: List[Dict[str, Any]] = []
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append({"sev":"error","line":int(line),"col":int(column),"msg":str(msg)})

# ---------- Utilidades ----------
_ERR_PAT = [
    re.compile(r".*?\b(linea|línea|line)\b\s+(\d+)\s*[: ,]\s*(\d+)\s*[:\-]?\s*(.+)", re.IGNORECASE),
]

def _semantic_str_to_struct(errs: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in errs or []:
        s = s.strip()
        m = None
        for p in _ERR_PAT:
            m = p.match(s)
            if m: break
        if m:
            out.append({"sev":"error","line":int(m.group(2)),"col":int(m.group(3)),"msg":m.group(4).strip()})
        else:
            out.append({"sev":"error","line":None,"col":None,"msg":s})
    return out

def _format_timing_line(timings: Dict[str, int], ok: bool) -> str:
    tag = "OK" if ok else "ERR"
    return (f"{tag}Parse {timings.get('parse_ms',0)} ms | "
            f"Semántica {timings.get('semantic_ms',0)} ms | "
            f"IR {timings.get('ir_ms',0)} ms | ASM {timings.get('asm_ms',0)} ms")

def _format_messages(errors: List[Dict[str, Any]], timings: Dict[str, int], tac_ok: bool) -> str:
    head = _format_timing_line(timings, ok=(len(errors) == 0 and tac_ok))
    if not errors:
        suf = "🔹 TAC generado correctamente." if tac_ok else ""
        return (head + ("\n" if suf else "") + suf + ("\n✅ Compilación sin errores." if tac_ok else "")).strip()
    body = "\n".join(f"line {e.get('line','-')}:{e.get('col','-')} {e.get('msg','')}" for e in errors)
    return (head + "\n" + body).strip()

# ---------- API principal para el IDE ----------
def parse_code_from_string(source: str) -> Dict[str, Any]:
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
    symbols_tree = None
    analyzer_errors: List[str] = []
    if not syn.errors:
        type_checker = TypeCheckVisitor()  # construye/gestiona scopes y offsets
        type_checker.visit(tree)
        analyzer_errors = type_checker.errors[:]  # lista de strings
        sem_struct = _semantic_str_to_struct(analyzer_errors)
        # export para IDE
        try:
            symbols_tree = type_checker.global_scope.to_dict()
        except Exception:
            symbols_tree = None
        # y además export JSON si quieres
        try:
            type_checker.global_scope.export_json(str(ROOT / "symbol_table.json"))
        except Exception:
            pass

    t2 = time.perf_counter()

    # IR/TAC
    ir  = ""
    asm = ""
    tac_ok = False
    if not syn.errors and not analyzer_errors:
        tac = TACGeneratorVisitor()
        tac.visit(tree)
        ir = tac.get_code()
        tac_ok = True

    t3 = time.perf_counter()

    timings = {
        "parse_ms":    round((t1 - t0) * 1000),
        "semantic_ms": round((t2 - t1) * 1000),
        "ir_ms":       round((t3 - t2) * 1000) if tac_ok else 0,
        "asm_ms":      0,
    }

    all_errors = syn.errors + sem_struct
    messages = _format_messages(all_errors, timings, tac_ok)

    return {
        "parse_tree": parse_tree_str,
        "messages": messages,
        "actions": "",
        "ir": ir,
        "asm": asm,
        "errors": all_errors,
        "symbols": symbols_tree,
        "timings": timings,
    }

# ---------- Modo consola ----------
def main(argv):
    src_path = ROOT / "program.cps"
    if len(argv) > 1:
        src_path = Path(argv[1]).resolve()
    input_stream = FileStream(str(src_path), encoding="utf-8")
    code = input_stream.read()
    out = parse_code_from_string(code)
    print(out["messages"])
    if out.get("ir"):
        print("\n=== TAC ===\n" + out["ir"])

if __name__ == '__main__':
    main(sys.argv)
