# archivo Nuevo
# tkinter_menu.py — IDE tipo VS Code con Problemas, AST, Símbolos y squiggles
import os
import re
import io
import tkinter as tk
from tkinter import filedialog, ttk, Menu, messagebox
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import redirect_stdout, redirect_stderr

# IMPORTA la API del Driver dentro de /program
from program.Driver import parse_code_from_string

# Para generar TAC
from program.TACGeneratorVisitor import TACGeneratorVisitor
from scripts.CompiscriptLexer import CompiscriptLexer
from scripts.CompiscriptParser import CompiscriptParser
from antlr4 import InputStream, CommonTokenStream


# ===== Paleta estilo VSCode =====
VSC = {
    "bg": "#1e1e1e", "fg": "#d4d4d4",
    "panel": "#252526", "panel_alt": "#2d2d30",
    "border": "#3c3c3c", "sel_bg": "#264f78",
    "gutter": "#2b2b2b", "line_hl": "#2a2a2a"
}
MONO = ("Consolas", 11)


# ===== Editor con números de línea =====
class CodeEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, style="Panel.TFrame")
        self.v_scroll = ttk.Scrollbar(self, orient="vertical")
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal")

        self.ln = tk.Text(
            self, width=6, padx=4, takefocus=0, wrap="none",
            bg=VSC["gutter"], fg="#888", bd=0, relief="flat", font=MONO, state="disabled"
        )
        self.text = tk.Text(
            self, undo=True, wrap="none",
            bg=VSC["bg"], fg=VSC["fg"], insertbackground=VSC["fg"],
            selectbackground=VSC["sel_bg"], bd=0, relief="flat", font=MONO
        )
        self.text.tag_configure("current_line", background=VSC["line_hl"])
        self.text.tag_configure("problem_highlight", background="#512020")
        self.text.tag_configure("squiggle", underline=True)

        self.text.configure(yscrollcommand=self._on_ys, xscrollcommand=self.h_scroll.set)
        self.v_scroll.configure(command=self._yview)
        self.h_scroll.configure(command=self.text.xview)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.ln.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.v_scroll.grid(row=0, column=2, sticky="ns")
        self.h_scroll.grid(row=1, column=0, columnspan=3, sticky="ew")

        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<Configure>", lambda e: self._recalc_linenums())
        self.text.bind("<KeyRelease>", self._after_key)
        self.text.bind("<ButtonRelease>", self._after_key)

        self._status_cb = None

    # API
    def get(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set(self, content: str):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._recalc_linenums()
        self._highlight_line()
        self._report_pos()

    def goto(self, line: int, col: int = 0, flash: bool = True):
        try:
            idx = f"{int(line)}.{max(int(col),0)}"
            self.text.mark_set("insert", idx)
            self.text.see(idx)
            if flash:
                self.text.tag_remove("problem_highlight", "1.0", "end")
                self.text.tag_add("problem_highlight", idx, f"{idx} lineend")
                self.after(800, lambda: self.text.tag_remove("problem_highlight", "1.0", "end"))
        except Exception:
            pass

    def on_status(self, cb):
        self._status_cb = cb

    # Internos
    def _on_modified(self, *_):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self._recalc_linenums()
            self._highlight_line()
            self._report_pos()

    def _after_key(self, *_):
        self._recalc_linenums()
        self._highlight_line()
        self._report_pos()

    def _recalc_linenums(self):
        total = int(self.text.index("end-1c").split(".")[0])
        nums = "\n".join(str(i) for i in range(1, total + 1))
        self.ln.configure(state="normal")
        self.ln.delete("1.0", "end")
        self.ln.insert("1.0", nums)
        self.ln.configure(state="disabled")

    def _highlight_line(self):
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", "insert linestart", "insert lineend+1c")

    def _report_pos(self):
        if self._status_cb:
            ln, col = self.text.index("insert").split(".")
            self._status_cb(int(ln), int(col))

    def _on_ys(self, first, last):
        self.v_scroll.set(first, last)
        self.ln.yview_moveto(first)

    def _yview(self, *args):
        self.text.yview(*args)
        self.ln.yview(*args)


# ===== Explorador =====
class Explorer(ttk.Frame):
    def __init__(self, master, on_open):
        super().__init__(master, style="Panel.TFrame")
        self.on_open = on_open
        self.tree = ttk.Treeview(self, show="tree")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewOpen>>", self._open_node)
        self.tree.bind("<Double-1>", self._double)

    def load_root(self, path: str):
        root = os.path.abspath(path)
        for i in self.tree.get_children(""):
            self.tree.delete(i)
        rid = self.tree.insert("", "end", text=os.path.basename(root) or root, open=True, values=[root])
        self._fill(rid, root)

    def _fill(self, node, path):
        try:
            entries = sorted(os.listdir(path))
        except Exception:
            return
        for name in entries:
            if name.startswith("."):
                continue
            full = os.path.join(path, name)
            if os.path.isdir(full):
                nid = self.tree.insert(node, "end", text=name, values=[full])
                self.tree.insert(nid, "end", text="…", values=["__lazy__"])
            else:
                if name.lower().endswith((".cps", ".cgt", ".txt", ".asm")):
                    self.tree.insert(node, "end", text=name, values=[full])

    def _open_node(self, *_):
        item = self.tree.focus()
        if not item:
            return
        path = self.tree.item(item, "values")[0]
        if not os.path.isdir(path):
            return
        self.tree.delete(*self.tree.get_children(item))
        self._fill(item, path)

    def _double(self, *_):
        item = self.tree.focus()
        if not item:
            return
        path = self.tree.item(item, "values")[0]
        if os.path.isfile(path):
            self.on_open(path)


# ===== Aplicación =====
class CompiscriptIDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Compiscript IDE — (sin título)")
        self.geometry("1200x720")
        self.minsize(900, 560)

        self.archivo_actual: Optional[Path] = None

        self._setup_theme()
        self._setup_menu()
        self._setup_toolbar()

        # Split vertical (arriba/abajo)
        self.vsplit = tk.PanedWindow(self, orient=tk.VERTICAL, sashwidth=6, bg=VSC["border"], bd=0, relief="flat")
        self.vsplit.pack(fill="both", expand=True)

        # Parte superior: split horizontal (explorer | editor | panel derecho)
        top = tk.PanedWindow(self.vsplit, orient=tk.HORIZONTAL, sashwidth=6, bg=VSC["border"], bd=0, relief="flat")
        self.vsplit.add(top, minsize=260)

        # Explorer
        self.explorer = Explorer(top, self._open_from_explorer)
        top.add(self.explorer, minsize=220, width=260)

        # Editor
        self.editor = CodeEditor(top)
        top.add(self.editor, minsize=400)
        self.editor.on_status(self._update_status_bar)

        # Panel derecho: Notebook con AST y Símbolos
        right = ttk.Frame(top, style="Panel.TFrame")
        top.add(right, minsize=260, width=360)

        self.right_tabs = ttk.Notebook(right)
        self.right_tabs.pack(fill="both", expand=True, padx=6, pady=6)

        # AST tab
        ast_frame = ttk.Frame(self.right_tabs, style="Panel.TFrame")
        self.tree_ast = ttk.Treeview(ast_frame)
        self.tree_ast.pack(fill="both", expand=True)
        self.right_tabs.add(ast_frame, text="Árbol")

        # Símbolos tab
        sym_frame = ttk.Frame(self.right_tabs, style="Panel.TFrame")
        cols = ("SCOPE", "NAME", "TYPE", "CONST", "LINE", "COL")
        self.tree_sym = ttk.Treeview(sym_frame, columns=cols, show="headings")
        for c, w in (("SCOPE", 110), ("NAME", 160), ("TYPE", 160), ("CONST", 60), ("LINE", 60), ("COL", 60)):
            self.tree_sym.heading(c, text=c)
            self.tree_sym.column(c, width=w, anchor="w")
        self.tree_sym.pack(fill="both", expand=True)
        self.tree_sym.bind("<Double-1>", self._jump_to_symbol)
        self.right_tabs.add(sym_frame, text="Símbolos")

        # Panel inferior: Problemas/Mensajes/Acciones/IR/ASM
        bottom = ttk.Frame(self.vsplit, style="PanelAlt.TFrame")
        self.vsplit.add(bottom, minsize=160, height=240)

        self.tabs = ttk.Notebook(bottom)
        self.tabs.pack(fill="both", expand=True)

        # Problemas
        self.problems = ttk.Treeview(self.tabs, columns=("SEV", "LINE", "COL", "MSG"), show="headings", height=6)
        for c, w in (("SEV", 80), ("LINE", 60), ("COL", 60), ("MSG", 900)):
            self.problems.heading(c, text=c)
            self.problems.column(c, width=w, anchor="w")
        self.problems.bind("<Double-1>", self._jump_to_problem)
        self.tabs.add(self.problems, text="Problemas")

        # Mensajes
        self.txt_msg = tk.Text(self.tabs, bg=VSC["panel_alt"], fg=VSC["fg"], bd=0, relief="flat", font=MONO, wrap="word")
        self.tabs.add(self.txt_msg, text="Mensajes")

        # Acciones
        self.txt_acc = tk.Text(self.tabs, bg=VSC["panel_alt"], fg=VSC["fg"], bd=0, relief="flat", font=MONO, wrap="word")
        self.tabs.add(self.txt_acc, text="Acciones")

        # IR
        self.txt_ir = tk.Text(self.tabs, bg=VSC["panel_alt"], fg=VSC["fg"], bd=0, relief="flat", font=MONO, wrap="none")
        self.tabs.add(self.txt_ir, text="Código Intermedio")

        # ASM
        self.txt_asm = tk.Text(self.tabs, bg=VSC["panel_alt"], fg=VSC["fg"], bd=0, relief="flat", font=MONO, wrap="none")
        self.tabs.add(self.txt_asm, text="Código Assembler")

        # Status
        self.status = ttk.Label(self, text="Ln 1, Col 0", style="Status.TLabel", anchor="w")
        self.status.pack(fill="x")

        # Inicialización
        self.explorer.load_root(os.getcwd())
        self.editor.set("")

        # Atajos
        self.bind_all("<Control-o>", lambda e: self.abrir_archivo())
        self.bind_all("<Control-s>", lambda e: self.guardar_archivo())
        self.bind_all("<Control-n>", lambda e: self.nuevo_archivo())
        self.bind_all("<F5>",        lambda e: self.compilar())

    # ===== Tema =====
    def _setup_theme(self):
        self.configure(bg=VSC["panel"])
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Panel.TFrame", background=VSC["panel"])
        st.configure("PanelAlt.TFrame", background=VSC["panel_alt"])
        st.configure("Caption.TLabel", background=VSC["panel"], foreground="#bbb")
        st.configure("Status.TLabel", background=VSC["panel_alt"], foreground="#aaa", padding=(8, 2))
        st.configure("TNotebook", background=VSC["panel"])
        st.configure("TNotebook.Tab", background=VSC["panel_alt"], foreground=VSC["fg"])
        st.map("TNotebook.Tab", background=[("selected", VSC["panel"])])
        st.configure("Treeview",
                     background=VSC["panel_alt"], fieldbackground=VSC["panel_alt"],
                     foreground=VSC["fg"], bordercolor=VSC["border"])
        st.configure("Treeview.Heading", background=VSC["panel"], foreground=VSC["fg"])

    # ===== Menú/Toolbar =====
    def _setup_menu(self):
        mb = Menu(self)

        m_cgt = Menu(mb, tearoff=0)
        m_cgt.add_command(label="Cargar", command=self.cargar_cgt)
        m_cgt.add_separator()
        m_cgt.add_command(label="Salir", command=self.quit)
        mb.add_cascade(label="Cargar CGT", menu=m_cgt)

        m_pr = Menu(mb, tearoff=0)
        m_pr.add_command(label="Abrir", command=self.abrir_archivo, accelerator="Ctrl+O")
        m_pr.add_command(label="Grabar", command=self.guardar_archivo, accelerator="Ctrl+S")
        m_pr.add_command(label="Nuevo", command=self.nuevo_archivo, accelerator="Ctrl+N")
        m_pr.add_command(label="Grabar Assembler", command=self.guardar_assembler)
        m_pr.add_separator()
        m_pr.add_command(label="Compilar", command=self.compilar, accelerator="F5")
        mb.add_cascade(label="Archivo de Prueba", menu=m_pr)

        m_build = Menu(mb, tearoff=0)
        m_build.add_command(label="Compilar (F5)", command=self.compilar, accelerator="F5")
        mb.add_cascade(label="Compilar", menu=m_build)

        self.config(menu=mb)

    def _setup_toolbar(self):
        bar = ttk.Frame(self, style="Panel.TFrame")
        bar.pack(fill="x")

        def btn(txt, cmd):
            b = ttk.Button(bar, text=txt, command=cmd)
            b.pack(side="left", padx=(8, 0), pady=6)
            return b

        btn("Abrir", self.abrir_archivo)
        btn("Guardar", self.guardar_archivo)
        btn("Compilar (F5)", self.compilar)

    # ===== Acciones de archivo =====
    def nuevo_archivo(self):
        self.editor.set("")
        self.archivo_actual = None
        self._title("(sin título)")

    def abrir_archivo(self):
        f = filedialog.askopenfilename(
            title="Abrir archivo",
            filetypes=[("Compiscript", "*.cps"), ("Texto", "*.txt"), ("Todos", "*.*")]
        )
        if not f:
            return
        self._open_file(Path(f))

    def _open_from_explorer(self, path: str):
        self._open_file(Path(path))

    def _open_file(self, path: Path):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return messagebox.showerror("Abrir", f"No se pudo abrir:\n{e}")
        self.editor.set(content)
        self.archivo_actual = path
        self._title(str(path))
        self.explorer.load_root(path.parent)

    def guardar_archivo(self):
        if not self.archivo_actual:
            f = filedialog.asksaveasfilename(defaultextension=".cps",
                                             filetypes=[("Compiscript", "*.cps"), ("Texto", "*.txt")])
            if not f:
                return
            self.archivo_actual = Path(f)
        try:
            self.archivo_actual.write_text(self.editor.get(), encoding="utf-8")
            self._msg(f"Guardado: {self.archivo_actual}\n")
            self._title(str(self.archivo_actual))
        except Exception as e:
            messagebox.showerror("Guardar", f"No se pudo guardar:\n{e}")

    def guardar_assembler(self):
        f = filedialog.asksaveasfilename(defaultextension=".asm", filetypes=[("Assembler", "*.asm")])
        if not f:
            return
        try:
            Path(f).write_text(self.txt_asm.get("1.0", "end-1c"), encoding="utf-8")
            self._msg(f"Assembler guardado en: {f}\n")
        except Exception as e:
            messagebox.showerror("Assembler", f"No se pudo guardar:\n{e}")

    def cargar_cgt(self):
        f = filedialog.askopenfilename(
            title="Cargar CGT/Compiscript",
            filetypes=[("CGT/Compiscript", "*.cgt *.cps"), ("Todos", "*.*")]
        )
        if not f:
            return
        try:
            s = Path(f).read_text(encoding="utf-8")
        except Exception as e:
            return messagebox.showerror("Cargar", f"No se pudo leer:\n{e}")
        self.editor.set(s)
        self.archivo_actual = Path(f)
        self._title(str(self.archivo_actual))
        self._msg(f"Archivo CGT/CPS cargado: {f}\n")

    # ===== Compilación =====
    def compilar(self):
        src = self.editor.get().strip()
        if not src:
            return self._msg("Nada que compilar (archivo vacío).\n")

        # Limpia vistas
        self._set_ast("(vacío)")
        self._set_symbols(None)
        for w in (self.txt_msg, self.txt_acc, self.txt_ir, self.txt_asm):
            self._set_text(w, "")
        self._set_problems([])
        self._clear_squiggles()

        # Ejecutar Driver y capturar stdout/stderr
        out_buf, err_buf = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out_buf), redirect_stderr(err_buf):
                result = parse_code_from_string(src)
        except Exception as e:
            self._msg(f"❌ Error ejecutando Driver: {e}\n")
            return messagebox.showerror("Compilar", str(e))
        printed = (out_buf.getvalue() + err_buf.getvalue())

        # Normalizar resultado
        if isinstance(result, dict):
            tree = result.get("parse_tree", "")
            messages = (result.get("messages") or "")
            if printed:
                messages = (messages + "\n" + printed).strip()
            actions = result.get("actions", "") or ""
            ir = result.get("ir", "") or ""
            asm = result.get("asm", "") or ""
            errors = result.get("errors")              # puede ser [], y eso ya significa “sin errores”
            if errors is None:                         # sólo si la clave no viene, inferimos desde texto
                errors = self._infer_errors(messages)
            timings = result.get("timings") or {}
            symbols = result.get("symbols")
        else:
            tree = ""
            messages = (str(result) + ("\n" + printed if printed else ""))
            actions = ir = asm = ""
            errors = self._infer_errors(messages)
            timings = {}
            symbols = None

        # Poblar UI
        self._set_ast(tree or "(sin árbol)")
        self._set_text(self.txt_msg, messages or "")
        self._set_text(self.txt_acc, actions or "")
        self._set_text(self.txt_ir, ir or "")
        self._set_text(self.txt_asm, asm or "")
        self._set_problems(errors)
        self._apply_squiggles(errors)
        self._set_symbols(symbols)

        # Timings al final de mensajes
        if timings:
            parts = []
            if "parse_ms" in timings: parts.append(f"Parse {timings['parse_ms']} ms")
            if "semantic_ms" in timings: parts.append(f"Semántica {timings['semantic_ms']} ms")
            if "ir_ms" in timings: parts.append(f"IR {timings['ir_ms']} ms")
            if "asm_ms" in timings: parts.append(f"ASM {timings['asm_ms']} ms")
            if parts:
                self._msg(" | ".join(parts) + "\n")

        if errors:
            self.tabs.select(self.problems)
        else:
            self._msg("✅ Compilación sin errores.\n")

    # ===== AST =====
    def _set_ast(self, s: str):
        self.tree_ast.delete(*self.tree_ast.get_children())
        txt = (s or "").strip()
        if not txt:
            return
        try:
            toks = txt.replace("(", " ( ").replace(")", " ) ").split()
            if not toks:
                raise ValueError()

            def add(parent, tokens):
                i = 0
                while i < len(tokens):
                    t = tokens[i]
                    if t == "(":
                        sub, d = [], 1
                        i += 1
                        while i < len(tokens) and d > 0:
                            if tokens[i] == "(":
                                d += 1
                            elif tokens[i] == ")":
                                d -= 1
                            if d > 0:
                                sub.append(tokens[i])
                            i += 1
                        if sub:
                            node = self.tree_ast.insert(parent, "end", text=sub[0])
                            add(node, sub[1:])
                    else:
                        self.tree_ast.insert(parent, "end", text=t)
                        i += 1

            root_label = toks[1] if toks and toks[0] == "(" and len(toks) > 1 else "program"
            root = self.tree_ast.insert("", "end", text=root_label)
            add(root, toks[1:])
        except Exception:
            self.tree_ast.insert("", "end", text=(txt[:120] + ("…" if len(txt) > 120 else "")))

    # ===== Símbolos =====
    def _set_symbols(self, symbols_tree: Any):
        """Puebla la pestaña 'Símbolos'. Espera un dict jerárquico:
           {
             "scope": "global",
             "symbols": [{"name":..., "type":..., "const":bool, "line":int?, "col":int?}, ...],
             "children": [ <subscopes> ]
           }
           Si es None, muestra (sin datos).
        """
        self.tree_sym.delete(*self.tree_sym.get_children())

        if not symbols_tree:
            self.tree_sym.insert("", "end",
                                 values=("—", "(sin datos)", "", "", "", ""))
            return

        def to_str(v):
            try:
                return str(v)
            except Exception:
                return repr(v)

        rows: List[tuple] = []

        def walk(scope_node, scope_name: str):
            # Cargar símbolos de este scope
            for sym in (scope_node.get("symbols") or []):
                rows.append((
                    scope_name,
                    to_str(sym.get("name")),
                    to_str(sym.get("type")),
                    "yes" if sym.get("const") else "no",
                    sym.get("line", ""),
                    sym.get("col", ""),
                ))
            # Recurse sub-scopes
            for child in (scope_node.get("children") or []):
                child_name = to_str(child.get("scope") or f"{scope_name}::anon")
                walk(child, child_name)

        root_name = to_str(symbols_tree.get("scope") or "global")
        walk(symbols_tree, root_name)

        if not rows:
            self.tree_sym.insert("", "end",
                                 values=(root_name, "(sin símbolos)", "", "", "", ""))
            return

        for r in rows:
            self.tree_sym.insert("", "end", values=r)

    def _jump_to_symbol(self, *_):
        item = self.tree_sym.focus()
        if not item:
            return
        scope, name, typ, const, line, col = self.tree_sym.item(item, "values")
        try:
            if line != "" and col != "":
                self.editor.goto(int(line), int(col))
        except Exception:
            pass

    # ===== Problemas / Squiggles =====
    def _set_problems(self, items: List[Dict[str, Any]]):
        self.problems.delete(*self.problems.get_children())
        for it in items or []:
            sev = (it.get("sev") or "ERROR").upper()
            line = it.get("line") if it.get("line") is not None else "-"
            col = it.get("col") if it.get("col") is not None else "-"
            msg = it.get("msg") or ""
            self.problems.insert("", "end", values=(sev, line, col, msg))

    def _jump_to_problem(self, *_):
        sel = self.problems.focus()
        if not sel:
            return
        sev, line, col, msg = self.problems.item(sel, "values")
        try:
            self.editor.goto(int(line), int(col))
        except Exception:
            pass

    def _clear_squiggles(self):
        try:
            self.editor.text.tag_remove("squiggle", "1.0", "end")
        except Exception:
            pass

    def _apply_squiggles(self, errors):
        for e in errors or []:
            if e.get("line") is None:
                continue
            try:
                line = int(e["line"])
                col = int(e.get("col", 0))
            except Exception:
                continue
            try:
                self.editor.text.tag_add("squiggle", f"{line}.{col}", f"{line}.end")
            except Exception:
                pass

    # ===== Helpers =====
    def _infer_errors(self, text: str) -> List[Dict[str, Any]]:
        if not text:
            return []
        out: List[Dict[str, Any]] = []
        pats = [
            r"^line\s+(?P<line>\d+)\s*[: ,]\s*(?P<col>\d+)\s*(?P<msg>.*)$",
            r"^[Ll]í?nea\s+(?P<line>\d+)\s*,?\s*[Cc](?:ol(?:\.|umna)?)?\s*(?P<col>\d+)\s*[:\-]?\s*(?P<msg>.*)$",
            r"^(?P<msg>mismatched input .+? expecting .+)$",
            r"^(?P<msg>no viable alternative at input .+)$",
            r"^(?P<msg>missing .+ at .+)$",
            r"^(?P<msg>extraneous input .+ expecting .+)$",
            r"^(?P<msg>token recognition error at: .+)$",
            r"^(?P<msg>error .+)$",
        ]
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            matched = False
            for pat in pats:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    d = {"sev": "error", "line": None, "col": None, "msg": m.groupdict().get("msg", "").strip() or line}
                    if "line" in m.groupdict() and m.group("line"):
                        try:
                            d["line"] = int(m.group("line"))
                        except Exception:
                            pass
                    if "col" in m.groupdict() and m.group("col"):
                        try:
                            d["col"] = int(m.group("col"))
                        except Exception:
                            pass
                    out.append(d)
                    matched = True
                    break
            lower = line.lower()
            if (not matched and (("error" in lower) or ("missing" in lower))
                and not re.search(r"\b(?:sin|no)\s+error(?:es)?\b", lower)):
                out.append({"sev": "error", "line": None, "col": None, "msg": line})
        return out

    def _set_text(self, w: tk.Text, s: str):
        w.delete("1.0", "end")
        if s:
            w.insert("1.0", s)

    def _msg(self, s: str):
        self.txt_msg.insert("end", s)
        self.txt_msg.see("end")

    def _title(self, t: str):
        self.title(f"Compiscript IDE — {t}")

    def _update_status_bar(self, ln: int, col: int):
        path = str(self.archivo_actual) if self.archivo_actual else "(sin título)"
        self.status.config(text=f"{path}    Ln {ln}, Col {col}")


if __name__ == "__main__":
    app = CompiscriptIDE()
    app.mainloop()
