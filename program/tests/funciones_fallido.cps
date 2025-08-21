// Test 3.7: Función sin return requerido
function obtenerNumero(): integer {
    print("Sin return");
    // ERROR: función integer debe tener return
}

// Test 3.8: Llamada con argumentos incorrectos
function multiplicar(a: integer, b: integer): integer {
    return a * b;
}
let mal: integer = multiplicar(5);  // ERROR: faltan argumentos

// Test 3.9: Tipo de retorno incorrecto
function obtenerTexto(): string {
    return 42;  // ERROR: retorna integer, esperado string
}

// Test 3.10: Función no declarada
let resultado: integer = funcionInexistente(5);  // ERROR: función no declarada

// Test 3.11: Argumentos de tipo incorrecto
function procesar(texto: string): void {
    print(texto);
}
procesar(123);  // ERROR: argumento integer, esperado string

// Test 3.12: Múltiples declaraciones de función
function duplicada(): void {}
function duplicada(): void {}  // ERROR: función ya declarada
