"""Run a real helper process with a Codex version fixture at its process boundary."""

import runpy
import os
import json
from pathlib import Path
import subprocess
import sys
import time


helper = sys.argv.pop(1)
original_run = subprocess.run
original_call = subprocess.call


def fixture_run(command, *args, **kwargs):
    pause = os.environ.get("IMPLEMENT_SPEC_TEST_PAUSE_GIT")
    if pause and command[0] == "git" and "status" in command:
        folder = Path(pause)
        (folder / "entered").touch()
        deadline = time.monotonic() + 60
        while not (folder / "resume").exists():
            if time.monotonic() > deadline:
                raise RuntimeError("Git fixture pause timed out")
            time.sleep(0.03)
    if command == [str(Path(sys.executable).resolve()), "--version"]:
        if os.environ.get("IMPLEMENT_SPEC_TEST_VERSION_CAPTURE"):
            Path(os.environ["IMPLEMENT_SPEC_TEST_VERSION_CAPTURE"]).write_text(json.dumps(command), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "codex-cli fixture\n", "")
    return original_run(command, *args, **kwargs)


def fixture_call(command, *args, **kwargs):
    child = os.environ.get("IMPLEMENT_SPEC_TEST_CHILD")
    if child and command[0] == str(Path(sys.executable).resolve()):
        if os.environ.get("IMPLEMENT_SPEC_TEST_SPAWN_FAILURE"):
            raise OSError("fixture spawn failure")
        return original_call([sys.executable, child, *command[1:]], *args, **kwargs)
    capture = os.environ.get("IMPLEMENT_SPEC_TEST_LAUNCH_CAPTURE")
    if capture and command[0] == str(Path(sys.executable).resolve()):
        child = (
            "import json, os, pathlib, sys; "
            "pathlib.Path(os.environ['IMPLEMENT_SPEC_TEST_LAUNCH_CAPTURE']).write_text(json.dumps({"
            "'arguments': sys.argv[1:], 'attached': os.environ.get('IMPLEMENT_SPEC_LAUNCH'), "
            "'executable': os.environ.get('IMPLEMENT_SPEC_CODEX')}), encoding='utf-8')"
        )
        return original_call([sys.executable, "-c", child, *command[1:]], *args, **kwargs)
    return original_call(command, *args, **kwargs)


subprocess.run = fixture_run
subprocess.call = fixture_call
sys.path.insert(0, str(Path(helper).parent))
sys.argv[0] = helper
runpy.run_path(helper, run_name="__main__")
