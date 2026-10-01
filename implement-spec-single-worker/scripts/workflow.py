#!/usr/bin/env python3
import subprocess
import re
import hashlib
import os
import fcntl
import json
import tempfile
import argparse
import sys
import tomllib
from contextlib import contextmanager
from pathlib import Path


class WorkflowError(RuntimeError):
    pass


@contextmanager
def exclusive(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WorkflowError("Another workflow operation owns this checkout.") from error
        yield handle.fileno()


def git(repo, *arguments):
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise WorkflowError(result.stderr.strip())
    return result.stdout.strip()


def choose_branch(repo, spec, requested=None):
    current = git(repo, "branch", "--show-current")
    if not current:
        raise WorkflowError("Detached HEAD: select a branch before starting.")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise WorkflowError("Fresh runs require a clean checkout; resume unfinished work.")
    if requested:
        git(repo, "check-ref-format", "--branch", requested)
        if requested.startswith("-") or requested == "HEAD":
            raise WorkflowError("Invalid branch name.")
        existing = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        if requested in existing.splitlines():
            git(repo, "switch", "--", requested)
        else:
            git(repo, "switch", "-c", requested)
        return requested
    if current != "main":
        return current
    slug = re.sub(r"[^a-z0-9-]+", "-", Path(spec).stem.lower()).strip("-") or "spec"
    prefix = f"implement/{slug}"
    branches = set(git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines())
    candidate = prefix
    suffix = 2
    while candidate in branches:
        candidate = f"{prefix}-{suffix}"
        suffix += 1
    git(repo, "switch", "-c", candidate)
    return candidate


def snapshot(repo, excluded=(), include_index=True):
    root = Path(repo)
    excluded = set(excluded)
    paths = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    ).decode().split("\0")
    paths += subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "-z", "HEAD"]
    ).decode().split("\0")
    digest = hashlib.sha256(git(root, "rev-parse", "HEAD").encode())
    for name in sorted(set(paths) - excluded - {""}):
        path = root / name
        digest.update(name.encode() + b"\0")
        if path.is_symlink():
            content = b"link\0" + os.readlink(path).encode()
        elif path.is_file():
            content = str(path.stat().st_mode & 0o777).encode() + b"\0" + path.read_bytes()
        elif not path.exists():
            content = b"deleted"
        else:
            raise WorkflowError(f"Unsupported directory or submodule in snapshot: {name}")
        digest.update(hashlib.sha256(content).digest())
    index = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"]
    ).split(b"\0")
    for entry in index:
        if include_index and entry and entry.split(b"\t", 1)[1].decode() not in excluded:
            digest.update(b"index\0" + entry + b"\0")
    return digest.hexdigest()


def validate_pass(report, ticket, checks, fingerprint):
    if report.get("verdict") != "PASS":
        raise WorkflowError("Verification did not pass.")
    if report.get("ticket") != ticket["path"] or report.get("reviewed_snapshot") != fingerprint:
        raise WorkflowError("Verification does not match this ticket and working tree.")
    if report.get("blocking_findings") != [] or report.get("unavailable_checks") != []:
        raise WorkflowError("Blocking findings or unavailable checks prevent PASS.")
    evidence = report.get("criteria", [])
    if len({item["id"] for item in evidence}) != len(evidence):
        raise WorkflowError("Duplicate acceptance evidence.")
    satisfied = {
        item["id"] for item in evidence
        if item.get("satisfied") is True and item.get("evidence")
    }
    if satisfied != set(ticket["criteria"]):
        raise WorkflowError("PASS must cover every agreed acceptance criterion.")
    results = report.get("checks", [])
    for command in checks:
        matching = [item for item in results if item.get("command") == command]
        if not matching or any(item.get("exit_code") != 0 or not item.get("evidence") for item in matching):
            raise WorkflowError(f"Missing or failed required check: {command}")
    return True


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".workflow-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def git_home(repo):
    return Path(git(repo, "rev-parse", "--absolute-git-dir")) / "implement-spec"


def relative_file(repo, name):
    root = Path(repo).resolve()
    candidate = root / name
    if Path(name).is_absolute() or candidate.is_symlink():
        raise WorkflowError(f"Expected a repository-relative regular file: {name}")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as error:
        raise WorkflowError(f"Path escapes the repository: {name}") from error
    return candidate


def status_text(path):
    matches = re.findall(r"^Status: (.+)$", path.read_text(), flags=re.MULTILINE)
    if len(matches) != 1:
        raise WorkflowError(f"Expected one Status line in {path}")
    return matches[0]


