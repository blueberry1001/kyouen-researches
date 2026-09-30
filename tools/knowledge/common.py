from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT / "research" / "knowledge"
ITEMS_DIR = KNOWLEDGE_DIR / "items"
VOCABULARY_PATH = KNOWLEDGE_DIR / "VOCABULARY.yaml"


@dataclass(frozen=True)
class KnowledgeItem:
    path: Path
    meta: dict[str, Any]
    body: str


def read_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("front matter must start with ---")

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("front matter closing --- not found")

    raw = "\n".join(lines[1:end])
    meta = yaml.safe_load(raw) or {}
    if not isinstance(meta, dict):
        raise ValueError("front matter must be a mapping")

    body = "\n".join(lines[end + 1 :])
    return meta, body


def item_paths() -> list[Path]:
    paths = []
    for path in ITEMS_DIR.glob("*.md"):
        if path.name == "README.md" or path.name.startswith("_"):
            continue
        paths.append(path)
    return sorted(paths)


def load_items() -> list[KnowledgeItem]:
    result = []
    for path in item_paths():
        meta, body = read_front_matter(path)
        result.append(KnowledgeItem(path=path, meta=meta, body=body))
    return result


def load_vocabulary() -> dict[str, list[str]]:
    data = yaml.safe_load(VOCABULARY_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("VOCABULARY.yaml must be a mapping")
    return data
