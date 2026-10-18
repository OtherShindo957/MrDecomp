# Changelog

## 0.11.0 — verified WebAssembly target and browser execution

- Add executable recompiler adapters with per-target dependencies and validation; preserve legacy matching implementations.
- Add direct RV32 subset-to-WebAssembly output, fixed memory, execution bounds and Node.js validation/execution.
- Generate a standalone browser page and authenticated, allowlisted local preview from the GUI.
- Verify actual native/WebAssembly/reference equivalence with an independent interpreter, randomized programs, boundary accesses and failure states.
- Execute the real GUI smoke test in headless Chromium, including WebAssembly output, invalid-code/step-limit errors and mobile layout checks.
- Add a disposable GUI test launcher and optional locked Playwright test dependencies.
- Correct capability reporting to distinguish experimental program translation from unsupported console game ports.
- Bump the application version so prior 0.10.6 daemons restart into the updated application.

## Unreleased — GUI preflight, backend registry and RV32 experiment

- Add dashboard system/backend diagnostics and shared CLI reports distinguishing required/optional tools.
- Add read-only header preflight, compiler status and output-folder review before game import.
- Support selected output parents in legacy ROM and community scratch workflows, preserving duplicate imports and existing folders.
- Add explicit backend registration and conservative header probes; preserve legacy import implementations.
- Add a separate experimental RV32I subset-to-C pipeline, actual native compilation/execution, bounded memory and instruction count, saved artifacts and GUI diagnostics.
- Test all 13 accepted instruction types, arithmetic/branch/memory behavior, malformed input and execution failures with redistributable fixtures.
- Add community clone/output regressions and a repeatable Playwright GUI smoke test (browser execution pending).
- Verify isolated Linux installer/menu integration; force reinstall when rerunning the installer so source updates apply.

## Initial MrDecomp Phase 1 foundation

- Preserve the Python matching engine, MCP tools, plain JavaScript GUI and MIT attribution.
- Brand local GUI, launcher and CLI as MrDecomp; preserve legacy Python package and commands.
- Add four project mode choices and a platform capability registry. Only matching decompilation is available; unavailable modes explain why and are rejected by the import API.
- Add `mrdecomp`, version reporting, non-installing dependency diagnostics, isolated Linux installer and applications-menu integration.
- Preserve existing project-home overrides and existing `~/Decomp` storage; new homes default to `~/MrDecomp`.
- Disable upstream application updates to protect the fork.
- Create target directories before legacy project build commands. Mark the existing API-agent demo test with its actual compiler prerequisite.
