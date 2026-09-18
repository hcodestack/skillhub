"""SQLite access. Single shared connection guarded by an RLock — the hub is a
single-user LAN service, write volume is tiny, and this keeps the stack
dependency-free (no ORM)."""
import sqlite3
import threading
from pathlib import Path

from .config import settings

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills(
  id          TEXT PRIMARY KEY,        -- library id, e.g. 'Anthropic/docx' or 'web-access'
  name        TEXT DEFAULT '',
  description TEXT DEFAULT '',
  source      TEXT DEFAULT '',         -- organized | self-made | installer
  category    TEXT DEFAULT '',         -- vendor prefix, derived
  tags        TEXT DEFAULT '[]',       -- domain tags, derived (JSON array)
  in_library  INTEGER DEFAULT 1,       -- 0 = disappeared from the index
  first_seen  TEXT DEFAULT '',
  last_seen   TEXT DEFAULT '',
  body_lines  INTEGER DEFAULT 0    -- SKILL.md length, refreshed on library sync
);

CREATE TABLE IF NOT EXISTS hosts(
  id             TEXT PRIMARY KEY,     -- hostname
  os             TEXT DEFAULT '',
  last_report_at TEXT DEFAULT '',
  agents_seen    TEXT DEFAULT '[]'     -- JSON: tools the reporter detected, entries or not
);

-- Where a skill is loaded: one row per (host, agent, scope, project, entry name).
CREATE TABLE IF NOT EXISTS installs(
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  host         TEXT NOT NULL,
  agent        TEXT NOT NULL,          -- claude-code | codex | workbuddy | ...
  scope        TEXT NOT NULL,          -- global | project
  project_path TEXT NOT NULL DEFAULT '',
  entry_name   TEXT NOT NULL,
  entry_path   TEXT DEFAULT '',
  link_type    TEXT DEFAULT '',        -- symlink | entity | broken | unrooted
  target_path  TEXT DEFAULT '',        -- realpath of symlink target
  skill_id     TEXT,                   -- resolved library id (NULL = unmanaged)
  shared_with  TEXT DEFAULT '',        -- other tools reading this same dir
  content_hash TEXT DEFAULT '',        -- entity dirs only; detects drift/dupes
  vcs          TEXT DEFAULT '',        -- entity only: vendored | untracked | loose
  skill_name   TEXT DEFAULT '',        -- SKILL.md frontmatter, for unmanaged
  skill_desc   TEXT DEFAULT '',
  first_seen   TEXT DEFAULT '',
  last_seen    TEXT DEFAULT '',
  active       INTEGER DEFAULT 1,
  UNIQUE(host, agent, scope, project_path, entry_name)
);
CREATE INDEX IF NOT EXISTS idx_inst_skill ON installs(skill_id);

