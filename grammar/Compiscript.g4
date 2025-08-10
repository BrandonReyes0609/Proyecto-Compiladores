grammar Compiscript;

// =====================
// 1) Reglas de PARSER
// =====================

program
  : (declaration | statement)* EOF
  ;

// --- Declaraciones ---
declaration
  : varDecl
  | constDecl
  | functionDecl
  | classDecl
  ;

varDecl
  : 'let' ID (':' typeExpr)? ('=' expr)? ';'
  ;

constDecl
  : 'const' ID (':' typeExpr)? '=' expr ';'
  ;

functionDecl
  : 'function' ID '(' paramList? ')' (':' typeExpr)? block
  ;

paramList
  : param (',' param)*
  ;

param
  : ID (':' typeExpr)?
  ;

classDecl
  : 'class' ID (':' typeExpr)? '{' classMember* '}'
  ;

classMember
  : varDecl
  | functionDecl
  | constructorDecl
  ;

constructorDecl
  : 'function' 'constructor' '(' paramList? ')' block
  ;

// --- Tipos ---
typeExpr
  : primaryType ('[' ']')*                         // arreglos: T[], T[][]
  ;

primaryType
  : 'integer' | 'float' | 'string' | 'boolean' | 'void' | ID
  ;

// --- Sentencias ---
statement
  : block
  | ifStmt
  | whileStmt
  | doWhileStmt
  | forStmt
  | foreachStmt
  | switchStmt
  | tryCatchStmt
  | returnStmt
  | breakStmt
  | continueStmt
  | exprStmt
  ;

block
  : '{' (declaration | statement)* '}'
  ;

ifStmt
  : 'if' '(' expr ')' statement ('else' statement)?
  ;

whileStmt
  : 'while' '(' expr ')' statement
  ;

doWhileStmt
  : 'do' statement 'while' '(' expr ')' ';'
  ;

forStmt
  : 'for' '(' forInit? ';' forCond? ';' forUpdate? ')' statement
  ;

forInit   : (varDecl | exprList);
forCond   : expr;
forUpdate : exprList;

foreachStmt
  : 'foreach' '(' ID 'in' expr ')' statement
  ;

switchStmt
  : 'switch' '(' expr ')' '{' caseBlock* defaultBlock? '}'
  ;

caseBlock
  : 'case' expr ':' (statement)*
  ;

defaultBlock
  : 'default' ':' (statement)*
  ;

tryCatchStmt
  : 'try' block 'catch' '(' ID ')' block
  ;

returnStmt
  : 'return' expr? ';'
  ;

breakStmt
  : 'break' ';'
  ;

continueStmt
  : 'continue' ';'
  ;

exprStmt
  : exprList ';'
  ;

exprList
  : expr (',' expr)*
  ;

// --- EXPRESIONES (precedencia de menor a mayor) ---
//  Asignación es derecha-asociativa.
expr
  : assignExpr
  ;

assignExpr
  : logicalOrExpr (assignOp assignExpr)?
  ;

assignOp
  : '='
  ;

logicalOrExpr
  : logicalAndExpr ('||' logicalAndExpr)*
  ;

logicalAndExpr
  : equalityExpr ('&&' equalityExpr)*
  ;

equalityExpr
  : relationalExpr (('==' | '!=') relationalExpr)*
  ;

relationalExpr
  : additiveExpr (('<' | '<=' | '>' | '>=') additiveExpr)*
  ;

additiveExpr
  : multiplicativeExpr (('+' | '-') multiplicativeExpr)*
  ;

multiplicativeExpr
  : unaryExpr (('*' | '/') unaryExpr)*
  ;

unaryExpr
  : ('!' | '-' | '+') unaryExpr
  | postfixExpr
  ;

postfixExpr
  : primaryExpr postfixOp*
  ;

postfixOp
  : '[' expr ']'              // indexación
  | '(' argList? ')'          // llamada
  | '.' ID                    // acceso a propiedad
  ;

argList
  : expr (',' expr)*
  ;

primaryExpr
  : literal
  | 'this'
  | 'new' typeExpr '(' argList? ')'     // instanciación
  | '(' expr ')'                        // agrupación
  | ID
  ;

// --- Literales ---
literal
  : INT_LIT
  | FLOAT_LIT
  | STRING_LIT
  | 'true'
  | 'false'
  | 'null'
  ;

// =====================
// 2) Reglas de LEXER
// =====================

// Palabras clave
IF        : 'if';
ELSE      : 'else';
WHILE     : 'while';
DO        : 'do';
FOR       : 'for';
FOREACH   : 'foreach';
IN        : 'in';
SWITCH    : 'switch';
CASE      : 'case';
DEFAULT   : 'default';
TRY       : 'try';
CATCH     : 'catch';
RETURN    : 'return';
BREAK     : 'break';
CONTINUE  : 'continue';
FUNCTION  : 'function';
CLASS     : 'class';
CONSTRUCTOR: 'constructor';
LET       : 'let';
CONST     : 'const';
NEW       : 'new';
THIS      : 'this';
TRUE      : 'true';
FALSE     : 'false';
NULL      : 'null';
INTEGER   : 'integer';
FLOAT     : 'float';
STRING    : 'string';
BOOLEAN   : 'boolean';
VOID      : 'void';

// Operadores y signos
PLUS    : '+';
MINUS   : '-';
STAR    : '*';
DIV     : '/';
NOT     : '!';
AND     : '&&';
OR      : '||';
EQ      : '==';
NEQ     : '!=';
LT      : '<';
LE      : '<=';
GT      : '>';
GE      : '>=';
ASSIGN  : '=';

LPAREN  : '(';
RPAREN  : ')';
LBRACE  : '{';
RBRACE  : '}';
LBRACK  : '[';
RBRACK  : ']';
DOT     : '.';
COMMA   : ',';
COLON   : ':';
SEMI    : ';';

// Identificadores y literales
ID          : [a-zA-Z_][a-zA-Z_0-9]*;
INT_LIT     : [0-9]+;
FLOAT_LIT   : [0-9]+ '.' [0-9]+;
STRING_LIT  : '"' (~["\\] | '\\' .)* '"';

// Espacios y comentarios
WS          : [ \t\r\n]+ -> channel(HIDDEN);
LINE_COMMENT: '//' ~[\r\n]* -> channel(HIDDEN);
BLOCK_COMMENT: '/*' .*? '*/' -> channel(HIDDEN);
