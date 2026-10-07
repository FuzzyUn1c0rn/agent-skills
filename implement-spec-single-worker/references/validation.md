# Portability validation

Recorded on 2026-10-07 for the portability changes. The passing hosted matrix
tested integration revision `0d8e8b41eb51ce481638a52e43034cafab52fd3c` in
[run 37621957481](https://github.com/FuzzyUn1c0rn/agent-skills/actions/runs/37621957481).
The original local full-suite revision was
`35764dc19513e5a542d4273d08516590578eea12`. Production scripts, requirements and
the CI workflow remain identical to that revision; the later fixture-only
correction and its additional validation are recorded below. This evidence
update changes documentation only.

From the repository root, install requirements and run the same complete suite
used by [.github/workflows/helper-tests.yml](../../.github/workflows/helper-tests.yml):

```sh
python -m pip install -r "implement-spec-single-worker/requirements.txt"
python -m unittest discover -s "implement-spec-single-worker/tests" -v
```

| Environment | Python | Complete-suite result |
| --- | --- | --- |
| Native Windows | 3.14.8 | PASS: 126 tests, 1165.001 seconds, three expected skips |
| WSL, Ubuntu 26.04 | 3.14.4 | PASS: 126 tests, 49.538 seconds, zero skips |
| Local Python 3.11 | Unavailable | Not executed |
| Hosted Windows | 3.11 | PASS: 126 tests, 353.169 seconds, three expected skips |
| Hosted Windows | 3.14 | PASS: 126 tests, 531.338 seconds, three expected skips |
| Hosted Linux | 3.11 | PASS: 126 tests, 39.316 seconds, zero skips |
| Hosted Linux | 3.14 | PASS: 126 tests, 47.652 seconds, zero skips |

The WSL run used Portalocker 4.4.0 installed from the requirements manifest into
an external temporary dependency directory. That environment lacked pip and
ensurepip, so a Linux Python/pip wheel bootstrap installed the manifest and
`PYTHONPATH` selected the resulting directory. The suite command itself matched
CI. Native Windows also used Portalocker 4.4.0 and the same suite command. Its
three skips covered Unix tabs/newlines/quotes in filenames, non-executable native
file permission rejection where chmod cannot represent it, and snapshot changes
from executable bits where the filesystem cannot represent them. Content and
integrity coverage remained active.

Earlier full runs exposed an obsolete initialization fixture that accepted
launch markers without dedicated admission. The fixture revision above checks
rejection through the public workflow interface. The earlier runs are not
passing evidence. Focused native checks passed after the correction.

The CI matrix uses the complete suite in all four jobs. Its `v7` action versions
were checked against the official [checkout](https://github.com/actions/checkout)
and [setup-python](https://github.com/actions/setup-python) documentation.
All four jobs in the linked successful run installed Portalocker 4.4.0 and ran
the complete suite. The Windows skips match the three capabilities described
above; all Linux tests ran without skips. Python 3.11 was tested in hosted CI,
although it remains unavailable in the local installations.

Fixtures use disposable repositories, isolated Git configuration and simulated
Codex metadata; they do not use real Codex authentication, accounts or models.
Content and audit-integrity assertions run on both platforms. Executable-bit and
Unix-specific filename checks skip only where their capabilities do not apply;
symlink checks skip only a reported unavailable creation capability.

Independent review compared integration revision `b8efd2` with baseline `924db`.
The standards review found no documented standards breaches; its optional note
about pre-existing duplicated Git path collection remained outside this scope.
The specification review found no actionable code findings or scope creep.

The first hosted run,
[37620192316](https://github.com/FuzzyUn1c0rn/agent-skills/actions/runs/37620192316),
passed both Linux jobs but exposed two Windows subtest errors in the legacy
configuration cleanup fixture. It serialized an unresolved temporary home path,
while the historical installer and cleanup guard use a resolved home. A real
Windows short-path alias reproduced the original errors; the corrected fixture
passed under the same alias. Commit `77419c3` resolves the fixture home before
rendering profiles and adds portable path-alias cases. Production cleanup guards
and all backup, idempotence and refusal assertions remain unchanged.

After that correction, all nine configuration tests passed locally on native
Windows and WSL. The full WSL suite passed again: 126 tests in 120.818 seconds,
zero skips. Independent standards and specification delta reviews found no
blockers. The subsequent hosted matrix passed on both supported Python versions
and both operating systems, as recorded above. The user authorized the push
before hosted validation. The parent issue remains unmodified as required by
ticket #7.
