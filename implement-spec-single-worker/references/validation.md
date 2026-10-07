# Portability validation

Recorded on 2026-10-07 for the portability changes. The local full-suite fixture
revision is `35764dc19513e5a542d4273d08516590578eea12`; later documentation edits do
not change the tested helper source or fixtures.

From the repository root, install requirements and run the same complete suite
used by [.github/workflows/helper-tests.yml](../../.github/workflows/helper-tests.yml):

```sh
python -m pip install -r "implement-spec-single-worker/requirements.txt"
python -m unittest discover -s "implement-spec-single-worker/tests" -v
```

| Environment | Python | Complete-suite result |
| --- | --- | --- |
| Native Windows | 3.14.8 | Final local run in progress |
| WSL, Ubuntu 26.04 | 3.14.4 | PASS: 126 tests, 49.538 seconds, zero skips |
| Local Python 3.11 | Unavailable | Not executed |
| Hosted Windows and Linux CI | 3.11 and 3.14 | Configured; not executed |

The WSL run used Portalocker 4.4.0 installed from the requirements manifest into
an external temporary dependency directory. That environment lacked pip and
ensurepip, so a Linux Python/pip wheel bootstrap installed the manifest and
`PYTHONPATH` selected the resulting directory. The suite command itself matched
CI. Native Windows results remain pending until the complete run finishes.

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
