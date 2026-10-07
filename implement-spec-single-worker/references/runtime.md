# Runtime installation

This workflow uses native named Codex agents for real work. It does not run
runtime probes, create test agents or require a compatibility receipt.
Current-session mode is the default: the invoking visible session remains
the outer agent. A separate launcher is available only through `session=new`.

## Install and configure

Use Python 3.11 or later in each environment. The helpers use the standard-library
TOML parser and Portalocker for exclusive checkout locks. The dependency range in
`requirements.txt` starts at the verified Portalocker 4.4.0 release and excludes
version 5. Exclusive locks need no optional dependency extras.

Select an interpreter and install the requirements into that same interpreter
before running the installer. From the skill directory, for example:

```powershell
py -3.11 -m pip install -r "requirements.txt"
py -3.11 "scripts/install.py"
```

```sh
python3 -m pip install -r "requirements.txt"
python3 "scripts/install.py"
```

An existing virtual environment is also supported: use its Python executable for
both commands. Missing prerequisites report the selected interpreter and a
command to repair it. Helper startup and installation never install packages or
create an environment automatically.

Install separately in native Windows and WSL. Generated profiles and launch
presets contain absolute paths for their environment; keep each environment's
skill destination and Codex home local to that environment. Keep unfinished runs
in their originating environment. Before upgrading, finish the run or explicitly
recover its stale ownership with the currently installed helper after confirming
all old workers stopped. Retain unfinished files, saved state and evidence.
The new helper preserves and rejects legacy ownership rather than migrating it;
there is no automatic state or profile migration between environments.

The agent runs the installer internally when installation or a settings change
is requested:

```sh
python3 "scripts/install.py"
```

Installation renders the four named profiles and a dedicated launch preset.
It backs up replaced files beneath the selected Codex home's `backups/` directory
(`~/.codex/backups/` by default) and removes the retired
probe script and receipt. It does not modify personal or project startup
configuration, the existing `/implement` skill or the TDD skill.

Edit only `settings.toml` to change a role's model or effort. `[launcher]`
controls the outer model only in new-session mode. `[roles.<name>]` controls
the four sub-agent profiles. The current outer's model and effort remain the
user's choice. Run the installer after changing settings to regenerate profiles.
Make these changes between runs, not while workers are active.

`workflow.py doctor` checks local installed models against `settings.toml`
and reports the CLI version. It does not start agents or make model calls.
Passing it is a local configuration check, not a guarantee of agent behavior.

## Codex executable

Helpers select the native `codex` executable from PATH. To select another
installation, set `IMPLEMENT_SPEC_CODEX` to one executable path, for example:

```powershell
$env:IMPLEMENT_SPEC_CODEX = 'C:\tools\codex.exe'
```

```sh
export IMPLEMENT_SPEC_CODEX='/home/user/native tools/codex'
```

Use the actual native executable, including a symlink to it. The value is a
path without arguments or surrounding shell quotes. Script wrappers such as npm
`.cmd` shims, shell scripts and PowerShell functions are unsupported. If PATH
selects a wrapper, the helper reports that selection and asks for the explicit
native path; it does not search past the wrapper for another installation.
No personal shell configuration change is required.

Each entry or dedicated launch resolves once and uses the same absolute path for
version checks and execution. Current-session ownership records that path, and
admission and guarded operations retain it even if PATH or the override changes.
`workflow.py doctor` reports its selected path and version. Finish or recover a
run before changing its executable; upgrading the executable at its recorded
path still invalidates admission if the version changes.

## Helper shell paths and temporary reports

From the repository root, use the same selected Python interpreter for every
helper. Resolve it to an absolute executable path; replace `python` or `python3`
below with that interpreter if needed. Set the skill path to its actual installed
destination and the specification path relative to the checkout. Quote every
executable, script, specification, ticket and report path.

Create an OS-derived report directory outside the checkout before saving plans
or handoff JSON. These recipes reject a temporary root inside the checkout before
creating files. If rejected, select an external OS temporary location and retry.

PowerShell:

```powershell
$Python = (python -c "import sys; print(sys.executable)")
$Skill = "$env:USERPROFILE/.agents/skills/implement-spec-single-worker"
$Spec = 'path with spaces/PRD.md'
$Reports = & $Python -c "from pathlib import Path; import tempfile; root=Path.cwd().resolve(); temp=Path(tempfile.gettempdir()).resolve(); assert not temp.is_relative_to(root), 'Temporary reports must be outside the checkout'; print(tempfile.mkdtemp(prefix='implement-spec-', dir=temp))"
```

POSIX shell (WSL):

```sh
PYTHON="$(python3 -c 'import sys; print(sys.executable)')"
SKILL="$HOME/.agents/skills/implement-spec-single-worker"
SPEC='path with spaces/PRD.md'
REPORTS="$("$PYTHON" -c 'from pathlib import Path; import tempfile; root=Path.cwd().resolve(); temp=Path(tempfile.gettempdir()).resolve(); assert not temp.is_relative_to(root), "Temporary reports must be outside the checkout"; print(tempfile.mkdtemp(prefix="implement-spec-", dir=temp))')"
```

