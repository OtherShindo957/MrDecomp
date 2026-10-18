# RV32I subset experiment

This is a static recompilation test, not a console game port. In MrDecomp's dashboard choose **Recompilation experiment**, leave the bundled program selected, enter `10`, and choose **Translate, compile & execute**. A successful native execution produces `a0 = 55`.

The fixture computes the sum 1 through its input, stores the result at guest address 4096, loads it back, and stops at EBREAK. For input zero the result is zero. Very large inputs exhaust the instruction budget and correctly fail.

## Execution contract

- Raw little-endian 32-bit instructions, loaded at PC zero, at most 4096 bytes.
- Register x10/a0 is the unsigned input and result; x0 is always zero.
- 64 KiB of unified guest memory; program bytes are initialized from the input, remaining bytes are zero.
- Program bytes are read-only. Word loads and stores require four-byte alignment and in-bounds addresses.
- EBREAK terminates this harness. No guest syscall ABI or OS exists.
- At most 100000 instructions are executed. Unknown PCs, invalid memory accesses, writes to code, and budget exhaustion fail the job.
- Accepted instructions: ADDI, ADD, SUB, XOR, OR, AND, LUI, BEQ, BNE, JAL, LW, SW, EBREAK. All other instruction encodings are rejected, including multiplication and compressed instructions.
- No ELF loader, relocations, dynamic linking, floating point, interrupts, console services, graphics, audio, or playable game runtime.

The output folder contains `input.rv32`, readable `translated.c`, the native `program`, and `result.json`. Translation emits C statements for each decoded instruction; the resulting executable does not decode instructions at runtime. Execution is compiled for the Linux AMD64 host with `cc`.

## Fixture source / assembly

The machine-code fixture returned by `decompnet.recomp.rv32.demo_program()` and the original instruction fixtures in `tests/test_recomp.py` are dedicated to the public domain under CC0-1.0. No commercial game code is used.

```asm
addi x1, a0, 0
addi a0, x0, 0
loop:
beq  x1, x0, done
add  a0, a0, x1
addi x1, x1, -1
jal  x0, loop
done:
lui  x2, 1
sw   a0, 0(x2)
lw   a0, 0(x2)
ebreak
```
