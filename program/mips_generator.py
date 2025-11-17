# program/mips_generator.py
import re

class MipsGenerator:
    """
    Generador MIPS final, robusto y orientado a pila.
    Soluciona los problemas de contexto, parsing de TAC y paso de parámetros.
    """
    def __init__(self, tac_instructions_str, symbol_table):
        self.tac_lines = tac_instructions_str.strip().split('\n')
        self.symbols = symbol_table
        self.asm_code = []
        self.data_section = [".data"]
        
        # Mapeos
        self.relational_op_map = {'<': 'slt', '<=': 'sle', '>': 'sgt', '>=': 'sge', '==': 'seq', '!=': 'sne'}
        self.temp_reg_pool = [f"$t{i}" for i in range(10)]

        # Estado del generadors
        self.current_function_name = None
        self.current_function_framesize = 0
        self.var_offset_counter = 8
        self.var_offsets = {}
        self.main_prologue_generated = False
        self.param_counter = 0
        self.string_literals = {}

    def _emit(self, instruction, comment=""):
        self.asm_code.append(f"    {instruction:<20} # {comment}" if comment else f"    {instruction}")

    def _emit_label(self, label_name):
        self.asm_code.append(f"{label_name.strip()}:")

    def _add_string_literal(self, string_val):
        if string_val in self.string_literals: return self.string_literals[string_val]
        label = f"str_{len(self.string_literals)}"
        self.string_literals[string_val] = label
        clean_string = string_val.replace('\\n', '\\n')
        self.data_section.append(f'{label}:  .asciiz {clean_string}')
        return label
            
    def _get_var_addr(self, var_name):
        if var_name not in self.var_offsets:
            self.var_offsets[var_name] = -self.var_offset_counter
            self.var_offset_counter += 4
        return f"{self.var_offsets[var_name]}($fp)"

    def generate(self):
        self._emit(".text")
        self._emit(".globl main")
        
        for line in self.tac_lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith('BeginFunc'): self._translate_BeginFunc(line); continue
            if line.startswith('FUNC'): continue

            if not self.main_prologue_generated:
                self.main_prologue_generated = True
                self._begin_function_context("main", 256)

            self._parse_and_translate(line)
            
        if self.current_function_name == "main":
            self._emit("li $v0, 10", "syscall: exit")
            self._emit("syscall")

        return "\n".join(self.data_section) + "\n\n" + "\n".join(self.asm_code)

    def _parse_and_translate(self, line):
        if line.startswith("return"): self._translate_return(line); return
        if line.startswith("param"): self._translate_param(line); return
        
        match = re.match(r'^(\w+)\s*=\s*LoadParam\s+(\d+)', line)
        if match: self._translate_load_param(match.groups(), line); return
            
        match = re.match(r'^(\w+\.\w+)\s*=\s*(.+)', line)
        if match: self._translate_placeholder(match.groups(), line, is_assignment=True); return
            
        match = re.match(r'^(\w+)\s*=\s*call\s+(method\s+)?(.+)', line)
        if match: self._translate_call(match.groups(), line); return
        
        match = re.match(r'^(\w+)\s*=\s*(getprop|newEstudiante)\s+(.+)', line)
        if match: self._translate_placeholder(match.groups(), line); return

        match = re.match(r'^(\w+)\s*=\s*(\w+\.\w+)', line)
        if match: self._translate_placeholder(match.groups(), line); return
        
        match = re.match(r'^(\w+)\s*=\s*(.+?)\s*(<=|>=|==|!=|<|>)\s*(.+)', line)
        if match: self._translate_relational_op(match.groups(), line); return

        if line.endswith(':'): self._emit_label(line[:-1]); return
        
        match = re.match(r'^goto\s+(\w+)', line)
        if match: self._emit(f"j {match.group(1)}", line); return
        
        match = re.match(r'^if\s+(.+?)\s*(==)\s*0\s+goto\s+(\w+)', line)
        if match: self._translate_if_zero(match.groups(), line); return
            
        match = re.match(r'^(\w+)\s*=\s*(.+?)\s*([+\-*/%])\s*(.+)', line)
        if match: self._translate_binary_op(match.groups(), line); return
            
        match = re.match(r'^(\w+)\s*=\s*(.+)', line)
        if match: self._translate_assign(match.groups(), line); return
            
        self._emit(f"# TAC no reconocido: {line}")
    
    def _begin_function_context(self, name, size):
        self.current_function_name = name
        self.current_function_framesize = size
        self.var_offsets = {}; self.var_offset_counter = 8
        self._emit_label(name if name == "main" else f"func_{name}")
        self._emit(f"# --- Prologue for {name} ---")
        self._emit(f"addi $sp, $sp, -{size}")
        self._emit("sw $ra, 0($sp)")
        self._emit("sw $fp, 4($sp)")
        self._emit("move $fp, $sp")

    def _translate_BeginFunc(self, line):
        func_name = line.split()[1]
        self._begin_function_context(func_name, 128)

    def _translate_return(self, line):
        parts = line.split()
        if len(parts) > 1:
            addr_ret = self._get_var_addr(parts[1])
            self._emit(f"lw $v0, {addr_ret}", f"Set return value from {parts[1]}")
        
        self._emit(f"# --- Epilogue for {self.current_function_name} ---")
        self._emit("lw $ra, 0($fp)")
        self._emit("lw $fp, 4($fp)")
        self._emit(f"addi $sp, $sp, {self.current_function_framesize}")
        self._emit("jr $ra")
        self.current_function_name = None

    def _translate_load_param(self, groups, comment):
        dest, index = groups
        addr_dest = self._get_var_addr(dest)
        self._emit(f"sw $a{index}, {addr_dest}", comment)

    def _translate_param(self, line):
        param_var = line.split(' ')[1]
        if self.param_counter < 4:
            addr_param = self._get_var_addr(param_var)
            self._emit(f"lw $a{self.param_counter}, {addr_param}", f"Load param {param_var} into $a{self.param_counter}")
        self.param_counter += 1

    def _translate_call(self, groups, comment):
        dest, _, func_name_full = groups
        func_name = func_name_full.split(',')[0].strip()
        self.param_counter = 0 # Reset for next call
        self._emit(f"jal func_{func_name}", comment)
        addr_dest = self._get_var_addr(dest)
        self._emit(f"sw $v0, {addr_dest}", f"{dest} = return value")

    def _translate_assign(self, groups, comment):
        dest, source = [s.strip() for s in groups]
        addr_dest = self._get_var_addr(dest)
        
        if source.isdigit() or (source.startswith('-') and source[1:].isdigit()):
            self._emit(f"li {self.temp_reg_pool[0]}, {source}")
        elif source.startswith('"'):
            label = self._add_string_literal(source)
            self._emit(f"la {self.temp_reg_pool[0]}, {label}")
        else:
            addr_source = self._get_var_addr(source)
            self._emit(f"lw {self.temp_reg_pool[0]}, {addr_source}")
        self._emit(f"sw {self.temp_reg_pool[0]}, {addr_dest}", comment)

    def _translate_binary_op(self, groups, comment):
        dest, arg1, op, arg2 = groups
        addr1 = self._get_var_addr(arg1)
        self._emit(f"lw {self.temp_reg_pool[0]}, {addr1}", f"Load {arg1}")
        
        if arg2.isdigit():
             if op in ['/', '%']:
                self._emit(f"li {self.temp_reg_pool[1]}, {arg2}")
                self._emit(f"div {self.temp_reg_pool[0]}, {self.temp_reg_pool[1]}", comment)
                self._emit("mflo {self.temp_reg_pool[0]}" if op == '/' else f"mfhi {self.temp_reg_pool[0]}")
             else:
                self._emit(f"addi {self.temp_reg_pool[0]}, {self.temp_reg_pool[0]}, {arg2}" if op == '+' else f"subi {self.temp_reg_pool[0]}, {self.temp_reg_pool[0]}, {arg2}", comment)
        else:
             addr2 = self._get_var_addr(arg2)
             self._emit(f"lw {self.temp_reg_pool[1]}, {addr2}", f"Load {arg2}")
             if op in ['/', '%']:
                 self._emit(f"div {self.temp_reg_pool[0]}, {self.temp_reg_pool[1]}", comment)
                 self._emit("mflo {self.temp_reg_pool[0]}" if op == '/' else f"mfhi {self.temp_reg_pool[0]}")
             else:
                 self._emit(f"{'add' if op == '+' else 'sub'} {self.temp_reg_pool[0]}, {self.temp_reg_pool[0]}, {self.temp_reg_pool[1]}", comment)

        addr_dest = self._get_var_addr(dest)
        self._emit(f"sw {self.temp_reg_pool[0]}, {addr_dest}", f"Store result in {dest}")
        
    def _translate_relational_op(self, groups, comment):
        dest, arg1, op, arg2 = groups
        addr1 = self._get_var_addr(arg1)
        addr2 = self._get_var_addr(arg2)
        self._emit(f"lw {self.temp_reg_pool[0]}, {addr1}")
        self._emit(f"lw {self.temp_reg_pool[1]}, {addr2}")
        self._emit(f"{self.relational_op_map[op]} {self.temp_reg_pool[0]}, {self.temp_reg_pool[0]}, {self.temp_reg_pool[1]}", comment)
        addr_dest = self._get_var_addr(dest)
        self._emit(f"sw {self.temp_reg_pool[0]}, {addr_dest}")

    def _translate_if_zero(self, groups, comment):
        arg1, _, label = groups
        addr1 = self._get_var_addr(arg1)
        self._emit(f"lw {self.temp_reg_pool[0]}, {addr1}")
        self._emit(f"beq {self.temp_reg_pool[0]}, $zero, {label}", comment)

    def _translate_placeholder(self, groups, comment, is_assignment=False):
        if is_assignment:
            dest_prop, source = groups
            addr_source = self._get_var_addr(source)
            self._emit(f"# PLACEHOLDER: {comment}")
        else:
            dest = groups[0]
            addr_dest = self._get_var_addr(dest)
            self._emit(f"li {self.temp_reg_pool[0]}, 0")
            self._emit(f"sw {self.temp_reg_pool[0]}, {addr_dest}", f"PLACEHOLDER for {comment}")