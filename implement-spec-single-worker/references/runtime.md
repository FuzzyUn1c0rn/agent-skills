# Runtime installation

This workflow uses native named Codex agents for real work. It does not run
runtime probes, create test agents or require a compatibility receipt.
Current-session mode is the default: the invoking visible session remains
the outer agent. A separate launcher is available only through `session=new`.

## Install and configure

The agent runs the installer internally when installation or a settings change
is requested:

```sh
python3 scripts/install.py
```

Installation renders the four named profiles and a dedicated launch preset.
It backs up replaced files beneath `~/.codex/backups/` and removes the retired
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
run `install.py --remove-project-setup /absolute/repository/root --confirm-workflow-only`.
Cleanup checks the exact generated contents, backs up and removes the file.
Otherwise restore only confirmed workflow changes from the original backup,
preserving subsequent user edits. The old `--project` setup option is removed.
Existing sessions may retain loaded settings after cleanup; clearing context
alone does not establish a settings reload.

## State and real-work safeguards

Both modes share the checkout lock. Current-session entry holds it with a
persistent helper and requires inactive-worker evidence to recover stale
ownership after a crash. Only its outer and registered real coordinator may
change run state. Registration reads that coordinator's existing native session
metadata; it does not create a test agent.

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

```sh
python3 -m unittest discover -s tests -v
```

These are development tests for the helpers, not an automatic implementation
startup step.
