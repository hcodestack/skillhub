"""Which MCP servers each tool on this machine is configured to talk to.

Skills can now be served over MCP (SEP-2640), which means a tool can load a
skill that never touches the filesystem: the extension requires hosts to keep
their cache out of every skill-discovery path. A scanner that only walks entry
directories is blind to those skills by design. This adapter recovers the one
thing the client side still knows — which servers a tool is pointed at — and
leaves enumerating their skills to the hub.

Boundaries, deliberately narrow:

  * Credentials are never read. A config's `env` or `headers` block is reduced
    to a single boolean. The values never leave this function.
  * Endpoint URLs are stripped of query and fragment before being recorded,
    because tokens are routinely passed that way.
  * A stdio server's command is reduced to its program name. Arguments carry
    secrets often enough that keeping them is not worth the detail.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

try:                                            # 3.11+, and the reporter requires it
    import tomllib
except ModuleNotFoundError:                     # pragma: no cover
    tomllib = None

HOME = Path.home()

# (agent key, path relative to $HOME, shape). Shapes:
#   "mcpServers"  — {"mcpServers": {name: cfg}}, the de-facto standard
#   "claude"      — same, plus a per-project map under "projects"
#   "servers"     — {"servers": {name: cfg}}, VS Code's spelling
#   "toml"        — [mcp_servers.<name>] tables
GLOBAL_CONFIGS = [
    ("claude-code", ".claude.json", "claude"),
    ("codex", ".codex/config.toml", "toml"),
    ("cursor", ".cursor/mcp.json", "mcpServers"),
    ("gemini-cli", ".gemini/settings.json", "mcpServers"),
    ("codebuddy", ".codebuddy/mcp.json", "mcpServers"),
    ("qoder", ".qoder/mcp.json", "mcpServers"),
    ("trae", ".trae/mcp.json", "mcpServers"),
    ("windsurf", ".codeium/windsurf/mcp_config.json", "mcpServers"),
    ("cline", ".cline/mcp.json", "mcpServers"),
    ("github-copilot", ".vscode/mcp.json", "servers"),
    ("opencode", ".config/opencode/mcp.json", "mcpServers"),
    ("amp", ".config/amp/mcp.json", "mcpServers"),
]

# Project-level files, relative to a project root, with the tool that reads them.
# `.mcp.json` is read by several tools; it is attributed to the shared key the
# inventory scanner already uses for directories more than one tool reads.
PROJECT_CONFIGS = [
    ("shared:.mcp.json", ".mcp.json", "mcpServers"),
    ("github-copilot", ".vscode/mcp.json", "servers"),
    ("cursor", ".cursor/mcp.json", "mcpServers"),
]


def _safe_endpoint(url: str) -> str:
    """URL without query or fragment. Tokens ride in both."""
    try:
        p = urlsplit(url)
    except ValueError:
        return ""
    if not p.scheme:
        return ""
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def _describe(name: str, cfg: dict) -> dict | None:
    """One server config reduced to what is safe to report."""
    if not isinstance(cfg, dict):
        return None
    url = cfg.get("url") or cfg.get("serverUrl") or ""
    has_auth = bool(cfg.get("env") or cfg.get("headers") or cfg.get("authorization"))
    if url:
        endpoint = _safe_endpoint(str(url))
        if not endpoint:
            return None
        transport = str(cfg.get("type") or "http").lower()
        if transport not in ("http", "sse", "streamable-http"):
            transport = "http"
        return {"name": name, "transport": transport, "endpoint": endpoint,
                "has_auth": has_auth}
    command = cfg.get("command")
    if not command:
        return None
    # Program name only; args are dropped along with anything hiding in them.
    # Splitting on whitespace first would cut a path that contains a space,
    # which is how "/Applications/Some App/bin/x" became "stdio:Some".
    raw = str(command).strip()
    program = os.path.basename(raw) if "/" in raw else (raw.split()[0] if raw else "")
    return {"name": name, "transport": "stdio", "endpoint": f"stdio:{program}",
            "has_auth": has_auth}


def _from_map(servers, agent, scope, project_path) -> list[dict]:
    out = []
    for name, cfg in (servers or {}).items():
        d = _describe(str(name), cfg)
        if d:
            out.append({**d, "agent": agent, "scope": scope,
                        "project_path": project_path})
    return out


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _read_config(path: Path, shape: str, agent: str, scope: str,
                 project_path: str) -> list[dict]:
    if shape == "toml":
        if tomllib is None:
            return []
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return _from_map(data.get("mcp_servers"), agent, scope, project_path)

    data = _load_json(path)
    if not isinstance(data, dict):
        return []
    if shape == "servers":
        return _from_map(data.get("servers"), agent, scope, project_path)
    out = _from_map(data.get("mcpServers"), agent, scope, project_path)
    if shape == "claude":
        # Claude Code keeps per-project servers in one global file
        for proj, pd in (data.get("projects") or {}).items():
            if isinstance(pd, dict) and pd.get("mcpServers"):
                out += _from_map(pd["mcpServers"], agent, "project", str(proj))
    return out


def collect(project_roots: list[str] | None = None) -> list[dict]:
    """Every MCP server this machine's tools are configured to reach."""
    found: list[dict] = []
    for agent, rel, shape in GLOBAL_CONFIGS:
        p = HOME / rel
        if p.is_file():
            found += _read_config(p, shape, agent, "global", "")

    seen_roots = set()
    for root in project_roots or []:
        if not root or root in seen_roots:
            continue
        seen_roots.add(root)
        rp = Path(root)
        if not rp.is_dir():
            continue
        for agent, rel, shape in PROJECT_CONFIGS:
            p = rp / rel
            if p.is_file():
                found += _read_config(p, shape, agent, "project", root)

    # one row per (agent, scope, project, name); later reads win
    uniq: dict[tuple, dict] = {}
    for s in found:
        uniq[(s["agent"], s["scope"], s["project_path"], s["name"])] = s
    return list(uniq.values())
