"""Explicit backend registration. Registration does not execute third-party code or install tools."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..recomp.adapters import Recompiler


@dataclass(frozen=True)
class Backend:
    id: str
    name: str
    platforms: tuple[str, ...]
    architecture: str
    modes: tuple[str, ...]
    status: str
    dependencies: tuple[str, ...]
    formats: tuple[str, ...]
    limitation: str
    probe: Callable[[bytes, str], str | None] | None = None

    recompiler: Recompiler | None = None

    def public(self) -> dict:
        data = {f.name: getattr(self, f.name) for f in fields(self) if f.name not in ('probe', 'recompiler')}
        if self.recompiler:
            data['targets'] = self.recompiler.describe()['targets']
        return data


class Registry:
    def __init__(self):
        self._items: dict[str, Backend] = {}

    def register(self, backend: Backend) -> None:
        if backend.id in self._items:
            raise ValueError(f'Duplicate backend: {backend.id}')
        if backend.status not in {'supported', 'experimental', 'analysis-only', 'planned', 'unsupported'}:
            raise ValueError(f'Invalid backend status: {backend.status}')
        self._items[backend.id] = backend

    def get(self, key: str) -> Backend:
        try:
            return self._items[key]
        except KeyError:
            raise ValueError(f'Unknown backend: {key}') from None

    def recompiler(self, key: str) -> Recompiler:
        backend = self.get(key)
        if backend.recompiler is None or 'recompilation' not in backend.modes:
            raise ValueError(f'Backend {key} has no executable recompilation pipeline')
        return backend.recompiler

    def entries(self) -> list[dict]:
        return [b.public() for b in self._items.values()]

    def detect(self, head: bytes, name: str = '') -> list[dict]:
        found = []
        for backend in self._items.values():
            fmt = backend.probe(head, name) if backend.probe else None
            if fmt:
                found.append(backend.public() | {'detected_format': fmt, 'confidence': 'header'})
        return found


def _n64(head: bytes, name: str) -> str | None:
    return 'N64 ROM' if head[:4] in (bytes.fromhex('80371240'), bytes.fromhex('37804012'), bytes.fromhex('40123780')) else None


def _powerpc(head: bytes, name: str) -> str | None:
    from ..forks.scratch_dtk import disc_kind
    kind = disc_kind(head)
    if kind:
        return f'{kind} disc container'
    if len(head) >= 0x100:
        entry = int.from_bytes(head[0xe0:0xe4], 'big')
        sections = [(int.from_bytes(head[i*4:i*4+4], 'big'),
                     int.from_bytes(head[72+i*4:76+i*4], 'big'),
                     int.from_bytes(head[144+i*4:148+i*4], 'big')) for i in range(18)]
        used = [(off, addr, size) for off, addr, size in sections if size]
        if (used and 0x80000000 <= entry < 0x81800000 and
                all(off >= 0x100 and 0x80000000 <= addr < 0x81800000 and addr + size <= 0x81800000 for off, addr, size in used)):
            return 'DOL header (section bounds require full validation)'
    return None


def _ps(head: bytes, name: str) -> str | None:
    if head[:8] == b'MComprHD':
        return 'CHD container (disc platform requires full validation)'
    if any(head[offset:offset+5] == b'CD001' for offset in (0x8001, 0x9319, 0x9311)):
        return 'ISO9660 disc (platform requires full validation)'
    if head[:8] == b'PS-X EXE':
        return 'PS-X EXE'
    if len(head) >= 20 and head[:4] == b'\x7fELF' and head[4:6] == b'\x01\x01' and int.from_bytes(head[18:20], 'little') == 8:
        return 'ELF32 MIPS (platform must be verified)'
    return None


def _gba(head: bytes, name: str) -> str | None:
    from ..rom.gba import is_gba
    return 'GBA ROM' if is_gba(head) else None


def _nds(head: bytes, name: str) -> str | None:
    from ..forks.scratch_dsd import is_nds
    return 'DS ROM' if is_nds(head) else None


def default_registry() -> Registry:
    from ..recomp.adapters import RV32Recompiler
    reg = Registry()
    for backend in [
        Backend('matching-n64', 'N64 matching (splat)', ('n64',), 'MIPS', ('decompilation',), 'supported',
                ('gcc-2.7.2-kmc', 'ido-7.1', 'ld.lld'), ('N64 ROM',), 'Compiler and per-game configuration required.', _n64),
        Backend('matching-powerpc', 'GameCube / Wii matching (dtk)', ('gc', 'wii'), 'PowerPC', ('decompilation',), 'supported',
                ('dtk', 'mwcc', 'ninja'), ('DOL', 'disc image'), 'Proprietary compiler requires explicit license acceptance.', _powerpc),
        Backend('matching-ps', 'PlayStation matching', ('psx', 'ps2'), 'MIPS', ('decompilation',), 'experimental',
                ('gcc-2.7.2-psx', 'ee-gcc-2.96'), ('PS-X EXE', 'ELF', 'disc image'), 'ELF recognition alone cannot establish console provenance.', _ps),
        Backend('matching-gba', 'GBA matching', ('gba',), 'ARM', ('decompilation',), 'experimental',
                ('agbcc',), ('GBA ROM',), 'Tested primarily with redistributable programs.', _gba),
        Backend('matching-nds', 'DS matching', ('nds',), 'ARM', ('decompilation',), 'experimental',
                ('mwccarm', 'dsd'), ('DS ROM',), 'Proprietary compiler requires explicit license acceptance.', _nds),
    ]:
        reg.register(backend)
    reg.register(Backend('rv32i-subset', 'RV32I subset experiment', ('rv32-test',), 'RISC-V RV32I subset',
                         ('recompilation',), 'experimental', ('cc', 'node'), ('raw little-endian words',),
                         '13 tested instructions; no ELF, relocations, syscalls, floating point, or console runtime.', recompiler=RV32Recompiler()))
    return reg
