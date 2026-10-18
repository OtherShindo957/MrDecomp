"""Executable recompilation contracts. Targets own their build/verification dependencies."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import platform
import shutil
from typing import Callable, Protocol

from . import rv32


@dataclass(frozen=True)
class Target:
    id: str
    name: str
    dependencies: tuple[str, ...]
    status: str = 'experimental'


class Recompiler(Protocol):
    def describe(self) -> dict: ...
    def validate(self, code: bytes, argument: int, target: str) -> None: ...
    def build(self, code: bytes, root: Path, argument: int, target: str, log: Callable = print) -> dict: ...


class RV32Recompiler:
    targets = (Target('linux-amd64', 'Native Linux AMD64', ('cc',)),
               Target('wasm', 'WebAssembly / browser', ('node',)))

    def describe(self) -> dict:
        targets = []
        for target in self.targets:
            missing = [dependency for dependency in target.dependencies if not shutil.which(dependency)]
            if target.id == 'linux-amd64' and (platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64')):
                missing.append('Linux AMD64 host')
            targets.append(asdict(target) | {'available': not missing, 'missing': missing})
        return {'targets': targets, 'supported_instructions': rv32.SUPPORTED,
                'demo_hex': rv32.demo_program().hex(), 'max_bytes': rv32.MAX_CODE,
                'memory_bytes': rv32.MEMORY_SIZE, 'max_steps': rv32.MAX_STEPS,
                'input_contract': 'Raw little-endian words at PC 0; x10/a0 input and result; EBREAK stops the test harness. Code is read-only. Other registers and data memory start at zero.'}

    def validate(self, code: bytes, argument: int, target: str) -> None:
        if target not in {t.id for t in self.targets}:
            raise rv32.TranslationError(f'Unsupported output target: {target}')
        if type(argument) is not int or not 0 <= argument <= 0xffffffff:
            raise rv32.TranslationError('a0 input must be an unsigned 32-bit integer')
        rv32.decode(code)

    def build(self, code: bytes, root: Path, argument: int, target: str, log=print) -> dict:
        self.validate(code, argument, target)
        if target == 'wasm':
            from . import wasm
            return wasm.build_and_run(code, root, argument, log)
        return rv32.build_and_run(code, root, argument, log)
