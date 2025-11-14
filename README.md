```

```


Código de preuba ejemplo1.cps

```
// --- Utilidad global ---
function toString(x: integer): string {
  return "";
}

// --- Clase base ---
class Persona {
  let nombre: string;
  let edad: integer;
  let color: string;

  function constructor(nombre: string, edad: integer) {
    this.nombre = nombre;
    this.edad = edad;
    this.color = "rojo";
  }

  function saludar(): string {
    return "Hola, mi nombre es " + this.nombre;
  }

  function incrementarEdad(anos: integer): string {
    this.edad = this.edad + anos;
    return "Ahora tengo " + toString(this.edad) + " años.";
  }
}

// --- Clase derivada ---
class Estudiante : Persona {
  let grado: integer;

  function constructor(nombre: string, edad: integer, grado: integer) {
    // No hay 'super': inicializamos campos heredados directamente
    this.nombre = nombre;
    this.edad = edad;
    this.color = "rojo";
    this.grado = grado;
  }

  function estudiar(): string {
    return this.nombre + " está estudiando en " + toString(this.grado) + " grado.";
  }

  function promedioNotas(nota1: integer, nota2: integer, nota3: integer): integer {
    let promedio: integer = (nota1 + nota2 + nota3) / 3; // división entera
    return promedio;
  }
}

// --- Programa principal ---
let log: string = "";

let nombre: string = "Erick";
let juan: Estudiante = new Estudiante(nombre, 20, 3);

// "Imprimir" = concatenar al log con saltos de línea
log = log + juan.saludar() + "\n";
log = log + juan.estudiar() + "\n";
log = log + juan.incrementarEdad(5) + "\n";

// Bucle (uso de while por compatibilidad)
let i: integer = 1;
while (i <= 5) {
  if ((i % 2) == 0) {
    log = log + toString(i) + " es par\n";
  } else {
    log = log + toString(i) + " es impar\n";
  }
  i = i + 1;
}

// Expresión aritmética (entera)
let resultado: integer = (juan.edad * 2) + ((5 - 3) / 2);
log = log + "Resultado de la expresión: " + toString(resultado) + "\n";

// Ejemplo de promedio (entero)
let prom: integer = 0;
prom = juan.promedioNotas(90, 85, 95);
log = log + "Promedio (entero): " + toString(prom) + "\n";

// Nota: 'log' contiene todas las salidas.
```



Compilación de salida de Codigo Intermedio:

```
FUNC toString_START:
BeginFunc toString 1
ActivationRecord toString
p_x = LoadParam 0
t1 = ""
return t1
FUNC toString_END:
EndFunc toString
FUNC constructor_START:
BeginFunc constructor 2
ActivationRecord constructor
p_nombre = LoadParam 0
p_edad = LoadParam 1
nombre = nombre
edad = edad
color = color
return
FUNC constructor_END:
EndFunc constructor
FUNC saludar_START:
BeginFunc saludar 0
ActivationRecord saludar
t1 = "Hola, mi nombre es "
t2 = getprop this, nombre
t1 = t1 + t2
return t1
FUNC saludar_END:
EndFunc saludar
FUNC incrementarEdad_START:
BeginFunc incrementarEdad 1
ActivationRecord incrementarEdad
p_anos = LoadParam 0
edad = edad
t1 = "Ahora tengo "
t2 = this.edad
param t2
t2 = call toString, 1
t1 = t1 + t2
t2 = " años."
t1 = t1 + t2
return t1
FUNC incrementarEdad_END:
EndFunc incrementarEdad
FUNC constructor_START:
BeginFunc constructor 3
ActivationRecord constructor
p_nombre = LoadParam 0
p_edad = LoadParam 1
p_grado = LoadParam 2
nombre = nombre
edad = edad
color = color
grado = grado
return
FUNC constructor_END:
EndFunc constructor
FUNC estudiar_START:
BeginFunc estudiar 0
ActivationRecord estudiar
t1 = getprop this, nombre
t2 = " está estudiando en "
t1 = t1 + t2
t2 = this.grado
param t2
t2 = call toString, 1
t1 = t1 + t2
t2 = " grado."
t1 = t1 + t2
return t1
FUNC estudiar_END:
EndFunc estudiar
FUNC promedioNotas_START:
BeginFunc promedioNotas 3
ActivationRecord promedioNotas
p_nota1 = LoadParam 0
p_nota2 = LoadParam 1
p_nota3 = LoadParam 2
t1 = nota1
t2 = nota2
t1 = t1 + t2
t2 = nota3
t1 = t1 + t2
t2 = 3
t1 = t1 / t2
t2 = promedio
return t2
FUNC promedioNotas_END:
EndFunc promedioNotas
t2 = ""
t4 = 3
param t4
t4 = 20
param t4
t4 = nombre
param t4
t4 = call newEstudiante, 3
t5 = log
param juan
t6 = call method saludar, 1
t5 = t5 + t6
t6 = "\n"
t5 = t5 + t6
log = t5
t5 = log
param juan
t6 = call method estudiar, 1
t5 = t5 + t6
t6 = "\n"
t5 = t5 + t6
log = t5
t5 = log
t6 = 5
param t6
param juan
t6 = call method incrementarEdad, 2
t5 = t5 + t6
t6 = "\n"
t5 = t5 + t6
log = t5
t5 = 1
L1:
t6 = i
t7 = 5
t6 = t6 <= t7
if t6 == 0 goto L2
t6 = i
t7 = 2
t6 = t6 % t7
t7 = 0
t6 = t6 == t7
if t6 == 0 goto L3
t6 = log
t7 = i
param t7
t7 = call toString, 1
t6 = t6 + t7
t7 = " es par\n"
t6 = t6 + t7
log = t6
goto L4
L3:
t6 = log
t7 = i
param t7
t7 = call toString, 1
t6 = t6 + t7
t7 = " es impar\n"
t6 = t6 + t7
log = t6
L4:
t6 = i
t7 = 1
t6 = t6 + t7
i = t6
goto L1
L2:
t6 = getprop juan, edad
t7 = 2
t6 = t6 * t7
t7 = 5
t8 = 3
t7 = t7 - t8
t8 = 2
t7 = t7 / t8
t6 = t6 + t7
t7 = log
t8 = "Resultado de la expresión: "
t7 = t7 + t8
t8 = resultado
param t8
t8 = call toString, 1
t7 = t7 + t8
t8 = "\n"
t7 = t7 + t8
log = t7
t7 = 0
t8 = 95
param t8
t8 = 85
param t8
t8 = 90
param t8
param juan
t8 = call method promedioNotas, 4
prom = t8
t8 = log
t9 = "Promedio (entero): "
t8 = t8 + t9
t9 = prom
param t9
t9 = call toString, 1
t8 = t8 + t9
t9 = "\n"
t8 = t8 + t9
log = t8
```
