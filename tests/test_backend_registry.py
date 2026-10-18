from dataclasses import replace
from pathlib import Path
import pytest

from decompnet.backends import Registry, default_registry
from decompnet.app.diagnostics import output_parent, report
from tests.test_app_server import app


def test_registry_detects_headers_and_rejects_duplicate_plugins():
    reg = default_registry()
    assert reg.detect(bytes.fromhex('80371240'))[0]['id'] == 'matching-n64'
    assert reg.detect(b'PS-X EXE')[0]['id'] == 'matching-ps'
    assert reg.detect(b'not a program') == []
    assert reg.detect(b'\x7fELF\x02\x01' + b'\0' * 30) == []
    with pytest.raises(ValueError, match='Duplicate'):
        reg.register(reg.get('matching-n64'))
    with pytest.raises(ValueError, match='Unknown'):
        reg.get('missing')
    with pytest.raises(ValueError, match='Invalid'):
        Registry().register(replace(reg.get('matching-n64'), status='playable'))


def test_output_validation_does_not_create_or_overwrite(tmp_path):
    target = tmp_path / 'new' / 'parent'
    assert output_parent(str(target), tmp_path) == target
    assert not target.exists()
    assert output_parent('', tmp_path) == tmp_path
    for path in ('relative/path', '\0invalid'):
        with pytest.raises(ValueError):
            output_parent(path, tmp_path)
    file = tmp_path / 'file'
    file.write_text('keep')
    with pytest.raises(ValueError, match='writable'):
        output_parent(str(file / 'child'), tmp_path)
    assert file.read_text() == 'keep'


def test_host_diagnostics_are_read_only(tmp_path):
    result = report(tmp_path / 'absent')
    assert result['python_supported']
    assert result['storage_writable']
    assert {t['id'] for t in result['tools']} >= {'git', 'cc', 'emcc'}
    assert not (tmp_path / 'absent').exists()


def test_preflight_and_diagnostics_require_auth(app, tmp_path):
    client, _, _ = app
    assert client.get('/api/diagnostics').json()['application'] == 'MrDecomp'
    assert any(b['id'] == 'matching-n64' for b in client.get('/api/backends').json()['backends'])
    assert client.post('/api/preflight', json={'head': '80371240'}).status_code == 403
    response = client.post('/api/preflight', json={'head': '80371240', 'output': str(tmp_path / 'out')}, headers={'X-Decomp': '1'})
    assert response.status_code == 200
    assert response.json()['detected'][0]['architecture'] == 'MIPS'
    assert response.json()['can_start']
    assert not (tmp_path / 'out').exists()
    for body in ({'head': 'zz'}, {'head': ''}, {'head': '00', 'output': 'relative'}, {'head': '00', 'mode': 'web'}):
        assert client.post('/api/preflight', json=body, headers={'X-Decomp': '1'}).status_code == 400


def test_local_disc_preflight_reads_only_header(app, tmp_path):
    client, _, _ = app
    disc = tmp_path / 'disc.iso'
    header = bytearray(0x440)
    header[0x1c:0x20] = bytes.fromhex('c2339f3d')
    disc.write_bytes(header)
    response = client.post('/api/preflight', json={'path': str(disc)}, headers={'X-Decomp': '1'})
    assert response.status_code == 200
    assert response.json()['detected'][0]['id'] == 'matching-powerpc'
    assert response.json()['size'] == len(header)
    assert disc.read_bytes() == header


def test_preflight_reports_registered_compiler(app):
    client, _, _ = app
    result = client.post('/api/preflight', json={'head': '80371240', 'toolchain': 'gcc-2.7.2-kmc'}, headers={'X-Decomp': '1'})
    assert result.status_code == 200
    assert result.json()['compiler']['id'] == 'gcc-2.7.2-kmc'


