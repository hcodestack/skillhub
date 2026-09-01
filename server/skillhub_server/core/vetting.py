"""Deterministic safety review of skill contents.

A skill is code someone else wrote that your agent will run with your
permissions. Half this library ships executable scripts, most of it pulled from
third-party repos, and none of it was ever reviewed.

The checklist is a deterministic red-flag review: regex rules over the files
a skill ships, needing no model, no key, no bill and no network round trip —
so it can run on every skill on every sync.

Findings are signals, not verdicts: `curl` in a web-fetching skill is the point
of the skill. Severity says how much a human should care, and every rule carries
the reason so a reader can dismiss it knowingly.
"""
import os
import re

# (id, category, severity, description, pattern, exclude, scope)
#
# scope decides which files a rule reads:
#   "any"  — instructions the agent will act on, so SKILL.md counts as much as
#            a script: "curl | bash" written in prose is still an instruction
#   "code" — a property of executed code. A `.exec(` or `atob()` inside an API
#            example in reference docs describes someone else's API, not what
#            this skill does, and matching it only produces noise.
RULES: list[tuple[str, str, str, str, str, str, str]] = [
    ("AGENT_MEMORY", "vet.cat.credentials", "high",
     "vet.rule.AGENT_MEMORY",
     r"MEMORY\.md|USER\.md|SOUL\.md|IDENTITY\.md|\.claude/memory|\.claude/settings"
     r"|\.codex/auth|auth\.json",
     r"skillhub|本项目|reference/", "any"),
    ("CREDENTIAL_PROMPT", "vet.cat.credentials", "high",
     "vet.rule.CREDENTIAL_PROMPT",
     r"(?<![A-Za-z0-9_])input\s*\(.*(?:password|token|secret|credential)"
     r"|getpass\.getpass"
     r"|prompt[^\n]{0,40}\b(?:enter|provide|paste)\b[^\n]{0,40}"
     r"(?:api[ _-]?key|token|password|secret)",
     r"", "any"),
    ("SECRET_PATHS", "vet.cat.credentials", "high",
     "vet.rule.SECRET_PATHS",
     r"~/\.ssh|~/\.aws|\$HOME/\.ssh|\$HOME/\.aws|\.aws/credentials|id_rsa|id_ed25519",
     r"", "any"),
    ("BROWSER_SESSION", "vet.cat.credentials", "high",
     "vet.rule.BROWSER_SESSION",
     r"cookies\.sqlite|\.mozilla/firefox|Chrome/(?:Default|Profile)"
     r"|browser.{0,12}cookie",
     r"cookie banner|cookie 弹窗|同意.{0,4}cookie", "any"),
    ("IP_ENDPOINT", "vet.cat.exfiltration", "high",
     "vet.rule.IP_ENDPOINT",
     r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
     r"127\.0\.0\.1|0\.0\.0\.0|192\.168\.|10\.\d|172\.(?:1[6-9]|2\d|3[01])\.", "any"),
    ("REMOTE_EXEC", "vet.cat.execution", "high",
     "vet.rule.REMOTE_EXEC",
     r"curl[^\n|]{0,120}\|\s*(?:ba)?sh|wget[^\n|]{0,120}\|\s*(?:ba)?sh"
     r"|curl[^\n]{0,120}\|\s*python",
     r"", "any"),
    ("EVAL_EXEC", "vet.cat.execution", "medium",
     "vet.rule.EVAL_EXEC",
     r"(?<![.\w])eval\s*\(|(?<![.\w])exec\s*\(|new Function\s*\(",
     r"eval\s*\(\s*['\"]", "code"),
    ("SUDO", "vet.cat.execution", "medium",
     "vet.rule.SUDO",
     r"\bsudo\s+\w|osascript .{0,40}administrator privileges",
     r"", "any"),
    ("SYSTEM_WRITE", "vet.cat.execution", "medium",
     "vet.rule.SYSTEM_WRITE",
     r"(?:>|>>|tee|write|open)\s*\(?\s*['\"]?/(?:etc|usr|var|opt)/",
     r"", "code"),
    # exclusions here all assert the destination is *not* external. `${...}`
    # and `{{...}}` used to be excluded too, as documentation placeholders —
    # but this rule is scope="code" and never reads a .md, and in code those
    # are ordinary interpolation building a real URL (`fetch(`${host}/batch/`)`).
    # They mark the destination unknown, and unknown is not evidence of safety.
    # Dropping them surfaced only real findings in testing (e.g. an analytics
    # POST built with template-literal URLs that the exclusion had hidden).
    ("DATA_POST", "vet.cat.exfiltration", "medium",
     "vet.rule.DATA_POST",
     r"curl[^\n]{0,80}(?:--data|-d\s)|wget[^\n]{0,80}--post-data"
     r"|requests\.post\(|fetch\([^\n]{0,60}method:\s*['\"]POST",
     r"localhost|127\.0\.0\.1|api\.github\.com", "code"),
    ("UNPINNED_INSTALL", "vet.cat.exfiltration", "low",
     "vet.rule.UNPINNED_INSTALL",
     r"pip3?\s+install\s+(?!-r\s|-e\s)[a-zA-Z]|npm\s+install\s+-g\s|gem\s+install\s+",
     r"requirements\.txt|package\.json", "any"),
    ("OBFUSCATED", "vet.cat.execution", "medium",
     "vet.rule.OBFUSCATED",
     r"base64\s+(?:-d|--decode)|b64decode|atob\s*\(",
     r"encode|-w\s*0|base64 编码", "code"),
]

