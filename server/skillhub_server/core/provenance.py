"""Recorded provenance for library skills that are not git checkouts.

Skills copied out of a bigger upstream repository carry no origin of their
own, so upstream-movement checks need a mapping you provide. Point
SKILLHUB_PROVENANCE_FILE at a JSON object:

    {
      "some-family": {
        "origin": "https://github.com/org/repo",
        "kind": "catalog",             // catalog | installer
        "confidence": "confirmed",     // confirmed | inferred
        "prefix": "",                  // local name prefix to strip, if any
        "evidence": "how this mapping was established"
      }
    }

A key matches a skill id's first path segment ("family/skill"), or the whole
id for top-level skills. kind=catalog: the hub reports upstream movement and
leaves syncing to you. kind=installer: the skill's own installer CLI owns
updates and the hub only labels it. Without the file, every non-git skill is
reported as origin-unknown — which is the honest default.
"""
import json
import os

from .config import settings

_cache: dict | None = None


def _families() -> dict:
    global _cache
    if _cache is None:
        _cache = {}
        f = settings.provenance_file
        if f and os.path.isfile(f):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    _cache = data
            except (OSError, ValueError):
                _cache = {}
    return _cache


def lookup(skill_id: str):
    """(origin, kind, confidence, subpath, evidence) or None."""
    fam = _families()
    for key in (skill_id.split("/")[0], skill_id):
        rec = fam.get(key)
        if rec:
            prefix = rec.get("prefix", "")
            local = skill_id.split("/")[-1]
            sub = local[len(prefix):] if prefix and local.startswith(prefix) else local
            return (rec.get("origin", ""), rec.get("kind", "catalog"),
                    rec.get("confidence", "inferred"), sub,
                    rec.get("evidence", ""))
    return None
