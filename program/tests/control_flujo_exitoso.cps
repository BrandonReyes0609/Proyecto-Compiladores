// Test 4.1: Condicional if-else correcto
let edad: integer = 18;
if (edad >= 18) {
    print("Mayor de edad");
} else {
    print("Menor de edad");
}

// Test 4.2: Bucle while
let contador: integer = 0;
while (contador < 5) {
    print("Iteración");
    contador = contador + 1;
}

// Test 4.3: Bucle for con break y continue
for (let i: integer = 0; i < 10; i = i + 1) {
    if (i == 3) {
        continue;
    }
    if (i == 7) {
        break;
    }
    print("i");
}

// Test 4.4: Do-while
let x: integer = 0;
do {
    x = x + 1;
} while (x < 3);

// Test 4.5: Switch statement
let opcion: integer = 2;
switch (opcion) {
    case 1:
        print("Uno");
        break;
    case 2:
        print("Dos");
        break;
    default:
        print("Otro");
}

// Test 4.6: Foreach (si está implementado)
let numeros: integer[] = [1, 2, 3];
foreach (numero in numeros) {
    print("numero");
}

