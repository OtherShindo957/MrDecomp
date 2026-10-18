# Changelog

## Unreleased — MrDecomp Phase 1 foundation

- Preserve the Python matching engine, MCP tools, plain JavaScript GUI and MIT attribution.
- Brand local GUI, launcher and CLI as MrDecomp; preserve legacy Python package and commands.
- Add four project mode choices and a platform capability registry. Only matching decompilation is available; unavailable modes explain why and are rejected by the import API.
- Add `mrdecomp`, version reporting, non-installing dependency diagnostics, isolated Linux installer and applications-menu integration.
- Preserve existing project-home overrides and existing `~/Decomp` storage; new homes default to `~/MrDecomp`.
- Disable upstream application updates to protect the fork.
- Create target directories before legacy project build commands. Mark the existing API-agent demo test with its actual compiler prerequisite.
