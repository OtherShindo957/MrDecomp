# RV32I subset experiment

This is a static recompilation test, not a console game port. In MrDecomp's dashboard choose **Recompilation experiment**, leave the bundled program selected, enter `10`, and choose **Translate, compile & execute**. Choose **Native Linux AMD64** or **WebAssembly / browser** as the output target. A successful execution produces `a0 = 55`. For WebAssembly, choose **Open local WebAssembly test**, then **Execute WebAssembly** to run the translated program in the browser.

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

Native output contains `input.rv32`, readable `translated.c`, the native `program`, and `result.json`. It requires a Linux AMD64 host and `cc`. Translation emits C statements for each decoded instruction; the resulting executable does not decode instructions at runtime.

WebAssembly output contains `program.wasm`, `index.html`, `browser.js`, `style.css`, `input.rv32`, `verify.cjs` and `result.json`. It directly emits WebAssembly instructions from the same decoded program, with no runtime RISC-V decoder and no external compiler. Node.js must validate and execute the module successfully before the build job succeeds. The browser page instantiates the module and executes it again from user input; it does not show a cached result.

The local preview requires the running authenticated MrDecomp session. Only the four generated browser assets are served through its preview routes. After a restart, use a local HTTP server for the saved output folder; prior in-memory job preview addresses are not restored yet.

The WebAssembly module exports `run(i32) -> i32` and `memory`. `run` resets state on every call and returns 0 for halted, 1 for step limit, 2 for invalid PC, 3 for invalid memory access, or 4 for a code write. Its fixed two-page memory separates the 64 KiB guest page from host-readable diagnostics in the second page:

| Offset | Contents |
|---|---|
| 0–65535 | Guest memory; program bytes followed by zeroed data |
| 65536–65663 | Registers x0 through x31, little-endian uint32 |
| 65664 | Guest PC |
| 65668 | Executed guest instruction count |
| 65672 | Execution status code |

Guest loads/stores cannot address the diagnostics page. The module imports no host functions and cannot grow its memory. Its encoding follows the [WebAssembly Core binary specification](https://webassembly.github.io/spec/core/binary/index.html).

## Fixture source / assembly

The machine-code fixture returned by `decompnet.recomp.rv32.demo_program()` and the original instruction fixtures and reference interpreter in `tests/` are dedicated to the public domain under CC0-1.0. No commercial game code is used.

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
