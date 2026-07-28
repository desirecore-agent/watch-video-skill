#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_dir="$(CDPATH= cd -- "$script_dir/.." && pwd)"
source_dir="$repo_dir/skills/watch"
target="codex"
destination=""
force="false"

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Options:
  --target codex|claude      Select a standard runtime (default: codex)
  --destination PATH         Install to an exact custom skill path
  --force                    Back up an existing installation before replacing it
  -h, --help                 Show this help
EOF
}

require_value() {
  if [ "$#" -lt 2 ] || [ -z "$2" ]; then
    printf 'Missing value for %s\n' "$1" >&2
    exit 2
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      require_value "$@"
      target="$2"
      shift
      ;;
    --destination)
      require_value "$@"
      destination="$2"
      shift
      ;;
    --force)
      force="true"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ ! -d "$source_dir" ]; then
  printf 'Skill source not found: %s\n' "$source_dir" >&2
  exit 1
fi

if [ -z "$destination" ]; then
  case "$target" in
    codex)
      if [ -n "${CODEX_HOME:-}" ]; then
        destination="${CODEX_HOME}/skills/watch"
      else
        destination="${HOME}/.codex/skills/watch"
      fi
      ;;
    claude)
      if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
        destination="${CLAUDE_CONFIG_DIR}/skills/watch"
      else
        destination="${HOME}/.claude/skills/watch"
      fi
      ;;
    *)
      printf 'Unsupported target: %s\n' "$target" >&2
      exit 2
      ;;
  esac
fi

destination_parent="$(dirname -- "$destination")"
mkdir -p "$destination_parent"

if [ -e "$destination" ]; then
  if [ "$force" != "true" ]; then
    printf 'Destination already exists: %s\n' "$destination" >&2
    printf 'Re-run with --force to create a backup and replace it.\n' >&2
    exit 1
  fi
  backup="${destination}.backup.$(date -u +%Y%m%dT%H%M%SZ)"
  mv "$destination" "$backup"
  printf 'Backed up existing skill to: %s\n' "$backup"
fi

cp -R "$source_dir" "$destination"
printf 'Installed watch skill to: %s\n' "$destination"
printf 'Start a new agent session if the runtime caches skill metadata.\n'
