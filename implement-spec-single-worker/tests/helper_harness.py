"""Run a real helper process with a Codex version fixture at its process boundary."""

import runpy
from pathlib import Path
import subprocess
import sys


helper = sys.argv.pop(1)
original_run = subprocess.run


def fixture_run(command, *args, **kwargs):
    if command == ["codex", "--version"]:
        return subprocess.CompletedProcess(command, 0, "codex-cli fixture\n", "")
    return original_run(command, *args, **kwargs)


subprocess.run = fixture_run
sys.path.insert(0, str(Path(helper).parent))
sys.argv[0] = helper
runpy.run_path(helper, run_name="__main__")
