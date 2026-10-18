"""Direct RV32 subset -> WebAssembly binary emitter, with no external compiler.

The module exports run(i32)->i32 status and a fixed two-page memory. The first
page is guest memory; the second holds result diagnostics and is inaccessible to
guest load/store operations. See the WebAssembly Core binary specification:
https://webassembly.github.io/spec/core/binary/index.html
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import rv32

STATES = ('halted', 'step-limit', 'pc-trap', 'memory-trap', 'code-write-trap')
REGISTERS = 65536
PC, STEPS, STATUS = REGISTERS + 128, REGISTERS + 132, REGISTERS + 136


def uleb(value: int) -> bytes:
    if value < 0:
        raise ValueError('Unsigned LEB128 cannot encode negative integers')
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        out.append(byte | (128 if value else 0))
        if not value:
            return bytes(out)


def sleb(value: int) -> bytes:
    value = rv32.signed(value & 0xffffffff, 32)
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        done = (value == 0 and not byte & 64) or (value == -1 and byte & 64)
        out.append(byte | (0 if done else 128))
        if done:
            return bytes(out)


def const(value: int) -> bytes:
    return b'\x41' + sleb(value)


def get(local: int) -> bytes:
    return b'\x20' + uleb(local)


def put(local: int, expression: bytes) -> bytes:
    return expression + b'\x21' + uleb(local)


def section(kind: int, payload: bytes) -> bytes:
    return bytes([kind]) + uleb(len(payload)) + payload


def name(value: str) -> bytes:
    data = value.encode('utf-8')
    return uleb(len(data)) + data


def emit(code: bytes) -> tuple[bytes, list[dict]]:
    from dataclasses import asdict
    instructions = rv32.decode(code)
    # Parameter 0: input; locals 1..32: x0..x31; 33: PC; 34: steps; 35: status; 36: address.
    pc, steps, status, addr = 33, 34, 35, 36
    reg = lambda index: get(index + 1)
    setreg = lambda index, value: put(index + 1, value) if index else value + b'\x1a'
    # Reset all memory for repeatable execution. This loop uses no guest instructions.
    body = put(addr, const(0)) + b'\x03\x40'
    body += get(addr) + const(0) + b'\x36\x02\x00'
    body += put(addr, get(addr) + const(4) + b'\x6a')
    body += get(addr) + const(131072) + b'\x49\x0d\x00\x0b'
    for i in instructions:
        body += const(i.pc) + const(i.word) + b'\x36\x02\x00'
    body += put(11, get(0))
    body += b'\x02\x40\x03\x40'  # exit block, execution loop
    body += get(steps) + const(rv32.MAX_STEPS) + b'\x4f\x04\x40'
    body += put(status, const(1)) + b'\x0c\x02\x0b'
    body += put(steps, get(steps) + const(1) + b'\x6a')
    for i in instructions:
        body += get(pc) + const(i.pc) + b'\x46\x04\x40'
        if i.op == 'EBREAK':
            body += put(status, const(0)) + b'\x0c\x02'
        elif i.op == 'ADDI':
            body += setreg(i.rd, reg(i.rs1) + const(i.imm) + b'\x6a')
        elif i.op in ('ADD', 'SUB', 'XOR', 'OR', 'AND'):
            opcode = {'ADD': 0x6a, 'SUB': 0x6b, 'XOR': 0x73, 'OR': 0x72, 'AND': 0x71}[i.op]
            body += setreg(i.rd, reg(i.rs1) + reg(i.rs2) + bytes([opcode]))
        elif i.op == 'LUI':
            body += setreg(i.rd, const(i.imm))
        elif i.op in ('BEQ', 'BNE'):
            condition = reg(i.rs1) + reg(i.rs2) + (b'\x46' if i.op == 'BEQ' else b'\x47')
            body += put(pc, condition + b'\x04\x7f' + const(i.pc + i.imm) + b'\x05' + const(i.pc + 4) + b'\x0b')
        elif i.op == 'JAL':
            body += setreg(i.rd, const(i.pc + 4)) + put(pc, const(i.pc + i.imm))
        elif i.op in ('LW', 'SW'):
            body += put(addr, reg(i.rs1) + const(i.imm) + b'\x6a')
            body += get(addr) + const(3) + b'\x71' + get(addr) + const(rv32.MEMORY_SIZE - 4) + b'\x4b\x72\x04\x40'
            body += put(status, const(3)) + b'\x0c\x03\x0b'
            if i.op == 'LW':
                body += setreg(i.rd, get(addr) + b'\x28\x02\x00')
            else:
                body += get(addr) + const(len(code)) + b'\x49\x04\x40'
                body += put(status, const(4)) + b'\x0c\x03\x0b'
                body += get(addr) + reg(i.rs2) + b'\x36\x02\x00'
        if i.op not in ('BEQ', 'BNE', 'JAL', 'EBREAK'):
            body += put(pc, const(i.pc + 4))
        body += b'\x0c\x01\x0b'  # continue loop from instruction if
    body += put(status, const(2)) + b'\x0c\x01\x0b\x0b'
    for index in range(32):
        body += const(REGISTERS + index * 4) + reg(index) + b'\x36\x02\x00'
    for offset, local in ((PC, pc), (STEPS, steps), (STATUS, status)):
        body += const(offset) + get(local) + b'\x36\x02\x00'
    body += get(status) + b'\x0b'
    function = b'\x01' + uleb(36) + b'\x7f' + body  # one local group: 36 i32
    module = b'\0asm\x01\0\0\0'
    module += section(1, b'\x01\x60\x01\x7f\x01\x7f')
    module += section(3, b'\x01\x00')
    module += section(5, b'\x01\x01\x02\x02')  # exactly two memory pages
    exports = b'\x02' + name('run') + b'\x00\x00' + name('memory') + b'\x02\x00'
    module += section(7, exports)
    module += section(10, b'\x01' + uleb(len(function)) + function)
    return module, [asdict(i) for i in instructions]


HARNESS_JS = '''"use strict";
const fs = require("node:fs");
(async () => {
  const {instance} = await WebAssembly.instantiate(fs.readFileSync(process.argv[2]));
  const status = instance.exports.run(Number(process.argv[3]) >>> 0);
  const data = new DataView(instance.exports.memory.buffer);
  const states = ["halted", "step-limit", "pc-trap", "memory-trap", "code-write-trap"];
  console.log(JSON.stringify({state: states[status], pc: data.getUint32(65664, true), steps: data.getUint32(65668, true),
    registers: Array.from({length: 32}, (_, i) => data.getUint32(65536 + i * 4, true))}));
})().catch(error => { console.error(error); process.exitCode = 1; });
'''

BROWSER_JS = '''"use strict";
const run = document.getElementById("run");
const output = document.getElementById("result");
run.onclick = async () => {
  run.disabled = true;
  try {
    const input = Number(document.getElementById("argument").value);
    if (!Number.isInteger(input) || input < 0 || input > 4294967295) throw new Error("Input must be an unsigned 32-bit integer");
    const response = await fetch("program.wasm");
    if (!response.ok) throw new Error(`Could not load WebAssembly (${response.status})`);
    const {instance} = await WebAssembly.instantiate(await response.arrayBuffer());
    const status = instance.exports.run(input);
    const data = new DataView(instance.exports.memory.buffer);
    const states = ["halted", "step-limit", "pc-trap", "memory-trap", "code-write-trap"];
    const result = {state: states[status], a0: data.getUint32(65576, true), pc: data.getUint32(65664, true), steps: data.getUint32(65668, true)};
    output.textContent = JSON.stringify(result, null, 2);
    output.dataset.state = result.state;
  } catch (error) { output.textContent = `Failed: ${error.message}`; output.dataset.state = "error"; }
  finally { run.disabled = false; }
};
'''
BROWSER_HTML = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; object-src 'none'; base-uri 'none'">
<title>MrDecomp — WebAssembly experiment</title><link rel="stylesheet" href="style.css"></head>
<body><main><p>MrDecomp · experimental output</p><h1>Translated program in WebAssembly</h1>
<p>This executes a small RV32I test program. It is not a playable console game port.</p>
<label>a0 input <input id="argument" type="number" value="10" min="0" max="4294967295" step="1"></label>
<button id="run" type="button">Execute WebAssembly</button><pre id="result" role="status">Ready.</pre>
<p>Serve this folder over local HTTP to test it. No external services or assets are required.</p>
</main><script src="browser.js"></script></body></html>'''


def build_and_run(code: bytes, root: Path, argument: int = 10, log=print) -> dict:
    if type(argument) is not int or not 0 <= argument <= 0xffffffff:
        raise rv32.TranslationError('a0 input must be an unsigned 32-bit integer')
    node = shutil.which('node')
    if not node:
        raise rv32.TranslationError('Node.js is required to verify WebAssembly output before reporting success')
    module, instructions = emit(code)
    root.mkdir(parents=True, exist_ok=False)
    (root / 'input.rv32').write_bytes(code)
    (root / 'program.wasm').write_bytes(module)
    (root / 'verify.cjs').write_text(HARNESS_JS, encoding='utf-8')
    (root / 'browser.js').write_text(BROWSER_JS, encoding='utf-8')
    (root / 'index.html').write_text(BROWSER_HTML, encoding='utf-8')
    (root / 'style.css').write_text('body{font:16px system-ui;background:#111714;color:#e1eee6;margin:0}main{max-width:760px;margin:8vh auto;padding:24px}input,button{font:inherit;padding:10px;margin:8px}pre{white-space:pre-wrap;background:#1f2b23;padding:20px}', encoding='utf-8')
    log(f'Statically translated {len(instructions)} instructions to {len(module)} WebAssembly bytes')
    log('Validating and executing WebAssembly in Node.js')
    try:
        run = subprocess.run([node, str(root / 'verify.cjs'), str(root / 'program.wasm'), str(argument)],
                             capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired as e:
        raise rv32.TranslationError('WebAssembly verification timed out') from e
    if run.returncode:
        raise rv32.TranslationError(f'WebAssembly validation/execution failed ({run.returncode}): {run.stderr[-4000:]}')
    try:
        execution = json.loads(run.stdout)
        success = execution['state'] == 'halted'
    except (ValueError, KeyError) as e:
        raise rv32.TranslationError('Invalid WebAssembly harness result') from e
    result = {'backend': 'rv32i-subset', 'target': 'wasm', 'output': str(root), 'source': '',
              'instructions': instructions, 'execution': execution, 'success': success,
              'module_bytes': len(module), 'compiler_diagnostics': '',
              'files': ['program.wasm', 'index.html', 'browser.js', 'style.css']}
    (root / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    log(f"WebAssembly execution state: {execution['state']}; a0={execution['registers'][10]}; steps={execution['steps']}")
    if not success:
        raise rv32.TranslationError(f"Translated WebAssembly stopped with {execution['state']} at PC 0x{execution['pc']:08x}; diagnostics saved in {root}")
    return result
