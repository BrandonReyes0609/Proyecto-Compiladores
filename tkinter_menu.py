import tkinter as tk
from tkinter import filedialog, ttk, Menu
import os
from Driver import parse_code_from_string  # Importado desde tu archivo Driver.py

class CompiscriptIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Compiscript IDE Visual")
        self.archivo_actual = None

        self.setup_menu()
        self.setup_tabs()

    def setup_menu(self):
        menu_bar = Menu(self.root)

        menu_cgt = Menu(menu_bar, tearoff=0)
        menu_cgt.add_command(label="Cargar", command=self.cargar_cgt)
        menu_cgt.add_separator()
        menu_cgt.add_command(label="Salir", command=self.root.quit)
        menu_bar.add_cascade(label="Cargar CGT", menu=menu_cgt)

        menu_prueba = Menu(menu_bar, tearoff=0)
        menu_prueba.add_command(label="Abrir", command=self.abrir_archivo)
        menu_prueba.add_command(label="Grabar", command=self.guardar_archivo)
        menu_prueba.add_command(label="Grabar Assembler", command=self.guardar_assembler)
        menu_prueba.add_command(label="Compilar", command=self.compilar)
        menu_bar.add_cascade(label="Archivos de Prueba", menu=menu_prueba)

        self.root.config(menu=menu_bar)

    def setup_tabs(self):
        self.tab_control = ttk.Notebook(self.root)

        # Input Text
        self.text_input = tk.Text(self.tab_control)
        self.tab_control.add(self.text_input, text="Input Text")

        # Árbol Sintáctico
        self.tree_tab = ttk.Frame(self.tab_control)
        self.tree_view = ttk.Treeview(self.tree_tab)
        self.tree_view.pack(fill="both", expand=True)
        self.tab_control.add(self.tree_tab, text="Árbol Sintáctico")

        # Acciones
        self.text_acciones = tk.Text(self.tab_control)
        self.tab_control.add(self.text_acciones, text="Acciones")

        # Mensajes
        self.text_mensajes = tk.Text(self.tab_control)
        self.tab_control.add(self.text_mensajes, text="Mensajes")

        # Código Intermedio
        self.text_codigo_intermedio = tk.Text(self.tab_control)
        self.tab_control.add(self.text_codigo_intermedio, text="Código Intermedio Generado")

        # Código Assembler
        self.text_codigo_assembler = tk.Text(self.tab_control)
        self.tab_control.add(self.text_codigo_assembler, text="Código Assembler Generado")

        self.tab_control.pack(expand=1, fill="both")

    def cargar_cgt(self):
        archivo = filedialog.askopenfilename(filetypes=[("CGT or Compiscript Files", "*.cgt *.cps"), ("All files", "*.*")])
        if archivo:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, contenido)
            self.archivo_actual = archivo
            self.text_mensajes.insert(tk.END, f"Archivo CGT cargado: {archivo}\n")

    def abrir_archivo(self):
        archivo = filedialog.askopenfilename(filetypes=[("Compiscript files", "*.cps"), ("Text files", "*.txt"), ("All files", "*.*")])
        if archivo:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, contenido)
            self.archivo_actual = archivo
            self.text_mensajes.insert(tk.END, f"Archivo abierto: {archivo}\n")

    def guardar_archivo(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".cps", filetypes=[("Compiscript files", "*.cps")])
        if archivo:
            contenido = self.text_input.get("1.0", tk.END)
            with open(archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
            self.text_mensajes.insert(tk.END, f"Archivo guardado como: {archivo}\n")

    def guardar_assembler(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".asm", filetypes=[("Assembler files", "*.asm")])
        if archivo:
            contenido = self.text_codigo_assembler.get("1.0", tk.END)
            with open(archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
            self.text_mensajes.insert(tk.END, f"Assembler guardado en: {archivo}\n")

    def compilar(self):
        texto = self.text_input.get("1.0", tk.END).strip()
        arbol, mensaje = parse_code_from_string(texto)
        self.text_mensajes.insert(tk.END, mensaje + "\n")
        if arbol:
            self.mostrar_arbol(arbol)

    def mostrar_arbol(self, arbol_texto):
        self.tree_view.delete(*self.tree_view.get_children())
        arbol_texto = arbol_texto.strip()

        def agregar_nodo(padre, tokens):
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token == "(":
                    sub_tokens = []
                    depth = 1
                    i += 1
                    while i < len(tokens) and depth > 0:
                        if tokens[i] == "(":
                            depth += 1
                        elif tokens[i] == ")":
                            depth -= 1
                        if depth > 0:
                            sub_tokens.append(tokens[i])
                        i += 1
                    if sub_tokens:
                        nodo = self.tree_view.insert(padre, "end", text=sub_tokens[0])
                        agregar_nodo(nodo, sub_tokens[1:])
                else:
                    self.tree_view.insert(padre, "end", text=token)
                    i += 1

        tokens = arbol_texto.replace("(", " ( ").replace(")", " ) ").split()
        if tokens:
            raiz = self.tree_view.insert("", "end", text=tokens[1] if tokens[0] == "(" else "Raíz")
            agregar_nodo(raiz, tokens[1:])

if __name__ == "__main__":
    root = tk.Tk()
    app = CompiscriptIDE(root)
    root.mainloop()
