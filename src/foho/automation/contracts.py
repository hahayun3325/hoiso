from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def load_strict_schema(path: str | Path) -> dict[str, Any]:
    payload = load_json(path)
    schema = payload.get("schema", payload) if isinstance(payload, dict) else payload
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError(f"schema_root_must_be_object:{path}")
    if schema.get("additionalProperties") is not False:
        raise ValueError(f"schema_root_must_forbid_extra_fields:{path}")
    Draft202012Validator.check_schema(schema)
    return schema


def validate_packet(packet: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]:
    validator = Draft202012Validator(dict(schema))
    errors = sorted(validator.iter_errors(dict(packet)), key=lambda item: list(item.path))
    if errors:
        message = ";".join(
            f"{'.'.join(map(str, error.path)) or '$'}:{error.message}" for error in errors
        )
        raise ValueError(f"contract_validation_failed:{message}")
    return dict(packet)