def set_status(path, label):
    status_text(path)
    if not label or "\n" in label or "\r" in label:
        raise WorkflowError("Invalid tracker label.")
    path.write_text(re.sub(r"^Status: .+$", lambda match: f"Status: {label}",
                           path.read_text(), count=1, flags=re.MULTILINE))


class Run:
    def __init__(self, repo, spec):
        self.repo = Path(repo).resolve()
        relative_file(self.repo, spec)
        self.spec = spec
        branch = git(self.repo, "branch", "--show-current")
        identity = hashlib.sha256((spec + "\0" + branch).encode()).hexdigest()[:20]
        self.path = git_home(self.repo) / "runs" / identity / "state.json"
        self.record = str(Path(spec).parent / "implementation-run.json")
        self.data = json.loads(self.path.read_text()) if self.path.exists() else None

    def create(self, plan):
        if self.data is not None:
            raise WorkflowError("A run record already exists. Resume it instead of overwriting it.")
        if git(self.repo, "status", "--porcelain", "--untracked-files=all"):
            raise WorkflowError("Preflight requires a clean checkout; keep the draft plan outside it.")
        if plan.get("spec") != self.spec or not plan.get("checks"):
            raise WorkflowError("The plan needs the matching spec and required offline checks.")
        if not plan.get("requirements"):
            raise WorkflowError("The plan needs the PRD requirement identifiers.")
        if any(not command or not isinstance(command, list)
               or any(not isinstance(part, str) or not part for part in command)
               for command in plan["checks"]):
            raise WorkflowError("Required checks must be nonempty argument lists.")
        if not plan.get("approval_evidence"):
            raise WorkflowError("Record the evidence for approved requirements and testing boundaries.")
        if not git(self.repo, "branch", "--show-current"):
            raise WorkflowError("Detached HEAD is not supported.")
        relative_file(self.repo, self.spec).read_text()
        tickets = plan.get("tickets", [])
        paths = [ticket["path"] for ticket in tickets]
        if not paths or len(paths) != len(set(paths)):
            raise WorkflowError("Plan needs a nonempty, unique required-ticket list.")
        remaining = set(paths)
        completed = set()
        while remaining:
            available = [
                ticket["path"] for ticket in tickets
                if ticket["path"] in remaining and set(ticket.get("blocked_by", [])) <= completed
            ]
            if not available:
                raise WorkflowError("Missing dependency or dependency cycle.")
            for path in available:
                remaining.remove(path)
                completed.add(path)
        records = {}
        for ticket in tickets:
            path = relative_file(self.repo, ticket["path"])
            if ticket["path"] in {self.spec, self.record}:
                raise WorkflowError("Ticket, specification and execution-record paths must differ.")
            if ticket.get("execution") != "AFK" or not ticket.get("criteria"):
                raise WorkflowError(f"Ticket is not fully specified for AFK: {ticket['path']}")
            if ticket.get("kind", "behavior") == "behavior" and not ticket.get("seams"):
                raise WorkflowError(f"Missing approved testing boundaries: {ticket['path']}")
            label = status_text(path)
            if label not in {plan.get("finished_ticket", "closed"), plan.get("ready_ticket", "ready-for-agent")}:
                raise WorkflowError(f"Ticket is not ready or already finished: {ticket['path']}")
            closed = label == plan.get("finished_ticket", "closed")
            records[ticket["path"]] = {
                "attempts": 0, "commit": git(self.repo, "rev-parse", "HEAD") if closed else None,
                "preexisting": closed, "findings": [], "implementer": None, "history": [],
            }
        self.data = {
            "version": 1, "repo": str(self.repo), "spec": self.spec,
            "branch": git(self.repo, "branch", "--show-current"),
            "baseline": git(self.repo, "rev-parse", "HEAD"),
            "head": git(self.repo, "rev-parse", "HEAD"),
            "outer_session": os.environ.get("CODEX_THREAD_ID"),
            "plan": plan, "tickets": records, "phase": "ready", "current": None,
            "checkpoint": None,
        }
        self.save()

    def save(self):
        self.data["checkpoint"] = snapshot(self.repo, [self.record])
        write_json(self.path, self.data)
        write_json(relative_file(self.repo, self.record), self.data)

    def ensure(self, phase=None, checkpoint=False):
        if not self.data or self.data["repo"] != str(self.repo):
            raise WorkflowError("No matching run record.")
        if git(self.repo, "branch", "--show-current") != self.data["branch"]:
            raise WorkflowError("Run belongs to another branch; unfinished changes were preserved.")
        if git(self.repo, "rev-parse", "HEAD") != self.data["head"]:
            raise WorkflowError("HEAD differs from the run record; reconcile the commit before resuming.")
        if phase and self.data["phase"] not in phase:
            raise WorkflowError(f"Cannot perform this operation in phase {self.data['phase']}.")
        if checkpoint and snapshot(self.repo, [self.record]) != self.data["checkpoint"]:
            raise WorkflowError("Checkout differs from the last checkpoint; inspect before resuming.")

    def ticket(self):
        return next(item for item in self.data["plan"]["tickets"] if item["path"] == self.data["current"])

    def begin(self, requested):
        self.ensure({"ready", "rework"}, checkpoint=True)
        if self.data["current"] not in (None, requested):
            raise WorkflowError("Another ticket is unfinished.")
        ticket = next((item for item in self.data["plan"]["tickets"] if item["path"] == requested), None)
        if ticket is None or self.data["tickets"][requested]["commit"]:
            raise WorkflowError("Ticket is not unfinished work in this plan.")
        if any(not self.data["tickets"][dependency]["commit"] for dependency in ticket.get("blocked_by", [])):
            raise WorkflowError("Ticket dependencies are not complete.")
        record = self.data["tickets"][requested]
        if record["attempts"] >= 3:
            self.data.update(phase="blocked", requires_user_resolution=True,
                             blocker="Three implementation attempts exhausted.")
            self.save()
            raise WorkflowError("Three implementation attempts exhausted; the whole run is blocked.")
        record["attempts"] += 1
        record.setdefault("review_base", self.data["head"])
        record["implementer"] = None
        record.setdefault("history", []).append({
            "attempt": record["attempts"], "implementer": None, "implementation": None, "reviews": [],
        })
        self.data.update(current=requested, phase="implementing", review=None, implementation=None)
        self.save()

    def checkpoint(self, implementer=None):
        self.ensure({"implementing", "blocked", "rework"})
        if implementer:
            if self.data["phase"] != "implementing" or not self.data["current"]:
                raise WorkflowError("Register a fresh implementer only for a started attempt.")
            record = self.data["tickets"][self.data["current"]]
            if record["implementer"] not in (None, implementer) or any(
                entry.get("implementer") == implementer
                for ticket, saved in self.data["tickets"].items()
                for entry in saved.get("history", [])
                if ticket != self.data["current"] or entry["attempt"] != record["attempts"]
            ):
                raise WorkflowError("Every attempt needs one fresh implementer; do not resume or replace it.")
            record["implementer"] = implementer
            record["history"][-1]["implementer"] = implementer
        self.save()

    def implemented(self, report):
        self.ensure({"implementing"})
        ticket = self.ticket()
        attempt = self.data["tickets"][ticket["path"]]["attempts"]
        if report.get("ticket") != ticket["path"] or report.get("attempt") != attempt:
            raise WorkflowError("Implementation result belongs to another ticket or attempt.")
        if report.get("outcome") != "READY_FOR_REVIEW":
            self.data["tickets"][ticket["path"]]["history"][-1]["implementation"] = report
            self.data.update(phase="blocked", blocker=report)
            self.save()
            return
        if ticket.get("kind", "behavior") == "behavior":
            cycles = report.get("tdd", [])
            if not cycles or any(
                cycle.get("boundary") not in ticket["seams"]
                or not cycle.get("red", {}).get("command")
                or cycle.get("red", {}).get("exit_code") in (None, 0)
                or not cycle.get("red", {}).get("evidence")
                or not cycle.get("green", {}).get("command")
                or cycle.get("green", {}).get("exit_code") != 0
                or not cycle.get("green", {}).get("evidence")
                for cycle in cycles
            ):
                raise WorkflowError("Implementation requires observed red/green evidence at approved boundaries.")
        elif not report.get("tdd_not_applicable_reason") or not report.get("checks"):
            raise WorkflowError("Nonbehavioral work requires its validation and TDD explanation.")
        self.data.update(phase="reviewing", implementation=report)
        self.data["tickets"][ticket["path"]]["history"][-1]["implementation"] = report
        self.save()

    def reviewed(self, report):
        self.ensure({"reviewing"}, checkpoint=True)
        current = self.data["current"]
        record = self.data["tickets"][current]
        if (report.get("ticket") != current or report.get("attempt") != record["attempts"]
                or report.get("base_commit") != record.get("review_base", self.data["head"])
                or report.get("reviewed_snapshot") != self.data["checkpoint"]):
            raise WorkflowError("Review does not match the current ticket, attempt, commit and snapshot.")
        verdict = report.get("verdict")
        findings = report.get("blocking_findings", [])
        finding_ids = [finding.get("id") for finding in findings]
        if any(not isinstance(identifier, str) or not identifier.strip() for identifier in finding_ids):
            raise WorkflowError("Blocking findings need stable, nonempty identifiers.")
        if len(finding_ids) != len(set(finding_ids)):
            raise WorkflowError("Blocking finding identifiers must be unique.")
        previous_ids = {
            finding["id"] for entry in record.get("history", [])
            for review in entry.get("reviews", []) for finding in review.get("blocking_findings", [])
        }
        if verdict == "PASS":
            validate_pass(report, self.ticket(), self.data["plan"]["checks"], self.data["checkpoint"])
            self.data["phase"] = "approved"
        elif verdict == "REWORK" and report.get("blocking_findings"):
            self.data["phase"] = "rework"
        elif verdict == "BLOCKED":
            self.data["phase"] = "blocked"
            if record.get("adjudication", {}).get("decision"):
                self.data["requires_user_resolution"] = True
        else:
            raise WorkflowError("Incomplete or invalid verification verdict.")
        record["findings"] = report.get("blocking_findings", [])
        record["history"][-1]["reviews"].append(report)
        self.data["review"] = report
        repeated = sorted(set(finding_ids) & previous_ids)
        if verdict == "REWORK" and repeated:
            self._queue_adjudication(repeated, "Blocking findings recur after prior verification.")
        self.save()

    def _queue_adjudication(self, finding_ids, evidence):
        record = self.data["tickets"][self.data["current"]]
        if record.get("adjudication"):
            self.data.update(phase="blocked", requires_user_resolution=True,
                             blocker="The ticket's single adjudication is exhausted; user resolution is required.")
            return
        record["adjudication"] = {
            "attempt": record["attempts"], "reviewed_snapshot": self.data["checkpoint"],
            "finding_ids": finding_ids, "evidence": evidence, "decision": None,
        }
        self.data["phase"] = "adjudicating"

    def dispute(self, report):
        self.ensure({"rework", "blocked", "adjudicating"}, checkpoint=True)
        current = self.data["current"]
        if not current:
            raise WorkflowError("No current ticket review is available to dispute.")
        record = self.data["tickets"][current]
        review = self.data.get("review") or {}
        identifiers = report.get("finding_ids", [])
        if (report.get("ticket") != current or report.get("attempt") != record["attempts"]
                or report.get("reviewed_snapshot") != self.data["checkpoint"]
                or review.get("verdict") not in {"REWORK", "BLOCKED"} or not report.get("evidence")
                or not identifiers or len(identifiers) != len(set(identifiers))
                or not set(identifiers) <= {finding["id"] for finding in record["findings"]}):
            raise WorkflowError("Dispute must identify current blocking findings and evidence on this snapshot.")
        if self.data["phase"] != "adjudicating":
            self._queue_adjudication(identifiers, report["evidence"])
        if self.data["phase"] == "adjudicating":
            request = record["adjudication"]
            if request.get("dispute") not in (None, report):
                raise WorkflowError("A dispute is already recorded; preserve its evidence for the outer agent.")
            request["dispute"] = report
        self.save()

    def adjudicate(self, report):
        self.ensure({"adjudicating"}, checkpoint=True)
        current = self.data["current"]
        record = self.data["tickets"][current]
        request = record["adjudication"]
        outer = self.data.get("outer_session")
        if outer and os.environ.get("CODEX_THREAD_ID") != outer:
            raise WorkflowError("Only the recorded outer session may adjudicate this ticket.")
        if (request.get("decision") is not None or report.get("ticket") != current
                or report.get("attempt") != record["attempts"]
                or report.get("reviewed_snapshot") != request["reviewed_snapshot"]
                or report.get("reviewed_snapshot") != self.data["checkpoint"]
                or report.get("previous_workers_inactive") is not True or not report.get("evidence")):
            raise WorkflowError("Adjudication requires current evidence, inactive workers and an unused decision.")
        findings = report.get("findings", [])
        identifiers = [finding.get("id") for finding in findings]
        classifications = {finding.get("classification") for finding in findings}
        if (len(identifiers) != len(set(identifiers))
                or set(identifiers) != {finding["id"] for finding in record["findings"]}
                or not classifications <= {"confirmed_blocker", "advisory", "unsupported", "needs_human"}
                or any(not finding.get("evidence") or not finding.get("reference") for finding in findings)):
            raise WorkflowError("Classify every current blocker with evidence and a requirement or rule reference.")
        decision = report.get("decision")
        if decision == "REVERIFY" and classifications <= {"advisory", "unsupported"}:
            target = "reviewing"
        elif decision == "REPAIR" and "confirmed_blocker" in classifications and "needs_human" not in classifications:
            target = "rework" if record["attempts"] < 3 else "blocked"
        elif decision == "BLOCKED":
            target = "blocked"
        else:
            raise WorkflowError("Decision does not match the finding classifications.")
        request["decision"] = report
        self.data.update(phase=target, review=None)
        self.data.pop("blocker", None)
        self.data.pop("requires_user_resolution", None)
        if target == "blocked":
            self.data.update(requires_user_resolution=True,
                             blocker="Adjudication needs a user decision or no repair attempts remain.")
        self.save()

    def commit_ticket(self):
        self.ensure({"approved"}, checkpoint=True)
        validate_pass(self.data["review"], self.ticket(), self.data["plan"]["checks"],
                      snapshot(self.repo, [self.record]))
        ticket = self.data["current"]
        path = relative_file(self.repo, ticket)
        transaction = {
            "kind": "ticket", "path": ticket, "old_status": status_text(path),
            "new_status": self.data["plan"].get("finished_ticket", "closed"),
            "parent": self.data["head"], "message": f"Implement {Path(ticket).stem}",
            "before_status_snapshot": snapshot(self.repo, [self.record], include_index=False),
            "status_restored": True,
        }
        changed = subprocess.check_output(
            ["git", "-C", str(self.repo), "diff", "--name-only", "-z", "HEAD"]
        ).decode().split("\0")
        untracked = subprocess.check_output(
            ["git", "-C", str(self.repo), "ls-files", "--others", "--exclude-standard", "-z"]
        ).decode().split("\0")
        transaction["paths"] = sorted((set(changed) | set(untracked) | {ticket, self.record}) - {""})
        self.data.update(phase="committing", transaction=transaction)
        self.save()
        return self.reconcile_commit()

    def reconcile_commit(self):
        if self.data["phase"] != "committing" or not self.data.get("transaction"):
            raise WorkflowError("No interrupted commit to reconcile.")
        transaction = self.data["transaction"]
        if git(self.repo, "branch", "--show-current") != self.data["branch"]:
            raise WorkflowError("Run belongs to another branch.")
        current_head = git(self.repo, "rev-parse", "HEAD")
        status_path = relative_file(self.repo, transaction["path"])
        if current_head == transaction["parent"]:
            label = status_text(status_path)
            if label not in {transaction["old_status"], transaction["new_status"]}:
                raise WorkflowError("Pending transaction status was changed unexpectedly.")
            if label != transaction["old_status"]:
                set_status(status_path, transaction["old_status"])
            excluded = [self.record]
            if transaction["kind"] == "audit":
                excluded.append(transaction["audit_path"])
            if snapshot(self.repo, excluded, include_index=False) != transaction["before_status_snapshot"]:
                raise WorkflowError("Pending commit files changed; preserve them and request fresh verification.")
            if transaction["kind"] == "audit":
                audit_path = relative_file(self.repo, transaction["audit_path"])
                content = "# Implementation audit\n\n```json\n" + json.dumps(self.data["audit"], indent=2) + "\n```\n"
                if audit_path.exists() and audit_path.read_text() != content:
                    raise WorkflowError("Pending audit report was changed; preserve it and investigate.")
                if not audit_path.exists():
                    audit_path.write_text(content)
            set_status(status_path, transaction["new_status"])
            transaction["status_restored"] = False
            transaction["working_snapshot"] = snapshot(self.repo, [self.record], include_index=False)
            self.save()
            present = [name for name in transaction["paths"]
                       if (self.repo / name).exists() or (self.repo / name).is_symlink()]
            missing = [name for name in transaction["paths"] if name not in present]
            if present:
                git(self.repo, "add", "--", *present)
            if missing:
                git(self.repo, "update-index", "--force-remove", "--", *missing)
            staged = set(git(self.repo, "diff", "--cached", "--name-only", "HEAD").splitlines())
            if staged - set(transaction["paths"]):
                raise WorkflowError("Unreviewed paths are staged outside the pending transaction.")
            expected_tree = git(self.repo, "write-tree")
            if transaction.get("tree") and transaction["tree"] != expected_tree:
                differences = set(git(self.repo, "diff", "--name-only", transaction["tree"], expected_tree).splitlines())
                if differences - {self.record}:
                    raise WorkflowError("Pending index differs from the recorded transaction.")
            transaction["tree"] = expected_tree
            write_json(self.path, self.data)
            try:
                git(self.repo, "commit", "-m", transaction["message"])
            except WorkflowError:
                if git(self.repo, "rev-parse", "HEAD") == transaction["parent"]:
                    set_status(status_path, transaction["old_status"])
                    transaction["status_restored"] = True
                    self.data["blocker"] = "Commit failed; fix its cause, then reconcile-commit."
                    self.save()
                raise
            current_head = git(self.repo, "rev-parse", "HEAD")
        dirty = set(git(self.repo, "diff", "--name-only", "HEAD").splitlines())
        dirty.update(git(self.repo, "diff", "--cached", "--name-only", "HEAD").splitlines())
        dirty.update(git(self.repo, "ls-files", "--others", "--exclude-standard").splitlines())
        if (git(self.repo, "rev-parse", "HEAD^") != transaction["parent"]
                or git(self.repo, "rev-parse", "HEAD^{tree}") != transaction.get("tree")
                or dirty - {self.record}):
            if transaction["new_status"] != transaction["old_status"]:
                set_status(status_path, transaction["old_status"])
            raise WorkflowError("Committed tree or remaining files differ from verification; stop and inspect.")
        if status_text(status_path) != transaction["new_status"]:
            raise WorkflowError("Status edit is missing from the commit.")
        if transaction["kind"] == "ticket":
            self.data["tickets"][self.data["current"]]["commit"] = current_head
            self.data.update(head=current_head, current=None, phase="ready")
            self.data.pop("transaction")
            self.data.pop("blocker", None)
            self.save()
        else:
            self.data.update(head=current_head, phase=transaction["target_phase"])
            self.data.pop("transaction")
            self.data.pop("blocker", None)
            self.data["checkpoint"] = snapshot(self.repo, [self.record])
            write_json(self.path, self.data)
        return current_head

    def finish(self, report):
        self.ensure({"ready"}, checkpoint=True)
        if any(not item["commit"] for item in self.data["tickets"].values()):
            raise WorkflowError("Required tickets remain unfinished.")
        if report.get("audited_commit") != self.data["head"] or report.get("baseline_commit") != self.data["baseline"]:
            raise WorkflowError("Audit does not match the complete run.")
        if report.get("reviewed_snapshot") != self.data["checkpoint"]:
            raise WorkflowError("Audit does not match the current checkout.")
        verdict = report.get("verdict")
        if verdict not in {"PASS", "REWORK", "BLOCKED"}:
            raise WorkflowError("Invalid audit verdict.")
        if verdict == "PASS":
            criteria = self.data["plan"].get("requirements", [])
            if not criteria:
                raise WorkflowError("The plan needs PRD requirements before final approval.")
            normalized = dict(report, ticket=self.spec, criteria=report.get("requirements", []))
            validate_pass(normalized, {"path": self.spec, "criteria": criteria},
                          self.data["plan"]["checks"], self.data["checkpoint"])
        elif not report.get("blocking_findings") and not report.get("unavailable_checks"):
            raise WorkflowError("A failed audit needs its findings or unavailable checks.")
        unexpected = set(git(self.repo, "diff", "--name-only", "HEAD").splitlines()) - {self.record}
        unexpected.update(set(git(self.repo, "diff", "--cached", "--name-only", "HEAD").splitlines()) - {self.record})
        untracked = set(git(self.repo, "ls-files", "--others", "--exclude-standard").splitlines()) - {self.record}
        if unexpected or untracked:
            raise WorkflowError("Uncommitted implementation changes prevent the final audit commit.")
        audit = str(Path(self.spec).parent / "final-audit.md")
        audit_path = relative_file(self.repo, audit)
        if audit_path.exists():
            raise WorkflowError("An audit report already exists; preserve it and resolve the destination.")
        previous = status_text(relative_file(self.repo, self.spec))
        transaction = {
            "kind": "audit", "path": self.spec, "old_status": previous,
            "new_status": self.data["plan"].get("finished_spec", "done") if verdict == "PASS" else previous,
            "parent": self.data["head"], "message": f"Record implementation audit for {Path(self.spec).stem}",
            "paths": [audit, self.record, self.spec],
            "before_status_snapshot": snapshot(self.repo, [self.record, audit], include_index=False),
            "status_restored": True, "target_phase": "done" if verdict == "PASS" else "audit-blocked",
            "audit_path": audit,
        }
        self.data.update(phase="committing", transaction=transaction, audit=report)
        self.save()
        return self.reconcile_commit()

    def invalidate(self, report):
        if (not self.data or self.data["phase"] != "committing"
                or git(self.repo, "branch", "--show-current") != self.data["branch"]):
            raise WorkflowError("Only this branch's pending ticket transaction can be invalidated.")
        transaction = self.data.get("transaction", {})
        if (transaction.get("kind") != "ticket" or not report.get("evidence")
                or report.get("previous_workers_inactive") is not True):
            raise WorkflowError("Ticket invalidation needs evidence and confirmed inactive workers.")
        current_head = git(self.repo, "rev-parse", "HEAD")
        if current_head != self.data["head"]:
            if git(self.repo, "rev-parse", "HEAD^") != transaction["parent"]:
                raise WorkflowError("Unexpected history change; only the pending commit can be reconciled.")
            record = self.data["tickets"][self.data["current"]]
            record.setdefault("review_base", transaction["parent"])
            record.setdefault("unverified_commits", []).append(current_head)
            self.data["head"] = current_head
        path = relative_file(self.repo, transaction["path"])
        if status_text(path) == transaction["new_status"]:
            set_status(path, transaction["old_status"])
        self.data.setdefault("invalidations", []).append(report)
        self.data.pop("transaction", None)
        self.data.update(phase="reviewing", review=None)
        self.save()

    def resolve(self, resolution):
        self.ensure({"blocked"}, checkpoint=True)
        if not resolution.get("evidence") or resolution.get("previous_workers_inactive") is not True:
            raise WorkflowError("Resolution requires evidence and confirmed inactive previous workers.")
        current = self.data["current"]
        if not current:
            raise WorkflowError("Inspect this non-ticket blocker before changing its state.")
        if (self.data.get("requires_user_resolution") or self.data["tickets"][current]["attempts"] >= 3):
            if not resolution.get("user_authorization"):
                raise WorkflowError("The automatic budget is exhausted; record the user's explicit resolution.")
        target = resolution.get("next_phase")
        if target == "reviewing":
            implementation = self.data.get("implementation") or {}
            if (implementation.get("ticket") != current
                    or implementation.get("attempt") != self.data["tickets"][current]["attempts"]
                    or implementation.get("outcome") != "READY_FOR_REVIEW"):
                raise WorkflowError("No completed implementation for this ticket and attempt exists to verify.")
        elif target == "rework":
            if self.data["tickets"][current]["attempts"] >= 3:
                raise WorkflowError("Attempt limit remains exhausted; resolution cannot reset it.")
        else:
            raise WorkflowError("Resolution can resume verification or an available repair.")
        self.data.setdefault("resolutions", []).append(resolution)
        self.data["phase"] = target
        self.data.pop("requires_user_resolution", None)
        self.save()


