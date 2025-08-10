# Generated from SimpleLang.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .SimpleLangParser import SimpleLangParser
else:
    from SimpleLangParser import SimpleLangParser

# This class defines a complete listener for a parse tree produced by SimpleLangParser.
class SimpleLangListener(ParseTreeListener):

    # Enter a parse tree produced by SimpleLangParser#prog.
    def enterProg(self, ctx:SimpleLangParser.ProgContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#prog.
    def exitProg(self, ctx:SimpleLangParser.ProgContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#stat.
    def enterStat(self, ctx:SimpleLangParser.StatContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#stat.
    def exitStat(self, ctx:SimpleLangParser.StatContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#Float.
    def enterFloat(self, ctx:SimpleLangParser.FloatContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#Float.
    def exitFloat(self, ctx:SimpleLangParser.FloatContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#Bool.
    def enterBool(self, ctx:SimpleLangParser.BoolContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#Bool.
    def exitBool(self, ctx:SimpleLangParser.BoolContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#MulDiv.
    def enterMulDiv(self, ctx:SimpleLangParser.MulDivContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#MulDiv.
    def exitMulDiv(self, ctx:SimpleLangParser.MulDivContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#AddSub.
    def enterAddSub(self, ctx:SimpleLangParser.AddSubContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#AddSub.
    def exitAddSub(self, ctx:SimpleLangParser.AddSubContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#Parens.
    def enterParens(self, ctx:SimpleLangParser.ParensContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#Parens.
    def exitParens(self, ctx:SimpleLangParser.ParensContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#PowExpr.
    def enterPowExpr(self, ctx:SimpleLangParser.PowExprContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#PowExpr.
    def exitPowExpr(self, ctx:SimpleLangParser.PowExprContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#String.
    def enterString(self, ctx:SimpleLangParser.StringContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#String.
    def exitString(self, ctx:SimpleLangParser.StringContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#Equality.
    def enterEquality(self, ctx:SimpleLangParser.EqualityContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#Equality.
    def exitEquality(self, ctx:SimpleLangParser.EqualityContext):
        pass


    # Enter a parse tree produced by SimpleLangParser#Int.
    def enterInt(self, ctx:SimpleLangParser.IntContext):
        pass

    # Exit a parse tree produced by SimpleLangParser#Int.
    def exitInt(self, ctx:SimpleLangParser.IntContext):
        pass



del SimpleLangParser