# Portability validation

Recorded on 2026-10-07 for the portability changes. The local full-suite fixture
revision is `35764dc19513e5a542d4273d08516590578eea12`; later documentation edits do
not change the tested helper source or fixtures. The scripts, tests, requirements
and CI workflow at integration revision `b8efd2` were verified to match that
tested revision exactly.

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
| Hosted Windows and Linux CI | 3.11 and 3.14 | Configured; not executed |

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
No hosted run is claimed without a resulting CI execution.

Fixtures use disposable repositories, isolated Git configuration and simulated
Codex metadata; they do not use real Codex authentication, accounts or models.
Content and audit-integrity assertions run on both platforms. Executable-bit and
Unix-specific filename checks skip only where their capabilities do not apply;
symlink checks skip only a reported unavailable creation capability.

Independent review compared integration revision `b8efd2` with baseline `924db`.
The standards review found no documented standards breaches; its optional note
about pre-existing duplicated Git path collection remained outside this scope.
The specification review found no actionable code findings or scope creep.

Python 3.11 and the four hosted CI jobs remain unexecuted. Hosted validation and
publication of the Git history await an authorized push; these local results do
not establish a hosted CI pass or completion of the parent specification.