Save plans and reports as UTF-8 JSON. Complete entry admission before workflow
mutations. Other command references use `<report-directory>` for this
saved absolute directory, and `SPEC`, `TICKET` or `REPORT` as replaceable arguments.
Prefix helper arguments with the selected interpreter and quoted script path.
Retain report files as recovery evidence until the run has been reconciled.

## Native agent tools

The invoking session must have tools that support the configured named roles
and coordinator-to-worker nesting. Use those tools for actual work. If a
required tool is absent or a real spawn fails, report the actual error and
stop. Do not copy role prompts into generic agents, create diagnostic threads
or silently switch to a separate outer session.

Spawn named roles without full-history forking. The tested runtime rejects
selecting a different named role together with a full-history fork.

## Configuration scope

Keep existing defaults whenever adequate. This skill never installs project-wide
feature flags, depth limits, agent-count limits or role registrations.
Current-session entry does not require a project config file or alter startup
settings. The dedicated launcher supplies its configured outer model, role
paths and nesting allowance through arguments to that process only.

The coordinator inherits delegation settings without adding a depth ceiling.
Leaf profiles retain their task-specific no-delegation and sandbox settings.
Neither entry mode installs a concurrent-agent cap. Sequential execution is
the coordinator's responsibility, not a hard runtime guarantee.

To undo an older project installation, first inspect its original installation
evidence and backups. Matching generated values does not prove ownership:
an old setup may have overwritten a user's depth or retained their cap.
Only when setup created the file without replacing user settings may the agent
run `install.py --remove-project-setup "/absolute/repository/root" --confirm-workflow-only`.
Cleanup checks the exact generated contents, backs up and removes the file.
Otherwise restore only confirmed workflow changes from the original backup,
preserving subsequent user edits. The old `--project` setup option is removed.
Existing sessions may retain loaded settings after cleanup; clearing context
alone does not establish a settings reload.

## State and real-work safeguards

Both modes share the checkout lock and launch-specific ownership. Current-session
entry holds it with a persistent helper; the dedicated launcher retains it while
waiting for Codex. Dedicated admission binds the native outer before mutations.
Both modes require inactive-worker evidence to recover stale ownership after a
crash. Only the admitted outer and registered real coordinator may change run
state. Registration reads that coordinator's existing native session
metadata; it does not create a test agent. Dedicated release needs matching
worker-shutdown evidence plus normal Codex exit; release immediately stops state
mutations. Read [entry.md](entry.md) for admission, release and recovery.

The guard retains dependency checks, retry budgets, saved handovers, independent
ticket verification, snapshot checks and commit recovery. None requires
simulated agents. The lock excludes another cooperating workflow, not unrelated
agents or editors. Keep the checkout exclusive.

For repairs, close the verifier and spawn a fresh configured implementer with
the current diff, prior TDD evidence and verifier findings. Native resume was
observed on Codex 0.159.3 to change a closed implementer's model and effort to
its parent's settings. Fresh repair agents remain the agreed behavior.

Resume reconciles the saved run and confirms old workers stopped before real
delegation. Changing the outer owner does not reset attempts or accept
unfinished changes automatically. Read [entry.md](entry.md) for handover.

Verifiers and auditors may need disposable test output. Use the repository's
supported temporary-directory options. Unavailable required checks block
verification; do not silently broaden permissions or treat them as passing.

## Maintainer tests

The helper tests use temporary Git repositories and simulated session metadata.
They do not launch Codex agents or make model calls:

From the repository root, use the selected interpreter for the same command
locally and in CI:

```sh
python -m pip install -r "implement-spec-single-worker/requirements.txt"
python -m unittest discover -s "implement-spec-single-worker/tests" -v
```

The [CI workflow](../../.github/workflows/helper-tests.yml) runs the complete
suite on Windows and Linux with Python 3.11 and 3.14. Test fixtures isolate
personal Git configuration, attributes, hooks, templates and inherited Codex
ownership; subprocess fixtures use Python and temporary installed profiles.
Executable-bit checks skip only where that filesystem cannot represent them.
Unavailable symlink creation is reported as a capability skip; content and
integrity checks still run. See [validation.md](validation.md) for recorded local
results and unexecuted matrix entries.

These are development tests for the helpers, not an automatic implementation
startup step.

## Portability scope

Support covers native Windows and WSL with environment-local installations.
Simultaneous Windows/WSL operation against one checkout and cross-OS migration
of unfinished state are unsupported. Native executable resolution excludes
shell functions and script wrappers. Package installation, environment creation,
authentication and personal shell configuration remain user-managed.

Locks coordinate cooperating local workflows. Network-filesystem guarantees,
distributed locking and macOS certification are outside scope. Recovery requires
confirmed inactive workers; the helpers provide no process-tree supervision or
automatic process killing. Roles, current-session model selection, sequential
execution and retry allowances retain their existing contracts.