def test_selected_output_reaches_import_without_mutating_global_workspace(app, tmp_path, monkeypatch):
    import time
    client, net, _ = app
    previous = net.workspace
    observed = {}
    def capture(game, **kwargs):
        observed.update(kwargs)
        return 'captured-project'
    monkeypatch.setattr(net, 'import_rom', capture)
    monkeypatch.setattr(net, 'start_autopilot', lambda *a: None)
    target = tmp_path / 'chosen'
    response = client.post('/api/import', params={'demo': '1', 'output': str(target)}, headers={'X-Decomp': '1'})
    assert response.status_code == 200
    for _ in range(100):
        state = client.get('/api/job', params={'id': response.json()['job']}).json()
        if state['state'] != 'running':
            break
        time.sleep(.01)
    assert state['state'] == 'done'
    assert observed['output'] == target
    assert net.workspace == previous


def test_experiment_api_reports_actual_execution_and_errors(app, tmp_path):
    import time
    import shutil
    client, _, _ = app
    spec = client.get('/api/recomp/experiment').json()
    assert 'SW' in spec['supported_instructions']
    headers = {'X-Decomp': '1'}
    assert client.post('/api/recomp/experiment', json={}).status_code == 403
    for invalid in ({'hex': 'ffffffff'}, {'hex': spec['demo_hex'], 'argument': -1}):
        assert client.post('/api/recomp/experiment', json=invalid, headers=headers).status_code == 400
    if not shutil.which('cc'):
        pytest.skip('native experiment needs cc')
    for code, expected in ((spec['demo_hex'], 'done'), ('6f000000', 'error')):
        result = client.post('/api/recomp/experiment', json={'hex': code, 'argument': 10, 'output': str(tmp_path)}, headers=headers)
        assert result.status_code == 200
        for _ in range(200):
            job = client.get('/api/job', params={'id': result.json()['job']}).json()
            if job['state'] != 'running':
                break
            time.sleep(.01)
        assert job['state'] == expected
        if expected == 'done':
            assert job['result']['execution']['registers'][10] == 55
            assert (Path(job['result']['output']) / 'translated.c').is_file()
        else:
            assert 'step-limit' in job['error']


def test_community_clone_still_works_without_compiler_tools(tmp_path):
    import subprocess
    import shutil
    from decompnet.app.engine import RomNetwork
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / 'local-source'
    shutil.copytree(root / 'projects/demo-fork', source)
    subprocess.run(['git', 'init', '-q', str(source)], check=True)
    subprocess.run(['git', '-C', str(source), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    workspace = tmp_path / 'workspace'
    net = RomNetwork(tmp_path / 'db.sqlite', workspace)
    slug = net.forks.clone(str(source), log=lambda _: None)
    assert Path(net.project_row(slug)['root']).is_relative_to(workspace)
    assert net.forks.clone(str(source), log=lambda _: None) == slug


def test_community_scratch_uses_selected_output_and_preserves_collisions(tmp_path, monkeypatch):
    from decompnet.app.engine import RomNetwork
    from decompnet.app import forkengine
    net = RomNetwork(tmp_path / 'db.sqlite', tmp_path / 'workspace')
    game = tmp_path / 'test.dol'
    game.write_bytes(b'fixture')
    monkeypatch.setattr(net, '_community_layout', lambda *a: game)
    monkeypatch.setattr(forkengine.scratch_dsd, 'is_nds', lambda _: False)
    monkeypatch.setattr(forkengine.scratch_dtk, 'game_info', lambda _: {'dol': b'test code', 'title': 'Test', 'kind': 'dol'})
    def create(dest, *a, **kw):
        dest.mkdir(parents=True)
        return {'platform': 'gc', 'id': 'TEST01', 'title': 'Test', 'compiler': 'GC/1.3.2'}
    monkeypatch.setattr(forkengine.scratch_dtk, 'create', create)
    monkeypatch.setattr(net.forks, 'check', lambda *a, **kw: None)
    output = tmp_path / 'chosen'
    (output / 'test').mkdir(parents=True)
    marker = output / 'test/keep'
    marker.write_text('preserved')
    slug = net.import_rom(game, confirmed=True, output=output, log=lambda _: None)
    assert Path(net.project_row(slug)['root']) == output / 'test-2'
    assert marker.read_text() == 'preserved'
    assert net.workspace == tmp_path / 'workspace'
    # A duplicate import reopens the existing project, even with another requested parent.
    assert net.import_rom(game, confirmed=True, output=tmp_path / 'other', log=lambda _: None) == slug
