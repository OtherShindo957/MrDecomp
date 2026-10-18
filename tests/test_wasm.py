import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from decompnet.recomp import rv32, wasm
from decompnet.backends import default_registry, Registry
from tests.rv32_oracle import execute
from tests.test_recomp import words, addi, reg, HALT
from tests.test_app_server import app

needs_node = pytest.mark.skipif(not shutil.which('node'), reason='WebAssembly verification needs Node.js')
needs_native = pytest.mark.skipif(not shutil.which('node') or not shutil.which('cc'), reason='cross-target comparison needs Node.js and cc')


def fixture(seed):
    rng = random.Random(seed)
    instructions = [0x00001137, addi(1, 0, -1)]  # data base x2=4096; x1=0xffffffff
    for _ in range(24):
        rd, a, b = rng.randrange(32), rng.randrange(32), rng.randrange(32)
        choice = rng.randrange(4)
        if choice == 0:
            instructions.append(addi(rd, a, rng.randrange(-2048, 2048)))
        elif choice == 1:
            f3, f7 = rng.choice([(0, 0), (0, 32), (4, 0), (6, 0), (7, 0)])
            instructions.append(reg(rd, a, b, f3, f7))
        elif choice == 2:
            instructions.append((rng.randrange(1 << 20) << 12) | (rd << 7) | 0x37)
        else:
            # Explicit independent raw encodings for taken/not-taken BEQ/BNE and a skip.
            instructions.extend([(b << 20) | (a << 15) | (rng.randrange(2) << 12) | (4 << 8) | 0x63, addi(rd, a, 3)])
    # Reinitialize data base, store/load a random register, and test JAL's link result.
    instructions += [0x00001137, (rng.randrange(32) << 20) | (2 << 15) | (2 << 12) | 0x23,
                     0x00012503, 0x008000ef, addi(10, 0, 999), HALT]
    return words(*instructions)


@needs_native
@pytest.mark.parametrize('seed', range(16))
def test_independent_oracle_native_and_wasm_agree(tmp_path, seed):
    code = fixture(seed)
    argument = random.Random(seed).getrandbits(32)
    expected = execute(code, argument)
    native = rv32.build_and_run(code, tmp_path / 'native', argument, log=lambda _: None)
    browser = wasm.build_and_run(code, tmp_path / 'wasm', argument, log=lambda _: None)
    assert native['execution'] == expected
    assert browser['execution'] == expected


@needs_node
@pytest.mark.parametrize('argument', [0, 1, 10, 57, 123])
def test_wasm_loop_and_memory(tmp_path, argument):
    result = wasm.build_and_run(rv32.demo_program(), tmp_path / 'out', argument, log=lambda _: None)
    assert result['execution'] == execute(rv32.demo_program(), argument)
    assert result['execution']['registers'][10] == argument * (argument + 1) // 2
    assert (tmp_path / 'out/program.wasm').read_bytes().startswith(b'\0asm')


@needs_node
@pytest.mark.parametrize('code', [words(0x0000006f), words(addi(10, 0, 1)), words(0x00010137, 0x00012503, HALT), words(0x00a02023, HALT)])
def test_wasm_traps_match_reference(tmp_path, code):
    expected = execute(code)
    with pytest.raises(rv32.TranslationError, match=expected['state']):
        wasm.build_and_run(code, tmp_path / 'out', log=lambda _: None)
    assert json.loads((tmp_path / 'out/result.json').read_text())['execution'] == expected


@needs_node
def test_module_memory_reset_and_no_imports(tmp_path):
    module, _ = wasm.emit(rv32.demo_program())
    path = tmp_path / 'program.wasm'
    path.write_bytes(module)
    script = '''const fs=require('node:fs');const assert=require('node:assert/strict');
    const module=new WebAssembly.Module(fs.readFileSync(process.argv[1]));
    assert.deepEqual(WebAssembly.Module.imports(module),[]);
    const e=new WebAssembly.Instance(module).exports;
    assert.equal(e.run(10),0);assert.equal(new DataView(e.memory.buffer).getUint32(65576,true),55);
    new Uint8Array(e.memory.buffer).fill(255);
    assert.equal(e.run(0),0);assert.equal(new DataView(e.memory.buffer).getUint32(65576,true),0);
    assert.equal(e.memory.buffer.byteLength,131072);
    assert.throws(()=>e.memory.grow(1));'''
    subprocess.run([shutil.which('node'), '-e', script, str(path)], check=True, capture_output=True, text=True)


