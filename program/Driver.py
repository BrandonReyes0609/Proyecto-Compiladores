import sys
from antlr4 import *
sys.path.append('..')
from scripts.CompiscriptLexer import CompiscriptLexer
from scripts.CompiscriptParser import CompiscriptParser
from semantic_analyzer import SemanticAnalyzer 

def main(argv):
    input_stream = FileStream("program.cps", encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(token_stream)

    #tree = parser.prog()  # Asegúrate que la regla inicial sea 'prog'
    tree = parser.program()
    print(f"--- Análisis Semántico del archivo: {input_stream} ---")

    analyzer = SemanticAnalyzer()
    analyzer.visit(tree)
    # print(tree.toStringTree(recog=parser))

    #visitor = TypeCheckVisitor()
    #try:
    #    visitor.visit(tree)
    #    print("Type checking passed")
    #except TypeError as e:
    #    print(f"Type checking error: {e}")

    if analyzer.errors:
        print("Se encontraron los siguientes errores semánticos:")
        for error in analyzer.errors:
            print(error)
        print(f"\nTotal: {len(analyzer.errors)} errores.")
    else:
        print("El análisis semántico finalizó sin errores.")

if __name__ == '__main__':
    main(sys.argv)
