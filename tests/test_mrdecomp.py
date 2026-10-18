import pytest
from decompnet.app.capabilities import registry, require_mode
from decompnet.app.cli import main, home_dir
from tests.test_app_server import app


def test_modes_are_honest():
    caps = registry()
    assert len(caps['modes']) == 4
    assert [m['id'] for m in caps['modes'] if m['available']] == ['decompilation']
    require_mode('decompilation')
    for mode in ('native', 'recompilation', 'web', 'bogus'):
        with pytest.raises(ValueError):
            require_mode(mode)
    assert next(p for p in caps['platforms'] if p['id'] == 'gc')['status'] == 'supported'


def test_modes_rejected_before_import(app):
    client, _, _ = app
    assert client.get('/api/state').json()['capabilities']['modes']
    for mode in ('native', 'recompilation', 'web', 'bogus'):
        result = client.post('/api/import?mode=' + mode, content=b'', headers={'X-Decomp': '1'})
        assert result.status_code == 400
        assert result.json()['error']
    html = client.get('/').text
    assert '<title>MrDecomp</title>' in html
    assert 'id="projectMode"' in html


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as result:
        main(['--version'])
    assert result.value.code == 0
    assert 'MrDecomp' in capsys.readouterr().out


def test_home_override(monkeypatch, tmp_path):
    monkeypatch.setenv('MRDECOMP_HOME', str(tmp_path))
    assert home_dir() == tmp_path
