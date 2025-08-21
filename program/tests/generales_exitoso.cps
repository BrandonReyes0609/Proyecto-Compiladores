// Test 8.1: Función con múltiples paths de retorno
function buscar(array: integer[], target: integer): boolean {
    for (let i: integer = 0; i < 5; i = i + 1) {
        if (array[i] == target) {
            return true;
        }
    }
    return false;
}

// Test 8.2: Try-catch (si está implementado)

// Test 8.3: Expresiones complejas válidas
let resultado: boolean = (5 > 3) && (10 < 20) || false;

// Test 8.4: Declaraciones mixtas
let entero: integer = 42;
const TEXTO: string = "constante";
let booleano: boolean = entero > 0;



// Test 8.6: Inicialización de múltiples variables
let a: integer = 1;
let b: integer = 2;
let c: integer = a + b;



