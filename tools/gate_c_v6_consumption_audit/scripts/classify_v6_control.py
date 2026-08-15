#!/usr/bin/env python3
"""Classify whether the accepted v6 result discriminates the disputed joint source.

The classification is intentionally conservative. Only source-confirmed rows that
participated in a gradient, checkpoint selector, or final acceptance gate count.
The script never authorizes an optimizer run.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ACTIVE_ROLES = {"gradient", "selector", "acceptance"}
REPRESENTATIONS = {
    "canonical_21j",
    "mesh_helper_21j",
    "saved_2d_target",
    "saved_3d_target",
    "direct_fingertip_vertices",
    "mesh_vertices",
    "object_surface",
    "camera_or_raster",
    "other",
    "unknown",
}


def parse_bool(value: str) -> bool:
    text = value.strip().lower()
    if text in {"1", "true", "yes", "y", "active"}:
        return True
    if text in {"0", "false", "no", "n", "inactive", ""}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


@dataclass(frozen=True)
class Row:
    stage: str
    term: str
    role: str
    active: bool
    representation: str
    tensor_name: str
    producer: str
    source_evidence: str
    artifact_path: str
    review_status: str
    notes: str


def load_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "stage", "term", "role", "active", "representation", "tensor_name",
            "producer", "source_evidence", "artifact_path", "review_status", "notes",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest is missing columns: {sorted(missing)}")
        for line_no, raw in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw.values()):
                continue
            role = (raw["role"] or "").strip().lower()
            representation = (raw["representation"] or "unknown").strip().lower()
            if role not in {"gradient", "selector", "acceptance", "audit_only", "unused"}:
                raise ValueError(f"line {line_no}: invalid role {role!r}")
            if representation not in REPRESENTATIONS:
                raise ValueError(
                    f"line {line_no}: invalid representation {representation!r}; "
                    f"allowed={sorted(REPRESENTATIONS)}"
                )
            rows.append(
                Row(
                    stage=(raw["stage"] or "").strip(),
                    term=(raw["term"] or "").strip(),
                    role=role,
                    active=parse_bool(raw["active"] or ""),
                    representation=representation,
                    tensor_name=(raw["tensor_name"] or "").strip(),
                    producer=(raw["producer"] or "").strip(),
                    source_evidence=(raw["source_evidence"] or "").strip(),
                    artifact_path=(raw["artifact_path"] or "").strip(),
                    review_status=(raw["review_status"] or "").strip().lower(),
                    notes=(raw["notes"] or "").strip(),
                )
            )
    return rows


def decide(rows: list[Row]) -> dict[str, object]:
    if not rows:
        return {
            "route": "HOLD_V6_CONSUMPTION_MANIFEST_EMPTY",
            "reason": "No reviewed loss-input rows were supplied.",
        }

    incomplete = [
        row for row in rows
        if row.active
        and row.role in ACTIVE_ROLES
        and (
            row.review_status != "confirmed"
            or row.representation == "unknown"
            or not row.source_evidence
        )
    ]
    active_rows = [row for row in rows if row.active and row.role in ACTIVE_ROLES]
    if not active_rows:
        return {
            "route": "HOLD_V6_NO_ACTIVE_ACCEPTED_PATH_ROWS",
            "reason": "The manifest does not identify any active gradient, selector, or acceptance term.",
        }
    if incomplete:
        return {
            "route": "HOLD_V6_CONSUMPTION_PATH_INCOMPLETE",
            "reason": (
                "At least one active term lacks confirmed source evidence or has an unknown representation."
            ),
            "incomplete_terms": [f"{r.stage}:{r.term}" for r in incomplete],
        }

    representations = {row.representation for row in active_rows}
    canonical = "canonical_21j" in representations
    mesh_helper = "mesh_helper_21j" in representations
    direct_tip = "direct_fingertip_vertices" in representations
    saved_targets = bool({"saved_2d_target", "saved_3d_target"} & representations)
    mesh_vertices = "mesh_vertices" in representations

    if canonical and mesh_helper:
        route = "V6_MIXED_JOINT_CONSUMPTION_REQUIRES_TERM_SPLIT"
        reason = (
            "The accepted path used both canonical and mesh-helper joint sources. "
            "The terms must be separated and tested independently; v6 does not justify a global helper replacement."
        )
    elif canonical:
        route = "V6_DISCRIMINATES_CANONICAL_JOINT_CONSUMPTION"
        reason = (
            "At least one source-confirmed active accepted term consumed canonical 21-joint predictions, "
            "and no active accepted term consumed mesh-helper 21-joint predictions."
        )
    elif mesh_helper:
        route = "V6_DISCRIMINATES_MESH_HELPER_JOINT_CONSUMPTION"
        reason = (
            "At least one source-confirmed active accepted term consumed mesh-helper 21-joint predictions, "
            "and no active accepted term consumed canonical 21-joint predictions."
        )
    elif direct_tip or saved_targets or mesh_vertices:
        route = "V6_FUNCTIONAL_CONTROL_ONLY_NONDISCRIMINATING"
        reason = (
            "The accepted path is supported by direct mesh/fingertip vertices and/or saved targets, "
            "but it does not exercise the disputed internal 21-joint producer. It is a functional "
            "contact/export control, not a canonical-versus-mesh-helper adjudicator."
        )
    else:
        route = "HOLD_V6_CONSUMPTION_ROUTE_UNRESOLVED"
        reason = "The confirmed active terms do not establish a recognized hand-representation route."

    return {
        "route": route,
        "reason": reason,
        "active_term_count": len(active_rows),
        "representations": sorted(representations),
        "active_terms": [
            {
                "stage": row.stage,
                "term": row.term,
                "role": row.role,
                "representation": row.representation,
                "tensor_name": row.tensor_name,
                "producer": row.producer,
                "source_evidence": row.source_evidence,
            }
            for row in active_rows
        ],
    }


def recommendations(route: str) -> list[str]:
    if route == "V6_DISCRIMINATES_CANONICAL_JOINT_CONSUMPTION":
        return [
            "Prepare a versioned source-faithful canonical-joint adapter.",
            "Run zero-update identity and projection checks before any placement update.",
            "Keep the historical v3 target immutable and keep C2/F3.4/Gate D closed.",
        ]
    if route == "V6_DISCRIMINATES_MESH_HELPER_JOINT_CONSUMPTION":
        return [
            "Do not replace the live helper merely because canonical joints differ.",
            "Proceed to the same-run physical-hand/candidate audit under the frozen helper contract.",
            "Authorize no articulation until one candidate passes source, chirality, raster, and projection gates.",
        ]
    if route == "V6_MIXED_JOINT_CONSUMPTION_REQUIRES_TERM_SPLIT":
        return [
            "Split the keypoint/contact/selector terms by producer and rerun only paired zero-update ablations.",
            "Do not apply a global helper replacement while mixed consumption remains.",
            "Version every derivative and retain the immutable v3 target.",
        ]
    if route == "V6_FUNCTIONAL_CONTROL_ONLY_NONDISCRIMINATING":
        return [
            "Treat v6 as a functional fingertip/contact/export control only.",
            "Run the source-faithful H0-H2 producer audit or a paired zero-update projection check; do not replay full optimization first.",
            "Do not change the helper based on the v6 success result alone.",
        ]
    return [
        "Recover the missing source/artifact evidence or create one clean fresh versioned control run.",
        "If the path cannot be reconstructed, close the branch as a contained placement failure.",
        "Do not rewrite targets, guess mappings, or launch placement/contact optimization.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        rows = load_rows(args.manifest)
        result = decide(rows)
    except (OSError, ValueError) as exc:
        print(f"[HOLD] cannot classify manifest: {exc}")
        return 1

    route = str(result["route"])
    result["generated_utc"] = datetime.now(timezone.utc).isoformat()
    result["manifest"] = str(args.manifest.resolve())
    result["recommendations"] = recommendations(route)
    result["authorizations"] = {
        "helper_source_edit": False,
        "candidate_scoring": False,
        "mano_articulation": False,
        "object_movement": False,
        "c2": False,
        "f3_4": False,
        "gate_d": False,
    }

    json_path = args.out_dir / "v6_consumption_decision.json"
    md_path = args.out_dir / "v6_consumption_decision.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "# v6 hand-representation consumption decision",
        "",
        f"**Route:** `{route}`",
        "",
        str(result.get("reason", "")),
        "",
        "## Recommendations",
        "",
    ]
    for item in result["recommendations"]:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Authorization state",
        "",
        "This classifier does not authorize source edits or optimization. All downstream",
        "movement, articulation, C2, F3.4, and Gate-D actions remain closed until a",
        "separate preregistration and zero-update gate pass.",
    ]
    md_path.write_text("\n".join(lines) + "\n")

    print(f"[DECISION] {route}")
    print(f"[PASS] DECISION_JSON={json_path}")
    print(f"[PASS] DECISION_MD={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
