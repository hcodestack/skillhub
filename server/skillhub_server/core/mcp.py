"""A read-only SEP-2640 probe: what skills does this MCP server serve?

Skills served over MCP are invisible to a filesystem scanner on purpose — the
extension requires hosts to cache them outside every skill-discovery path. The
only way to see them is to ask the server, so this module speaks just enough
MCP to do that: `initialize`, then `skills/list`.

Three boundaries hold this to the project's read-only charter:

  * Only `initialize` and `skills/list` are ever sent. Both are read-only. No
    tool is called, no resource is read, no skill content is fetched.
  * stdio servers are never started. Spawning a server is running a command on
    someone's machine, which is not observation. They are reported as declared
    and unprobed, with the reason.
  * The probe is anonymous. Credentials in a user's MCP config are never read
    by the reporter and never sent by the hub; a server that wants auth is
    recorded as needing it, and left alone.
"""
import ipaddress
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

EXTENSION = "io.modelcontextprotocol/skills"
CLIENT_PROTOCOL = "2026-03-26"
TIMEOUT = 20
MAX_PAGES = 20          # a catalog may be paginated; bound the walk

# Per-skill protocol limits (SEP-2640). A skill over either is not guaranteed
# to be loadable by any conforming host.
MAX_FILES = 512
MAX_BYTES = 16 * 1024 * 1024


