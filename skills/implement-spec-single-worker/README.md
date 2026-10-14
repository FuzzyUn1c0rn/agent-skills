# implement-spec-single-worker

A Codex skill for implementing an approved specification one ticket at a time.
It uses a coordinator, a TDD implementer, an independent verifier, and a final
specification auditor. AFK tickets are tickets approved for autonomous execution.
The workflow creates local commits and updates the configured issue tracker;
it never pushes commits.

## Before you install

You need:

- Codex with native named agent roles and coordinator-to-worker nesting support.
  Copying the skill alone does not enable those capabilities in an existing session.
- Python 3.11 or later, with pip, and Git.
- A complete `tdd` skill installed at `~/.agents/skills/tdd/SKILL.md`, including
  its supporting references. This repository does not bundle that dependency.
  If you already have a TDD skill elsewhere, copy its whole folder into
  `~/.agents/skills/tdd` before running the installer.
- Access to the models configured in [settings.toml](settings.toml).

`~` means your home folder: `%USERPROFILE%` on Windows and `$HOME` in WSL.
The instructions below install the skill for your user account, across repositories.
Codex discovers user skills in this location; see the
[official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Install

Clone this repository, install the Python dependency, and run the supplied
installer. If you already cloned it, start from that checkout and skip the clone.
Use the same Python interpreter for installation and subsequent helper commands.

### Windows PowerShell

```powershell
git clone https://github.com/FuzzyUn1c0rn/agent-skills.git
Set-Location agent-skills
py -3.11 -m pip install -r "implement-spec-single-worker/requirements.txt"
py -3.11 "implement-spec-single-worker/scripts/install.py"
```

### WSL

Use a Python 3.11+ interpreter in your chosen environment. If your system Python
requires a virtual environment, activate one before these commands.

```sh
git clone https://github.com/FuzzyUn1c0rn/agent-skills.git
cd agent-skills
python3 -m pip install -r "implement-spec-single-worker/requirements.txt"
python3 "implement-spec-single-worker/scripts/install.py"
```

Install separately in Windows and WSL: generated files contain absolute paths.
Keep unfinished runs in the environment where they started.

The installer writes these files:

| Location | Purpose |
| --- | --- |
| `~/.agents/skills/implement-spec-single-worker/` | The skill and its helpers |
| `~/.codex/agents/implementation_coordinator.toml` | Coordinator profile |
| `~/.codex/agents/ticket_implementer.toml` | Implementer profile |
| `~/.codex/agents/ticket_verifier.toml` | Verifier profile |
| `~/.codex/agents/spec_auditor.toml` | Final auditor profile |
| `~/.codex/implement-spec.config.toml` | Dedicated-session launch preset |

Changed existing files are backed up under `~/.codex/backups/implement-spec-<timestamp>/`.
The installer leaves personal and project `config.toml` files unchanged.
It also leaves your TDD skill unchanged.

If you set `CODEX_HOME`, the profiles, preset, and backups go there instead of
`~/.codex`. The installer also accepts `--destination` and `--codex-home`; a custom
skill destination requires `tdd/SKILL.md` in its sibling `tdd` folder. Use the same
Codex home when running the workflow, and record custom paths for removal later.

Restart Codex after installation so you start with fresh session settings. Confirm
the skill appears in the skill selector. You can also check the local installation:

```powershell
py -3.11 "$env:USERPROFILE/.agents/skills/implement-spec-single-worker/scripts/workflow.py" doctor
```

```sh
python3 "$HOME/.agents/skills/implement-spec-single-worker/scripts/workflow.py" doctor
```

`doctor` checks generated configuration and the Codex executable without starting
agents or making model calls. A passing check does not prove that your session
supports the required agent roles.

## Use the skill

Open the repository you want to implement in Codex. It needs an approved
specification, its AFK tickets, agreed testing boundaries, and issue-tracker
instructions in `docs/agents/issue-tracker.md`. Ensure Git is ready to make local
commits and keep the checkout exclusive while the workflow runs.

Send a prompt in Codex, replacing `<spec-reference>` with the actual specification
or Wayfinder-map reference from that repository's tracker:

```text
$implement-spec-single-worker <spec-reference>
```

The default uses your current session and its selected model and effort.
To request a separate outer session and a branch explicitly:

```text
$implement-spec-single-worker <spec-reference> session=new branch=feature/my-spec
```

To continue an interrupted recorded run after confirming its old workers stopped:

```text
$implement-spec-single-worker <spec-reference> resume
```

Codex handles the internal Python commands. Live tests, migrations, and
external-service writes require explicit run-level authorization. Missing
decisions, failed required checks, or exhausted repair attempts can stop the run.
Sequential work is enforced by the workflow's instructions; keep unrelated agents
and editors from changing the checkout during execution.

## Update or change settings

Finish any active run, or recover interrupted ownership with the installed helper
after confirming all old workers stopped, before replacing the installation.
Keep unfinished files and recovery evidence. See
[entry and recovery](references/entry.md) for the recovery procedure.

To update, pull changes in your source checkout and repeat the dependency and
installer commands above. To change models, effort, or the default session mode,
edit the source [settings.toml](settings.toml), then rerun the installer. The
launcher settings apply to `session=new`; your current outer session keeps the
model and effort you selected. Preserve your settings edits when updating.

## Uninstall

1. Finish or stop the workflow through Codex and confirm that its coordinator,
   workers, and lock-holding helper have stopped. Preserve any unfinished changes
   and run evidence before removing the helpers.
2. In your file manager, remove the installed
   `~/.agents/skills/implement-spec-single-worker/` folder.
3. Remove the five generated TOML files listed in the installation table above:
   the four individual profiles and `implement-spec.config.toml`. If installation
   replaced files you previously owned, restore their originals from the matching
   installation backup instead. Preserve any later edits you still need.
4. Restart Codex and confirm the skill is absent from the skill selector. If it
   still appears, check for another installed copy in the repository's
   `.agents/skills` folder or another user skill directory.

Use your recorded custom paths if you installed outside the defaults. Remove
only the listed skill folder and individual generated files; keep the shared
`.agents/skills`, `.codex/agents`, and `.codex` directories.

You can keep the TDD skill, Python dependency, source checkout, and installation
backups for other use. Uninstalling leaves implementation commits, tracker
updates, `.implement-spec/` evidence, and Git's `implement-spec/` recovery state
in place; removing the skill does not undo completed work.

There is no uninstall command. The installer's `--remove-project-setup` option
cleans up an older project configuration and then installs the skill again;
use the [legacy cleanup instructions](references/runtime.md#configuration-scope)
only if you used that older setup.

## Troubleshooting

- **Required TDD skill is missing:** place the complete TDD folder beside the
  destination skill folder, then rerun the installer.
- **Portalocker is missing:** install `requirements.txt` with the Python
  interpreter that runs the helpers.
- **Codex executable is a wrapper:** set `IMPLEMENT_SPEC_CODEX` to the absolute
  path of the native Codex executable, such as `codex.exe`. npm `.cmd` shims,
  shell scripts, and shell functions are unsupported.
- **Named agent roles or nesting are unavailable:** the current session cannot
  run this workflow. Codex should report the missing capability; choose
  `session=new` explicitly if you want to try the dedicated launcher.

See [runtime details](references/runtime.md) for interpreter, executable,
configuration, and environment guidance, and [SKILL.md](SKILL.md) for the full
execution contract.
