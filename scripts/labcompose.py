"""Build `docker compose` argv that works from the tools container (paths resolve on the host daemon)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compose(*files: str, env_files: tuple[str, ...] = (".env",), project: str | None = None,
            profiles: tuple[str, ...] = ()) -> list[str]:
    argv = ["docker", "compose"]
    for env_file in env_files:
        argv += ["--env-file", str(ROOT / env_file)]
    for profile in profiles:
        argv += ["--profile", profile]
    for name in files or ("compose.yaml",):
        argv += ["-f", str(ROOT / name)]
    if project:
        argv += ["-p", project]
    return argv
