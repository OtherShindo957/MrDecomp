# Roadmap

## Phase 1 — in progress

Implemented: local GUI branding; four honest mode choices; capability registry; legacy matching workflows preserved; CLI entry point, diagnostics, Linux installation script and launcher; API rejection tests and startup smoke check.

Remaining: full sequential project wizard with preflight and output folder selection, installed-backend versus dependency reporting, graphical system diagnostics, complete branding audit (including hosted site, services and MCP instructions), browser interaction/accessibility tests and installation QA on Mint 22, Ubuntu 24.04 and Debian 12. Existing source, assembly, diff, logs and agent screens remain inherited behavior.

## Phase 2

Extract registered backend interfaces from existing engine dispatch. Add per-game compatibility and dependency reporting. Verify N64, GameCube and Wii regressions with appropriate toolchains.

## Phase 3

Implement one deliberately small instruction translator, binary loader, ABI and memory model, with freely redistributable execution fixtures before enabling recompilation.

## Phases 4–6

Implement native runtime services and a redistributable playable test game; verify build, rendering, input and game logic. Share runtime services with a tested Emscripten/browser pipeline. Expand platforms only when backed by execution tests.
