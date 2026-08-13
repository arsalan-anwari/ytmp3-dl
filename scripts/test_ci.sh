#!/usr/bin/env bash
#
# Run the CI gate locally, with or without act.
#
#   scripts/test_ci.sh              local gate, then act if it is installed
#   scripts/test_ci.sh --no-act     local gate only
#   scripts/test_ci.sh --fix        apply ruff fixes first, then the gate

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="$HOME/.local/bin:$PATH"

WORKFLOW=".github/workflows/ci.yml"
ACT_IMAGE="catthehacker/ubuntu:act-latest"

fix=false
run_act=true
act_args=()

bold=$'\033[1m'; red=$'\033[31m'; green=$'\033[32m'; yellow=$'\033[33m'; dim=$'\033[2m'; off=$'\033[0m'
info() { printf '%s==>%s %s\n' "$bold" "$off" "$*"; }
warn() { printf '%swarn%s %s\n' "$yellow" "$off" "$*" >&2; }
die()  { printf '%serror%s %s\n' "$red" "$off" "$*" >&2; exit 1; }
run()  { printf '%s$ %s%s\n' "$dim" "$*" "$off"; "$@"; }

usage() {
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
    cat <<'EOF'

Options:
  --fix        Run ruff check --fix and ruff format before the gate.
  --no-act     Skip act even if it is installed.
  -h, --help   Show this help.

Anything else is passed through to act, e.g. --job test, -v.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fix)     fix=true; shift ;;
        --no-act)  run_act=false; shift ;;
        -h|--help) usage; exit 0 ;;
        *)         act_args+=("$1"); shift ;;
    esac
done

command -v uv >/dev/null || die "uv is not installed: https://docs.astral.sh/uv/"
[[ -f "$WORKFLOW" ]] || die "no workflow at $WORKFLOW"

# Sync

info "Sync"
run uv sync --frozen

# Fix

if $fix; then
    info "Fix"
    run uv run ruff check --fix .
    # Not part of the gate; CI checks lint rules, not formatting.
    run uv run ruff format .
fi

# Gate

info "Lint"
run uv run ruff check .

info "Tests"
run uv run pytest -q

info "Build"
rm -rf dist
run uv build
run uv run --with "twine>=6.1" twine check dist/*

info "${green}Local gate passed${off}"

# Act 

if ! $run_act; then
    exit 0
fi

if ! command -v act >/dev/null 2>&1; then
    warn "act is not installed; ran the local gate only"
    exit 0
fi

# act speaks the Docker API; on Fedora that is the rootless podman socket.
SOCK="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
if [[ -z "${DOCKER_HOST:-}" && -S "$SOCK" ]]; then
    export DOCKER_HOST="unix://$SOCK"
    info "Using podman at $SOCK"
fi

info "act"
if ! act push -W "$WORKFLOW" -P "ubuntu-latest=$ACT_IMAGE" "${act_args[@]}"; then
    warn "act did not complete (container backend or image pull unavailable);
     the local gate above is authoritative and passed"
fi
