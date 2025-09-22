# nsb8: An Intel 8008 Emulator in Python for NotSoBot
# FINAL VERSION: Self-contained system with program management and emulation.

import sys

# ===================================================================
# | SYSTEM CORE: Determines the mode (Manage or Emulate)            |
# ===================================================================
try:
    # NotSoBot passes the whole command string as 'args'
    full_command = args.split()
    sub_command = full_command[0].lower()

    if sub_command in ["new", "cont"]:
        # --- MODE 1: PROGRAM MANAGER ---
        # Usage: .nsb8 new <name> <code>
        #   or   .nsb8 cont <name> <code>
        # This mode GENERATES a bot command for the user to run.
        if len(full_command) < 3:
            final_output = "Error: Manager mode requires a name and code. Usage: .nsb8 new <program_name> <your_code...>"
        else:
            program_name = full_command[1]
            # The rest is the assembly code
            assembly_code = " ".join(full_command[2:])
            # We format this into a command that creates/updates a tag.
            # The user must copy and run this output.
            final_output = (
                f"Copy the following command and run it to save your program:\n"
                f"```\n"
                f".t add {program_name} {{text:\n{assembly_code}\n}}\n"
                f"```"
            )

    elif sub_command == "run":
        # --- MODE 2: EMULATOR (with 'run' keyword) ---
        # Usage: .nsb8 run {tag:program_name}
        # The 'run' keyword is ignored, and the rest is treated as code.
        assembly_code = " ".join(full_command[1:])
        # Now we proceed to the assembler and emulator...

    else:
        # --- MODE 3: EMULATOR (direct execution) ---
        # Usage: .nsb8 <raw_code> or .nsb8 {tag:program_name}
        # The entire input is treated as code.
        assembly_code = args
        # Now we proceed to the assembler and emulator...

except (NameError, IndexError):
    final_output = "Error: No command provided. Use 'new', 'cont', or 'run'."

