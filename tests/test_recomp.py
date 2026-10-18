"""Executable ISA-subset tests use only machine code generated from CC0 fixtures here."""
import json
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from decompnet.recomp import rv32


def words(*values):
    return struct.pack('<' + 'I' * len(values), *values)


def addi(rd, rs1, imm):
    return ((imm & 4095) << 20) | (rs1 << 15) | (rd << 7) | 0x13


def reg(rd, rs1, rs2, f3=0, f7=0):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x33


HALT = 0x00100073
needs_cc = pytest.mark.skipif(shutil.which('cc') is None, reason='native recompilation tests need cc')


@pytest.mark.parametrize('word,op,imm', [
    (0xfff08093, 'ADDI', -1), (0x00150533, 'ADD', 0), (0x40150533, 'SUB', 0),
    (0x00154533, 'XOR', 0), (0x00156533, 'OR', 0), (0x00157533, 'AND', 0),
    (0xfffff537, 'LUI', 0xfffff000), (0x00008863, 'BEQ', 16),
    (0x00009863, 'BNE', 16), (0xff5ff06f, 'JAL', -12),
    (0xffc12503, 'LW', -4), (0xfea12e23, 'SW', -4), (HALT, 'EBREAK', 0),
])
def test_known_encodings(word, op, imm):
    # Place backward jump at PC 12 and forward branches in a sufficiently large program.
    pc = 12 if op == 'JAL' else 0
    fixture = words(*([HALT] * (pc // 4)), word, *([HALT] * 5))
    instruction = rv32.decode(fixture)[pc // 4]
    assert (instruction.op, instruction.imm) == (op, imm)


@pytest.mark.parametrize('code,message', [
    (b'', 'aligned'), (b'\x13', 'aligned'), (b'\0' * 4100, 'aligned'),
    (words(0xffffffff), 'Unsupported'), (words(0x02000533, HALT), 'Unsupported'),  # MUL is not accepted
    (words(0x0020006f, HALT), 'unaligned'), (words(0x0080006f, HALT), 'out-of-range'),
    (words(0x00000073), 'Unsupported'),  # ECALL has no host ABI
])
def test_rejects_unsupported_or_malformed_code(code, message):
    with pytest.raises(rv32.TranslationError, match=message):
        rv32.translate(code)


@needs_cc
@pytest.mark.parametrize('argument', [0, 1, 2, 10, 100])
def test_loop_memory_and_native_execution(tmp_path, argument):
    result = rv32.build_and_run(rv32.demo_program(), tmp_path / 'out', argument, log=lambda _: None)
    assert result['success']
    assert result['execution']['registers'][10] == argument * (argument + 1) // 2
    assert result['execution']['registers'][0] == 0
    assert json.loads((tmp_path / 'out/result.json').read_text()) == result
    assert (tmp_path / 'out/program').is_file()


@needs_cc
@pytest.mark.parametrize('f3,f7,expected', [(0, 0, 4), (0, 32, 0xfffffffe), (4, 0, 2), (6, 0, 3), (7, 0, 1)])
def test_register_arithmetic(tmp_path, f3, f7, expected):
    code = words(addi(1, 0, 1), addi(2, 0, 3), reg(10, 1, 2, f3, f7), HALT)
    result = rv32.build_and_run(code, tmp_path / 'out', log=lambda _: None)
    assert result['execution']['registers'][10] == expected


@needs_cc
def test_unsigned_wraparound_and_zero_register(tmp_path):
    code = words(addi(1, 0, -1), addi(0, 0, 123), addi(10, 1, 1), HALT)
    result = rv32.build_and_run(code, tmp_path / 'out', log=lambda _: None)
    regs = result['execution']['registers']
    assert regs[0] == 0 and regs[1] == 0xffffffff and regs[10] == 0


@needs_cc
@pytest.mark.parametrize('f3,a,b,expected', [(0, 1, 1, 0), (0, 1, 2, 7), (1, 1, 1, 7), (1, 1, 2, 0)])
def test_branch_taken_and_not_taken(tmp_path, f3, a, b, expected):
    # branch x1,x2,+8; addi a0,x0,7; ebreak
    branch = (2 << 20) | (1 << 15) | (f3 << 12) | (4 << 8) | 0x63
    code = words(addi(1, 0, a), addi(2, 0, b), branch, addi(10, 0, 7), HALT)
    assert rv32.build_and_run(code, tmp_path / 'out', 0, log=lambda _: None)['execution']['registers'][10] == expected


@needs_cc
def test_jump_link_register(tmp_path):
    # jal x10,+8 must skip the addi and write PC+4 to x10.
    result = rv32.build_and_run(words(0x0080056f, addi(10, 0, 99), HALT), tmp_path / 'out', log=lambda _: None)
    assert result['execution']['registers'][10] == 4


@needs_cc
@pytest.mark.parametrize('code,state', [
    (words(0x0000006f), 'step-limit'),
    (words(addi(10, 0, 1)), 'pc-trap'),
    (words(addi(2, 0, 1), 0x00012503, HALT), 'memory-trap'),
    (words(0x00010137, 0x00012503, HALT), 'memory-trap'),
    (words(0x00a02023, HALT), 'code-write-trap'),
])
def test_runtime_traps_are_failures(tmp_path, code, state):
    with pytest.raises(rv32.TranslationError, match=state):
        rv32.build_and_run(code, tmp_path / 'out', log=lambda _: None)
    assert json.loads((tmp_path / 'out/result.json').read_text())['success'] is False


@needs_cc
def test_memory_little_endian_negative_offset(tmp_path):
    code = words(0x00001137, addi(2, 2, 4), addi(10, 0, -1), 0xfea12e23, 0xffc12503, HALT)
    result = rv32.build_and_run(code, tmp_path / 'out', log=lambda _: None)
    assert result['execution']['registers'][10] == 0xffffffff


def test_compilation_failure_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(rv32.shutil, 'which', lambda _: '/compiler')
    monkeypatch.setattr(rv32.subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a, 1, '', 'fixture compiler failure'))
    with pytest.raises(rv32.TranslationError, match='fixture compiler failure'):
        rv32.build_and_run(words(HALT), tmp_path / 'out')


@needs_cc
def test_existing_output_is_preserved(tmp_path):
    root = tmp_path / 'out'
    root.mkdir()
    sentinel = root / 'translated.c'
    sentinel.write_text('keep this')
    with pytest.raises(FileExistsError):
        rv32.build_and_run(words(HALT), root)
    assert sentinel.read_text() == 'keep this'
