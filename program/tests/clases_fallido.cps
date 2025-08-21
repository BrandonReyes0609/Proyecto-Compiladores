// Test 5.7: Acceso a atributo inexistente
class Simple {
    let valor: integer;
}
let obj: Simple = new Simple();
obj.inexistente = 5;  // ERROR: atributo no existe

// Test 5.8: Instanciación de clase no declarada
let obj: ClaseInexistente = new ClaseInexistente();  // ERROR: clase no declarada

// Test 5.9: Uso de this fuera de clase
function externa(): void {
    this.valor = 5;  // ERROR: this solo en métodos de clase
}

// Test 5.10: Herencia de clase inexistente
class Hija : PadreInexistente {  // ERROR: clase padre no existe
    let atributo: integer;
}

// Test 5.11: Acceso a método inexistente
class Basica {
    function metodo1(): void {}
}
let obj: Basica = new Basica();
obj.metodoInexistente();  // ERROR: método no existe

// Test 5.12: Redeclaración de clase
class Duplicada {}
class Duplicada {}  // ERROR: clase ya declarada
