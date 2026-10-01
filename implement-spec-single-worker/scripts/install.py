#!/usr/bin/env python3
import argparse
import datetime
import os
from pathlib import Path
import shutil
import tomllib
import json
import subprocess

import configuration


def remove_project_setup(project, codex_home, confirmed_workflow_only=False):
    project = Path(project).resolve()
    codex_home = Path(codex_home).resolve()
    root = subprocess.check_output(
        ["git", "-C", str(project), "rev-parse", "--show-toplevel"], text=True
    ).strip()
    if Path(root).resolve() != project:
        raise RuntimeError("Project cleanup requires the repository root.")
    target = project / ".codex/config.toml"
    if target.is_symlink() or target.parent.is_symlink():
        raise RuntimeError("Project configuration must not be a symlink.")
    if not target.exists():
        return
    if not confirmed_workflow_only:
        raise RuntimeError(
            "Configuration values do not prove ownership. Inspect the original installation evidence "
            "and backups first. Confirm workflow-only ownership only if no prior user configuration "
            "was replaced; otherwise restore the confirmed original settings separately."
        )
    original = target.read_text()
    installed = tomllib.loads(original)
    expected = {
        "features": {"multi_agent": True, "multi_agent_v2": False},
        "agents": {
            "max_depth": 2,
            **{role: {"config_file": str(codex_home / "agents" / f"{role}.toml")}
               for role in configuration.DEPTHS},
        },
    }
    if installed.get("agents", {}).get("max_concurrent_threads_per_session") == 2:
        expected["agents"]["max_concurrent_threads_per_session"] = 2
    if installed != expected:
        raise RuntimeError(
            "Project configuration contains user settings or differs from the old workflow setup. "
            "Inspect its backup and remove only confirmed workflow additions; no file was changed."
        )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = codex_home / "backups" / f"implement-spec-project-removed-{timestamp}.toml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(original)
    target.unlink()
    print(f"Removed workflow-only project configuration: {target}. Backup: {backup}")
    print("Existing sessions may retain loaded settings. Start a new session to use your normal defaults.")


def install(source, destination, codex_home):
    source = source.resolve()
    destination = destination.resolve()
    codex_home = codex_home.resolve()
    settings = configuration.load(source / "settings.toml")
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
    for retired in ("scripts/smoke_test.py", "references/runtime-evidence.json"):
        files[destination / retired] = None
    templates = [source / "assets" / "implement-spec.config.toml"]
    templates.extend(sorted((source / "assets" / "agents").glob("*.toml")))
    for template in templates:
        content = template.read_text()
        role = settings["launcher"] if template.name.endswith(".config.toml") else settings["roles"][template.stem]
        content = content.replace('"@MODEL@"', json.dumps(role["model"]))
        content = content.replace('"@EFFORT@"', json.dumps(role["effort"]))
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
        if content is None:
            target.unlink(missing_ok=True)
            continue
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
    parser.add_argument("--remove-project-setup", type=Path,
                        help="Back up and remove an old workflow-only project configuration.")
    parser.add_argument("--confirm-workflow-only", action="store_true",
                        help="Confirm independent evidence that setup created the file without replacing user settings.")
    arguments = parser.parse_args()
    if arguments.confirm_workflow_only and not arguments.remove_project_setup:
        parser.error("--confirm-workflow-only requires --remove-project-setup")
    if arguments.remove_project_setup:
        remove_project_setup(arguments.remove_project_setup, arguments.codex_home, arguments.confirm_workflow_only)
    install(arguments.source, arguments.destination, arguments.codex_home)
