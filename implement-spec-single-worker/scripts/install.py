#!/usr/bin/env python3
import argparse
import datetime
import os
from pathlib import Path
import shutil
import tomllib


def install(source, destination, codex_home):
    source = source.resolve()
    destination = destination.resolve()
    codex_home = codex_home.resolve()
    agent_root = codex_home / "agents"
    tdd = destination.parent / "tdd" / "SKILL.md"
    if not tdd.is_file():
        raise RuntimeError(f"Required TDD skill is missing: {tdd}")
    replacements = {
        "@SKILL_ROOT@": str(destination),
        "@AGENT_ROOT@": str(agent_root),
        "@TDD_SKILL@": str(tdd),
    }
    files = {}
    for path in source.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[destination / path.relative_to(source)] = path.read_bytes()
    templates = [source / "assets" / "implement-spec.config.toml"]
    templates.extend(sorted((source / "assets" / "agents").glob("*.toml")))
    for template in templates:
        content = template.read_text()
        for token, value in replacements.items():
            content = content.replace(token, value)
        tomllib.loads(content)
        target = codex_home / template.name if template.name.endswith(".config.toml") else agent_root / template.name
        files[target] = content.encode()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = codex_home / "backups" / f"implement-spec-{timestamp}"
    for target, content in files.items():
        if target.exists() and target.read_bytes() != content:
            saved = backup / target.relative_to(Path.home()) if target.is_relative_to(Path.home()) else backup / target.name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    for target, content in files.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
    print(f"Installed skill: {destination}")
    print(f"Installed launch preset: {codex_home / 'implement-spec.config.toml'}")
    print(f"Backups, if needed: {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--destination", type=Path, default=Path.home() / ".agents/skills/implement-spec-single-worker")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))))
    arguments = parser.parse_args()
    install(arguments.source, arguments.destination, arguments.codex_home)
