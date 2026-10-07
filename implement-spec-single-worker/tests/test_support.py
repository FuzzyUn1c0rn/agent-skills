"""Temporary test environment; production helpers keep the user's Git behavior."""

import os
import tempfile
from unittest.mock import patch


def isolate_git(test):
    template = tempfile.TemporaryDirectory(prefix="implement-spec-git-template-")
    test.addCleanup(template.cleanup)
    inherited = {
        "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR",
        "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_EXTERNAL_DIFF",
    }
    environment = {
        name: value for name, value in os.environ.items()
        if name not in inherited and not name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
    }
    environment.update(
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_NOSYSTEM="1",
        GIT_ATTR_NOSYSTEM="1", GIT_CONFIG_COUNT="0", GIT_TEMPLATE_DIR=template.name,
        XDG_CONFIG_HOME=template.name,
    )
    isolated = patch.dict(os.environ, environment, clear=True)
    isolated.start()
    test.addCleanup(isolated.stop)
