// Test 6.1: Declaración de arrays
let enteros: integer[] = [1, 2, 3, 4, 5];
let textos: string[] = ["a", "b", "c"];

// Test 6.2: Acceso por índice
let primer: integer = enteros[0];
let ultimo: integer = enteros[4];

// Test 6.3: Asignación por índice
enteros[2] = 10;
textos[1] = "modificado";

// Test 6.4: Array vacío
let vacio: integer[] = [];

// Test 6.5: Arrays anidados (si se soporta)
let matriz: integer[][] = [[1, 2], [3, 4]];

// Test 6.6: Iteración sobre array
let numeros: integer[] = [1, 2, 3];
for (let i: integer = 0; i < 3; i = i + 1) {
    let elemento: integer = numeros[i];
}
