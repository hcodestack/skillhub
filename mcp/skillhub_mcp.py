#!/usr/bin/env python3
"""Skillmgmnt MCP server — lets your own agent query the hub as a native tool.

Runs on your machine (stdio), talks to the hub over HTTP. The model and any
keys stay in your agent; the hub only answers questions. That split is the
whole point: putting an LLM client inside the hub would mean a second place
that holds credentials and a second opinion about which model to use.

**Read-only on purpose.** The hub's one write action (`git pull --ff-only` on
git-backed skills) is deliberately not exposed here. An agent that can update
library skills unattended is a different risk than an agent that can read about
them, and that call belongs to a human at the dashboard. Adding it later is a
tools[] entry and one handler — the omission is a decision, not an oversight.

Pure stdlib, same as the reporter, so it runs anywhere Python does without an
install step.

Usage:
    skillhub_mcp.py [hub-url]          # default: $SKILLMGMNT_URL, else localhost

Register with Claude Code:
    claude mcp add skillhub -- /path/to/skillhub_mcp.py http://<hub-host>:8787
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HUB = (sys.argv[1] if len(sys.argv) > 1
       else os.environ.get("SKILLMGMNT_URL", "http://127.0.0.1:8787")).rstrip("/")
TIMEOUT = 20
PROTOCOL_VERSION = "2025-06-18"

# /api/v1/skills is ~640 KB of every skill with every install record. Search
# filters it locally, so it is fetched once and reused: a handful of tool calls
# in one turn should not pull that down a handful of times.
_CACHE: dict[str, tuple[float, object]] = {}
CACHE_TTL = 60


def log(msg: str) -> None:
    # stdout is the protocol channel; anything else said there corrupts it
    print(f"[skillhub-mcp] {msg}", file=sys.stderr, flush=True)


def get(path: str, ttl: int = 0):
    if ttl and path in _CACHE:
        at, val = _CACHE[path]
        if time.time() - at < ttl:
            return val
    req = urllib.request.Request(f"{HUB}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        val = json.loads(r.read().decode("utf-8"))
    if ttl:
        _CACHE[path] = (time.time(), val)
    return val


def skills() -> list[dict]:
    return get("/api/v1/skills", ttl=CACHE_TTL).get("items", [])


def trim(s: dict) -> dict:
    """One skill as a search hit: enough to decide whether to ask for detail.

    `installs` is dropped here — it is the bulk of the payload and is what
    skill_detail exists to serve."""
    v = s.get("vetting") or {}
    return {
        "key": s.get("key"),
        "name": s.get("name"),
        "description": (s.get("description") or "")[:200],
        "source": s.get("source"),
        "category": s.get("category"),
        "tags": s.get("tags"),
        "in_library": s.get("in_library"),
        "loaded_into": sorted({i.get("agent") for i in s.get("installs") or []}),
        "usage": s.get("usage"),
        "safety": {"count": v.get("count"), "top_severity": v.get("top_severity")} if v else None,
    }


# ---------------------------------------------------------------- tools

def t_overview(_args):
    return {"tiles": get("/api/v1/stats/tiles"), "hosts": get("/api/v1/hosts")}


def t_search_skills(args):
    q = (args.get("q") or "").strip().lower()
    limit = min(int(args.get("limit", 20)), 100)
    items = skills()
    if q:
        terms = q.split()
        scored = []
        for s in items:
            hay = " ".join(str(x) for x in (
                s.get("key"), s.get("name"), s.get("description"),
                s.get("category"), " ".join(s.get("tags") or []))).lower()
            if all(t in hay for t in terms):
                # an exact key/name hit is what the caller almost always meant
                exact = q == str(s.get("key", "")).lower() or q == str(s.get("name", "")).lower()
                scored.append((0 if exact else 1, s))
        items = [s for _, s in sorted(scored, key=lambda p: p[0])]
    return {"query": args.get("q", ""), "matched": len(items),
            "items": [trim(s) for s in items[:limit]]}


def t_skill_detail(args):
    key = args.get("key")
    if not key:
        raise ValueError("key is required")
    for s in skills():
        if s.get("key") == key or s.get("id") == key:
            return s
    near = [s["key"] for s in skills()
            if key.lower() in str(s.get("key", "")).lower()][:8]
    raise ValueError(f"no skill with key {key!r}" + (f"; did you mean: {near}" if near else ""))


def t_health_findings(args):
    data = get("/api/v1/health/findings")
    want = args.get("section")
    limit = min(int(args.get("limit", 20)), 200)

    def head(s):
        return {k: s[k] for k in ("key", "severity", "title", "hint", "count") if k in s}

    # The raw endpoint is ~120 KB because every section carries its full item
    # list. Headlines answer "what is wrong" on their own; items come only for
    # the section actually asked about.
    sections = [head(s) if s.get("key") != want
                else {**head(s), "items": (s.get("items") or [])[:limit]}
                for s in data.get("sections", [])]
    out = {"sections": sections}
    if not want:
        out["note"] = "pass section=<key> for that section's items"
    return out


def t_safety_findings(args):
    data = get("/api/v1/vetting")
    rows = data if isinstance(data, list) else data.get("items", [])
    sev = args.get("severity")
    skill = args.get("skill")
    limit = min(int(args.get("limit", 20)), 200)
    if skill:
        rows = [r for r in rows if skill.lower() in str(r.get("skill_id", "")).lower()]
    if sev:
        rows = [r for r in rows if r.get("top_severity") == sev]
    return {"matched": len(rows), "items": rows[:limit]}


def t_remediation_plan(_args):
    # The read-only boundary holds: the hub compiles the plan, the agent that
    # calls this executes it — with its own user's confirmation, on the machine
    # where the files are. Exactly the split the MCP layer exists for.
    return get("/api/v1/report/plan")


def t_usage_events(args):
    key = args.get("key")
    if not key:
        raise ValueError("key is required")
    q = urllib.parse.urlencode({"k": key, "limit": min(int(args.get("limit", 50)), 200)})
    return get(f"/api/v1/skills/events?{q}")


TOOLS = [
    ("overview", "Skillmgmnt 总览：库内技能数、已载入数、调用数、工具数、断链数、"
                 "元数据常驻 token 数，以及上报的主机列表。回答「现在整体什么状况」。",
     {"type": "object", "properties": {}}, t_overview),
    ("search_skills", "按关键词搜索技能（匹配 id/名称/描述/分类/标签，多词为 AND）。"
                      "返回精简记录；要完整信息用 skill_detail。q 留空则列出全部。",
     {"type": "object", "properties": {
         "q": {"type": "string", "description": "关键词，空格分隔"},
         "limit": {"type": "integer", "description": "最多返回条数，默认 20"}}}, t_search_skills),
    ("skill_detail", "一个技能的完整记录：描述、来源、分类、正文行数、载入到了哪些工具/"
                     "项目（含软链类型与目标）、调用统计、上游更新状态、安全命中。",
     {"type": "object", "properties": {
         "key": {"type": "string", "description": "技能 key 或 id"}},
      "required": ["key"]}, t_skill_detail),
    ("health_findings", "治理发现：散落实体、仓库自带、断链、无法判定的软链、未索引、"
                        "描述过短、正文超标、重复副本、闲置技能等。不带参数时只返回各节"
                        "标题与条数；传 section 取该节明细。",
     {"type": "object", "properties": {
         "section": {"type": "string", "description":
                     "节 key，如 broken_links / loose_entities / duplicate_copies"},
         "limit": {"type": "integer", "description": "明细最多返回条数，默认 20"}}},
     t_health_findings),
    ("safety_findings", "确定性安全审查结果（凭据与隐私 / 外发与下载 / 执行与提权）。"
                        "命中是信号不是判决——每条带规则、文件、行号与原因，供人判断。",
     {"type": "object", "properties": {
         "severity": {"type": "string", "enum": ["high", "medium", "low"]},
         "skill": {"type": "string", "description": "只看某个技能（子串匹配）"},
         "limit": {"type": "integer", "description": "最多返回条数，默认 20"}}},
     t_safety_findings),
    ("remediation_plan", "结构化的治理方案：断链清单（含可安全执行的删除命令与重链命令）、"
                          "散落实体清单（含替换为软链的建议命令，需人工确认后执行）、"
                          "重复副本与安全高危摘要。命令在生成时已做 shell 引号处理；"
                          "断链删除命令自带「执行时仍悬空才删」守卫。执行前向用户复述要做什么。",
     {"type": "object", "properties": {}}, t_remediation_plan),
    ("usage_events", "某个技能的调用记录（时间、工具、项目）。注意：12 个工具中仅 3 个"
                     "会产出可解析的调用日志，所以「没有记录」不等于「没被用过」。",
     {"type": "object", "properties": {
         "key": {"type": "string", "description": "技能 key"},
         "limit": {"type": "integer", "description": "最多返回条数，默认 50"}},
      "required": ["key"]}, t_usage_events),
]
HANDLERS = {name: fn for name, _d, _s, fn in TOOLS}


# ---------------------------------------------------------------- protocol

def reply(rid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": rid}
    msg["error" if error else "result"] = error if error else result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(req):
    method = req.get("method")
    rid = req.get("id")
    params = req.get("params") or {}

    # notifications carry no id and must not be answered
    if rid is None:
        return

    if method == "initialize":
        # echo the client's protocol version when it names one, so a client
        # pinned to an older revision is not turned away over a version string
        return reply(rid, {
            "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "skillhub", "version": "0.1.0"},
        })
    if method == "ping":
        return reply(rid, {})
    if method in ("resources/list", "prompts/list"):
        # some clients probe these; answering empty is friendlier than erroring
        return reply(rid, {"resources": []} if method.startswith("resources")
                     else {"prompts": []})
    if method == "tools/list":
        return reply(rid, {"tools": [
            {"name": n, "description": d, "inputSchema": s} for n, d, s, _fn in TOOLS]})
    if method == "tools/call":
        name = params.get("name")
        fn = HANDLERS.get(name)
        if not fn:
            return reply(rid, error={"code": -32602, "message": f"unknown tool {name!r}"})
        try:
            out = fn(params.get("arguments") or {})
            text = json.dumps(out, ensure_ascii=False, indent=1, default=str)
        except (urllib.error.URLError, OSError) as e:
            # the hub being down is an answerable condition, not a crash: say so
            # in-band so the agent can tell the user instead of losing the server
            text, err = f"Skillmgmnt 不可达（{HUB}）：{e}", True
        except Exception as e:
            text, err = f"{type(e).__name__}: {e}", True
        else:
            err = False
        return reply(rid, {"content": [{"type": "text", "text": text}], "isError": err})

    return reply(rid, error={"code": -32601, "message": f"unknown method {method!r}"})


def main():
    log(f"serving {HUB}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"bad frame: {e}")
            continue
        try:
            handle(req)
        except Exception as e:          # one bad request must not end the session
            log(f"handler failed: {type(e).__name__}: {e}")
            if req.get("id") is not None:
                reply(req["id"], error={"code": -32603, "message": str(e)})


if __name__ == "__main__":
    main()
