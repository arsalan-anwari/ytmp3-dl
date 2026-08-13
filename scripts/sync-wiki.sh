#!/usr/bin/env bash
#
# Mirror docs/ into the GitHub wiki, which is its own git repository.
#
#   scripts/sync-wiki.sh --dry-run    show what would change
#   scripts/sync-wiki.sh              copy, commit and push
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOCS="$ROOT/docs"
DEFAULT_SLUG="arsalan-anwari/ytmp3-dl"

dry_run=false
message=""
slug=""

bold=$'\033[1m'; red=$'\033[31m'; green=$'\033[32m'; yellow=$'\033[33m'; dim=$'\033[2m'; off=$'\033[0m'
info() { printf '%s==>%s %s\n' "$bold" "$off" "$*"; }
warn() { printf '%swarn%s %s\n' "$yellow" "$off" "$*" >&2; }
die()  { printf '%serror%s %s\n' "$red" "$off" "$*" >&2; exit 1; }
run()  { printf '%s$ %s%s\n' "$dim" "$*" "$off"; "$@"; }

usage() {
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
    cat <<'EOF'

Options:
  -n, --dry-run     Show the diff without committing or pushing.
  -m, --message M   Commit message. Default: "docs: sync from <short sha>".
  --repo OWNER/NAME Wiki to sync to. Default: the origin remote.
  -h, --help        Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run) dry_run=true; shift ;;
        -m|--message) message="${2:-}"; [[ -n "$message" ]] || die "--message needs a value"; shift 2 ;;
        --repo)       slug="${2:-}"; [[ -n "$slug" ]] || die "--repo needs OWNER/NAME"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        *)            die "unknown option: $1 (try --help)" ;;
    esac
done

[[ -d "$DOCS" ]] || die "no docs/ directory at $DOCS"

# The wiki is flat: a page is a file, and there are no subdirectories.
if find "$DOCS" -mindepth 2 -name '*.md' -print -quit | grep -q .; then
    find "$DOCS" -mindepth 2 -name '*.md'
    die "docs/ must be flat; the GitHub wiki has no subdirectories"
fi

shopt -s nullglob
pages=("$DOCS"/*.md)
shopt -u nullglob
[[ ${#pages[@]} -gt 0 ]] || die "docs/ contains no .md files"
[[ -f "$DOCS/Home.md" ]] || warn "docs/Home.md is missing; the wiki will have no landing page"

# Locate the wiki

if [[ -z "$slug" ]]; then
    remote="$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)"
    # Bash regexes are POSIX ERE and have no lazy quantifiers, so trim the
    # suffix first rather than trying to make the group skip it.
    remote="${remote%/}"
    remote="${remote%.git}"
    if [[ "$remote" =~ github\.com[:/]+([^/]+/[^/]+)$ ]]; then
        slug="${BASH_REMATCH[1]}"
    else
        slug="$DEFAULT_SLUG"
        warn "no github origin remote; assuming $slug"
    fi
fi

WIKI_URL="git@github.com:${slug}.wiki.git"
WIKI_DIR="$(dirname "$ROOT")/$(basename "${slug#*/}").wiki"

info "docs/ → ${bold}${slug}${off} wiki  ${dim}($WIKI_DIR)${off}"

# Clone or update 

if [[ -d "$WIKI_DIR/.git" ]]; then
    info "Updating the wiki checkout"
    run git -C "$WIKI_DIR" fetch --quiet origin
    run git -C "$WIKI_DIR" reset --quiet --hard origin/HEAD
    run git -C "$WIKI_DIR" clean -qfd
else
    [[ -e "$WIKI_DIR" ]] && die "$WIKI_DIR exists but is not a git checkout"
    info "Cloning the wiki"
    if ! git clone --quiet "$WIKI_URL" "$WIKI_DIR"; then
        rm -rf "$WIKI_DIR"
        die "could not clone $WIKI_URL

A GitHub wiki repository does not exist until its first page is created. Open
  https://github.com/${slug}/wiki
create any page in the web UI, save it, then run this script again — it will
overwrite that page with docs/Home.md."
    fi
fi

# Copy

info "Copying pages"
find "$WIKI_DIR" -maxdepth 1 -name '*.md' -delete
for page in "${pages[@]}"; do
    sed -E 's/\]\(([A-Za-z0-9][A-Za-z0-9._-]*)\.md(#[^)]*)?\)/](\1\2)/g' \
        "$page" > "$WIKI_DIR/$(basename "$page")"
    printf '  %s\n' "$(basename "$page")"
done

# Commit and push 

git -C "$WIKI_DIR" add -A

if git -C "$WIKI_DIR" diff --cached --quiet; then
    info "${green}Already up to date${off}; nothing to push"
    exit 0
fi

git -C "$WIKI_DIR" diff --cached --stat

if $dry_run; then
    run git -C "$WIKI_DIR" reset --quiet
    info "${green}Dry run${off}: nothing committed or pushed"
    exit 0
fi

if [[ -z "$message" ]]; then
    sha="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    message="docs: sync from $sha"
fi

run git -C "$WIKI_DIR" commit --quiet -m "$message"
run git -C "$WIKI_DIR" push --quiet origin HEAD

info "${green}Pushed${off} → https://github.com/${slug}/wiki"
