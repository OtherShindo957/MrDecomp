"""Read-only host and tool diagnostics, shared by CLI and GUI."""
from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def report(home: Path) -> dict:
    host_ok = sys.platform.startswith('linux') and platform.machine().lower() in ('x86_64', 'amd64')
    tools = []
    for name, purpose, required in [('git', 'Community project import', True),
                                     ('cc', 'Native compilation and recompilation tests', False),
                                     ('ld.lld', 'N64 target linking', False),
                                     ('emcc', 'Future Emscripten browser builds', False),
                                     ('node', 'JavaScript and WebAssembly test harnesses', False)]:
        path = shutil.which(name)
        tools.append({'id': name, 'purpose': purpose, 'path': path, 'installed': bool(path), 'required': required})
    ancestor = home.expanduser().resolve()
    while not ancestor.exists():
        ancestor = ancestor.parent
    writable = ancestor.is_dir() and os.access(ancestor, os.W_OK | os.X_OK)
    return {'application': 'MrDecomp', 'python': platform.python_version(), 'python_supported': sys.version_info >= (3, 12),
            'host_os': platform.system(), 'host_architecture': platform.machine(), 'primary_host': host_ok,
            'project_home': str(home), 'storage_writable': writable, 'tools': tools,
            'ready': host_ok and writable and all(t['installed'] for t in tools if t['required']),
            'notes': ['Tool availability is separate from game-platform support.',
                      'No packages or proprietary compilers are installed by this check.']}


def output_parent(value: str, default: Path) -> Path:
    if not isinstance(value, str) or '\x00' in value:
        raise ValueError('Output folder must be a valid local path')
    path = Path(value).expanduser() if value.strip() else default
    if not path.is_absolute():
        raise ValueError('Choose an absolute output folder path')
    path = path.resolve()
    ancestor = path
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir() or not os.access(ancestor, os.W_OK | os.X_OK):
        raise ValueError('Output folder is not writable')
    return path
