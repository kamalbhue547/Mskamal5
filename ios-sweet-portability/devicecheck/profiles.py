"""Load a small, reviewable set of evidence-backed reference profiles."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class ProfileError(Exception):
    """Profile data is missing or invalid; never treat it as a match."""


@dataclass(frozen=True)
class Evidence:
    subject: str
    url: str
    note: str


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    support_level: str
    codename: str | None
    manufacturer: str | None
    model: str | None
    soc_labels: tuple[str, ...]
    cpu_arch: str | None
    evidence: tuple[Evidence, ...]


PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"
LEVELS = {"upstream_reference", "hardware_verified", "research_only"}
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


def _text(value: object, name: str, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ProfileError(f"{name} must be a non-empty string of at most {limit} characters")
    value = value.strip()
    if not value.isprintable():
        raise ProfileError(f"{name} must contain printable characters only")
    return value


def _parse_profile(data: object, path: Path) -> Profile:
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ProfileError("schema_version must be the integer 1")
    profile_id = _text(data.get("id"), "id", 64)
    if not ID_PATTERN.fullmatch(profile_id) or path.stem != profile_id:
        raise ProfileError("id must match its lowercase JSON filename")
    name = _text(data.get("name"), "name")
    level = _text(data.get("support_level"), "support_level")
    if level not in LEVELS:
        raise ProfileError(f"support_level must be one of {', '.join(sorted(LEVELS))}")
    identity = data.get("identity")
    if not isinstance(identity, dict):
        raise ProfileError("identity must be an object")
    def identity_text(key: str) -> str | None:
        value = identity.get(key)
        if value is None and level == "research_only":
            return None
        return _text(value, f"identity.{key}")

    codename = identity_text("codename")
    manufacturer = identity_text("manufacturer")
    model = identity_text("model")
    labels = identity.get("soc_labels")
    if not isinstance(labels, list) or (not labels and level != "research_only"):
        raise ProfileError("identity.soc_labels must be a list (non-empty for a supported reference)")
    soc_labels = tuple(_text(label, "identity.soc_labels entry") for label in labels)
    if len({label.casefold() for label in soc_labels}) != len(soc_labels):
        raise ProfileError("identity.soc_labels must not contain duplicates")

    platform = data.get("platform", {})
    if not isinstance(platform, dict):
        raise ProfileError("platform must be an object")
    cpu_arch = platform.get("cpu_arch")
    if cpu_arch is not None:
        cpu_arch = _text(cpu_arch, "platform.cpu_arch")

    raw_evidence = data.get("evidence")
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise ProfileError("at least one evidence record is required")
    evidence = []
    for item in raw_evidence:
        if not isinstance(item, dict):
            raise ProfileError("each evidence record must be an object")
        url = _text(item.get("url"), "evidence.url", 2048)
        try:
            parts = urlparse(url)
            # Accessing .port validates that a supplied port is numeric and in range.
            _ = parts.port
            valid_url = (parts.scheme == "https" and bool(parts.hostname)
                         and parts.username is None and parts.password is None
                         and not any(char.isspace() for char in url))
        except ValueError as exc:
            raise ProfileError("evidence URLs must be valid absolute HTTPS URLs without credentials") from exc
        if not valid_url:
            raise ProfileError("evidence URLs must be valid absolute HTTPS URLs without credentials")
        evidence.append(Evidence(_text(item.get("subject"), "evidence.subject"), url,
                                 _text(item.get("note"), "evidence.note", 500)))
    return Profile(profile_id, name, level, codename, manufacturer, model, soc_labels, cpu_arch, tuple(evidence))


def load_profiles(directory: Path = PROFILE_DIR) -> tuple[Profile, ...]:
    """Fail closed on missing, malformed, duplicate or unreviewed-as-data files.

    Schema validation cannot establish that a source is truthful or that a port
    exists. Human review of the evidence and physical tests are still required.
    """
    if not directory.is_dir():
        raise ProfileError(f"profile directory is unavailable: {directory}")
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ProfileError(f"no device profiles found in {directory}")
    profiles = []
    for path in paths:
        try:
            with path.open(encoding="utf-8") as stream:
                data = json.load(stream)
            profiles.append(_parse_profile(data, path))
        except (OSError, UnicodeError, json.JSONDecodeError, ProfileError) as exc:
            raise ProfileError(f"invalid profile {path.name}: {exc}") from exc
    if len({p.id for p in profiles}) != len(profiles):
        raise ProfileError("duplicate profile ids")
    return tuple(profiles)
