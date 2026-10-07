#!/usr/bin/env python3
import subprocess
import re
import hashlib
import os
import json
import tempfile
import argparse
import sys
import platform_support
import tomllib
import copy
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath

import configuration
import datetime


class WorkflowError(RuntimeError):
    pass


class LockContended(WorkflowError, platform_support.LockContended):
    pass


@contextmanager
def exclusive(path):
    try:
        with platform_support.exclusive(path) as descriptor:
            yield descriptor
    except platform_support.LockContended as error:
        raise LockContended(str(error)) from error


def git(repo, *arguments):
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise WorkflowError(result.stderr.strip())
    return result.stdout.strip()


def git_paths(repo, *arguments):
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments, "-z"], capture_output=True, check=False,
    )
    if result.returncode:
        raise WorkflowError(result.stderr.decode("utf-8", errors="replace").strip())
    return {name.decode("utf-8") for name in result.stdout.split(b"\0") if name}


def choose_branch(repo, spec, requested=None):
    spec = repository_path(spec)
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
    excluded = {repository_path(name) for name in excluded}
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


def validate_pass(report, ticket, checks, fingerprint, finding_ids=()):
    if report.get("verdict") != "PASS":
        raise WorkflowError("Verification did not pass.")
    if (repository_path(report.get("ticket")) != repository_path(ticket["path"])
            or report.get("reviewed_snapshot") != fingerprint):
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
    if finding_ids:
        resolved = report.get("resolved_findings", [])
        identifiers = [item.get("id") for item in resolved]
        if (len(identifiers) != len(set(identifiers)) or set(identifiers) != set(finding_ids)
                or any(not item.get("evidence") for item in resolved)):
            raise WorkflowError("Repair PASS needs independent evidence for every assigned audit finding.")
    return True


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".workflow-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
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


def repository_path(name):
    if not isinstance(name, str) or not name or "\0" in name:
        raise WorkflowError(f"Expected a repository-relative file path: {name}")
    path = PurePosixPath(name.replace(os.sep, "/"))
    if (path.is_absolute() or PureWindowsPath(name).drive
            or any(part in {"..", ".git"} for part in path.parts) or not path.parts):
        raise WorkflowError(f"Expected a repository-relative file without traversal: {name}")
    return path.as_posix()


def ticket_paths(ticket):
    ticket = copy.deepcopy(ticket)
    ticket["path"] = repository_path(ticket["path"])
    for field in ("blocked_by", "related_tickets"):
        if field in ticket:
            ticket[field] = [repository_path(name) for name in ticket[field]]
    return ticket


def report_paths(report):
    report = copy.deepcopy(report)
    if "ticket" in report:
        report["ticket"] = repository_path(report["ticket"])
    if "tickets" in report:
        report["tickets"] = [ticket_paths(ticket) for ticket in report["tickets"]]
    return report


def relative_file(repo, name):
    name = repository_path(name)
    root = Path(repo).resolve()
    candidate = root / name
    current = root
    for part in PurePosixPath(name).parts:
        current = current / part
        if current.is_symlink():
            raise WorkflowError(f"Expected a repository-relative regular file: {name}")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as error:
        raise WorkflowError(f"Path escapes the repository: {name}") from error
    return candidate


def status_text(path):
    matches = re.findall(r"^Status: ([^\r\n]*)\r?$", path.read_bytes().decode("utf-8"), flags=re.MULTILINE)
    if len(matches) != 1 or not matches[0]:
        raise WorkflowError(f"Expected one Status line in {path}")
    return matches[0]


def set_status(path, label):
    status_text(path)
    if not label or "\n" in label or "\r" in label:
        raise WorkflowError("Invalid tracker label.")
    path.write_bytes(re.sub(rb"^Status: [^\r\n]+", lambda match: f"Status: {label}".encode("utf-8"),
                           path.read_bytes(), count=1, flags=re.MULTILINE))


def validate_graph(tickets):
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
        remaining.difference_update(available)
        completed.update(available)


def audit_cycle(number, authorization, round_limit=None):
    return {
        "number": number, "authorization": authorization,
        "round_limit": round_limit if round_limit is not None else configuration.load()["audit_repair_rounds"],
        "rounds": [], "finding_attempts": {},
    }


