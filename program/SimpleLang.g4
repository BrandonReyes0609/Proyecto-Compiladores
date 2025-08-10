grammar SimpleLang;

prog: stat+ ;

stat: expr NEWLINE ;

expr
    : expr op=(MUL | DIV | MOD) expr         # MulDiv
    | expr op=(ADD | SUB) expr              # AddSub
    | expr op=POW expr                      # PowExpr
    | expr op=EQ expr                       # Equality
    | '(' expr ')'                          # Parens
    | INT                                   # Int
    | FLOAT                                 # Float
    | STRING                                 # String
    | BOOL                                   # Bool
    ;

MUL: '*';
DIV: '/';
MOD: '%';
POW: '^';
ADD: '+';
SUB: '-';
EQ: '==';

INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
STRING: '"' .*? '"';
BOOL: 'true' | 'false';
WS: [ \t\r\n]+ -> skip;