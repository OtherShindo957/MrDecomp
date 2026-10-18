# Development handoff

## Architecture audit

The project is Python 3.12+, packaged with uv_build. `decompnet.app.cli` starts Uvicorn and the authenticated local web/MCP server. `app/static` is plain HTML, CSS and JavaScript with no frontend build step. `app/engine.py` manages ROM projects and matching; `forks`, compiler/toolchain, ROM and project modules implement community imports and platform-specific work. SQLite stores project/function/claim state. Agent manager/bridge/connect modules implement local processes and MCP connectivity. `site/` is the separate upstream marketing/distribution site, not the application GUI. Upstream installers target upstream releases and are retained for reference; use `packaging/install-linux.sh` for this fork.

## Current implementation

`backends/` describes the included platform adapters and probes headers without installing tools. Existing platform implementation remains in the legacy engine; matching dispatch extraction is future work; recompilation now uses executable `Recompiler` adapters from `recomp/adapters.py`. Each adapter validates input, lists target-specific dependencies/availability and dispatches build/verification to the selected target. `app/diagnostics.py` is shared by the GUI and `mrdecomp doctor`. `/api/preflight` is read-only: it reports likely adapters, compiler state and output location. Full import remains authoritative.

`RomNetwork.import_rom` serializes allocation/registration with an instance lock and passes an optional output parent down to the legacy and community scratch paths. It never temporarily reassigns the global workspace. Existing project hashes reopen their original folders. Community clone behavior remains unchanged and now has a compiler-independent regression test.

`recomp/rv32.py` decodes an explicitly enumerated RV32I subset and emits C statements, then compiles and runs a generated native program with guest memory/step bounds. The GUI experiment uses the authenticated `/api/recomp/experiment` endpoint and existing background jobs. Two experiments may run concurrently. Each new experiment folder retains input, source, executable and JSON results; traps produce an error job and saved diagnostics. `recomp/wasm.py` emits a standalone WebAssembly module from the same decoded instructions, validates/executes it in Node, and writes a self-contained browser test page. Guest memory remains 64 KiB; a second fixed page exposes diagnostics to the browser. `/experiments/{job_id}/{filename}` serves only the four browser assets for successful authenticated WebAssembly jobs. Preview addresses are in-memory and do not survive application restart; saved folders remain usable with a local HTTP server. See examples/rv32/README.md for the exact ABI, supported instructions and CC0 fixture provenance.

## Validation

Original baseline: 107 passed, 139 skipped, 3 failed, 20 errors. Missing target directories caused most errors; demo-dependent tests lacked compiler prerequisite markers.

Latest focused run (unmodified runtime sandbox settings):

```bash
uv run pytest -q tests/test_recomp.py tests/test_backend_registry.py tests/test_mrdecomp.py tests/test_app_server.py tests/test_updates.py tests/test_gc.py tests/test_ds_init.py tests/test_dtksplits.py tests/test_wasm.py
```

Result: **124 passed, 10 skipped**. Includes actual generated C compilation/execution, per-instruction cases, guest traps, API job success/failure, read-only preflight, clone regression, output forwarding/collision preservation and existing API/update regressions.

Latest full fixture run: **221 passed, 141 skipped**, with the inherited SOCKS proxy environment variables removed for loopback HTTP tests and `compiler._sandbox_mode` temporarily overridden in the test process to select `none` for auto-sandboxed trusted repository fixtures. Production code and sandbox defaults were not changed. This verifies compilation/matching behavior with the host compiler; it does not certify production bubblewrap isolation. A normal full run in this host previously encountered compiler sandbox timeouts and a missing socksio proxy dependency.

`node --check` passed for app.js and tests/gui/smoke.cjs; shell syntax and git diff whitespace checks passed. The installer was executed with temporary HOME, UV_TOOL_DIR and UV_TOOL_BIN_DIR: isolated application install, applications-menu entry, icon, and installed `mrdecomp --version` all passed. `mrdecomp doctor` correctly reports required versus optional tools. The local backend startup/health smoke check passed in the initial change.

Playwright end-to-end tests now **pass** in headless Chromium 143 on this Ubuntu 24.04 AMD64 container. The test opens the real app, checks mode gating/diagnostics/preflight, executes a native program, builds WebAssembly, opens the authenticated local preview and executes it in the browser, rejects invalid code, displays step-limit failures, and checks mobile overflow. Desktop and WebAssembly screenshots were visually inspected. This verifies the tested browser flow, not a physical Linux Mint desktop or a full browser matrix.

To reproduce with an installed Chromium:

```bash
npm ci --prefix tests/gui
npm exec --prefix tests/gui -- playwright install chromium
uv run python tests/gui/run_smoke.py
```

`MRDECOMP_CHROMIUM=/path/to/chromium` can select an existing headless browser. The test helper creates a fresh temporary project home, starts the app on loopback with an ephemeral port, runs the browser checks and cleans up. Playwright is an optional test dependency and is not needed to launch MrDecomp.

The independent test-only RV32 interpreter in tests/rv32_oracle.py imports no production decoder. Tests compare native, WebAssembly and reference state across 16 deterministic randomized programs, loop fixtures, boundary memory access, trap cases and unsigned arithmetic. Wasm tests also verify no host imports, fixed memory size/reset, invalid-module failure and authenticated asset allowlisting. Toolchain-dependent game tests remain skipped; no commercial game assets were used.

## Continue here

Prioritize real Mint desktop installation, legacy matching-backend dispatch extraction, a full external ISA oracle, saved experiment history and a minimal graphics/input runtime for a redistributable test game. Do not enable game recompilation/native/web modes based on the RV32 test backend. Keep package/module names and legacy MCP commands compatible until a migration is tested. Hosted upstream installers and some service/MCP wording remain inherited; application updates are disabled to protect the fork. Toolchain installation still uses inherited consent flows.