def config_paths():
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    return [home / "implement-spec.config.toml"] + [
        home / "agents" / f"{role}.toml"
        for role in ("implementation_coordinator", "ticket_implementer", "ticket_verifier", "spec_auditor")
    ]


def config_fingerprint():
    digest = hashlib.sha256()
    for path in config_paths():
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def runtime_version():
    result = subprocess.run(["codex", "--version"], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def enforced_config_arguments():
    config = tomllib.loads(config_paths()[0].read_text())
    values = {
        "model": config["model"], "model_reasoning_effort": config["model_reasoning_effort"],
        "features.multi_agent": config["features"]["multi_agent"],
        "features.multi_agent_v2": config["features"]["multi_agent_v2"],
        "agents.max_depth": config["agents"]["max_depth"],
        "agents.max_concurrent_threads_per_session": config["agents"]["max_concurrent_threads_per_session"],
    }
    for path in config_paths()[1:]:
        values[f"agents.{path.stem}.config_file"] = str(path)
    return [part for key, value in values.items() for part in ("-c", f"{key}={json.dumps(value)}")]


def verify_capability():
    receipt_path = Path(__file__).resolve().parents[1] / "references" / "runtime-evidence.json"
    if not receipt_path.exists():
        raise WorkflowError("Runtime compatibility is unverified. Run scripts/smoke_test.py first.")
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get("runtime") != runtime_version()
            or receipt.get("config_fingerprint") != config_fingerprint()
            or not all(receipt.get("checks", {}).get(name) is True for name in
                       ("named_profiles", "effective_models", "nested_delegation",
                        "second_worker_rejected", "workers_completed",
                        "repair_lifecycle", "children_closed"))):
        raise WorkflowError("Runtime or profiles differ from verified evidence. Repeat the isolated smoke test.")
    return receipt


