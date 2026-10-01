# Runtime installation and verification

This workflow targets the local Codex CLI and its native V1 agent tools. The
current chat's tool facade can differ from the standalone CLI. A facade without
an `agent_type` selector cannot establish that named profiles were selected.

Install the skill and render its four personal agent profiles and dedicated
launch preset:

```sh
python3 scripts/install.py
python3 ~/.agents/skills/implement-spec-single-worker/scripts/smoke_test.py
```

Installation backs up replaced files beneath `~/.codex/backups/`. It does not
change the base `~/.codex/config.toml` or the existing `/implement` and TDD skills.
The existing skill remains explicitly invoked.

The launch preset registers each role's `config_file` and pins the agreed
models and efforts. It enables native V1 delegation. The shared tree capacity
is two open threads, including the coordinator itself. Keep the coordinator
resident until ticket work stops; this leaves one worker slot.
Leaf profiles disable delegation. Native depth is two. The smoke test must
prove that these settings compose on the installed version.

Project configuration can override a selected preset. The launcher and native
probe therefore also pin the preset's model, effort, role paths and concurrency
settings with CLI overrides. The compatibility receipt covers those profile files.

An outer limit of one was tested and rejected: it also prevented the
coordinator's first worker. The limit is shared; a child profile cannot raise it.
The supported topology therefore retains the coordinator for the entire
ticket phase. Arbitrary direct root-worker orchestration is outside this mode.

Run the helper tests before installing changed guard code:

```sh
python3 -m unittest discover -s tests -v
```

The native smoke test uses a temporary Git repository. It selects each real
profile by name, exercises the outer/coordinator/worker nesting, attempts a
second worker while the coordinator remains open, then exercises two sequential
fresh implementers and fresh verifiers. It checks completed waits, slot closures,
and recorded runtime model, effort and role metadata. It preserves only the probe evidence needed to
explain the result. It does not implement application tickets.

`references/runtime-evidence.json` identifies the tested CLI version and profile
fingerprint. The launcher refuses a different version or changed profiles until
the smoke test is repeated. The process lock rejects another invocation of this
launcher in the same checkout. Neither mechanism controls a human or unrelated
software deliberately editing the checkout; exclusive checkout use is required.

For repairs, close the verifier, then spawn a fresh Sol/high implementer with the
current diff, prior TDD evidence and verifier findings. Native resume was tested
on Codex 0.159.3: a closed Sol/high implementer resumed with its parent's
Luna/medium settings, even with explicit sub-agent model defaults. Native V1
resume accepts no model override. Fresh repair agents are the user-approved
v1 choice; never silently fall back to resumed or generic agents.
For session recovery, the launcher resumes the recorded outer Codex session,
then reconciles the saved run and old agent lifecycle before fresh delegation.
Do not assume resumed sub-agents retain their configured models.

The read-only verifier and auditor still need temporary test output. Use the
repository's supported temporary-directory options. Required tests that need
unavailable filesystem permissions block verification; do not silently broaden
the profile or call those checks passed.

Official references consulted for configuration and hook limitations:

- `https://developers.openai.com/codex/multi-agent/`
- `https://developers.openai.com/codex/config-reference/`
- `https://developers.openai.com/codex/hooks/`

Hook files alone are not used as the concurrency guarantee. Unsupported hook
responses, hook failures and untrusted hooks can leave calls unblocked.
