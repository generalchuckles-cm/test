# nsb8: An Intel 8008 Emulator in Python for NotSoBot
# Part 1: The Foundation and First 10 Instructions

import sys

# NotSoBot passes arguments in a list called 'args'
# We'll default to a test string if 'args' isn't available for local testing
try:
    assembly_code = args[1]
except (NameError, IndexError):
    assembly_code = "LAI 10 HLT" # Default for testing outside the bot

# ===================================================================
# | Simple 8008 Assembler                                           |
# ===================================================================
def assemble(code):
    """Converts 8008 assembly mnemonics into bytecode."""
    bytecode = []
    status = "Assembled successfully. "
    
    opcodes = {
        # Mnemonic: (Opcode, Number of Operands)
        "HLT": (0x01, 0), "LAI": (0x06, 1), "LBI": (0x0E, 1), "LCI": (0x16, 1),
        "LAB": (0xC1, 0), "LBA": (0x87, 0), "ADB": (0x80, 0), "LAM": (0xC6, 0),
        "LMA": (0x77, 0), "JMP": (0x44, 2)
    }

    # Normalize input: handle multiple instructions on one line
    clean_code = code.replace('\n', ' ').upper()
    tokens = [token for token in clean_code.split(' ') if token] # Split and remove empty strings

    i = 0
    while i < len(tokens):
        mnemonic = tokens[i]
        if mnemonic in opcodes:
            opcode, num_operands = opcodes[mnemonic]
            bytecode.append(opcode)
            
            if i + num_operands >= len(tokens):
                return None, f"Error: Mnemonic '{mnemonic}' requires {num_operands} operand(s), but not enough were provided."

            # Handle operands
            if num_operands == 1:
                operand = int(tokens[i+1])
                bytecode.append(operand)
                i += 1
            elif num_operands == 2: # For JMP addr
                addr = int(tokens[i+1])
                low_byte = addr & 0xFF
                high_byte = (addr >> 8) & 0xFF
                bytecode.append(low_byte)
                bytecode.append(high_byte)
                i += 1
        
        else:
            # Handle comments, which might be passed as tokens
            if mnemonic.startswith(';'):
                break # Stop processing at comment
            return None, f"Error: Unknown mnemonic '{mnemonic}'"
        i += 1

    status += f"Program size: {len(bytecode)} bytes."
    return bytecode, status

# ===================================================================
# | Intel 8008 CPU Class                                            |
# ===================================================================
class Intel8008:
    def __init__(self):
        # Memory: 16KB, initialized to zeros
        self.memory = bytearray(16384)
        
        # Registers: A, B, C, D, E, H, L
        self.regs = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'H': 0, 'L': 0}
        
        # Flags: Carry, Zero, Sign, Parity
        self.flags = {'C': 0, 'Z': 1, 'S': 0, 'P': 1}
        
        # Program Counter (14-bit) and Halted state
        self.pc = 0
        self.halted = False

    def load_program(self, bytecode):
        """Copies the assembled program into the CPU's memory."""
        self.memory[0:len(bytecode)] = bytecode

    def get_hl(self):
        """Returns the 14-bit memory address from registers H and L."""
        # H is the high 6 bits, L is the low 8 bits
        return ((self.regs['H'] & 0x3F) << 8) | self.regs['L']

    def update_flags(self, val):
        """Updates Z, S, and P flags based on a result value."""
        val &= 0xFF # Ensure value is 8-bit
        self.flags['Z'] = 1 if val == 0 else 0
        self.flags['S'] = 1 if (val & 0x80) else 0
        
        # Parity check (count set bits)
        parity = 0
        for i in range(8):
            if (val >> i) & 1:
                parity += 1
        self.flags['P'] = 1 if parity % 2 == 0 else 0
        
    def execute(self):
        """The main fetch-decode-execute loop."""
        max_cycles = 200000
        for _ in range(max_cycles):
            if self.halted:
                break
            
            opcode = self.memory[self.pc]
            self.pc += 1

            # --- INSTRUCTION DECODING ---
            if opcode == 0x01: # HLT
                self.halted = True
            
            elif opcode == 0x06: # LAI data
                self.regs['A'] = self.memory[self.pc]
                self.pc += 1
            
            elif opcode == 0x0E: # LBI data
                self.regs['B'] = self.memory[self.pc]
                self.pc += 1
                
            elif opcode == 0x16: # LCI data
                self.regs['C'] = self.memory[self.pc]
                self.pc += 1

            elif opcode == 0xC1: # LAB
                self.regs['A'] = self.regs['B']
            
            elif opcode == 0x87: # LBA
                self.regs['B'] = self.regs['A']
                
            elif opcode == 0x80: # ADB
                result = self.regs['A'] + self.regs['B']
                self.flags['C'] = 1 if result > 255 else 0
                self.regs['A'] = result & 0xFF
                self.update_flags(self.regs['A'])
                
            elif opcode == 0xC6: # LAM
                addr = self.get_hl()
                self.regs['A'] = self.memory[addr]
            
            elif opcode == 0x77: # LMA
                addr = self.get_hl()
                self.memory[addr] = self.regs['A']
                
            elif opcode == 0x44: # JMP addr
                low_byte = self.memory[self.pc]
                high_byte = self.memory[self.pc + 1]
                self.pc = (high_byte << 8) | low_byte
        
        else: # This 'else' belongs to the 'for' loop
            return "Warning: Execution hit max cycle limit."
        return "Execution halted normally."

    def get_screen_output(self):
        """Reads the 'screen' memory region and returns it as a string."""
        screen_mem = self.memory[0xEEE : 0xFFF + 1]
        output = ""
        for char_code in screen_mem:
            if 32 <= char_code < 127:
                output += chr(char_code)
            else:
                output += "·"
        return output

# ===================================================================
# | Main Execution Logic                                            |
# ===================================================================
bytecode, status = assemble(assembly_code)

if not bytecode:
    # If assembly failed, status contains the error message
    final_output = status
else:
    # 1. Create a CPU instance
    cpu = Intel8008()
    # 2. Load the program
    cpu.load_program(bytecode)
    # 3. Execute the program
    halt_status = cpu.execute()
    
    # 4. Format and print the final state
    screen = cpu.get_screen_output()
    regs = cpu.regs
    flags = cpu.flags
    czsp = f"{flags['C']}{flags['Z']}{flags['S']}{flags['P']}"
    
    final_output = (
        f"{status}\n{halt_status}\n---\n"
        f"Screen (0xEEE - 0xFFF):\n{screen}\n---\n"
        f"Final A:{regs['A']} B:{regs['B']} C:{regs['C']} | Flags(CZSP):{czsp}"
    )

# The 'print' function sends the output back to the bot
print(final_output)
