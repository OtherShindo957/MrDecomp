#!/usr/bin/env bash
# Run from a checkout of OtherShindo957/MrDecomp. No sudo or system Python writes.
set -euo pipefail
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo 'This installer targets Linux AMD64.' >&2
  exit 1
fi
command -v uv >/dev/null || { echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' >&2; exit 1; }
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
uv tool install --python 3.12 --from "$repo_dir" decompnet
"$(uv tool dir --bin)/mrdecomp" shortcut
echo 'Installed MrDecomp. Open it from the applications menu, or run mrdecomp.'
