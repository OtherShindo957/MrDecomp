"""Independent test-only RV32 subset interpreter; does not import the translator/decoder.

Fixtures and this reference implementation are CC0-1.0. The oracle models only
the experiment's explicit harness contract, not a complete RISC-V system.
"""

def execute(code, argument=10):
    registers = [0] * 32
    registers[10] = argument
    memory = bytearray(65536)
    memory[:len(code)] = code
    pc, steps, state = 0, 0, 'step-limit'
    sign = lambda n, width: (n ^ (1 << (width - 1))) - (1 << (width - 1))
    while steps < 100000:
        steps += 1
        if pc % 4 or pc < 0 or pc + 4 > len(code):
            state = 'pc-trap'
            break
        word = int.from_bytes(code[pc:pc+4], 'little')
        opcode = word & 127
        rd, rs1, rs2, funct3 = (word >> 7) & 31, (word >> 15) & 31, (word >> 20) & 31, (word >> 12) & 7
        next_pc = pc + 4
        a, b = registers[rs1], registers[rs2]
        result = None
        if word == 0x100073:
            state = 'halted'
            break
        if opcode == 0x13:
            assert funct3 == 0
            result = a + sign(word >> 20, 12)
        elif opcode == 0x33:
            funct7 = word >> 25
            if (funct3, funct7) == (0, 0): result = a + b
            elif (funct3, funct7) == (0, 32): result = a - b
            elif (funct3, funct7) == (4, 0): result = a ^ b
            elif (funct3, funct7) == (6, 0): result = a | b
            elif (funct3, funct7) == (7, 0): result = a & b
            else: raise AssertionError('Unsupported reference arithmetic')
        elif opcode == 0x37:
            result = word & 0xfffff000
        elif opcode == 0x63:
            offset = ((word & 0x80000000) >> 19) | ((word & 128) << 4) | ((word >> 20) & 0x7e0) | ((word >> 7) & 30)
            taken = (a == b) if funct3 == 0 else (a != b)
            if taken: next_pc = pc + sign(offset, 13)
        elif opcode == 0x6f:
            offset = ((word >> 11) & 0x100000) | (word & 0xff000) | ((word >> 9) & 0x800) | ((word >> 20) & 0x7fe)
            result, next_pc = pc + 4, pc + sign(offset, 21)
        elif opcode in (3, 35):
            immediate = word >> 20 if opcode == 3 else ((word >> 20) & 0xfe0) | ((word >> 7) & 31)
            address = (a + sign(immediate, 12)) & 0xffffffff
            if address % 4 or address > 65532:
                state = 'memory-trap'
                break
            if opcode == 3:
                result = int.from_bytes(memory[address:address+4], 'little')
            else:
                if address < len(code):
                    state = 'code-write-trap'
                    break
                memory[address:address+4] = b.to_bytes(4, 'little')
        else:
            raise AssertionError('Unsupported reference encoding')
        if result is not None and rd:
            registers[rd] = result & 0xffffffff
        pc = next_pc
    return {'state': state, 'pc': pc, 'steps': steps, 'registers': registers}
