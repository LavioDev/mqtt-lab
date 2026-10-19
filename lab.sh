#!/usr/bin/env bash
# Docker-only launcher: the host needs nothing but Docker.
set -Eeuo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")"

HOST_PROJECT_DIR="$(pwd)"
# Git Bash on Windows: C:/x -> /c/x so the Docker daemon resolves bind mounts.
if [[ "$HOST_PROJECT_DIR" =~ ^([A-Za-z]):/(.*)$ ]]; then
  HOST_PROJECT_DIR="/${BASH_REMATCH[1],,}/${BASH_REMATCH[2]}"
fi
export HOST_PROJECT_DIR

C=(docker compose -f compose.tools.yaml)
case "${1:-}" in
  firmware)
    shift
    if [[ "${1:-}" == "flash" ]]; then
      "${C[@]}" --profile flash run --rm flash
    else
      mkdir -p firmware/build
      "${C[@]}" run --rm firmware
    fi ;;
  *) "${C[@]}" run --rm tools scripts/lab.py "$@" ;;
esac
