// Error: variable no declarada
x = 10;

// Error: constante sin inicializar
const c: boolean;

// Error: comparación incompatible
if ("hola" < 5) { }

// Error: función llamada con tipos incorrectos
function mult(a: integer, b: integer): integer {
    return a * b;
}
var res = mult("texto", 3.5);
