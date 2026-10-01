# Entry modes

The outer agent runs these helpers. Do not tell the user to memorize commands.
Resolve an absolute PRD path to its repository-relative path for guard commands.
The explicit `session=current|new` argument overrides `settings.toml`'s
`default_session`. Branch and resume choices apply to either mode.

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

When upgrading an interrupted entry from the probe-based version, ignore its
old `probe_prompt`. Once all previous workers are confirmed stopped, release
its live helper with `stop`, or use `recover` if that helper has exited. Then
start the new entry, using `resume` if a saved run exists. Preserve the saved
run and unfinished changes; do not execute the old diagnostic instructions.

1. Confirm exclusive use of the checkout and finish unrelated checkout work.
   For an existing saved run, confirm every old coordinator and leaf stopped.
   Do not start new workers while old workers might still be editing.
2. Start a persistent shell execution, retaining its tool session ID:

   ```sh
   python3 <skill-directory>/scripts/entry.py start path/to/PRD.md --session current
   ```

   Add `--branch name` or `--resume` as requested. The process prints
   `preflight` and remains running to hold the checkout lock. It does not
   launch Codex, switch branches or change the chosen model. Do not kill it,
   impose a short timeout or close its execution session during ticket work.
3. Run `entry.py admit SPEC`. It checks local configuration and checkout
   ownership, selects the branch and records this session as the owner.
   A resume requires the inactive-worker handover evidence below.
   It does not start agents, inspect test transcripts, require a compatibility
   receipt or compare the outer model with launcher defaults.
4. Perform preflight and continue the outer workflow in `SKILL.md`. Use
   `workflow.py` for state, ticket and commit operations. Keep the lock holder
   alive. Do not alter profiles or delegation features during a run. After compaction,
   `entry.py status SPEC` identifies this session's existing lock and admission;
   do not start a duplicate holder or create diagnostic agents.
   Register the fresh ticket coordinator with
   `entry.py coordinator SPEC --agent ID` after its ready response and before
   sending it the plan. Only this outer and that registered native child may
   change run state. Old owners and other sessions are rejected.
5. On completion, blocker or preflight failure, close every workflow agent.
   Save a JSON report outside the checkout containing
   `previous_workers_inactive: true` and concrete `evidence`. Call
   `entry.py stop SPEC --report /tmp/release.json`, then poll the retained shell
   execution until it exits successfully. Release the lock before yielding to
   the user; preserve the run record and unfinished files.

If the helper crashes, its OS lock disappears but its ownership record remains.
Neither entry mode may overwrite that record. Confirm that old workers have
stopped, then run `entry.py recover SPEC --report /tmp/recovery.json`. The report
must contain `previous_workers_inactive: true`, `previous_outer_session` matching
the saved entry and evidence of shutdown. Recovery only clears stale ownership,
not ticket state, changes or attempt counts. A live holder cannot be recovered.

### Resume into this outer session

Use `start --session current --resume` for an interrupted recorded run.
Do not use `resume` merely because a PRD contains already-closed tickets;
without a framework run record, initialize a fresh run that includes and skips
those completed dependencies.

For a resume, `admit --report /tmp/handover.json` requires:

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

## New session

Run the existing launcher with a terminal-capable shell execution:

```sh
python3 <skill-directory>/scripts/entry.py start path/to/PRD.md --session new
```

`workflow.py launch SPEC` remains a supported explicit alias for this mode.
It uses the configured launcher model and effort, locally checked preset and shared
checkout lock. `--resume` resumes the recorded outer rather than adopting the
run into the caller. If the current tool environment cannot host that terminal,
report the limitation instead of silently substituting current-session mode.

Inside the launched outer, `IMPLEMENT_SPEC_LAUNCH=1` identifies the launcher
context. Run `workflow.py doctor` and proceed to preflight, not `entry.py start`.
The guard also checks that the launcher lock is held. The launcher keeps it
until that Codex process exits. Do not run both entry modes in the same checkout.

Neither mode imposes a concurrent-agent limit or writes project startup settings.
Both rely on the coordinator to follow the sequential instructions. Current mode
uses the capabilities already loaded in the invoking session. New mode supplies
its role registrations, outer model and necessary nesting allowance to the
dedicated process only. Other sessions keep their own settings.
