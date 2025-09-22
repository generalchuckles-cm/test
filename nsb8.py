# nsb8: An Intel 8008 Emulator in Python for NotSoBot
# Part 3.1: Corrected argument handling for file attachments

import sys
import urllib.request

# --- CORRECTED INPUT HANDLER ---
try:
    # The bot passes the attachment URL as the entire 'args' string
    user_input = args
    if user_input.startswith('http'):
        try:
            # When the input is a URL, download the content
            with urllib.request.urlopen(user_input) as response:
               assembly_code = response.read().decode('utf-8', errors='ignore')
            status_prefix = f"Assembled from attached file. "
        except Exception as e:
            assembly_code = "" # Ensure assembly fails
            status_prefix = f"Error: Could not download from URL. {e}"
    else:
        # It's direct code from a code block
        assembly_code = user_input
        status_prefix = "Assembled from code block. "
except (NameError, IndexError):
    assembly_code = ""
    status_prefix = "Error: No code provided. Attach a file, use a code block, or provide a URL."

# ===================================================================
# | Robust 8008 Assembler                                           |
# ===================================================================
def assemble(code, status_prefix):
    """Converts 8008 assembly mnemonics into bytecode."""
    bytecode = []
    
    opcodes = {
        "HLT": (0x01, 0), "LAI": (0x06, 1), "LBI": (0x0E, 1), "LCI": (0x16, 1),
        "LDI": (0x26, 1), "LEI": (0x2E, 1), "LHI": (0x36, 1), "LLI": (0x3E, 1),
        "LAB": (0xC1, 0), "LBA": (0x87, 0), "ADB": (0x80, 0), "LAM": (0xC6, 0),
        "LMA": (0x77, 0), "JMP": (0x44, 2), "INB": (0x0C, 0), "DCB": (0x0D, 0), 
        "SUI": (0x96, 1), "JFC": (0x40, 2), "JTC": (0x48, 2), "CAL": (0x46, 2)
    }

    # Remove comments from each line before processing
    code_no_comments = "\n".join([line.split(';')[0] for line in code.split('\n')])
    tokens = code_no_comments.upper().split()

    i = 0
    while i < len(tokens):
        mnemonic = tokens[i]; i += 1
        if mnemonic in opcodes:
            opcode, num_operands = opcodes[mnemonic]
            bytecode.append(opcode)
            if i + num_operands > len(tokens): return None, f"Error: Mnemonic '{mnemonic}' needs {num_operands} operand(s)."
            
            operands = tokens[i : i + num_operands]; i += num_operands
            
            if num_operands == 1: bytecode.append(int(operands[0]))
            elif num_operands == 2:
                addr = int(operands[0]); bytecode.append(addr & 0xFF); bytecode.append((addr >> 8) & 0xFF)
        else: return None, f"Error: Unknown mnemonic '{mnemonic}'"
            
    status = status_prefix + f"Program size: {len(bytecode)} bytes."
    return bytecode, status

# ===================================================================
# | Intel 8008 CPU Class                                            |
# ===================================================================
class Intel8008:
    def __init__(self):
        self.memory = bytearray(16384)
        self.regs = {'A':0,'B':0,'C':0,'D':0,'E':0,'H':0,'L':0}
        self.flags = {'C':0,'Z':1,'S':0,'P':1}
        self.pc = 0; self.sp = 0; self.stack = [0] * 7; self.halted = False
    def load_program(self, bytecode): self.memory[0:len(bytecode)] = bytecode
    def get_hl(self): return ((self.regs['H'] & 0x3F) << 8) | self.regs['L']
    def read_mem(self, addr): return self.memory[addr & 0x3FFF]
    def write_mem(self, addr, val): self.memory[addr & 0x3FFF] = val & 0xFF
    def update_flags(self, val):
        val &= 0xFF; self.flags['Z'] = 1 if val == 0 else 0; self.flags['S'] = 1 if (val & 0x80) else 0; self.flags['P'] = 1 if bin(val).count('1') % 2 == 0 else 0
    def execute(self):
        for _ in range(300000):
            if self.halted: break
            opcode = self.read_mem(self.pc); self.pc += 1
            if   opcode == 0x01: self.halted = True
            elif opcode == 0x06: self.regs['A'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0x0E: self.regs['B'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0x16: self.regs['C'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0x26: self.regs['D'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0x2E: self.regs['E'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0x36: self.regs['H'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0x3E: self.regs['L'] = self.read_mem(self.pc); self.pc += 1
            elif opcode == 0xC1: self.regs['A'] = self.regs['B']
            elif opcode == 0x87: self.regs['B'] = self.regs['A']
            elif opcode == 0x80: res = self.regs['A'] + self.regs['B']; self.flags['C'] = 1 if res > 255 else 0; self.regs['A'] = res & 0xFF; self.update_flags(self.regs['A'])
            elif opcode == 0xC6: self.regs['A'] = self.read_mem(self.get_hl())
            elif opcode == 0x77: self.write_mem(self.get_hl(), self.regs['A'])
            elif opcode in [0x44, 0x40, 0x48, 0x46]:
                low=self.read_mem(self.pc); high=self.read_mem(self.pc+1); addr=(high<<8)|low; do_jump=False
                if opcode==0x44: do_jump=True
                if opcode==0x40 and self.flags['C']==0: do_jump=True
                if opcode==0x48 and self.flags['C']==1: do_jump=True
                if opcode==0x46: self.stack[self.sp]=self.pc+2; self.sp=(self.sp+1)%7; do_jump=True
                if do_jump: self.pc=addr
                else: self.pc+=2
            elif opcode == 0x0C: self.regs['B'] = (self.regs['B'] + 1) & 0xFF; self.update_flags(self.regs['B'])
            elif opcode == 0x0D: self.regs['B'] = (self.regs['B'] - 1) & 0xFF; self.update_flags(self.regs['B'])
            elif opcode == 0x96: data=self.read_mem(self.pc); self.pc+=1; res=self.regs['A']-data; self.flags['C']=1 if res<0 else 0; self.regs['A']=res&0xFF; self.update_flags(self.regs['A'])
        else: return "Warning: Execution hit max cycle limit."
        return "Execution halted normally."
    def get_screen_output(self):
        output = ""; 
        for char_code in self.memory[0xEEE : 0xFFF + 1]: output += chr(char_code) if 32 <= char_code < 127 else "·"
        return output

# ===================================================================
# | Main Execution Logic                                            |
# ===================================================================
bytecode, status = assemble(assembly_code, status_prefix)
if not bytecode: final_output = status
else:
    cpu = Intel8008(); cpu.load_program(bytecode)
    halt_status = cpu.execute()
    regs, flags = cpu.regs, cpu.flags; czsp = f"{flags['C']}{flags['Z']}{flags['S']}{flags['P']}"
    final_output = (f"{status}\n{halt_status}\n---\n"f"Screen (0xEEE-FFF):\n{cpu.get_screen_output()}\n---\n"f"Final A:{regs['A']} B:{regs['B']} C:{regs['C']} D:{regs['D']} E:{regs['E']} H:{regs['H']} L:{regs['L']} | Flags(CZSP):{czsp}")
print(final_output)
