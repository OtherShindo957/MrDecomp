# Roadmap

## Phase 1 — GUI foundation implemented; desktop QA remains

Implemented: local GUI branding; four honest game-mode choices; capability registry; legacy matching workflows; CLI entry point, shared CLI/GUI diagnostics, isolated Linux installer and applications-menu launcher; dashboard actions; compatibility preflight with header detection and compiler status; custom output-parent selection for both legacy ROM imports and GameCube/Wii/DS scratch projects. Duplicate imports reopen existing project folders. New imports allocate unique subfolders without changing global workspace state.

Remaining: native directory-picker integration, fully sequential wizard refinement, complete branding audit (hosted site, services, MCP instructions), broader cross-browser/accessibility testing and installation QA on actual Mint 22, Ubuntu 24.04 and Debian 12. The isolated installer and Chromium GUI flow were tested here, but this Ubuntu container is not a Mint desktop.

## Phase 2 — backend registry implemented; extraction continues

Implemented: explicit backend descriptors, duplicate/status validation, format/header probes, included-adapter versus installed-toolchain reporting, diagnostics API. Existing N64, GameCube, Wii, PS1/PS2, GBA and DS engine workflows remain in use.

Executable recompiler adapters now own validation, supported output targets, dependency reporting and build/verification dispatch. Remaining: migrate legacy matching import/build dispatch into executable backend interfaces; shared binary-loader services; per-game compatibility database. Registry inclusion does not certify a particular game.

## Phase 3 — executable static recompilation proof of concept

Implemented: raw RV32I subset decoder and C translator; fixed PC/register/memory contract; branch/jump target checks; bounded guest memory and instruction count; generated native execution harness; translation/compiler/runtime diagnostics and persistent outputs; GUI experiment runner with real job state. Tests execute every accepted instruction and failure states. The CC0 sum fixture executes real translated logic and returns 55 for input 10.

An independent test-only interpreter now checks complete register/PC/step results against both native and WebAssembly output, including deterministic randomized programs. Remaining: broader instruction coverage, ELF loaders, relocations, ABI interoperability, comparison against a full external emulator, runtime services and real console architecture backends. The experiment is explicitly separate from game import modes. It supports 13 named instructions, not the complete RV32I ISA.

## Phase 4 — native game runtime planned

Implement graphics/audio/input/filesystem/timing services and a redistributable playable test game; verify rendering, input and game logic. Native translated program execution is verified, but no playable native game runtime exists yet.

## Phase 5 — WebAssembly program pipeline implemented; game runtime planned

Implemented: direct RV32 subset-to-WebAssembly output, fixed guest memory and diagnostics, Node.js validation/execution, standalone local browser page, authenticated allowlisted preview routes and GUI target selection. Chromium end-to-end tests execute the translated program in the browser and validate a0=55. Native/WebAssembly/reference results agree for the tested programs. Unsupported instructions, guest traps and invalid modules fail explicitly.

Remaining: graphics/audio/input/gamepad/filesystem runtime services, a playable redistributable browser test game, persistent experiment history, browser-matrix testing and common console runtime support. This is a verified program translation proof of concept, not a commercial game port.

## Phase 6 — additional platforms planned

Expand platforms only when backed by decoding, translation, ABI and execution tests. Header recognition alone never enables game porting.
