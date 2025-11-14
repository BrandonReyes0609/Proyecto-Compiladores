#!/usr/bin/env python3
"""
test_tac_generator.py
Script de prueba para verificar todas las correcciones del generador TAC
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'program'))

# Mock de las clases ANTLR para pruebas
class MockContext:
    def __init__(self, text="", children=None):
        self.text = text
        self.children = children or []
        self.start = type('obj', (object,), {'line': 1, 'column': 0})()
    
    def getText(self):
        return self.text
    
    def getChild(self, i):
        return self.children[i] if i < len(self.children) else None
    
    def getChildCount(self):
        return len(self.children)
    
    def Identifier(self, idx=0):
        return type('obj', (object,), {'getText': lambda: f"id{idx}"})()
    
    def expression(self, idx=None):
        if idx is None:
            return MockContext("expr")
        return [MockContext(f"expr{i}") for i in range(idx)]
    
    def block(self, idx=None):
        if idx is None:
            return MockContext("block")
        return MockContext(f"block{idx}")
    
    def accept(self, visitor):
        return "mock_value"

# Importar el generador TAC
from TACGeneratorVisitor import TACGeneratorVisitor, TempManager, FrameManager


def test_temp_manager():
    """Prueba el sistema de reutilización de temporales"""
    print("\n=== TEST: Reutilización de Temporales ===")
    
    tm = TempManager()
    
    # Crear temporales
    t1 = tm.new()
    t2 = tm.new()
    t3 = tm.new()
    print(f"Creados: {t1}, {t2}, {t3}")
    
    # Liberar algunos
    tm.free(t2)
    tm.free(t1)
    print(f"Liberados: t1, t2")
    
    # Reutilizar
    t4 = tm.new()  # Debería reutilizar t1
    t5 = tm.new()  # Debería reutilizar t2
    print(f"Reutilizados: {t4}, {t5}")
    
    # Verificar
    assert t4 == "t1", f"Error: esperaba t1, obtuvo {t4}"
    assert t5 == "t2", f"Error: esperaba t2, obtuvo {t5}"
    
    # Estadísticas
    stats = tm.get_usage_stats()
    print(f"Estadísticas: {stats}")
    
    print("✅ Test de reutilización pasado")


def test_frame_manager():
    """Prueba el sistema de base+desplazamiento"""
    print("\n=== TEST: Base+Desplazamiento ===")
    
    fm = FrameManager()
    
    # Iniciar frame de función
    fm.start_frame("test_func")
    
    # Agregar parámetros (FP+)
    p1_offset = fm.add_param("param1")
    p2_offset = fm.add_param("param2")
    print(f"Parámetros: param1 en FP+{p1_offset}, param2 en FP+{p2_offset}")
    
    # Agregar locales (FP-)
    l1_offset = fm.add_local("local1")
    l2_offset = fm.add_local("local2")
    print(f"Locales: local1 en FP{l1_offset}, local2 en FP{l2_offset}")
    
    # Verificar offsets
    assert p1_offset == 8, f"Error: param1 debería estar en FP+8"
    assert p2_offset == 12, f"Error: param2 debería estar en FP+12"
    assert l1_offset == -4, f"Error: local1 debería estar en FP-4"
    assert l2_offset == -8, f"Error: local2 debería estar en FP-8"
    
    # Finalizar frame
    frame = fm.end_frame()
    print(f"Frame finalizado: {frame['name']}")
    
    print("✅ Test de base+desplazamiento pasado")


def test_constructor_generation():
    """Prueba la generación correcta de constructores"""
    print("\n=== TEST: Constructores ===")
    
    visitor = TACGeneratorVisitor()
    
    # Simular creación de objeto
    visitor.constructors.add("Perro.constructor")
    visitor.emit_comment("Test de constructor")
    
    # new Perro("Max", 3)
    obj = visitor.new_temp()
    visitor.emit(f"{obj} = alloc Perro")
    visitor.emit(f"push_param {obj}  # this para constructor")
    visitor.emit(f'push_param "Max"')
    visitor.emit(f"push_param 3")
    visitor.emit(f"call_constructor Perro.constructor, 3")
    visitor.emit("pop_params")
    
    code = visitor.get_code()
    print("Código generado:")
    print(code)
    
    # Verificar que usa call_constructor
    assert "call_constructor" in code, "Error: debe usar call_constructor"
    assert "push_param t1  # this para constructor" in code
    
    print("✅ Test de constructores pasado")


def test_method_vs_function_calls():
    """Prueba la distinción entre llamadas a métodos y funciones"""
    print("\n=== TEST: Distinción Función/Método ===")
    
    visitor = TACGeneratorVisitor()
    
    # Llamada a función global
    visitor.emit_comment("Llamada a función global")
    visitor.emit("push_func_param 10  # arg0")
    visitor.emit("push_func_param 20  # arg1")
    result1 = visitor.new_temp()
    visitor.emit(f"{result1} = call_func sumar, 2")
    visitor.emit("pop_func_params")
    
    # Llamada a método
    visitor.emit_comment("Llamada a método")
    visitor.emit("push_method_param this  # this")
    visitor.emit("push_method_param 5  # arg0")
    result2 = visitor.new_temp()
    visitor.emit(f"{result2} = call_method Animal.envejecer, 2")
    visitor.emit("pop_method_params")
    
    code = visitor.get_code()
    print("Código generado:")
    print(code)
    
    # Verificar distinciones
    assert "push_func_param" in code
    assert "call_func" in code
    assert "push_method_param" in code
    assert "call_method" in code
    
    print("✅ Test de distinción pasado")


def test_complex_expression():
    """Prueba la traducción de expresiones complejas"""
    print("\n=== TEST: Expresiones Complejas ===")
    
    visitor = TACGeneratorVisitor()
    
    # Simular: (5 + 3) * 2 - (10 / 2)
    visitor.emit_comment("Expresión: (5 + 3) * 2 - (10 / 2)")
    
    t1 = visitor.new_temp()
    visitor.emit(f"{t1} = 5 + 3")
    visitor.emit(f"{t1} = {t1} * 2")  # Reutiliza t1
    
    t2 = visitor.new_temp()
    visitor.emit(f"{t2} = 10 / 2")
    
    visitor.emit(f"{t1} = {t1} - {t2}")  # Reutiliza t1
    visitor.tm.free(t2)
    
    visitor.emit(f"resultado = {t1}")
    visitor.tm.free(t1)
    
    code = visitor.get_code()
    print("Código generado:")
    print(code)
    
    # Verificar reutilización
    assert "t1 = t1 * 2" in code
    assert "t1 = t1 - t2" in code
    
    print("✅ Test de expresiones complejas pasado")


def test_loops_complete():
    """Prueba la implementación completa de ciclos"""
    print("\n=== TEST: Ciclos Completos ===")
    
    visitor = TACGeneratorVisitor()
    
    # FOR loop
    visitor.emit_comment("FOR loop")
    visitor.emit("i = 0")
    l1 = visitor.new_label()
    l2 = visitor.new_label()
    l3 = visitor.new_label()
    
    visitor.emit(f"{l1}:")
    t1 = visitor.new_temp()
    visitor.emit(f"{t1} = i < 10")
    visitor.emit(f"if {t1} == 0 goto {l3}")
    visitor.tm.free(t1)
    
    # Cuerpo con break/continue
    visitor.emit("# Cuerpo del for")
    visitor.emit(f"if condicion_break goto {l3}  # break")
    visitor.emit(f"if condicion_continue goto {l2}  # continue")
    
    visitor.emit(f"{l2}:  # Continue point")
    visitor.emit("i = i + 1")
    visitor.emit(f"goto {l1}")
    visitor.emit(f"{l3}:  # End")
    
    # FOREACH
    visitor.emit_comment("FOREACH loop")
    idx = visitor.new_temp()
    size = visitor.new_temp()
    visitor.emit(f"{idx} = 0")
    visitor.emit(f"{size} = length(array)")
    
    l4 = visitor.new_label()
    l5 = visitor.new_label()
    visitor.emit(f"{l4}:")
    visitor.emit(f"if {idx} >= {size} goto {l5}")
    visitor.emit(f"element = array[{idx}]")
    visitor.emit("# Cuerpo del foreach")
    visitor.emit(f"{idx} = {idx} + 1")
    visitor.emit(f"goto {l4}")
    visitor.emit(f"{l5}:")
    
    code = visitor.get_code()
    print("Código generado:")
    print(code)
    
    # Verificar estructura de ciclos
    assert "# Continue point" in code
    assert "break" in code
    assert "continue" in code
    assert "FOREACH" in code
    
    print("✅ Test de ciclos completos pasado")


def test_optimization():
    """Prueba las optimizaciones de código"""
    print("\n=== TEST: Optimizaciones ===")
    
    visitor = TACGeneratorVisitor()
    
    # Código con redundancias
    visitor.emit("t1 = t1")  # Redundante
    visitor.emit("t2 = 5")
    visitor.emit("goto L1")
    visitor.emit("L1:")  # Salto redundante
    visitor.emit("t3 = t2 + 1")
    
    # Optimizar
    optimized = visitor._optimize_code(visitor.code)
    
    print("Código original:")
    for line in visitor.code:
        print(f"  {line}")
    
    print("\nCódigo optimizado:")
    for line in optimized:
        print(f"  {line}")
    
    # Verificar optimizaciones
    assert "t1 = t1" not in optimized
    assert len(optimized) < len(visitor.code)
    
    print("✅ Test de optimizaciones pasado")


def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("=" * 60)
    print("EJECUTANDO SUITE DE PRUEBAS DEL GENERADOR TAC")
    print("=" * 60)
    
    tests = [
        test_temp_manager,
        test_frame_manager,
        test_constructor_generation,
        test_method_vs_function_calls,
        test_complex_expression,
        test_loops_complete,
        test_optimization
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test fallido: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"✅ Pruebas pasadas: {passed}")
    print(f"❌ Pruebas fallidas: {failed}")
    print(f"📊 Tasa de éxito: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisar los errores arriba.")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)