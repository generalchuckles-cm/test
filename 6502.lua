-- nsb8: An Intel 8008 Emulator in Lua for NotSoBot
-- Part 2.2: Removed all modulo (%) operators for ultra-compatibility

local assembly_code = args[1]
if not assembly_code then
    return "Error: No 8008 assembly code provided. Example: .nsb8 LBI 42 LAI 10 ADB HLT"
end

-- ===================================================================
-- | Helper function to replace the '%' operator                   |
-- ===================================================================
local function modulo(a, b)
    return a - math.floor(a / b) * b
end

-- ===================================================================
-- | Simple 8008 Assembler                                           |
-- ===================================================================
local function assemble(code)
    local bytecode, status = {}, "Assembled successfully. "
    local opcodes = {
        HLT = {0x01, 0}, LAI = {0x06, 1}, LBI = {0x0E, 1}, LCI = {0x16, 1},
        LAB = {0xC1, 0}, LBA = {0x87, 0}, ADB = {0x80, 0}, LAM = {0xC6, 0},
        LMA = {0x77, 0}, JMP = {0x44, 2}
    }

    for line_num, line in ipairs(code:split('\n')) do
        line = line:gsub(';.*', ''):gsub('^%s*', ''):gsub('%s*$', '')
        if line ~= '' then
            local parts = line:split('%s+')
            local mnemonic = parts[1]:upper()
            if opcodes[mnemonic] then
                local op_info = opcodes[mnemonic]
                table.insert(bytecode, op_info[1])
                if #parts - 1 ~= op_info[2] then
                    return nil, "Error on line " .. line_num .. ": Mnemonic '" .. mnemonic .. "' expects " .. op_info[2] .. " operand(s)."
                end
                if op_info[2] == 1 then
                    table.insert(bytecode, tonumber(parts[2]))
                elseif op_info[2] == 2 then
                    local addr = tonumber(parts[2])
                    local low_byte = modulo(addr, 256)
                    local high_byte = modulo(math.floor(addr / 256), 256)
                    table.insert(bytecode, low_byte)
                    table.insert(bytecode, high_byte)
                end
            else
                return nil, "Error on line " .. line_num .. ": Unknown mnemonic '" .. mnemonic .. "'"
            end
        end
    end
    status = status .. "Program size: " .. #bytecode .. " bytes."
    return bytecode, status
end

-- ===================================================================
-- | Intel 8008 Emulator Core                                        |
-- ===================================================================
local regs = { [0]=0, [1]=0, [2]=0, [3]=0, [4]=0, [5]=0, [7]=0 }
local reg_map = { B=0, C=1, D=2, E=3, H=4, L=5, A=7 }
local flags = { C=0, Z=1, S=0, P=1 }
local pc, sp, stack, halted = 0, 0, {0,0,0,0,0,0,0}, false
local memory = {}
for i = 0, 16383 do memory[i] = 0 end

local function read_byte(addr) return memory[modulo(addr, 16384)] or 0 end
local function write_byte(addr, val) memory[modulo(addr, 16384)] = modulo(val, 256) end
local function get_hl() return (modulo(regs[reg_map.H], 64)) * 256 + regs[reg_map.L] end
local function update_flags(val)
    val = modulo(val, 256)
    flags.Z = (val == 0) and 1 or 0
    flags.S = (val >= 128) and 1 or 0
    local p_count = 0
    for i=0,7 do if modulo(math.floor(val / (2^i)), 2) == 1 then p_count=p_count+1 end end
    flags.P = (modulo(p_count, 2) == 0) and 1 or 0
end

-- ===================================================================
-- | Main Execution Logic                                            |
-- ===================================================================
local assembled_code, status = assemble(assembly_code)
if not assembled_code then return status end
for i, byte in ipairs(assembled_code) do memory[i-1] = byte end

local max_cycles = 200000
for cycle = 1, max_cycles do
    if halted then break end
    local opcode = read_byte(pc)
    pc = pc + 1

    if opcode == 0x01 then halted = true
    elseif opcode == 0x06 then regs[reg_map.A] = read_byte(pc); pc = pc + 1
    elseif opcode == 0x0E then regs[reg_map.B] = read_byte(pc); pc = pc + 1
    elseif opcode == 0x16 then regs[reg_map.C] = read_byte(pc); pc = pc + 1
    elseif opcode == 0xC1 then regs[reg_map.A] = regs[reg_map.B]
    elseif opcode == 0x87 then regs[reg_map.B] = regs[reg_map.A]
    elseif opcode == 0x80 then
        local result = regs[reg_map.A] + regs[reg_map.B]
        flags.C = (result > 255) and 1 or 0
        regs[reg_map.A] = modulo(result, 256)
        update_flags(regs[reg_map.A])
    elseif opcode == 0xC6 then regs[reg_map.A] = read_byte(get_hl())
    elseif opcode == 0x77 then write_byte(get_hl(), regs[reg_map.A])
    elseif opcode == 0x44 then
        local low = read_byte(pc)
        local high = read_byte(pc + 1)
        pc = high * 256 + low
    end
    
    if cycle == max_cycles then
        halted = true
        status = status .. "\nWarning: Execution hit max cycle limit."
    end
end

-- Output Generation
local screen_output = "Screen (0xEEE - 0xFFF):\n"
for addr = 0xEEE, 0xFFF do
    local char_code = read_byte(addr)
    if char_code > 31 and char_code < 127 then
        screen_output = screen_output .. string.char(char_code)
    else
        screen_output = screen_output .. "·"
    end
end

return status .. "\n---\n" .. screen_output .. "\n---\n" .. "Final A:"..regs[reg_map.A].." B:"..regs[reg_map.B].." C:"..regs[reg_map.C].." | Flags(CZSP):"..flags.C..flags.Z..flags.S..flags.P
