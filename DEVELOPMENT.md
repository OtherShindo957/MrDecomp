# Development handoff

## Architecture audit

The project is Python 3.12+, packaged with uv_build. `decompnet.app.cli` starts Uvicorn and the authenticated local web/MCP server. `app/static` is plain HTML, CSS and JavaScript with no frontend build step. `app/engine.py` manages ROM projects and matching; `forks`, compiler/toolchain, ROM and project modules implement community imports and platform-specific work. SQLite stores project/function/claim state. Agent manager/bridge/connect modules implement local processes and MCP connectivity. `site/` is the separate upstream marketing/distribution site, not the application GUI. Upstream installers target upstream releases and are retained for reference; use `packaging/install-linux.sh` for this fork.

## Validation

Baseline, before edits: 107 passed, 139 skipped, 3 failed, 20 errors. Missing target directories caused most errors; a demo-dependent API-agent test had no prerequisite marker.

Focused post-change run: `uv run pytest -q tests/test_mrdecomp.py tests/test_app_server.py tests/test_updates.py` — 24 passed, 5 skipped. `node --check src/decompnet/app/static/app.js` passed. `mrdecomp --version` passed; `mrdecomp doctor` correctly reported missing ld.lld with nonzero exit status. A temporary-home subprocess smoke check launched `mrdecomp --no-browser` and verified `/health` before terminating it.

Full post-change suite attempted: compiler tests time out in this execution environment (15 seconds per compilation); `test_every_solution_matches` reports a compiler timeout. Full-suite completion is not certified. Toolchain-dependent tests remain skipped; no commercial game or playable native/browser port was tested. No visual browser automation or physical Linux Mint installation was performed.

## Continue here

Finish Phase 1 items in ROADMAP.md. Keep package/module names compatible until MCP, update, tool installation and bridge migration tests exist. Capability status reflects inherited engine coverage, not a fresh real-game certification. The mode registry is deliberately conservative; do not enable planned modes merely because a file's architecture can be recognized. Application update routes are disabled; toolchain installation still uses inherited consent flows. Review obsolete hosted installer links before distributing a release.
