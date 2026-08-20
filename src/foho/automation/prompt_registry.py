from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .contracts import file_sha256


@dataclass(frozen=True)
class PromptOwner:
    owner_id: str
    path: Path
    sha256: str


class PromptRegistry:
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.payload: dict[str, Any] = json.loads(self.manifest_path.read_text())
        self.owners: dict[str, PromptOwner] = {}
        for owner_id, item in self.payload.get("owners", {}).items():
            path = Path(item["path"])
            expected = item["sha256"]
            actual = file_sha256(path)
            if actual != expected:
                raise ValueError(f"owner_hash_mismatch:{owner_id}:{actual}:{expected}")
            self.owners[owner_id] = PromptOwner(owner_id, path, expected)
        policy = self.payload.get("keyword_policy", {})
        self.max_keywords = int(policy.get("max_keywords", 8))
        self.max_chars = int(policy.get("max_chars", 96))
        self.reject_prefixes = tuple(policy.get("reject_prefixes", ["no ", "without "]))

    def owner(self, owner_id: str) -> PromptOwner:
        if owner_id not in self.owners:
            raise KeyError(f"unknown_prompt_owner:{owner_id}")
        return self.owners[owner_id]

    def render_keywords(self, values: Iterable[str]) -> str:
        keywords=[]
        for raw in values:
            value=str(raw).strip()
            lowered=value.lower()
            if not value or "\n" in value or "\r" in value:
                raise ValueError("foundation_keyword_must_be_one_nonempty_line")
            if any(lowered.startswith(prefix) for prefix in self.reject_prefixes):
                raise ValueError(f"negative_foundation_keyword_rejected:{value}")
            keywords.append(value)
        if not keywords or len(keywords) > self.max_keywords:
            raise ValueError(f"foundation_keyword_count_out_of_bounds:{len(keywords)}")
        rendered=", ".join(keywords)
        if len(rendered) > self.max_chars:
            raise ValueError(f"foundation_prompt_too_long:{len(rendered)}")
        return rendered
