"""AI coding tool directory table — where each tool keeps its skills.

Derived from public per-tool documentation (MIT), src-tauri/src/core/tool_adapters/mod.rs
assembled from each tool's public documentation.

Keys use hyphens to match the agent keys this project already stores
(claude-code, codex, workbuddy).

Fields: global skills dir and detect dir are relative to $HOME; project is
relative to a project root (None = tool has no project-level skills dir).
"""

TOOLS = {
    "cursor": ("Cursor", ".cursor/skills", ".agents/skills", ".cursor"),
    "claude-code": ("Claude Code", ".claude/skills", ".claude/skills", ".claude"),
    "codex": ("Codex", ".codex/skills", ".agents/skills", ".codex"),
    "deepseek-harness": ("DeepSeek Harness", ".dsh/skills", ".dsh/skills", ".dsh"),
    "opencode": ("OpenCode", ".config/opencode/skills", ".agents/skills", ".config/opencode"),
    "antigravity": ("Antigravity", ".gemini/config/skills", ".agents/skills", ".gemini/config"),
    "amp": ("Amp", ".config/agents/skills", ".agents/skills", ".config/agents"),
    "kimi-cli": ("Kimi Code CLI", ".config/agents/skills", ".agents/skills", ".config/agents"),
    "augment": ("Augment", ".augment/skills", ".augment/skills", ".augment"),
    "openclaw": ("OpenClaw", ".openclaw/skills", "skills", ".openclaw"),
    "copaw": ("Copaw", ".copaw/skill_pool", ".copaw/skill_pool", ".copaw"),
    "cline": ("Cline", ".agents/skills", ".agents/skills", ".agents"),
    "codebuddy": ("CodeBuddy", ".codebuddy/skills", ".codebuddy/skills", ".codebuddy"),
    "codewhale": ("CodeWhale", ".codewhale/skills", ".codewhale/skills", ".codewhale"),
    "workbuddy": ("WorkBuddy", ".workbuddy/skills", None, ".workbuddy"),
    "command-code": ("Command Code", ".commandcode/skills", ".commandcode/skills", ".commandcode"),
    "continue": ("Continue", ".continue/skills", ".continue/skills", ".continue"),
    "crush": ("Crush", ".config/crush/skills", ".crush/skills", ".config/crush"),
    "junie": ("Junie", ".junie/skills", ".junie/skills", ".junie"),
    "iflow-cli": ("iFlow CLI", ".iflow/skills", ".iflow/skills", ".iflow"),
    "kiro-cli": ("Kiro CLI", ".kiro/skills", ".kiro/skills", ".kiro"),
    "kode": ("Kode", ".kode/skills", ".kode/skills", ".kode"),
    "mcpjam": ("MCPJam", ".mcpjam/skills", ".mcpjam/skills", ".mcpjam"),
    "mistral-vibe": ("Mistral Vibe", ".vibe/skills", ".vibe/skills", ".vibe"),
    "mux": ("Mux", ".mux/skills", ".mux/skills", ".mux"),
    "openclaude": ("OpenClaude IDE", ".openclaude/skills", ".openclaude/skills", ".openclaude"),
    "openhands": ("OpenHands", ".openhands/skills", ".openhands/skills", ".openhands"),
    "pi": ("Pi", ".pi/agent/skills", ".pi/skills", ".pi"),
    "qoder": ("Qoder", ".qoder/skills", ".qoder/skills", ".qoder"),
    "qoderwork": ("QoderWork", ".qoderwork/skills", ".qoderwork/skills", ".qoderwork"),
    "qwen-code": ("Qwen Code", ".qwen/skills", ".qwen/skills", ".qwen"),
    "trae": ("Trae", ".trae/skills", ".trae/skills", ".trae"),
    "trae-cn": ("Trae CN", ".trae-cn/skills", ".trae/skills", ".trae-cn"),
    "zencoder": ("Zencoder", ".zencoder/skills", ".zencoder/skills", ".zencoder"),
    "neovate": ("Neovate", ".neovate/skills", ".neovate/skills", ".neovate"),
    "pochi": ("Pochi", ".pochi/skills", ".pochi/skills", ".pochi"),
    "adal": ("AdaL", ".adal/skills", ".adal/skills", ".adal"),
    "kilo-code": ("Kilo Code", ".kilocode/skills", ".kilocode/skills", ".kilocode"),
    "roo-code": ("Roo Code", ".roo/skills", ".roo/skills", ".roo"),
    "goose": ("Goose", ".config/goose/skills", ".goose/skills", ".config/goose"),
    "gemini-cli": ("Gemini CLI", ".gemini/skills", ".agents/skills", ".gemini"),
    "github-copilot": ("GitHub Copilot", ".copilot/skills", ".agents/skills", ".copilot"),
    "clawdbot": ("Clawdbot", ".clawdbot/skills", ".clawdbot/skills", ".clawdbot"),
    "droid": ("Droid", ".factory/skills", ".factory/skills", ".factory"),
    "windsurf": ("Windsurf", ".codeium/windsurf/skills", ".windsurf/skills", ".codeium/windsurf"),
    "moltbot": ("MoltBot", ".moltbot/skills", ".moltbot/skills", ".moltbot"),
    "hermes-agent": ("Hermes Agent", ".hermes/skills", None, ".hermes"),
}


# (display_name, global_dir, project_dir, detect_dir)
NAME, GLOBAL_DIR, PROJECT_DIR, DETECT_DIR = 0, 1, 2, 3


def tools_sharing(field: int, value: str) -> list[str]:
    """Display names of every tool using the same directory — one physical dir
    can serve many tools (e.g. project `.agents/skills` serves Cursor, Codex,
    Cline, OpenCode, Gemini CLI, Copilot ...)."""
    return [t[NAME] for t in TOOLS.values() if t[field] == value]