# rule id -> category message key, for callers that localise a cached finding
RULE_CATEGORY: dict[str, str] = {r[0]: r[1] for r in RULES}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

SCAN_EXT = {".md", ".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts",
            ".rb", ".pl", ".ps1", ".yaml", ".yml", ".toml", ".json"}
DOC_EXT = {".md", ".markdown", ".txt"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "site-packages",
             "__pycache__", "dist", "build",
             "test", "tests", "__tests__", "fixtures", "testdata"}
# fixtures carry fake IPs and fake keys on purpose; matching them says nothing
# about what the skill does. Vendored dependency trees say nothing either, and
# they are large enough to matter: a skill shipping a `venv/` can spend the
# whole MAX_FILES budget on site-packages and get flagged for code that
# belongs to its dependencies. A misattributed finding is worse than a noisy
# one: it names a skill for what a library it bundles does.
SKIP_FILE_RE = re.compile(r"(?:\.|-|_)(?:test|spec|fixture)s?\.", re.I)
MAX_FILE = 400_000
MAX_FILES = 60
WINDOW_LINES = 3   # how many consecutive lines pass 2 joins before matching


def _compiled():
    # every rule is case-insensitive: Python 3.11+ rejects an inline (?i) that
    # is not at the very start, and per-rule casing carried no meaning here
    out = []
    for rid, cat, sev, desc, pat, exc, scope in RULES:
        out.append((rid, cat, sev, desc, re.compile(pat, re.I),
                    re.compile(exc, re.I) if exc else None, scope))
    return out


_RULES = _compiled()


def scan_dir(path: str) -> list[dict]:
    """Findings for one skill directory: one entry per rule that matched,
    with the file and line that triggered it so a human can judge it."""
    hits: dict[str, dict] = {}
    seen_files = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() not in SCAN_EXT:
                continue
            if SKIP_FILE_RE.search(fn):
                continue
            if seen_files >= MAX_FILES:
                break
            seen_files += 1
            fp = os.path.join(root, fn)
            try:
                if os.path.getsize(fp) > MAX_FILE:
                    continue
                with open(fp, encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            rel = os.path.relpath(fp, path)
            is_doc = os.path.splitext(fn)[1].lower() in DOC_EXT
            code: list[tuple[int, str, str]] = []
            for i, line in enumerate(lines, 1):
                if len(line) > 2000:
                    line = line[:2000]
                stripped = line.strip()
                if stripped.startswith(("#", "//", "*")) and "curl" not in stripped:
                    continue          # a commented-out line is not behaviour
                code.append((i, line, stripped))

            def record(rid, cat, sev, desc, lineno, excerpt):
                hits[rid] = {
                    "rule": rid, "category": cat, "severity": sev,
                    "description": desc, "file": rel, "line": lineno,
                    "excerpt": excerpt[:160],
                }

            # pass 1 — one line at a time, which is what gives a finding its
            # exact line number
            for lineno, line, stripped in code:
                for rid, cat, sev, desc, rx, exc, scope in _RULES:
                    if rid in hits or (scope == "code" and is_doc):
                        continue
                    if rx.search(line) and not (exc and exc.search(line)):
                        record(rid, cat, sev, desc, lineno, stripped)

            # pass 2 — the same rules over a joined window, for what a
            # line-at-a-time reader is blind to: the call is split across lines.
            #     await fetch(`${host}/batch/`, {   ← no `method`
            #       method: "POST",                   ← no `fetch`
            # neither line matches DATA_POST — real telemetry has shipped in
            # exactly this shape and gone unreported. Lines are joined with a
            # space, not a newline, because the
            # patterns bound their spans with [^\n] — a newline would still cut
            # them. Only rules pass 1 left unmatched are tried, so this can add
            # findings but never move or drop an existing one.
            for start in range(len(code)):
                window = code[start:start + WINDOW_LINES]
                if len(window) < 2:
                    break
                joined = " ".join(s for _, _, s in window)
                for rid, cat, sev, desc, rx, exc, scope in _RULES:
                    if rid in hits or (scope == "code" and is_doc):
                        continue
                    if rx.search(joined) and not (exc and exc.search(joined)):
                        record(rid, cat, sev, desc, window[0][0], joined)
    return sorted(hits.values(), key=lambda h: SEVERITY_ORDER[h["severity"]])


def skill_dir(library_root: str, skill_id: str) -> str | None:
    """Directory for a library skill id (layout comes from configuration)."""
    from .config import settings
    return settings.skill_dir(skill_id)
