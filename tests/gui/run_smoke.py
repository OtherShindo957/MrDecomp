"""Launch a fresh local app and run its Playwright GUI smoke test.

Run with `uv run python tests/gui/run_smoke.py`. Playwright + Chromium must be
available; MRDECOMP_CHROMIUM can point to an existing headless Chromium binary.
The disposable app never imports commercial code or installs toolchains.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main() -> int:
    node = shutil.which('node')
    if not node:
        raise SystemExit('GUI smoke tests require Node.js, Playwright and Chromium')
    with tempfile.TemporaryDirectory(prefix='mrdecomp-gui-') as temporary:
        home = Path(temporary)
        env = dict(os.environ, MRDECOMP_HOME=str(home), DECOMP_BIND='127.0.0.1', DECOMP_UPDATES='off', DECOMP_RUNTIME='native')
        with (home / 'app.log').open('w') as logs:
            app = subprocess.Popen([sys.executable, '-m', 'decompnet.app.cli', '--no-browser', '--port', '0'],
                                   env=env, stdout=logs, stderr=logs)
            try:
                info = None
                for _ in range(100):
                    if app.poll() is not None:
                        raise RuntimeError('MrDecomp exited before becoming ready')
                    try:
                        info = json.loads((home / '.decomp/server.json').read_text())
                        with urllib.request.urlopen(f"http://127.0.0.1:{info['port']}/health", timeout=1):
                            break
                    except (OSError, ValueError):
                        time.sleep(.1)
                else:
                    raise RuntimeError('MrDecomp did not become ready')
                env['MRDECOMP_TEST_URL'] = f"http://127.0.0.1:{info['port']}/?k={info['secret']}"
                return subprocess.run([node, str(Path(__file__).with_name('smoke.cjs'))], env=env, timeout=120).returncode
            finally:
                app.terminate()
                try:
                    app.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait()


if __name__ == '__main__':
    raise SystemExit(main())