CREATE TABLE IF NOT EXISTS usage_events(
  hash       TEXT PRIMARY KEY,         -- idempotency key
  host       TEXT DEFAULT '',
  agent      TEXT DEFAULT '',
  skill_key  TEXT NOT NULL,            -- raw name as invoked
  skill_id   TEXT,                     -- resolved library id (NULL = unresolved)
  project    TEXT DEFAULT '',
  session_id TEXT DEFAULT '',
  ts         TEXT NOT NULL,            -- ISO timestamp
  source     TEXT DEFAULT '',          -- transcript | usage-log | hook | ...
  extra      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ue_skill ON usage_events(skill_id, ts);
CREATE INDEX IF NOT EXISTS idx_ue_key ON usage_events(skill_key, ts);
CREATE INDEX IF NOT EXISTS idx_ue_ts ON usage_events(ts);

CREATE TABLE IF NOT EXISTS skill_sources(
  skill_id   TEXT PRIMARY KEY,      -- library id
  kind       TEXT DEFAULT '',       -- git | installer
  origin     TEXT DEFAULT '',       -- upstream repo url
  local_ref  TEXT DEFAULT '',       -- commit in the library
  remote_ref TEXT DEFAULT '',       -- upstream HEAD at checked_at
  path       TEXT DEFAULT '',
  checked_at INTEGER DEFAULT 0,
  last_error TEXT DEFAULT '',
  confidence TEXT DEFAULT '',      -- confirmed | inferred
  subpath    TEXT DEFAULT '',      -- path of this skill inside the upstream repo
  evidence   TEXT DEFAULT '',      -- how the origin was established
  baseline_ref TEXT DEFAULT ''     -- upstream HEAD when first recorded (catalog)
);

CREATE TABLE IF NOT EXISTS skill_vetting(
  skill_id      TEXT PRIMARY KEY,
  findings      TEXT DEFAULT '[]',   -- JSON: rule/category/severity/file/line
  top_severity  TEXT DEFAULT '',
  count         INTEGER DEFAULT 0,
  scanned_at    INTEGER DEFAULT 0
);

-- MCP servers, and the skills they serve (SEP-2640).
--
-- Skills served over MCP never land in a tool's skills directory: the
-- extension requires hosts to cache them outside every discovery path. They
-- are therefore not installs and do not belong in `installs`. What is worth
-- recording is a different shape — an endpoint that serves them, the tools
-- pointed at it, and what it currently offers.
CREATE TABLE IF NOT EXISTS mcp_endpoints(
  endpoint       TEXT PRIMARY KEY,   -- https://host/path, or stdio:<program>
  transport      TEXT DEFAULT '',    -- http | sse | stdio
  server_name    TEXT DEFAULT '',    -- serverInfo.name, self-reported
  server_title   TEXT DEFAULT '',
  server_version TEXT DEFAULT '',
  protocol       TEXT DEFAULT '',    -- negotiated protocol version
  skills_ext     INTEGER DEFAULT 0,  -- declares io.modelcontextprotocol/skills
  directory_read INTEGER DEFAULT 0,
  state          TEXT DEFAULT '',    -- served|empty|no-extension|auth|unreachable|declared
  detail         TEXT DEFAULT '',    -- one line; why, for states that need it
  skills_count   INTEGER DEFAULT 0,
  meta_tokens    INTEGER DEFAULT 0,  -- resident cost if a host lists them all
  probed_at      INTEGER DEFAULT 0
);

-- Which tool on which host points at which endpoint. Credentials are never
-- stored: `has_auth` is the whole of what the reporter may say about them.
CREATE TABLE IF NOT EXISTS mcp_declarations(
  host         TEXT NOT NULL,
  agent        TEXT NOT NULL,
  scope        TEXT NOT NULL,        -- global | project
  project_path TEXT NOT NULL DEFAULT '',
  name         TEXT NOT NULL,        -- the name the config gives it
  endpoint     TEXT NOT NULL,
  transport    TEXT DEFAULT '',
  has_auth     INTEGER DEFAULT 0,
  last_seen    TEXT DEFAULT '',
  active       INTEGER DEFAULT 1,
  UNIQUE(host, agent, scope, project_path, name)
);
CREATE INDEX IF NOT EXISTS idx_mcp_decl_ep ON mcp_declarations(endpoint);

CREATE TABLE IF NOT EXISTS mcp_skills(
  endpoint    TEXT NOT NULL,
  uri         TEXT NOT NULL,
  name        TEXT DEFAULT '',
  description TEXT DEFAULT '',
  frontmatter TEXT DEFAULT '{}',
  files       INTEGER DEFAULT 0,     -- -1 = resources is "dynamic"
  bytes       INTEGER DEFAULT 0,
  verifiable  TEXT DEFAULT '',       -- full | partial | dynamic
  digest      TEXT DEFAULT '',       -- SKILL.md digest, when the entry carries one
  seen_at     INTEGER DEFAULT 0,
  UNIQUE(endpoint, uri)
);
CREATE INDEX IF NOT EXISTS idx_mcp_skills_name ON mcp_skills(name);

CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);

-- Last run of each background job. Keyed by job name because only the most
-- recent run is kept: a history would need pruning and nobody would read it,
-- while what a reader needs is "did the last one work, and when".
-- finished_at = 0 means still running (or the process died mid-run).
CREATE TABLE IF NOT EXISTS job_runs(
  job         TEXT PRIMARY KEY,     -- library_sync | upstream_check | vetting_scan
  started_at  INTEGER NOT NULL,
  finished_at INTEGER DEFAULT 0,
  ok          INTEGER DEFAULT 0,
  detail      TEXT DEFAULT '',      -- one line of result, e.g. "241 扫描 / 71 命中"
  error       TEXT DEFAULT ''
);
"""


# columns added after the first release; applied to existing databases on open
MIGRATIONS = [
    ("installs", "shared_with", "TEXT DEFAULT ''"),
    ("installs", "content_hash", "TEXT DEFAULT ''"),
    ("installs", "skill_name", "TEXT DEFAULT ''"),
    ("installs", "skill_desc", "TEXT DEFAULT ''"),
    ("skill_sources", "confidence", "TEXT DEFAULT ''"),
    ("skill_sources", "subpath", "TEXT DEFAULT ''"),
    ("skill_sources", "evidence", "TEXT DEFAULT ''"),
    ("skill_sources", "baseline_ref", "TEXT DEFAULT ''"),
    ("skills", "body_lines", "INTEGER DEFAULT 0"),
    ("installs", "vcs", "TEXT DEFAULT ''"),
    ("hosts", "agents_seen", "TEXT DEFAULT '[]'"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, column, decl in MIGRATIONS:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    conn.commit()


def get_conn() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(settings.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            _migrate(conn)
            _conn = conn
        return _conn


def tx() -> threading.RLock:
    """Usage: with tx(): conn.execute(...); conn.commit()"""
    return _lock
