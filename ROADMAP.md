# Roadmap

## Phase 1 — GUI foundation implemented; desktop QA remains

Implemented: local GUI branding; four honest game-mode choices; capability registry; legacy matching workflows; CLI entry point, shared CLI/GUI diagnostics, isolated Linux installer and applications-menu launcher; dashboard actions; compatibility preflight with header detection and compiler status; custom output-parent selection for both legacy ROM imports and GameCube/Wii/DS scratch projects. Duplicate imports reopen existing project folders. New imports allocate unique subfolders without changing global workspace state.

Remaining: native directory-picker integration, fully sequential wizard refinement, complete branding audit (hosted site, services, MCP instructions), visual/accessibility testing and installation QA on actual Mint 22, Ubuntu 24.04 and Debian 12. The isolated installer was tested here, but this container is not a Mint desktop.

## Phase 2 — backend registry implemented; extraction continues

Implemented: explicit backend descriptors, duplicate/status validation, format/header probes, included-adapter versus installed-toolchain reporting, diagnostics API. Existing N64, GameCube, Wii, PS1/PS2, GBA and DS engine workflows remain in use.

Remaining: migrate legacy import/build dispatch into executable backend interfaces; shared binary-loader services; per-game compatibility database. Registry inclusion does not certify a particular game.

## Phase 3 — executable static recompilation proof of concept

Implemented: raw RV32I subset decoder and C translator; fixed PC/register/memory contract; branch/jump target checks; bounded guest memory and instruction count; generated native execution harness; translation/compiler/runtime diagnostics and persistent outputs; GUI experiment runner with real job state. Tests execute every accepted instruction and failure states. The CC0 sum fixture executes real translated logic and returns 55 for input 10.

Remaining: broader instruction coverage, ELF loaders, relocations, ABI interoperability, an independent emulator oracle, runtime services and real console architecture backends. The experiment is explicitly separate from game import modes. It supports 13 named instructions, not the complete RV32I ISA.

## Phases 4–6 — planned

Implement native graphics/audio/input/filesystem/timing services and a redistributable playable test game; verify rendering, input and game logic. Add a verified browser/WebAssembly pipeline with shared runtime services. Expand platforms only when backed by execution tests. No playable native game or browser port has been demonstrated yet.