def test_adapter_dispatch_and_target_validation(tmp_path):
    reg = default_registry()
    adapter = reg.recompiler('rv32i-subset')
    assert {t['id'] for t in adapter.describe()['targets']} == {'linux-amd64', 'wasm'}
    with pytest.raises(ValueError, match='Unsupported output'):
        adapter.validate(words(HALT), 0, 'pretend-console')
    with pytest.raises(ValueError, match='no executable'):
        reg.recompiler('matching-n64')
    assert not tmp_path.joinpath('absent').exists()


def test_missing_node_never_reports_success(tmp_path, monkeypatch):
    monkeypatch.setattr(wasm.shutil, 'which', lambda _: None)
    with pytest.raises(rv32.TranslationError, match='Node.js'):
        wasm.build_and_run(words(HALT), tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


@needs_node
def test_verified_artifacts_are_authenticated_and_allowlisted(app, tmp_path):
    import time
    from starlette.testclient import TestClient
    client, _, _ = app
    spec = client.get('/api/recomp/experiment').json()
    response = client.post('/api/recomp/experiment', headers={'X-Decomp': '1'}, json={'hex': spec['demo_hex'], 'target': 'wasm', 'output': str(tmp_path)})
    assert response.status_code == 200
    job_id = response.json()['job']
    for _ in range(200):
        job = client.get('/api/job', params={'id': job_id}).json()
        if job['state'] != 'running': break
        time.sleep(.01)
    assert job['state'] == 'done', job.get('error')
    uri = f'/experiments/{job_id}/'
    assert client.get(uri+'program.wasm').headers['content-type'] == 'application/wasm'
    assert 'wasm-unsafe-eval' in client.get(uri+'index.html').text
    for forbidden in ('result.json', 'input.rv32', 'verify.cjs', 'missing'):
        assert client.get(uri+forbidden).status_code == 404
    anon = TestClient(client.app, base_url='http://127.0.0.1:6499')
    assert anon.get(uri+'program.wasm').status_code == 401
    assert client.get('/api/recomp/experiment?backend=matching-n64').status_code == 400
    assert client.post('/api/recomp/experiment', headers={'X-Decomp': '1'}, json={'hex': spec['demo_hex'], 'target': 'unknown'}).status_code == 400


@needs_native
@pytest.mark.parametrize('code', [
    words(0x00002503, HALT),  # load a known instruction word: checks little-endian code memory
    words(0x00010137, addi(2, 2, -4), addi(10, 0, -1), 0x00a12023, 0x00012503, HALT),  # last valid word
    words(addi(2, 0, -1), 0x00012003, HALT),  # LW x0 must still fault
    words(addi(2, 0, 1), 0x00012503, HALT),  # misaligned word load
])
def test_wasm_edge_cases_match_native_and_oracle(tmp_path, code):
    expected = execute(code)
    for target, runner in (('native', rv32.build_and_run), ('wasm', wasm.build_and_run)):
        root = tmp_path / target
        if expected['state'] == 'halted':
            result = runner(code, root, log=lambda _: None)
        else:
            with pytest.raises(rv32.TranslationError, match=expected['state']):
                runner(code, root, log=lambda _: None)
            result = json.loads((root / 'result.json').read_text())
        assert result['execution'] == expected


@needs_node
def test_invalid_wasm_never_reports_success(tmp_path, monkeypatch):
    monkeypatch.setattr(wasm, 'emit', lambda _: (b'invalid module', []))
    with pytest.raises(rv32.TranslationError, match='validation/execution failed'):
        wasm.build_and_run(words(HALT), tmp_path / 'out', log=lambda _: None)
    assert not (tmp_path / 'out/result.json').exists()
