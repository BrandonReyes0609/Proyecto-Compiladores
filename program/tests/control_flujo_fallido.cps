// Test 4.7: Condición if no boolean
let numero: integer = 5;
if (numero) {  // ERROR: condición debe ser boolean
    print("Error");
}

// Test 4.8: Break fuera de bucle
function malFormada(): void {
    break;  // ERROR: break solo dentro de bucles
}

// Test 4.9: Continue fuera de bucle
function otramal(): void {
    continue;  // ERROR: continue solo dentro de bucles
}

// Test 4.10: Return fuera de función
let x: integer = 5;
return x;  // ERROR: return solo dentro de funciones

// Test 4.11: While con condición no boolean
let texto: string = "hola";
while (texto) {  // ERROR: condición debe ser boolean
    print("Error");
}

// Test 4.12: For con condición no boolean
for (let i: integer = 0; i; i = i + 1) {  // ERROR: condición debe ser boolean
    print("Error");
}
