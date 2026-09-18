"""Runtime configuration, overridable via environment variables.

Variables are named SKILLMGMNT_*. The former SKILLHUB_* names still
work and are deprecated; see `_env` below.

SKILLMGMNT_LIBRARY_ROOT   the skills library directory (the one required setting).
                        The hub scans it recursively for directories containing
                        a SKILL.md — no index file or particular layout needed.
SKILLMGMNT_LIBRARY_INDEX  OPTIONAL: path to a pre-built index JSON
                        ([{"id","name","description","source"}, ...]). When set
                        and present it is used instead of scanning, and the hub
                        re-syncs whenever the file's mtime changes. Useful when
                        an external tool already maintains a catalog.
SKILLMGMNT_LIBRARY_SUBDIRS
                        OPTIONAL, comma-separated: restrict skill lookup to
                        these first-level subdirectories (e.g. "vendored,own").
                        Unset = the whole library root.
SKILLMGMNT_INSTALLER_SUBDIR
                        OPTIONAL: one subdirectory whose skills are managed by
                        their own installer CLI — the hub reports them but never
                        suggests updating them itself.
SKILLMGMNT_ENTITY_WHITELIST
                        OPTIONAL, comma-separated "agent:entry_name" pairs that
                        are legitimately real directories inside tool entry dirs
                        (not stray copies) and should not be flagged.
SKILLMGMNT_PROVENANCE_FILE
                        OPTIONAL: JSON file mapping skill families to upstream
                        repos for the update checker — see core/provenance.py
                        for the schema.
SKILLMGMNT_LIBRARY_DISPLAY_ROOT
                        library path as the USER sees it. The hub may see the
                        library at its own mount point (/library in Docker),
                        which is useless in a command someone pastes into their
                        own terminal — copyable commands use this instead.
SKILLMGMNT_SELF_REPORT    "auto" (default) | "1" | "0". When on, the server runs
                        the bundled reporter against itself every 15 minutes —
                        so a single-machine install needs no launchd/cron at
                        all. "auto" = on when the reporter script is present
                        and the server is NOT inside a container (a container
                        scanning its own $HOME would observe nothing useful).
                        Multi-machine setups keep per-machine reporters and
                        can leave this on for the hub machine itself.
SKILLMGMNT_DB             SQLite database path
SKILLMGMNT_STATIC         built web SPA dir served at /
SKILLMGMNT_HOST / SKILLMGMNT_PORT
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # server/


def _env(key: str, default: str) -> str:
    """Read `SKILLMGMNT_<key>`, falling back to the old `SKILLHUB_<key>`.

    The project was renamed after people had already put the old names into
    compose files and shell profiles. Dropping them would break those installs
    for a cosmetic reason, so the old prefix keeps working and is documented as
    deprecated. Remove the fallback only in a release that says it is doing so.
    """
    for prefix in ("SKILLMGMNT_", "SKILLHUB_"):
        v = os.environ.get(prefix + key)
        if v is not None:
            return v
    return default


def legacy_env_in_use() -> list[str]:
    """Old-prefix variables that are actually set, for a startup warning."""
    return sorted(k for k in os.environ
                  if k.startswith("SKILLHUB_")
                  and ("SKILLMGMNT_" + k[len("SKILLHUB_"):]) not in os.environ)


class Settings:
    db_path = _env("DB", str(BASE_DIR / "data" / "skillhub.db"))
    library_index = _env("LIBRARY_INDEX", "")
    library_root = _env("LIBRARY_ROOT", "")
    library_subdirs = _env("LIBRARY_SUBDIRS", "")
    installer_subdir = _env("INSTALLER_SUBDIR", "")
    entity_whitelist_raw = _env("ENTITY_WHITELIST", "")
    provenance_file = _env("PROVENANCE_FILE", "")
    library_display_root = _env("LIBRARY_DISPLAY_ROOT", "")
    static_dir = _env("STATIC", str(BASE_DIR.parent / "web" / "dist"))
    host = _env("HOST", "127.0.0.1")
    port = int(_env("PORT", "8787"))
    self_report = _env("SELF_REPORT", "auto")

    @property
    def reporter_script(self) -> str:
        p = BASE_DIR.parent / "reporter" / "skillhub_report.py"
        return str(p) if p.is_file() else ""

    def self_report_enabled(self) -> bool:
        if self.self_report == "1":
            return bool(self.reporter_script)
        if self.self_report == "0":
            return False
        # auto: single-machine source checkout, not a container
        return bool(self.reporter_script) and not os.path.exists("/.dockerenv")

    @property
    def library_root_path(self) -> str:
        if self.library_root:
            return self.library_root
        # legacy convenience: an index path implies its parent directory
        return str(Path(self.library_index).parent) if self.library_index else ""

    @property
    def library_display_path(self) -> str:
        return self.library_display_root or self.library_root_path

    def library_bases(self) -> list[str]:
        """Absolute directories a skill id is resolved under, in priority order.

        With SKILLMGMNT_LIBRARY_SUBDIRS unset the library root itself is the one
        base and a skill id is simply the directory's path relative to it —
        no layout convention is imposed."""
        root = self.library_root_path
        if not root:
            return []
        subs = [s.strip() for s in self.library_subdirs.split(",") if s.strip()]
        return [os.path.join(root, s) for s in subs] if subs else [root]

    def skill_dir(self, skill_id: str) -> str | None:
        """Filesystem directory for a library skill id, or None."""
        for base in self.library_bases():
            p = os.path.join(base, *skill_id.split("/"))
            if os.path.isdir(p):
                return p
        return None

    def entity_whitelist(self) -> set[tuple[str, str]]:
        out: set[tuple[str, str]] = set()
        for pair in self.entity_whitelist_raw.split(","):
            pair = pair.strip()
            if ":" in pair:
                agent, entry = pair.split(":", 1)
                out.add((agent.strip(), entry.strip()))
        return out


settings = Settings()