# If we are in an emulation mode, the 'assembly_code' variable is set.
# If we were in manager mode, the script would have already set 'final_output' and will skip this.
if 'assembly_code' in locals():
    # ===================================================================
    # | 8008 Assembler & CPU (Self-Contained)                         |
    # ===================================================================
    def assemble(code):
        bytecode = []
        opcodes = {
            "HLT": (0x01, 0), "LAI": (0x06, 1), "LBI": (0x0E, 1), "LCI": (0x16, 1),
            "LDI": (0x26, 1), "LEI": (0x2E, 1), "LHI": (0x36, 1), "LLI": (0x3E, 1),
            "LAB": (0xC1, 0), "LBA": (0x87, 0), "ADB": (0x80, 0), "LAM": (0xC6, 0),
            "LMA": (0x77, 0), "JMP": (0x44, 2), "INB": (0x0C, 0), "DCB": (0x0D, 0), 
            "SUI": (0x96, 1), "JFC": (0x40, 2), "JTC": (0x48, 2), "CAL": (0x46, 2)
        }
        code_no_comments = "\n".join([line.split(';')[0] for line in code.split('\n')])
        tokens = code_no_comments.upper().split()
        i = 0
        while i < len(tokens):
            mnemonic = tokens[i]; i += 1
            if mnemonic in opcodes:
                opcode, num_operands = opcodes[mnemonic]
                bytecode.append(opcode)
                if i + num_operands > len(tokens): return None, f"Error: '{mnemonic}' needs {num_operands} operand(s)."
                operands = tokens[i : i + num_operands]; i += num_operands
                if num_operands == 1: bytecode.append(int(operands[0]))
                elif num_operands == 2:
                    addr=int(operands[0]); bytecode.append(addr & 0xFF); bytecode.append((addr >> 8) & 0xFF)
            else: return None, f"Error: Unknown mnemonic '{mnemonic}'"
        return bytecode, f"Assembled successfully. Program size: {len(bytecode)} bytes."

    class Intel8008:
        def __init__(self):
            self.memory = bytearray(16384); self.regs = {'A':0,'B':0,'C':0,'D':0,'E':0,'H':0,'L':0}
            self.flags = {'C':0,'Z':1,'S':0,'P':1}; self.pc = 0; self.sp = 0; self.stack = [0]*7; self.halted = False
        def load_program(self, b): self.memory[0:len(b)] = b
        def get_hl(self): return ((self.regs['H'] & 0x3F) << 8) | self.regs['L']
        def read_mem(self, a): return self.memory[a & 0x3FFF]
        def write_mem(self, a, v): self.memory[a & 0x3FFF] = v & 0xFF
        def update_flags(self, v):
            v &= 0xFF; self.flags['Z']=1 if v==0 else 0; self.flags['S']=1 if(v&0x80)else 0; self.flags['P']=1 if bin(v).count('1')%2==0 else 0
        def execute(self):
            for _ in range(300000):
                if self.halted: break
                op=self.read_mem(self.pc); self.pc+=1
                if op==0x01: self.halted=True
                elif op==0x06: self.regs['A']=self.read_mem(self.pc); self.pc+=1
                elif op==0x0E: self.regs['B']=self.read_mem(self.pc); self.pc+=1
                elif op==0x16: self.regs['C']=self.read_mem(self.pc); self.pc+=1
                elif op==0x26: self.regs['D']=self.read_mem(self.pc); self.pc+=1
                elif op==0x2E: self.regs['E']=self.read_mem(self.pc); self.pc+=1
                elif op==0x36: self.regs['H']=self.read_mem(self.pc); self.pc+=1
                elif op==0x3E: self.regs['L']=self.read_mem(self.pc); self.pc+=1
                elif op==0xC1: self.regs['A']=self.regs['B']
                elif op==0x87: self.regs['B']=self.regs['A']
                elif op==0x80: r=self.regs['A']+self.regs['B']; self.flags['C']=1 if r>255 else 0; self.regs['A']=r&0xFF; self.update_flags(self.regs['A'])
                elif op==0xC6: self.regs['A']=self.read_mem(self.get_hl())
                elif op==0x77: self.write_mem(self.get_hl(), self.regs['A'])
                elif op in [0x44,0x40,0x48,0x46]:
                    l=self.read_mem(self.pc);h=self.read_mem(self.pc+1);a=(h<<8)|l;j=False
                    if op==0x44: j=True
                    if op==0x40 and self.flags['C']==0: j=True
                    if op==0x48 and self.flags['C']==1: j=True
                    if op==0x46: self.stack[self.sp]=self.pc+2;self.sp=(self.sp+1)%7;j=True
                    if j: self.pc=a
                    else: self.pc+=2
                elif op==0x0C: self.regs['B']=(self.regs['B']+1)&0xFF; self.update_flags(self.regs['B'])
                elif op==0x0D: self.regs['B']=(self.regs['B']-1)&0xFF; self.update_flags(self.regs['B'])
                elif op==0x96: d=self.read_mem(self.pc);self.pc+=1;r=self.regs['A']-d;self.flags['C']=1 if r<0 else 0; self.regs['A']=r&0xFF;self.update_flags(self.regs['A'])
            else: return "Warning: Execution hit max cycle limit."
            return "Execution halted normally."
        def get_screen(self):
            o=""; s=self.memory[0xEEE:0xFFF+1];
            for c in s: o+=chr(c) if 32<=c<127 else "·"
            return o

    bytecode, status = assemble(assembly_code)
    if not bytecode: final_output = status
    else:
        cpu=Intel8008(); cpu.load_program(bytecode); halt_status=cpu.execute()
        r,f=cpu.regs,cpu.flags; czsp=f"{f['C']}{f['Z']}{f['S']}{f['P']}"
        final_output=(f"{status}\n{halt_status}\n---\nScreen (0xEEE-FFF):\n{cpu.get_screen()}\n---\n"
                      f"Final A:{r['A']} B:{r['B']} C:{r['C']} D:{r['D']} E:{r['E']} H:{r['H']} L:{r['L']} | Flags(CZSP):{czsp}")

# This is the final print that sends the result back to Discord.
print(final_output)
