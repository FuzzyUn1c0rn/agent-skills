"""A real child process used instead of Codex by the subprocess fixture."""

import datetime
import json
import os
from pathlib import Path
import time


root = Path(os.environ["IMPLEMENT_SPEC_TEST_CHILD_ROOT"])
repo = os.environ["IMPLEMENT_SPEC_TEST_REPO"]
identifier = "dedicated-outer"
folder = Path(os.environ["CODEX_HOME"]) / "sessions" / "fixture"
folder.mkdir(parents=True, exist_ok=True)
metadata = {
    "type": "session_meta", "payload": {
        "id": identifier, "cwd": repo, "source": "cli",
        "timestamp": (datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
                      if os.environ.get("IMPLEMENT_SPEC_TEST_OLD_SESSION")
                      else datetime.datetime.now(datetime.timezone.utc)).isoformat(),
    },
}
(folder / f"rollout-{identifier}.jsonl").write_text(json.dumps(metadata) + "\n", encoding="utf-8")
(root / "child-ready.json").write_text(json.dumps({
    "pid": os.getpid(), "outer_session": identifier,
    "launch_id": os.environ.get("IMPLEMENT_SPEC_LAUNCH_ID"),
}), encoding="utf-8")
if os.environ.get("IMPLEMENT_SPEC_TEST_CHILD_EXIT"):
    raise SystemExit(int(os.environ["IMPLEMENT_SPEC_TEST_CHILD_EXIT"]))
deadline = time.monotonic() + 90
while not (root / "child-exit").exists():
    if time.monotonic() > deadline:
        raise SystemExit(90)
    (root / "child-heartbeat").write_text(str(time.monotonic()), encoding="utf-8")
    time.sleep(0.03)
(root / "child-exited").touch()
