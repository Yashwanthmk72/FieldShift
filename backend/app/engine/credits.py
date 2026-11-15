# AI-assisted: written with an AI coding assistant.
"""Parses backend/data/sources.md into structured credits for the in-app 'Data sources & credits' page.
Format: '## Name' sections; '- Key: value' bullets; free text lines become the section description."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SOURCES_MD = Path(__file__).resolve().parents[1] / "data" / "sources.md"


def parse(text: str) -> dict[str, Any]:
    title, intro, sections, cur = "", [], [], None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            cur = {"name": line[3:].strip(), "group": "", "fields": {}, "text": []}
            sections.append(cur)
        elif cur is not None and (m := re.match(r"^- ([A-Za-z][A-Za-z /&-]*?):\s*(.+)$", line)):
            k, v = m.group(1).strip(), m.group(2).strip()
            if k.lower() == "group":
                cur["group"] = v
            else:
                cur["fields"][k] = v
        elif cur is not None and line.strip():
            cur["text"].append(line.strip())
        elif cur is None and line.strip():
            intro.append(line.strip())
    for s in sections:
        s["text"] = " ".join(s["text"])
        s["urls"] = {k: v for k, v in s["fields"].items() if v.startswith("http")}
    return {"title": title, "intro": " ".join(intro), "sections": sections}


def load() -> dict[str, Any]:
    return parse(SOURCES_MD.read_text(encoding="utf-8"))
