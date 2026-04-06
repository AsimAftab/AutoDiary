#!/usr/bin/env python3
"""
Validate that skills_mapping.json keeps its duplicate lookup structures in sync.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def load_skills_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def find_duplicates(values: list[Any], label: str) -> list[str]:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    return [f"Duplicate {label}: {value!r}" for value in duplicates]


def find_missing_matches(skills: list[dict[str, Any]], name_to_id: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    for skill in skills:
        name = skill.get("name")
        skill_id = skill.get("id")
        mapped_id = name_to_id.get(name)
        if mapped_id is None:
            issues.append(f"Missing name_to_id entry for skill {name!r} (id={skill_id!r})")
        elif mapped_id != skill_id:
            issues.append(
                f"Mismatched id for skill {name!r}: skills has {skill_id!r}, "
                f"name_to_id has {mapped_id!r}"
            )

    skills_by_name = {skill.get("name"): skill.get("id") for skill in skills}
    for name, mapped_id in name_to_id.items():
        if name not in skills_by_name:
            issues.append(f"Missing skills entry for name_to_id key {name!r} (id={mapped_id!r})")
        elif skills_by_name[name] != mapped_id:
            issues.append(
                f"Mismatched id for name_to_id key {name!r}: name_to_id has {mapped_id!r}, "
                f"skills has {skills_by_name[name]!r}"
            )

    return issues


def validate_entries(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    skills = data.get("skills")
    name_to_id = data.get("name_to_id")

    if not isinstance(skills, list):
        return ["Expected 'skills' to be a list"]
    if not isinstance(name_to_id, dict):
        return ["Expected 'name_to_id' to be an object"]

    names: list[Any] = []
    ids: list[Any] = []
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            issues.append(f"Skill at index {index} is not an object")
            continue

        if "name" not in skill or "id" not in skill:
            issues.append(f"Skill at index {index} must contain both 'name' and 'id'")
            continue

        names.append(skill["name"])
        ids.append(skill["id"])

    issues.extend(find_duplicates(names, "skill name"))
    issues.extend(find_duplicates(ids, "skill id"))
    issues.extend(find_duplicates(list(name_to_id.keys()), "name_to_id key"))
    issues.extend(find_duplicates(list(name_to_id.values()), "name_to_id id"))
    issues.extend(find_missing_matches(skills, name_to_id))

    return issues


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    mapping_path = repo_root / "src" / "autodiary" / "resources" / "skills_mapping.json"

    try:
        data = load_skills_mapping(mapping_path)
    except Exception as exc:
        print(f"Failed to load {mapping_path}: {exc}", file=sys.stderr)
        return 1

    issues = validate_entries(data)
    if issues:
        print("skills_mapping validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"skills_mapping validation passed: {mapping_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