def _is_loopback(endpoint: str) -> bool:
    host = (urlsplit(endpoint).hostname or "").strip("[]")
    if not host:
        return False
    if host.lower() in ("localhost", "localhost.localdomain"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ProbeError(Exception):
    """Probe failed. `state` is the endpoint state to record."""

    def __init__(self, state: str, detail: str):
        super().__init__(detail)
        self.state = state
        self.detail = detail


def _rpc(url: str, method: str, params: dict | None, sid: str | None,
         rid: int, protocol: str) -> tuple[dict | None, str | None]:
    body: dict = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not method.startswith("notifications/"):
        body["id"] = rid
    headers = {
        "Content-Type": "application/json",
        # servers may answer either way; SSE is the streamable-HTTP default
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": protocol,
        "User-Agent": "skillhub-probe (read-only; initialize + skills/list)",
    }
    if sid:
        headers["Mcp-Session-Id"] = sid
    req = urllib.request.Request(url, json.dumps(body).encode(), headers)
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ProbeError("auth", f"HTTP {e.code}: server requires authentication")
        raise ProbeError("unreachable", f"HTTP {e.code} on {method}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ProbeError("unreachable", f"{type(e).__name__}: {e}"[:200])
    with resp:
        new_sid = resp.headers.get("Mcp-Session-Id") or sid
        raw = resp.read().decode("utf-8", "replace")
    if not raw.strip():
        return None, new_sid
    for line in raw.splitlines():                       # plain JSON or SSE frames
        line = line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if line.startswith("{"):
            try:
                return json.loads(line), new_sid
            except json.JSONDecodeError:
                continue
    raise ProbeError("unreachable", f"unparseable response to {method}")


def _entry(raw: dict) -> dict | None:
    """One `skills/list` entry reduced to what the dashboard stores.

    Tolerant on purpose. The spec makes `size`, `ttlMs` and `resultType`
    required, and the servers shipping today do not all send them; refusing
    such an entry would hide a skill that a host will happily load. What the
    gaps cost is recorded in `verifiable` instead.
    """
    uri = raw.get("uri")
    fm = raw.get("frontmatter")
    if not isinstance(uri, str) or not isinstance(fm, dict):
        return None
    res = raw.get("resources")
    files, size, verifiable, digest = 0, 0, "dynamic", ""
    if isinstance(res, list):
        files = len(res)
        have_size = all(isinstance(r, dict) and isinstance(r.get("size"), int) for r in res)
        have_digest = all(isinstance(r, dict) and r.get("digest") for r in res)
        size = sum(r.get("size") or 0 for r in res if isinstance(r, dict))
        verifiable = "full" if (have_size and have_digest) else "partial"
        for r in res:
            if isinstance(r, dict) and r.get("uri") == uri:
                digest = str(r.get("digest") or "")
                break
    elif res != "dynamic":
        return None                                     # invalid per spec
    return {
        "uri": uri,
        "name": str(fm.get("name") or ""),
        "description": str(fm.get("description") or ""),
        "frontmatter": fm,
        "files": -1 if verifiable == "dynamic" else files,
        "bytes": size,
        "verifiable": verifiable,
        "digest": digest,
    }


def probe(endpoint: str) -> dict:
    """Identify a server and enumerate the skills it serves.

    Returns the endpoint row. Raises ProbeError with the state to record.
    """
    if endpoint.startswith("stdio:"):
        raise ProbeError(
            "declared",
            "stdio server: starting it would run a command, which is outside "
            "this dashboard's read-only charter")

    if _is_loopback(endpoint):
        # A loopback address means a different machine to everyone who reads
        # it. The hub is usually not the machine whose config declared this, so
        # connecting would reach some unrelated service here rather than the
        # server the user meant — a wrong answer at best.
        raise ProbeError(
            "declared",
            "loopback address: this points at the machine that declared it, "
            "which is not the machine running the hub")

    init, sid = _rpc(endpoint, "initialize", {
        "protocolVersion": CLIENT_PROTOCOL,
        # declaring the extension is how a client asks for it; servers may
        # gate `skills/*` on the client having asked
        "capabilities": {"extensions": {EXTENSION: {}}},
        "clientInfo": {"name": "skillhub-probe", "version": "1"},
    }, None, 1, CLIENT_PROTOCOL)
    result = (init or {}).get("result") or {}
    if not result:
        raise ProbeError("unreachable", "no result from initialize")
    info = result.get("serverInfo") or {}
    caps = result.get("capabilities") or {}
    ext = (caps.get("extensions") or {}).get(EXTENSION)
    # echo the negotiated version back; sending a different one is a 400 on
    # at least one shipping server
    protocol = str(result.get("protocolVersion") or CLIENT_PROTOCOL)
    try:
        _rpc(endpoint, "notifications/initialized", {}, sid, 0, protocol)
    except ProbeError:
        pass                                            # optional; keep going

    row = {
        "endpoint": endpoint,
        "server_name": str(info.get("name") or ""),
        "server_title": str(info.get("title") or ""),
        "server_version": str(info.get("version") or ""),
        "protocol": protocol,
        "skills_ext": 1 if isinstance(ext, dict) else 0,
        "directory_read": 1 if isinstance(ext, dict) and ext.get("directoryRead") else 0,
        "state": "served",
        "detail": "",
        "skills": [],
    }
    if not isinstance(ext, dict):
        row["state"] = "no-extension"
        row["detail"] = "server does not declare " + EXTENSION
        return row

    skills, cursor, pages = [], None, 0
    while pages < MAX_PAGES:
        pages += 1
        params = {"cursor": cursor} if cursor else {}
        out, sid = _rpc(endpoint, "skills/list", params, sid, 10 + pages, protocol)
        res = (out or {}).get("result")
        if res is None:
            err = (out or {}).get("error") or {}
            raise ProbeError("unreachable",
                             f"skills/list: {err.get('message', 'no result')}"[:200])
        for raw in res.get("skills") or []:
            e = _entry(raw) if isinstance(raw, dict) else None
            if e:
                skills.append(e)
        cursor = res.get("nextCursor")
        if not cursor:
            break

    row["skills"] = skills
    if not skills:
        # legitimate per spec: large, generative or gateway-fronted catalogs
        # may return nothing and still serve skills by URI
        row["state"] = "empty"
        row["detail"] = "declares the extension but enumerates no skills"
    return row
