#!/usr/bin/env bash
#
# Build and publish ytmp3-dl to PyPI, from where pip, uv and pipx all install it.
#
#   scripts/release.sh --bump 0.2.0   set the version, then stop
#   scripts/release.sh --dry-run      checks and build only
#   scripts/release.sh --test         publish to TestPyPI
#   scripts/release.sh                publish to PyPI
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION_FILE="src/ytmp3/__init__.py"
DIST_NAME="ytmp3-dl"
TESTPYPI_URL="https://test.pypi.org/legacy/"

bump=""
dry_run=false
test_pypi=false
make_tag=false
skip_checks=false
assume_yes=false

bold=$'\033[1m'; red=$'\033[31m'; green=$'\033[32m'; yellow=$'\033[33m'; dim=$'\033[2m'; off=$'\033[0m'
info()  { printf '%s==>%s %s\n' "$bold" "$off" "$*"; }
warn()  { printf '%swarn%s %s\n' "$yellow" "$off" "$*" >&2; }
die()   { printf '%serror%s %s\n' "$red" "$off" "$*" >&2; exit 1; }
run()   { printf '%s$ %s%s\n' "$dim" "$*" "$off"; "$@"; }

usage() {
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
    cat <<'EOF'

Options:
  --bump VERSION   Write VERSION into src/ytmp3/__init__.py and exit.
  --dry-run        Run the checks and build, but do not upload.
  --test           Upload to TestPyPI instead of PyPI.
  --tag            Create an annotated git tag vVERSION after a successful upload.
  --skip-checks    Skip ruff and pytest. For re-runs after a failed upload.
  -y, --yes        Do not ask before uploading.
  -h, --help       Show this help.

Credentials:
  Set UV_PUBLISH_TOKEN to a PyPI API token (pypi-...), or configure a trusted
  publisher. Nothing is read from or written to the repository.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bump)       bump="${2:-}"; [[ -n "$bump" ]] || die "--bump needs a version"; shift 2 ;;
        --dry-run)    dry_run=true; shift ;;
        --test)       test_pypi=true; shift ;;
        --tag)        make_tag=true; shift ;;
        --skip-checks) skip_checks=true; shift ;;
        -y|--yes)     assume_yes=true; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            die "unknown option: $1 (try --help)" ;;
    esac
done

command -v uv >/dev/null || die "uv is not installed: https://docs.astral.sh/uv/"

read_version() {
    sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$VERSION_FILE"
}

# --bump: edit the single source of truth and stop

if [[ -n "$bump" ]]; then
    [[ "$bump" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.]+)?$ ]] \
        || die "not a version: $bump (expected e.g. 0.2.0 or 1.0.0rc1)"
    current="$(read_version)"
    [[ "$bump" != "$current" ]] || die "already at $current"

    tmp="$(mktemp)"
    sed "s/^__version__ = \".*\"$/__version__ = \"$bump\"/" "$VERSION_FILE" > "$tmp"
    mv "$tmp" "$VERSION_FILE"
    [[ "$(read_version)" == "$bump" ]] || die "failed to write the version into $VERSION_FILE"

    info "$current → ${green}${bump}${off}"
    echo "Next: add a CHANGELOG.md entry, commit, then run scripts/release.sh"
    exit 0
fi

VERSION="$(read_version)"
[[ -n "$VERSION" ]] || die "no __version__ found in $VERSION_FILE"
TAG="v$VERSION"

if $test_pypi; then
    target="TestPyPI"
else
    target="PyPI"
fi
info "Releasing ${bold}${DIST_NAME} ${VERSION}${off} to ${bold}${target}${off}"

# Preflight

if git rev-parse --git-dir >/dev/null 2>&1; then
    # A dry run only builds, so it is useful before anything is committed.
    if [[ -n "$(git status --porcelain)" ]]; then
        if $dry_run; then
            warn "working tree is dirty; a real release would refuse to run"
        else
            git status --short
            die "working tree is dirty; commit or stash first"
        fi
    fi
    if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
        $make_tag && die "tag $TAG already exists; bump the version first"
        warn "tag $TAG already exists"
    fi
else
    warn "not a git repository; skipping the clean-tree check"
fi

grep -q "\[$VERSION\]" CHANGELOG.md 2>/dev/null \
    || warn "CHANGELOG.md has no entry for $VERSION"

if ! $test_pypi && curl -sfI "https://pypi.org/pypi/$DIST_NAME/$VERSION/json" >/dev/null 2>&1; then
    die "$DIST_NAME $VERSION is already on PyPI; versions cannot be replaced, bump instead"
fi

# Checks

if $skip_checks; then
    warn "skipping ruff and pytest"
else
    info "Checks"
    run uv run ruff check .
    run uv run pytest -q
fi

# Build

info "Build"
rm -rf dist
run uv build
run uv run --with "twine>=6.1" twine check dist/*

ls -1 dist
[[ -f "dist/ytmp3_dl-$VERSION.tar.gz" ]] \
    || die "dist/ytmp3_dl-$VERSION.tar.gz missing; the built version does not match $VERSION"

if $dry_run; then
    info "${green}Dry run${off}: dist/ built, nothing uploaded"
    exit 0
fi

# Publish 

if [[ -z "${UV_PUBLISH_TOKEN:-}" ]]; then
    warn "UV_PUBLISH_TOKEN is not set; uv will prompt for credentials"
fi

if ! $assume_yes; then
    printf '\nUpload %s %s to %s? [y/N] ' "$DIST_NAME" "$VERSION" "$target"
    read -r reply
    [[ "$reply" =~ ^[Yy]$ ]] || die "aborted"
fi

info "Publish"
if $test_pypi; then
    run uv publish --publish-url "$TESTPYPI_URL" dist/*
else
    run uv publish dist/*
fi

# Tag

if $make_tag && git rev-parse --git-dir >/dev/null 2>&1; then
    run git tag -a "$TAG" -m "$DIST_NAME $VERSION"
    info "tagged $TAG — push it with: git push origin $TAG"
fi

info "${green}Published ${DIST_NAME} ${VERSION} to ${target}${off}"
if $test_pypi; then
    cat <<EOF

Verify the upload:
  uvx --index https://test.pypi.org/simple/ --index-strategy unsafe-best-match \\
      ${DIST_NAME}==${VERSION} --version
EOF
else
    cat <<EOF

Verify the upload:
  uvx ${DIST_NAME}@${VERSION} --version
EOF
fi
