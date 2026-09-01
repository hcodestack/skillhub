"""Deterministic quality checks on library skills.

Grounded in Anthropic's published skill-authoring guidance (the skill-creator
skill), which states:
  - name + description are ALWAYS in context (~100 words budgeted per skill)
  - the SKILL.md body should stay under ~500 lines
  - the description is the trigger mechanism, and Claude tends to *under*trigger,
    so a thin description is a real defect, not a style nit

No model is involved: every rule here is objectively checkable, which is why it
belongs in an observability tool. Judgement calls (is this skill any good?) are
left to skill-creator's grader/comparator, which already do that properly.
"""
import os

SHORT_DESC_CHARS = 40      # below this a description cannot carry trigger context
LONG_BODY_LINES = 500      # skill-creator's stated ideal ceiling
CHARS_PER_TOKEN = 3.5      # rough for mixed CN/EN; used only for an order of magnitude


def body_lines(library_root: str, skill_id: str) -> int:
    from .config import settings
    d = settings.skill_dir(skill_id)
    for p in ([os.path.join(d, "SKILL.md")] if d else []):
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    return sum(1 for _ in f)
            except OSError:
                return 0
    return 0


def est_tokens(chars: int) -> int:
    return int(chars / CHARS_PER_TOKEN)


BLOCK_SCALAR_ARTIFACTS = {"", "|", ">", "|-", ">-", "|+", ">+"}


def read_description(library_root: str, skill_id: str) -> str:
    """Real description from SKILL.md frontmatter, block scalars included.

    Simple index generators often read `description:` with a line regex, which
    captures only a `|` when the description is written as a YAML block scalar
    — so the dashboard parses the file itself rather than trusting an index.
    """
    from .config import settings
    d = settings.skill_dir(skill_id)
    for path in ([os.path.join(d, "SKILL.md")] if d else []):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.read(8000).splitlines()
        except OSError:
            return ""
        if not lines or lines[0].strip() != "---":
            return ""
        out: list[str] = []
        collecting = False
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if collecting:
                # block scalar continues while lines stay indented
                if line.startswith((" ", "\t")):
                    out.append(line.strip())
                    continue
                break
            if line.startswith("description:"):
                value = line[len("description:"):].strip()
                if value in BLOCK_SCALAR_ARTIFACTS:
                    collecting = True     # text lives on the indented lines below
                    continue
                return value.strip("\"'")
        return " ".join(out).strip()
    return ""