class Run:
    def __init__(self, repo, spec):
        self.repo = Path(repo).resolve()
        spec = repository_path(spec)
        relative_file(self.repo, spec)
        self.spec = spec
        branch = git(self.repo, "branch", "--show-current")
        identity = hashlib.sha256((spec + "\0" + branch).encode()).hexdigest()[:20]
        self.path = git_home(self.repo) / "runs" / identity / "state.json"
        self.record = (Path(spec).parent / "implementation-run.json").as_posix()
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else None
        if self.data:
            self.data.setdefault("audit_cycles", [
                audit_cycle(1, self.data["plan"]["approval_evidence"]),
            ])
            if "audits" not in self.data:
                self.data["audits"] = []
                if self.data.get("audit"):
                    transaction = self.data.get("transaction", {})
                    pending = transaction.get("kind") == "audit"
                    self.data["audits"].append({
                        "number": 1, "report": copy.deepcopy(self.data["audit"]),
                        "path": (Path(spec).parent / "final-audit.md").as_posix(),
                        "commit": None if pending else self.data["head"], "cycle": 1,
                    })

    def create(self, plan):
        plan = copy.deepcopy(plan)
        plan["spec"] = repository_path(plan.get("spec"))
        plan["tickets"] = [ticket_paths(ticket) for ticket in plan.get("tickets", [])]
        if self.data is not None:
            raise WorkflowError("A run record already exists. Resume it instead of overwriting it.")
        entry_path = git_home(self.repo) / "entry.json"
        if entry_path.exists():
            owner = json.loads(entry_path.read_text(encoding="utf-8"))["outer_session"]
            if os.environ.get("CODEX_THREAD_ID") != owner:
                raise WorkflowError("Only the admitted outer session may initialize a run.")
        elif os.environ.get("IMPLEMENT_SPEC_LAUNCH") == "1":
            session = session_metadata(os.environ.get("CODEX_THREAD_ID"))
            source = session.get("source")
            if not source or (isinstance(source, dict) and "subagent" in source):
                raise WorkflowError("Only the launcher's outer session may initialize a run.")
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
        relative_file(self.repo, self.spec).read_text(encoding="utf-8")
        tickets = plan.get("tickets", [])
        validate_graph(tickets)
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
            "version": 2, "repo": str(self.repo), "spec": self.spec,
            "branch": git(self.repo, "branch", "--show-current"),
            "baseline": git(self.repo, "rev-parse", "HEAD"),
            "head": git(self.repo, "rev-parse", "HEAD"),
            "outer_session": os.environ.get("CODEX_THREAD_ID"),
            "plan": plan, "tickets": records, "phase": "ready", "current": None,
            "checkpoint": None,
            "audits": [], "audit_cycles": [audit_cycle(1, plan["approval_evidence"])],
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
        self.require_audit_integrity()

    def require_audit_integrity(self):
        for audit in self.data["audits"]:
            if not audit.get("commit"):
                continue
            path = relative_file(self.repo, audit["path"])
            if not path.is_file():
                raise WorkflowError(f"Historical audit report changed or disappeared: {audit['path']}")
            canonical = subprocess.run(
                ["git", "-C", str(self.repo), "hash-object", f"--path={audit['path']}", "--stdin"],
                input=path.read_bytes(), capture_output=True, check=False,
            )
            if canonical.returncode:
                raise WorkflowError(canonical.stderr.decode("utf-8", errors="replace").strip())
            original = git(self.repo, "rev-parse", f"{audit['commit']}:{audit['path']}")
            if canonical.stdout.decode("ascii").strip() != original:
                raise WorkflowError(f"Historical audit report changed or disappeared: {audit['path']}")

    def ticket(self):
        return next(item for item in self.data["plan"]["tickets"] if item["path"] == self.data["current"])

    def require_outer(self):
        outer = self.data.get("outer_session")
        if outer and os.environ.get("CODEX_THREAD_ID") != outer:
            raise WorkflowError("Only the recorded outer session may plan or continue audit repairs.")

    def require_handoff(self, report):
        self.require_outer()
        if (not report or report.get("reviewed_snapshot") != self.data["checkpoint"]
                or report.get("previous_workers_inactive") is not True or not report.get("evidence")):
            raise WorkflowError("Audit handoff needs the current snapshot and evidence that all workers closed.")

    def attempts_remaining(self, requested):
        requested = repository_path(requested)
        record = self.data["tickets"][requested]
        remaining = record.get("attempt_limit", 3) - record["attempts"]
        if record.get("audit_findings"):
            cycle = self.data["audit_cycles"][-1]
            remaining = min(remaining, *[
                3 - cycle["finding_attempts"].get(identifier, 0)
                for identifier in record["audit_findings"]
            ])
        return remaining

    def begin(self, requested):
        requested = repository_path(requested)
        self.ensure({"ready", "rework"}, checkpoint=True)
        if self.data["current"] not in (None, requested):
            raise WorkflowError("Another ticket is unfinished.")
        ticket = next((item for item in self.data["plan"]["tickets"] if item["path"] == requested), None)
        if ticket is None or self.data["tickets"][requested]["commit"]:
            raise WorkflowError("Ticket is not unfinished work in this plan.")
        if any(not self.data["tickets"][dependency]["commit"] for dependency in ticket.get("blocked_by", [])):
            raise WorkflowError("Ticket dependencies are not complete.")
        record = self.data["tickets"][requested]
        if self.attempts_remaining(requested) <= 0:
            self.data.update(phase="blocked", requires_user_resolution=True,
                             current=requested, budget_exhausted="ticket_attempts",
                             blocker="Three implementation attempts exhausted in the current allowance.")
            self.save()
            raise WorkflowError("Three implementation attempts exhausted; the whole run is blocked.")
        record["attempts"] += 1
        for identifier in record.get("audit_findings", []):
            attempts = self.data["audit_cycles"][-1]["finding_attempts"]
            attempts[identifier] = attempts.get(identifier, 0) + 1
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
        report = report_paths(report)
        self.ensure({"implementing"})
        ticket = self.ticket()
        attempt = self.data["tickets"][ticket["path"]]["attempts"]
        if report.get("ticket") != ticket["path"] or report.get("attempt") != attempt:
            raise WorkflowError("Implementation result belongs to another ticket or attempt.")
        if report.get("outcome") != "READY_FOR_REVIEW":
            self.data["tickets"][ticket["path"]]["history"][-1]["implementation"] = report
            self.data.update(phase="blocked", blocker=report)
            if self.attempts_remaining(ticket["path"]) <= 0:
                self.data.update(budget_exhausted="ticket_attempts", requires_user_resolution=True)
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
        report = report_paths(report)
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
            if entry["attempt"] > record.get("attempt_start", 0)
            for review in entry.get("reviews", []) for finding in review.get("blocking_findings", [])
        }
        if verdict == "PASS":
            validate_pass(report, self.ticket(), self.data["plan"]["checks"], self.data["checkpoint"],
                          record.get("audit_findings", []))
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
        if verdict != "PASS" and self.attempts_remaining(current) <= 0:
            self.data.update(phase="blocked", requires_user_resolution=True,
                             budget_exhausted="ticket_attempts",
                             blocker="Three implementation attempts exhausted in the current allowance.")
        elif verdict == "REWORK" and repeated:
            self._queue_adjudication(repeated, "Blocking findings recur after prior verification.")
        self.save()

    def _queue_adjudication(self, finding_ids, evidence):
        record = self.data["tickets"][self.data["current"]]
        if record.get("adjudication"):
            self.data.update(phase="blocked", requires_user_resolution=True,
                             budget_exhausted="adjudication",
                             blocker="The ticket's single adjudication is exhausted; user resolution is required.")
            return
        record["adjudication"] = {
            "attempt": record["attempts"], "reviewed_snapshot": self.data["checkpoint"],
            "finding_ids": finding_ids, "evidence": evidence, "decision": None,
        }
        self.data["phase"] = "adjudicating"

    def dispute(self, report):
        report = report_paths(report)
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
        report = report_paths(report)
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
            target = "rework" if self.attempts_remaining(current) > 0 else "blocked"
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
            if decision == "REPAIR":
                self.data["budget_exhausted"] = "ticket_attempts"
        self.save()

    def commit_ticket(self):
        self.ensure({"approved"}, checkpoint=True)
        validate_pass(self.data["review"], self.ticket(), self.data["plan"]["checks"],
                      snapshot(self.repo, [self.record]),
                      self.data["tickets"][self.data["current"]].get("audit_findings", []))
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
        self.require_audit_integrity()
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
            edits = transaction.get("file_edits", {})
            excluded.extend(edits)
            if snapshot(self.repo, excluded, include_index=False) != transaction["before_status_snapshot"]:
                raise WorkflowError("Pending commit files changed; preserve them and request fresh verification.")
            for name, edit in edits.items():
                path = relative_file(self.repo, name)
                current = path.read_bytes().decode("utf-8") if path.exists() else None
                if current not in (edit["before"], edit["after"]):
                    raise WorkflowError("Pending repair ticket changed; preserve it and investigate.")
            for name, edit in edits.items():
                path = relative_file(self.repo, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(edit["after"].encode("utf-8"))
            if transaction["kind"] == "audit":
                audit_path = relative_file(self.repo, transaction["audit_path"])
                content = "# Implementation audit\n\n```json\n" + json.dumps(self.data["audit"], indent=2) + "\n```\n"
                if audit_path.exists() and audit_path.read_bytes().decode("utf-8") != content:
                    raise WorkflowError("Pending audit report was changed; preserve it and investigate.")
                if not audit_path.exists():
                    audit_path.write_bytes(content.encode("utf-8"))
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
            staged = git_paths(self.repo, "diff", "--cached", "--name-only", "HEAD")
            if staged - set(transaction["paths"]):
                raise WorkflowError("Unreviewed paths are staged outside the pending transaction.")
            expected_tree = git(self.repo, "write-tree")
            if transaction.get("tree") and transaction["tree"] != expected_tree:
                differences = git_paths(self.repo, "diff", "--name-only", transaction["tree"], expected_tree)
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
        dirty = git_paths(self.repo, "diff", "--name-only", "HEAD")
        dirty.update(git_paths(self.repo, "diff", "--cached", "--name-only", "HEAD"))
        dirty.update(git_paths(self.repo, "ls-files", "--others", "--exclude-standard"))
        if (git(self.repo, "rev-parse", "HEAD^") != transaction["parent"]
                or git(self.repo, "rev-parse", "HEAD^{tree}") != transaction.get("tree")
                or dirty - {self.record}):
            if transaction["new_status"] != transaction["old_status"]:
                set_status(status_path, transaction["old_status"])
            raise WorkflowError("Committed tree or remaining files differ from verification; stop and inspect.")
        if status_text(status_path) != transaction["new_status"]:
            raise WorkflowError("Status edit is missing from the commit.")
        if transaction["kind"] == "ticket":
            record = self.data["tickets"][self.data["current"]]
            record["commit"] = current_head
            record.setdefault("completions", []).append({
                "commit": current_head, "attempt": record["attempts"],
                "review_base": record.get("review_base"), "cycle": record.get("repair_cycle"),
            })
            self.data.update(head=current_head, current=None, phase="ready")
            self.data.pop("transaction")
            self.data.pop("blocker", None)
            self.save()
        else:
            if transaction["kind"] == "audit":
                self.data["audits"][-1]["commit"] = current_head
            elif transaction["kind"] == "repair-plan":
                self.data["audit_cycles"][-1]["rounds"][-1]["commit"] = current_head
            self.data.update(head=current_head, phase=transaction["target_phase"])
            self.data.pop("transaction")
            self.data.pop("blocker", None)
            self.data["checkpoint"] = snapshot(self.repo, [self.record])
            write_json(self.path, self.data)
        return current_head

    def finish(self, report):
        self.ensure({"ready"}, checkpoint=True)
        self.require_outer()
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
        identifiers = [finding.get("id") for finding in report.get("blocking_findings", [])]
        if (any(not isinstance(identifier, str) or not identifier.strip() for identifier in identifiers)
                or len(identifiers) != len(set(identifiers))):
            raise WorkflowError("Audit findings need unique, stable identifiers.")
        unexpected = git_paths(self.repo, "diff", "--name-only", "HEAD") - {self.record}
        unexpected.update(git_paths(self.repo, "diff", "--cached", "--name-only", "HEAD") - {self.record})
        untracked = git_paths(self.repo, "ls-files", "--others", "--exclude-standard") - {self.record}
        if unexpected or untracked:
            raise WorkflowError("Uncommitted implementation changes prevent the final audit commit.")
        number = len(self.data["audits"]) + 1
        filename = "final-audit.md" if number == 1 else f"final-audit-{number:03d}.md"
        audit = (Path(self.spec).parent / filename).as_posix()
        audit_path = relative_file(self.repo, audit)
        if audit_path.exists():
            raise WorkflowError("An audit report already exists; preserve it and resolve the destination.")
        previous = status_text(relative_file(self.repo, self.spec))
        cycle = self.data["audit_cycles"][-1]
        self.data["audits"].append({
            "number": number, "report": copy.deepcopy(report), "path": audit,
            "commit": None, "cycle": cycle["number"],
        })
        self.data.pop("budget_exhausted", None)
        self.data.pop("requires_user_resolution", None)
        if verdict != "PASS" and len(cycle["rounds"]) >= cycle["round_limit"]:
            self.data.update(budget_exhausted="audit_rounds", requires_user_resolution=True)
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

    @staticmethod
    def repair_allowance(record, cycle):
        if record.get("repair_cycle") == cycle:
            return
        if record.get("adjudication"):
            record.setdefault("adjudications", []).append({
                "cycle": record.get("repair_cycle"), "report": record.pop("adjudication"),
            })
        record.update(repair_cycle=cycle, attempt_start=record["attempts"],
                      attempt_limit=record["attempts"] + 3)

    def repair_audit(self, report):
        report = report_paths(report)
        self.ensure({"audit-blocked"}, checkpoint=True)
        self.require_handoff(report)
        audit = self.data["audits"][-1]
        cycle = self.data["audit_cycles"][-1]
        if (report.get("audit_number") != audit["number"] or audit["commit"] != self.data["head"]
                or audit["report"]["verdict"] == "PASS"):
            raise WorkflowError("Repair planning must identify the latest failed audit and its commit.")
        if len(cycle["rounds"]) >= cycle["round_limit"]:
            raise WorkflowError("Audit repair rounds exhausted; explicit user continuation is required.")
        findings = report.get("findings", [])
        identifiers = [finding.get("id") for finding in findings]
        expected = {finding["id"] for finding in audit["report"].get("blocking_findings", [])}
        if (len(identifiers) != len(set(identifiers)) or set(identifiers) != expected
                or any(finding.get("classification") not in {
                    "confirmed_blocker", "advisory", "unsupported", "needs_human",
                } or not finding.get("reference") or not finding.get("evidence") for finding in findings)):
            raise WorkflowError("Classify every audit finding with its requirement or rule and concrete evidence.")
        if any(finding["classification"] == "needs_human" for finding in findings):
            raise WorkflowError("Resolve the recorded requirements decision before planning automatic repairs.")
        if audit["report"].get("unavailable_checks") and not report.get("check_resolution"):
            raise WorkflowError("Record how unavailable required checks were restored; continuation cannot waive them.")
        confirmed = {finding["id"] for finding in findings if finding["classification"] == "confirmed_blocker"}
        changes = report.get("tickets", [])
        assigned = [identifier for ticket in changes for identifier in ticket.get("finding_ids", [])]
        if len(assigned) != len(set(assigned)) or set(assigned) != confirmed:
            raise WorkflowError("Assign every confirmed audit finding to exactly one repair ticket.")
        if any(cycle["finding_attempts"].get(identifier, 0) >= 3 for identifier in confirmed):
            self.data.update(budget_exhausted="ticket_attempts", requires_user_resolution=True)
            self.save()
            raise WorkflowError("Audit finding attempts exhausted; a new ticket cannot reset its allowance.")
        updated = copy.deepcopy(self.data)
        plan = updated["plan"]
        known = {ticket["path"]: ticket for ticket in plan["tickets"]}
        edits = {}
        reserved = {self.spec, self.record, *(item["path"] for item in self.data["audits"])}
        for change in changes:
            name = change["path"]
            path = relative_file(self.repo, name)
            if (name in reserved or name in edits
                    or not change.get("finding_ids") or not change.get("requirements")
                    or not set(change["requirements"]) <= set(plan["requirements"])):
                raise WorkflowError("Repair tickets need distinct paths, audit findings and approved PRD requirements.")
            if change.get("action") == "reopen":
                if name not in known or not updated["tickets"][name]["commit"]:
                    raise WorkflowError("Only a completed ticket in this plan can be reopened.")
                if status_text(path) != plan.get("finished_ticket", "closed"):
                    raise WorkflowError("Completed ticket status differs from the saved run.")
                before = path.read_bytes().decode("utf-8")
                after = re.sub(r"^Status: [^\r\n]+", lambda match: f"Status: {plan.get('ready_ticket', 'ready-for-agent')}",
                               before, count=1, flags=re.MULTILINE)
                record = updated["tickets"][name]
                if not record.get("completions"):
                    record["completions"] = [{
                        "commit": record["commit"], "attempt": record["attempts"],
                        "review_base": record.get("review_base"), "cycle": record.get("repair_cycle"),
                    }]
                record["commit"] = None
                record.pop("review_base", None)
            elif change.get("action") == "create":
                if name in known or path.exists() or git(self.repo, "ls-files", "-z", "--", name):
                    raise WorkflowError("New repair ticket would overwrite an existing file or planned ticket.")
                criteria = change.get("criteria", [])
                if (change.get("execution") != "AFK" or not criteria
                        or any(not isinstance(criterion, str) or not criterion.strip() for criterion in criteria)
                        or len(criteria) != len(set(criteria))
                        or change.get("kind", "behavior") not in {"behavior", "documentation"}
                        or (change.get("kind", "behavior") == "behavior" and not change.get("seams"))):
                    raise WorkflowError("New repair tickets need AFK criteria and approved testing boundaries.")
                after = change.get("content", "")
                if re.findall(r"^Status: ([^\r\n]*)\r?$", after, flags=re.MULTILINE) != [
                    plan.get("ready_ticket", "ready-for-agent"),
                ]:
                    raise WorkflowError("New repair ticket content needs exactly one ready Status line.")
                if not set(change.get("related_tickets", [])) <= set(known):
                    raise WorkflowError("Related repair tickets must identify existing planned work.")
                ticket = {key: copy.deepcopy(change[key]) for key in (
                    "path", "execution", "kind", "criteria", "seams", "blocked_by",
                    "requirements", "related_tickets",
                ) if key in change}
                plan["tickets"].append(ticket)
                known[name] = ticket
                record = {"attempts": 0, "commit": None, "preexisting": False, "findings": [],
                          "implementer": None, "history": []}
                updated["tickets"][name] = record
                before = None
            else:
                raise WorkflowError("Repair work must reopen a completed ticket or create a new one.")
            self.repair_allowance(record, cycle["number"])
            record["audit_findings"] = change["finding_ids"]
            if record["attempts"] >= record["attempt_limit"]:
                self.data.update(budget_exhausted="ticket_attempts", requires_user_resolution=True)
                self.save()
                raise WorkflowError("Ticket repair attempts exhausted in this allowance.")
            record["findings"] = [finding for finding in audit["report"]["blocking_findings"]
                                  if finding["id"] in change["finding_ids"]]
            audit_link = Path(os.path.relpath(self.repo / audit["path"], path.parent)).as_posix()
            newline = "\r\n" if "\r\n" in after else "\n"
            after += (
                f"\n## Audit repair {audit['number']}\n\n"
                f"Audit: [{audit['path']}]({audit_link})\n"
                f"Findings: {', '.join(change['finding_ids'])}\n"
                f"Requirements: {', '.join(change['requirements'])}\n"
            ).replace("\n", newline)
            edits[name] = {"before": before, "after": after}
        validate_graph(plan["tickets"])
        changed = git_paths(self.repo, "diff", "--name-only", "HEAD")
        changed.update(git_paths(self.repo, "diff", "--cached", "--name-only", "HEAD"))
        changed.update(git_paths(self.repo, "ls-files", "--others", "--exclude-standard"))
        if changed - {self.record}:
            raise WorkflowError("Audit repair planning requires the unchanged audited checkout.")
        updated["audit_cycles"][-1]["rounds"].append({
            "audit_number": audit["number"], "plan": copy.deepcopy(report), "commit": None,
        })
        previous = status_text(relative_file(self.repo, self.spec))
        updated.update(
            phase="committing", current=None, review=None, implementation=None,
            transaction={
                "kind": "repair-plan", "path": self.spec, "old_status": previous, "new_status": previous,
                "parent": self.data["head"], "message": f"Plan audit repairs for {Path(self.spec).stem}",
                "paths": [self.record, *edits], "file_edits": edits, "status_restored": True,
                "before_status_snapshot": snapshot(self.repo, [self.record, *edits], include_index=False),
                "target_phase": "ready",
            },
        )
        updated.pop("budget_exhausted", None)
        updated.pop("requires_user_resolution", None)
        self.data = updated
        self.save()
        return self.reconcile_commit()

    def continue_audit(self, report):
        self.ensure({"audit-blocked", "blocked", "rework"}, checkpoint=True)
        self.require_handoff(report)
        cycle = self.data["audit_cycles"][-1]
        current = self.data["current"]
        exhausted = self.data.get("budget_exhausted")
        if current and self.attempts_remaining(current) <= 0:
            exhausted = "ticket_attempts"
        if self.data["phase"] == "audit-blocked" and len(cycle["rounds"]) >= cycle["round_limit"]:
            exhausted = "audit_rounds"
        if (report.get("cycle") != cycle["number"] or not report.get("user_authorization")
                or not exhausted or not self.data["audits"]
                or self.data["audits"][-1]["report"]["verdict"] == "PASS"):
            raise WorkflowError("An exhausted audit allowance needs fresh, explicit user continuation for this cycle.")
        if current and not self.data["tickets"][current].get("repair_cycle"):
            raise WorkflowError("This blocker belongs to initial implementation, not audit repairs.")
        if current:
            record = self.data["tickets"][current]
            attempt = record["history"][-1]
            implementation = attempt.get("implementation") or {}
            reviews = attempt.get("reviews", [])
            adjudication = record.get("adjudication", {}).get("decision") or {}
            if ((implementation.get("outcome") == "BLOCKED"
                 or (reviews and reviews[-1].get("verdict") == "BLOCKED")
                 or adjudication.get("decision") == "BLOCKED") and not report.get("blocker_resolution")):
                raise WorkflowError("Record how the non-budget blocker was resolved before continuing repairs.")
        updated = copy.deepcopy(self.data)
        renewed = audit_cycle(cycle["number"] + 1, copy.deepcopy(report), cycle["round_limit"])
        unfinished = [name for name, record in updated["tickets"].items() if not record["commit"]]
        for name in unfinished:
            record = updated["tickets"][name]
            if not record.get("audit_findings"):
                raise WorkflowError("Only remaining audit repair work receives a new allowance.")
            self.repair_allowance(record, renewed["number"])
        if unfinished:
            renewed["rounds"].append({
                "audit_number": updated["audits"][-1]["number"], "carried_tickets": unfinished,
                "evidence": report["evidence"],
            })
            updated["phase"] = "rework" if current else "ready"
        updated["audit_cycles"].append(renewed)
        updated.update(review=None, implementation=None)
        for name in ("budget_exhausted", "requires_user_resolution", "blocker"):
            updated.pop(name, None)
        self.data = updated
        self.save()

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
        if self.data.get("requires_user_resolution") or self.attempts_remaining(current) <= 0:
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
            if self.attempts_remaining(current) <= 0:
                raise WorkflowError("Attempt limit remains exhausted; resolution cannot reset it.")
        else:
            raise WorkflowError("Resolution can resume verification or an available repair.")
        self.data.setdefault("resolutions", []).append(resolution)
        self.data["phase"] = target
        self.data.pop("requires_user_resolution", None)
        self.data.pop("budget_exhausted", None)
        self.save()


def config_paths():
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    return [home / "implement-spec.config.toml"] + [
        home / "agents" / f"{role}.toml"
        for role in configuration.DEPTHS
    ]


def config_fingerprint():
    digest = hashlib.sha256()
    digest.update(json.dumps(configuration.expectations(), sort_keys=True).encode())
    for path in config_paths():
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def verify_configuration():
    expected = configuration.expectations()
    for path in config_paths():
        role = "outer" if path.name.endswith(".config.toml") else path.stem
        installed = tomllib.loads(path.read_text(encoding="utf-8"))
        if (installed.get("model"), installed.get("model_reasoning_effort")) != expected[role][:2]:
            raise WorkflowError("Installed profiles differ from settings.toml. Run scripts/install.py.")


def session_metadata(identifier):
    if not identifier or not re.fullmatch(r"[A-Za-z0-9-]+", identifier):
        raise WorkflowError("Missing or invalid Codex session identifier.")
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"
    for path in home.rglob(f"*{identifier}.jsonl"):
        with path.open(encoding="utf-8") as stream:
            event = json.loads(next(stream))
        if event.get("type") == "session_meta" and event["payload"].get("id") == identifier:
            return event["payload"]
    raise WorkflowError("No native session metadata for the requested coordinator.")


def validate_coordinator(identifier, entry):
    session = session_metadata(identifier)
    source = session.get("source", {})
    spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
    if (spawn.get("parent_thread_id") != entry["outer_session"]
            or spawn.get("agent_role") != "implementation_coordinator"
            or spawn.get("depth") != 1
            or datetime.datetime.fromisoformat(session["timestamp"]).timestamp() < entry["admitted_at"]):
        raise WorkflowError("Only a fresh named coordinator belonging to the admitted owner may mutate the run.")


def runtime_version(executable=None):
    executable = executable if executable is not None else platform_support.resolve_codex()
    result = subprocess.run([str(executable), "--version"], check=True, capture_output=True,
                            text=True, encoding="utf-8")
    return result.stdout.strip()


def enforced_config_arguments(include_outer_model=True):
    verify_configuration()
    config = tomllib.loads(config_paths()[0].read_text(encoding="utf-8"))
    values = {
        "agents.max_depth": config["agents"]["max_depth"],
    }
    if include_outer_model:
        values.update(model=config["model"], model_reasoning_effort=config["model_reasoning_effort"])
    for path in config_paths()[1:]:
        values[f"agents.{path.stem}.config_file"] = str(path)
    return [part for key, value in values.items() for part in ("-c", f"{key}={json.dumps(value)}")]


def configuration_status():
    verify_configuration()
    executable = platform_support.resolve_codex()
    return {
        "runtime": runtime_version(executable),
        "codex_executable": str(executable),
        "config_fingerprint": config_fingerprint(),
        "checks": {"installed_models": True},
        "scope": "Local configuration only. No agents or model calls are started.",
    }


def verify_checkout_entry(repo, spec):
    spec = repository_path(spec)
    locked = False
    try:
        with exclusive(git_home(repo) / "launch.lock"):
            pass
    except LockContended:
        locked = True
    if not locked:
        raise WorkflowError("No active checkout lock. Start the workflow entry before changing run state.")
    path = git_home(repo) / "entry.json"
    if path.exists():
        entry = json.loads(path.read_text(encoding="utf-8"))
        if (entry.get("phase") != "admitted" or entry.get("release")
                or entry.get("spec") != spec
                or entry.get("branch") != git(repo, "branch", "--show-current")
                or entry.get("runtime") != runtime_version(entry["codex_executable"])
                or entry.get("config_fingerprint") != config_fingerprint()):
            raise WorkflowError("Current-session admission is missing or stale. Stop before ticket work.")
        verify_configuration()
        caller = os.environ.get("CODEX_THREAD_ID")
        if not caller or caller not in {entry["outer_session"], entry.get("coordinator")}:
            raise WorkflowError("Caller is not the admitted owner or its registered coordinator.")
        if caller != entry["outer_session"]:
            validate_coordinator(caller, entry)
    elif os.environ.get("IMPLEMENT_SPEC_LAUNCH") == "1":
        verify_configuration()
    else:
        raise WorkflowError("Checkout lock is not attached to this workflow entry.")


def launch(repo, spec, branch=None, resume=False):
    spec = repository_path(spec)
    verify_configuration()
    executable = platform_support.resolve_codex()
    version = runtime_version(executable)
    with exclusive(git_home(repo) / "launch.lock") as descriptor:
        if (git_home(repo) / "entry.json").exists():
            raise WorkflowError("An interrupted current-session entry needs entry.py recover before launching.")
        command = [str(executable), "--no-daemon", "--profile", "implement-spec", "--approve-for-me", "-C", str(repo)]
        command.extend(enforced_config_arguments())
        attached = ("You are already the outer session opened by the dedicated launcher. "
                    "The parent holds the checkout lock; IMPLEMENT_SPEC_LAUNCH=1. "
                    f"Codex executable: {executable}; version: {version}. "
                    "Do not run entry.py start or launch another outer. ")
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
            prompt = attached + "Resume the approved $implement-spec-single-worker workflow. Reconcile state and confirm old workers are inactive before continuing. " + json.dumps({"spec": spec})
            command.extend(["resume", run.data["outer_session"], prompt])
        else:
            selected = choose_branch(repo, spec, branch)
            run = Run(repo, spec)
            if run.data:
                raise WorkflowError("Run already exists on this branch. Use launch --resume.")
            prompt = attached + "Use $implement-spec-single-worker to execute the approved AFK workflow. Read the skill before acting. " + json.dumps({"spec": spec, "branch": selected})
            command.append(prompt)
        return subprocess.call(command, pass_fds=(descriptor,),
                               env=dict(os.environ, IMPLEMENT_SPEC_LAUNCH="1", IMPLEMENT_SPEC_CODEX=str(executable)))


def main():
    parser = argparse.ArgumentParser(description="Guard the sequential Codex implementation workflow.")
    parser.add_argument("action", choices=[
        "launch", "prepare", "init", "status", "snapshot", "begin", "implemented",
        "reviewed", "dispute", "adjudicate", "commit", "finish", "checkpoint",
        "reconcile-commit", "resolve", "invalidate", "doctor", "repair-audit", "continue-audit",
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
            print(json.dumps(configuration_status(), indent=2))
            return 0
        repo = Path(git(arguments.repo, "rev-parse", "--show-toplevel"))
        if not arguments.spec:
            raise WorkflowError("Provide the repository-relative PRD path.")
        if arguments.action == "launch":
            return launch(repo, arguments.spec, arguments.branch, arguments.resume)
        if arguments.action == "prepare":
            verify_checkout_entry(repo, arguments.spec)
            verify_configuration()
            print(choose_branch(repo, arguments.spec, arguments.branch))
            return 0
        run = Run(repo, arguments.spec)
        if arguments.action in {"status", "snapshot"}:
            value = snapshot(repo, [run.record]) if arguments.action == "snapshot" else run.data
            print(json.dumps(value, indent=2))
            return 0
        verify_checkout_entry(repo, arguments.spec)
        with exclusive(git_home(repo) / "state.lock"):
            run = Run(repo, arguments.spec)
            report = json.loads(Path(arguments.report).read_text(encoding="utf-8")) if arguments.report else None
            if arguments.action == "init":
                run.create(json.loads(Path(arguments.plan).read_text(encoding="utf-8")))
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
            elif arguments.action == "repair-audit":
                print(run.repair_audit(report))
            elif arguments.action == "continue-audit":
                run.continue_audit(report)
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
    except (WorkflowError, platform_support.LockError, platform_support.ExecutableError,
            OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
