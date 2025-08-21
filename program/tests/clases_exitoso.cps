// Test 5.1: Declaración de clase básica
class Persona {
    let nombre: string;
    let edad: integer;
}

// Test 5.2: Instanciación de clase
let persona: Persona = new Persona();

// Test 5.3: Acceso a atributos
class Vehiculo {
    let marca: string;
    let modelo: string;
}
let auto: Vehiculo = new Vehiculo();
auto.marca = "Toyota";
auto.modelo = "Corolla";

// Test 5.4: Métodos en clase
class Calculadora {
    function sumar(a: integer, b: integer): integer {
        return a + b;
    }
}

// Test 5.5: Uso de this
class Contador {
    let valor: integer;
    
    function incrementar(): void {
        this.valor = this.valor + 1;
    }
}

// Test 5.6: Herencia básica
class Animal {
    let nombre: string;
}

class Perro : Animal {
    let raza: string;
}
