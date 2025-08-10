import sys
from antlr4 import *
from scripts.CompiscriptLexer import CompiscriptLexer
from scripts.CompiscriptParser import CompiscriptParser

def main(argv):
    input_stream = FileStream("program.cps", encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(token_stream)

    #tree = parser.prog()  # Asegúrate que la regla inicial sea 'prog'
    tree = parser.program()

    print(tree.toStringTree(recog=parser))

    #visitor = TypeCheckVisitor()
    #try:
    #    visitor.visit(tree)
    #    print("Type checking passed")
    #except TypeError as e:
    #    print(f"Type checking error: {e}")

if __name__ == '__main__':
    main(sys.argv)
