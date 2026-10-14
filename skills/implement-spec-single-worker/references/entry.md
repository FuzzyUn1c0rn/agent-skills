# Entry modes

The outer agent runs these helpers. Do not tell the user to memorize commands.
Read [sources.md](sources.md) and resolve the canonical specification reference
before entry. Pass that same reference to every helper; ticket and specification
references identify actual artifacts in the configured tracker.
The explicit `session=current|new` argument overrides `settings.toml`'s
`default_session`. Branch and resume choices apply to either mode.

Before starting either mode, set the selected interpreter, skill path and external
report directory using [runtime.md](runtime.md#helper-shell-paths-and-temporary-reports).
Replace `entry.py` or `workflow.py` in inline commands below with that interpreter
and the corresponding quoted script path. Replace quoted `"SPEC"` with the
canonical specification reference and `"REPORT"` with the actual report path;
`<report-directory>` is the saved absolute directory from that recipe.

## Current session

The invoking session stays the outer agent, using the user's selected model and
effort. Use the session's available capabilities without changing startup
configuration. No project config file is required. The actual session must still
expose native `agent_type` tools, the configured roles and coordinator-to-worker
nesting. Use the available native tools for actual work; do not test them by
creating disposable agents. If a required tool is absent or a real spawn fails,
report the missing capability. Wait for the user's choice before changing modes.
Do not create project configuration, change personal defaults, copy prompts into
generic agents or claim that clearing context enables missing tools.

Finish or explicitly recover an interrupted entry with its installed helper
before upgrading. Legacy ownership without a launch ID is preserved and rejected
by the new helper; it is not migrated automatically. Retain the saved run and
unfinished changes.

1. Confirm exclusive use of the checkout and finish unrelated checkout work.
   For an existing saved run, confirm every old coordinator and leaf stopped.
   Reuse its canonical references, approved captures and tracker recovery journal;
   recover pending source operations before new implementation work.
   Do not start new workers while old workers might still be editing.
2. Start a persistent shell execution, retaining its tool session ID:

   ```powershell
   & $Python "$Skill/scripts/entry.py" start "$Spec" --session current
   ```

   ```sh
   "$PYTHON" "$SKILL/scripts/entry.py" start "$SPEC" --session current
   ```

   Add `--branch name` or `--resume` as requested. The process prints
   `preflight` with a unique `launch_id` and remains running to hold the checkout lock. It does not
   launch Codex, switch branches or change the chosen model. Do not kill it,
   impose a short timeout or close its execution session during ticket work.
3. Run `entry.py admit "SPEC"`. It checks local configuration and checkout
   ownership, selects the branch and records this session as the owner.
   A resume requires the inactive-worker handover evidence below.
   It does not start agents, inspect test transcripts, require a compatibility
   receipt or compare the outer model with launcher defaults.
4. Perform preflight and continue the outer workflow in `SKILL.md`. Use
   `workflow.py` for state, ticket and commit operations. Keep the lock holder
   alive. Do not alter profiles or delegation features during a run. After compaction,
   `entry.py status "SPEC"` identifies this session's existing lock and admission;
   do not start a duplicate holder or create diagnostic agents.
   Register the fresh ticket coordinator with
   `entry.py coordinator "SPEC" --agent ID` after its ready response and before
   sending it the plan. Only this outer and that registered native child may
   change run state. Old owners and other sessions are rejected.
   Before each whole-spec audit, close the coordinator and all its children, then
   call `entry.py release-coordinator "SPEC" --report "<report-directory>/coordinator-closed.json"`.
   Include the recorded `coordinator` ID, `previous_workers_inactive: true` and
   concrete closure `evidence`. This retires its registration while retaining the
   checkout lock. After audit repair planning, register a fresh coordinator with
   the same ready-response procedure. Closed coordinator IDs cannot be reused.
5. On completion, blocker or preflight failure, close every workflow agent.
   Save a JSON report outside the checkout containing
   the entry's matching `launch_id`, `previous_workers_inactive: true` and concrete `evidence`. Call
   `entry.py stop "SPEC" --report "<report-directory>/release.json"`, then poll the retained shell
   execution until it exits successfully. Release the lock before yielding to
   the user; preserve the run record and unfinished files.

If the helper crashes, its OS lock disappears but its ownership record remains.
Neither entry mode may overwrite that record. Confirm that old workers have
stopped, then run `entry.py recover "SPEC" --report "<report-directory>/recovery.json"`. The report
must contain the saved `launch_id`, `previous_workers_inactive: true`,
`previous_outer_session` matching the saved entry and evidence of shutdown.
Use `previous_outer_session: null` if no dedicated outer was admitted.
Recovery only clears stale ownership,
not ticket state, changes or attempt counts. A live holder cannot be recovered.

### Resume into this outer session

Use `start --session current --resume` for an interrupted recorded run.
Do not use `resume` merely because a specification contains already-closed tickets;
without a framework run record, initialize a fresh run that includes and skips
those completed dependencies.

For a resume, `entry.py admit "SPEC" --report "<report-directory>/handover.json"` requires:

```json
{
  "previous_outer_session": "the outer_session from workflow.py status",
  "previous_workers_inactive": true,
  "evidence": "How the old coordinator and every leaf were confirmed stopped"
}
```

Admission records the handover to this session without accepting changed code,
refreshing checkpoints, resetting budgets or resolving blockers. Reconcile the
saved state using [commands.md](commands.md) before fresh delegation. An
unfinished implementation still consumes its original attempt.

A resume also supports a saved failed-audit stop. It retains audits, ticket
history and allowance usage. To grant new rounds after exhaustion, the outer
records an explicit user instruction with `continue-audit` following
[audit-repairs.md](audit-repairs.md). Admission itself never grants that allowance.

## New session

Run the existing launcher with a terminal-capable shell execution:

```powershell
& $Python "$Skill/scripts/entry.py" start "$Spec" --session new
```

```sh
"$PYTHON" "$SKILL/scripts/entry.py" start "$SPEC" --session new
```

`workflow.py launch "SPEC"` remains a supported explicit alias for this mode.
It uses the configured launcher model and effort, locally checked preset and shared
checkout lock. `--resume` resumes the recorded outer rather than adopting the
run into the caller. If the current tool environment cannot host that terminal,
report the limitation instead of silently substituting current-session mode.

The launcher persists shared checkout ownership before spawning Codex and keeps
the OS lock itself while waiting. It passes `IMPLEMENT_SPEC_LAUNCH_ID` and the
retained executable path to the child. It does not inherit lock descriptors.

Inside the launched outer, the launch ID identifies context. Run
`entry.py admit "SPEC"` before workflow mutations. Admission validates the matching
launch, native outer-session metadata, checkout, branch, runtime and settings,
then binds the actual outer identity. A fresh launch starts with a null outer and
authorizes no mutations. A dedicated resume retains the saved outer identity and
requires inactive-worker evidence as above. An inherited marker alone never
authorizes a leaf agent or unrelated caller.

Follow the same coordinator ready-response, registration, retirement and fresh
replacement procedure as current mode. Only the admitted outer and its registered
native coordinator may mutate guarded state. Release is reserved for the outer.

Before exiting, close every workflow worker and save a UTF-8 JSON report in an
OS temporary directory outside the checkout:

```json
{
  "launch_id": "the launch_id from this entry",
  "previous_workers_inactive": true,
  "evidence": "How the coordinator and every leaf were confirmed stopped"
}
```

Call `entry.py stop "SPEC" --report "REPORT"` while Codex is still running. It records
release immediately and rejects subsequent workflow mutations; it does not wait
for child exit. Then end the dedicated Codex process. The launcher clears
ownership only after normal Codex exit and matching shutdown evidence, while
still holding the checkout lock. An exit status alone never clears ownership.

Spawn failure, failed admission, child failure, interruption, launcher death or
exit without release leaves ownership for explicit recovery. Both entry modes
reject it, including when a child survives launcher death. After confirming all
old agents and the old Codex process stopped, recover with the matching launch ID
and the saved outer identity (or null). Recovery preserves unfinished work,
history and retry budgets, and rejects a live lock holder. Do not start both entry
modes in the same checkout.

Neither mode imposes a concurrent-agent limit or writes project startup settings.
Both rely on the coordinator to follow the sequential instructions. Current mode
uses the capabilities already loaded in the invoking session. New mode supplies
its role registrations, outer model and necessary nesting allowance to the
dedicated process only. Other sessions keep their own settings.
