// Test 7.7: Redeclaración en mismo ámbito
let duplicada: integer = 5;
let duplicada: string = "error";  // ERROR: ya declarada

// Test 7.8: Acceso a variable fuera de ámbito
{
    let local: integer = 10;
}
print("local");  // ERROR: variable fuera de ámbito

// Test 7.9: Acceso a variable de función desde otra función
function funcion1(): void {
    let privada: integer = 5;
}

function funcion2(): void {
    print("privada");  // ERROR: variable no accesible
}

// Test 7.10: Uso antes de declaración
print("adelantada");  // ERROR: variable no declarada aún
let adelantada: integer = 5;

// Test 7.11: Parámetro duplicado
function mala(param: integer, param: string): void {  // ERROR: parámetro duplicado
}

// Test 7.12: Variable local oculta parámetro incorrectamente
function conflicto(param: integer): void {
    let param: string = "error";  // ERROR: redeclaración de parámetro
}
