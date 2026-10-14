from pathlib import Path
import platform_support
import tomllib


SETTINGS = Path(__file__).resolve().parents[1] / "settings.toml"
DEPTHS = {
    "implementation_coordinator": 1,
    "ticket_implementer": 2,
    "ticket_verifier": 2,
    "spec_auditor": 1,
}


def load(path=None):
    settings = tomllib.loads(Path(path or SETTINGS).read_text(encoding="utf-8"))
    if settings.get("default_session") not in {"current", "new"}:
        raise ValueError("default_session must be current or new.")
    rounds = settings.setdefault("audit_repair_rounds", 2)
    if type(rounds) is not int or rounds < 1:
        raise ValueError("audit_repair_rounds must be a positive integer.")
    if set(settings.get("roles", {})) != set(DEPTHS):
        raise ValueError("Settings must define exactly the four workflow roles.")
    for role in [settings.get("launcher", {}), *settings["roles"].values()]:
        if any(not isinstance(role.get(key), str) or not role[key].strip()
               for key in ("model", "effort")):
            raise ValueError("Every role and the launcher need a nonempty model and effort.")
    return settings


def expectations(path=None):
    settings = load(path)
    roles = {"outer": (settings["launcher"]["model"], settings["launcher"]["effort"], 0)}
    roles.update({
        name: (settings["roles"][name]["model"], settings["roles"][name]["effort"], depth)
        for name, depth in DEPTHS.items()
    })
    return roles
