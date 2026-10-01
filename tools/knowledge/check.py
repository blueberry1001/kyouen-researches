from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from common import ROOT, load_items, load_vocabulary

PERMANENT_ID = re.compile(r"^K\d{4,}$")
REQUIRED = ("id", "title", "summary", "kind", "status")


def as_list(value: Any, field: str, errors: list[str], where: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{where}: {field} must be a list")
        return []
    return value


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        vocab = load_vocabulary()
        items = load_items()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    allowed_kinds = set(vocab.get("kinds", []))
    allowed_statuses = set(vocab.get("statuses", []))
    status_by_kind = vocab.get("status_by_kind", {})
    allowed_relations = set(vocab.get("relations", []))
    allowed_roles = set(vocab.get("artifact_roles", []))
    known_topics = set(vocab.get("topics", []))
    known_boards = set(vocab.get("boards", []))

    if not isinstance(status_by_kind, dict):
        print("ERROR: VOCABULARY.yaml: status_by_kind must be a mapping")
        return 1

    by_id: dict[str, Path] = {}
    alias_owner: dict[str, str] = {}

    for item in items:
        meta = item.meta
        where = str(item.path.relative_to(ROOT))

        for key in REQUIRED:
            if key not in meta or meta[key] in (None, ""):
                errors.append(f"{where}: missing required field {key}")

        item_id = str(meta.get("id", ""))
        if item_id:
            if not PERMANENT_ID.fullmatch(item_id):
                errors.append(f"{where}: invalid id {item_id!r}; expected K followed by at least four digits")
            if not item.path.name.startswith(item_id + "-"):
                errors.append(f"{where}: filename must start with {item_id}-")
            if item_id in by_id:
                errors.append(
                    f"{where}: duplicate id {item_id}; already used by "
                    f"{by_id[item_id].relative_to(ROOT)}"
                )
            else:
                by_id[item_id] = item.path

        kind = meta.get("kind")
        status = meta.get("status")
        if kind and kind not in allowed_kinds:
            errors.append(f"{where}: unknown kind {kind!r}")
        if status and status not in allowed_statuses:
            errors.append(f"{where}: unknown status {status!r}")

        if kind in allowed_kinds and status in allowed_statuses:
            allowed_for_kind = status_by_kind.get(kind)
            if not isinstance(allowed_for_kind, list):
                errors.append(f"VOCABULARY.yaml: missing status_by_kind entry for {kind!r}")
            elif status not in allowed_for_kind:
                errors.append(
                    f"{where}: status {status!r} is not valid for kind {kind!r}; "
                    f"allowed: {', '.join(map(str, allowed_for_kind))}"
                )

        for topic in as_list(meta.get("topics"), "topics", errors, where):
            if topic not in known_topics:
                warnings.append(f"{where}: unregistered topic {topic!r}")
        for board in as_list(meta.get("boards"), "boards", errors, where):
            if board not in known_boards:
                warnings.append(f"{where}: unregistered board {board!r}")

        for alias in as_list(meta.get("aliases"), "aliases", errors, where):
            if not isinstance(alias, str) or not alias:
                errors.append(f"{where}: aliases must contain non-empty strings")
                continue
            if alias in alias_owner:
                errors.append(f"{where}: alias {alias!r} already belongs to {alias_owner[alias]}")
            else:
                alias_owner[alias] = item_id

        relations = meta.get("relations") or {}
        if not isinstance(relations, dict):
            errors.append(f"{where}: relations must be a mapping")
        else:
            for relation, targets in relations.items():
                if relation not in allowed_relations:
                    errors.append(f"{where}: unknown relation {relation!r}")
                as_list(targets, f"relations.{relation}", errors, where)

        artifacts = as_list(meta.get("artifacts"), "artifacts", errors, where)
        for i, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"{where}: artifacts[{i}] must be a mapping")
                continue
            path = artifact.get("path")
            role = artifact.get("role")
            if not isinstance(path, str) or not path:
                errors.append(f"{where}: artifacts[{i}].path is required")
            elif not (ROOT / path).exists():
                errors.append(f"{where}: artifact path does not exist: {path}")
            if role not in allowed_roles:
                errors.append(f"{where}: artifacts[{i}].role is invalid: {role!r}")

    known_ids = set(by_id)
    for item in items:
        where = str(item.path.relative_to(ROOT))
        relations = item.meta.get("relations") or {}
        if not isinstance(relations, dict):
            continue
        for relation, targets in relations.items():
            if not isinstance(targets, list):
                continue
            for target in targets:
                if not isinstance(target, str):
                    errors.append(f"{where}: {relation} targets must be strings")
                    continue
                if target not in known_ids:
                    errors.append(f"{where}: {relation} target does not exist: {target}")

    for message in warnings:
        print(f"WARNING: {message}", file=sys.stderr)
    for message in errors:
        print(f"ERROR: {message}", file=sys.stderr)

    print(
        f"knowledge check: {len(items)} items, "
        f"{len(errors)} errors, {len(warnings)} warnings"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