def launch(repo, spec, branch=None, resume=False):
    verify_capability()
    with exclusive(git_home(repo) / "launch.lock") as descriptor:
        command = ["codex", "--no-daemon", "--profile", "implement-spec", "--approve-for-me", "-C", str(repo)]
        command.extend(enforced_config_arguments())
        if resume:
            if branch and branch != git(repo, "branch", "--show-current"):
                existing = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
                if branch not in existing:
                    raise WorkflowError("A resume branch must already exist.")
                choose_branch(repo, spec, branch)
            run = Run(repo, spec)
            if not run.data or not run.data.get("outer_session"):
                raise WorkflowError("No saved outer session. Inspect the interrupted run before continuing.")
            if branch and branch != run.data["branch"]:
                raise WorkflowError("Requested branch conflicts with the saved run.")
            if git(repo, "branch", "--show-current") != run.data["branch"]:
                raise WorkflowError("Check out the saved run branch before resuming; no changes were moved.")
            prompt = "Resume the approved $implement-spec-single-worker workflow. Reconcile state and confirm old workers are inactive before continuing. " + json.dumps({"spec": spec})
            command.extend(["resume", run.data["outer_session"], prompt])
        else:
            selected = choose_branch(repo, spec, branch)
            run = Run(repo, spec)
            if run.data:
                raise WorkflowError("Run already exists on this branch. Use launch --resume.")
            prompt = "Use $implement-spec-single-worker to execute the approved AFK workflow. Read the skill before acting. " + json.dumps({"spec": spec, "branch": selected})
            command.append(prompt)
        return subprocess.call(command, pass_fds=(descriptor,))


