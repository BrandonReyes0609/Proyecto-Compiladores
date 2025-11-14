#Driver.py
import sys
from antlr4 import *
from scripts.CompiscriptLexer import CompiscriptLexer
from scripts.CompiscriptParser import CompiscriptParser

def main(argv):
    input_stream = FileStream("archivos_test/ejemplo_propio/ejemplo1.cps", encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(token_stream)
    tree = parser.program()
    print(tree.toStringTree(recog=parser))

def parse_code_from_string(code: str) -> tuple[str, str]:
    try:
        input_stream = InputStream(code)
        lexer = CompiscriptLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = CompiscriptParser(token_stream)
        tree = parser.program()
        return tree.toStringTree(recog=parser), "✔ Compilación exitosa"
    except Exception as e:
        return "", "❌ Error al compilar: " + str(e)

if __name__ == '__main__':
    main(sys.argv)
