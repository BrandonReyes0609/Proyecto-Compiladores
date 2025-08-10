# Generated from SimpleLang.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .SimpleLangParser import SimpleLangParser
else:
    from SimpleLangParser import SimpleLangParser

# This class defines a complete generic visitor for a parse tree produced by SimpleLangParser.

class SimpleLangVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SimpleLangParser#prog.
    def visitProg(self, ctx:SimpleLangParser.ProgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#stat.
    def visitStat(self, ctx:SimpleLangParser.StatContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#Float.
    def visitFloat(self, ctx:SimpleLangParser.FloatContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#Bool.
    def visitBool(self, ctx:SimpleLangParser.BoolContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#MulDiv.
    def visitMulDiv(self, ctx:SimpleLangParser.MulDivContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#AddSub.
    def visitAddSub(self, ctx:SimpleLangParser.AddSubContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#Parens.
    def visitParens(self, ctx:SimpleLangParser.ParensContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#PowExpr.
    def visitPowExpr(self, ctx:SimpleLangParser.PowExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#String.
    def visitString(self, ctx:SimpleLangParser.StringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#Equality.
    def visitEquality(self, ctx:SimpleLangParser.EqualityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SimpleLangParser#Int.
    def visitInt(self, ctx:SimpleLangParser.IntContext):
        return self.visitChildren(ctx)



del SimpleLangParser