def main():
    parser = argparse.ArgumentParser(description="Guard the sequential Codex implementation workflow.")
    parser.add_argument("action", choices=[
        "launch", "prepare", "init", "status", "snapshot", "begin", "implemented",
        "reviewed", "dispute", "adjudicate", "commit", "finish", "checkpoint",
        "reconcile-commit", "resolve", "invalidate", "doctor",
    ])
    parser.add_argument("spec", nargs="?")
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--branch")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--plan")
    parser.add_argument("--ticket")
    parser.add_argument("--report")
    parser.add_argument("--implementer")
    arguments = parser.parse_args()
    try:
        if arguments.action == "doctor":
            print(json.dumps(verify_capability(), indent=2))
            return 0
        repo = Path(git(arguments.repo, "rev-parse", "--show-toplevel"))
        if not arguments.spec:
            raise WorkflowError("Provide the repository-relative PRD path.")
        if arguments.action == "launch":
            return launch(repo, arguments.spec, arguments.branch, arguments.resume)
        if arguments.action == "prepare":
            verify_capability()
            print(choose_branch(repo, arguments.spec, arguments.branch))
            return 0
        run = Run(repo, arguments.spec)
        if arguments.action in {"status", "snapshot"}:
            value = snapshot(repo, [run.record]) if arguments.action == "snapshot" else run.data
            print(json.dumps(value, indent=2))
            return 0
        with exclusive(git_home(repo) / "state.lock"):
            run = Run(repo, arguments.spec)
            report = json.loads(Path(arguments.report).read_text()) if arguments.report else None
            if arguments.action == "init":
                run.create(json.loads(Path(arguments.plan).read_text()))
            elif arguments.action == "begin":
                run.begin(arguments.ticket)
            elif arguments.action == "implemented":
                run.implemented(report)
            elif arguments.action == "reviewed":
                run.reviewed(report)
            elif arguments.action == "dispute":
                run.dispute(report)
            elif arguments.action == "adjudicate":
                run.adjudicate(report)
            elif arguments.action == "commit":
                print(run.commit_ticket())
            elif arguments.action == "finish":
                print(run.finish(report))
            elif arguments.action == "reconcile-commit":
                print(run.reconcile_commit())
            elif arguments.action == "resolve":
                run.resolve(report)
            elif arguments.action == "invalidate":
                run.invalidate(report)
            elif arguments.action == "checkpoint":
                run.checkpoint(arguments.implementer)
            print(json.dumps(run.data, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
