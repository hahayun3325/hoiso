#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np


def mark(ok: bool, pass_text: str, hold_text: str) -> bool:
    print(f"[{'PASS' if ok else 'HOLD'}] {pass_text if ok else hold_text}")
    return ok


f31 = Path(os.environ["F31_ROOT"])
pipeline = Path(os.environ["PIPELINE"])
pair_dir = Path(os.environ["PAIR_DIR"])
token = os.environ["TOKEN"]

paths = {
    "target_ids": f31 / "inputs/F3_1_local_lid_target_vertex_ids.npy",
    "candidate_r0_c1": (
        f31 / "inputs/candidates/r0_c1_canonical_object_ids.npy"
    ),
    "contact_spec": f31 / "inputs/F3_1_contact_spec.json",
    "same_frame_object": pair_dir / f"{token}_obj_same_frame.ply",
    "same_frame_hand": pair_dir / f"{token}_hand_same_frame.ply",
    "canonical_lid": (
        Path(os.environ["F2_ROOT"])
        / "inputs"
        / f"{token}_gate_c_verified_target_screen_lid_canonical.ply"
    ),
    "pipeline": pipeline,
}

print("=== F3.1 required-file audit ===")
missing = []
for name, path in paths.items():
    exists = path.is_file() and path.stat().st_size > 0
    print(f"[{'PASS' if exists else 'HOLD'}] {name}: {path}")
    if not exists:
        missing.append(name)

target_ok = False
spec_ok = False

if not missing:
    ids = np.asarray(
        np.load(paths["target_ids"]), dtype=np.int64
    ).reshape(-1)
    expected = np.asarray(
        np.load(paths["candidate_r0_c1"]), dtype=np.int64
    ).reshape(-1)
    spec = json.loads(paths["contact_spec"].read_text())

    target_ok = (
        ids.size == 24
        and np.array_equal(ids, expected)
        and ids.min() >= 0
        and ids.max() < 15086
    )

    spec_ok = (
        spec.get("target_candidate_id") == "r0_c1"
        and spec.get("target_vertex_count") == 24
        and spec.get("primary_fingertip_vertices")
        == {"index": 320, "middle": 443}
        and spec.get("approved_for_runtime_preflight") is True
    )

    mark(
        target_ok,
        "F3_1_TARGET_IDS_MATCH_APPROVED_R0_C1",
        "F3_1_TARGET_IDS_DO_NOT_MATCH_APPROVED_R0_C1",
    )
    mark(
        spec_ok,
        "F3_1_CONTACT_SPEC_APPROVED",
        "F3_1_CONTACT_SPEC_NOT_APPROVED",
    )

print("=== pipeline syntax and runtime-marker audit ===")

source_ok = False
runtime_ok = False

if paths["pipeline"].is_file():
    text = paths["pipeline"].read_text(errors="replace")

    try:
        compile(text, str(paths["pipeline"]), "exec")
        source_ok = True
        print("[PASS] PIPELINE_SOURCE_SYNTAX_OK")
    except SyntaxError as exc:
        print(f"[HOLD] PIPELINE_SOURCE_SYNTAX_ERROR: {exc}")

    markers = {
        "F3.1 opt-in": "FOHO_F3_1_STAGE1",
        "rotation delta": "rotation_delta_hand",
        "F3.1 spec filename": "F3_1_contact_spec.json",
        "F3.1 target filename":
            "F3_1_local_lid_target_vertex_ids.npy",
        "rotation bound":
            "FOHO_F3_1_MAX_ROTATION_DELTA_DEG",
        "two-trainable pass":
            "F3_1_RUNTIME_TRAINABLES_TRANS_PLUS_ROT_DELTA_ONLY",
        "F3.1 runtime plan":
            "FOHO_F3_1_RUNTIME_PLAN",
    }

    marker_results = {}
    for name, marker in markers.items():
        marker_results[name] = marker in text
        print(
            f"[{'PASS' if marker_results[name] else 'HOLD'}] "
            f"{name}: {marker}"
        )

    runtime_ok = source_ok and all(marker_results.values())

print("=== decision ===")

if missing:
    print(
        "[HOLD] F3_1_EXPERIMENT_INPUT_FILES_MISSING: "
        + ", ".join(missing)
    )
elif not target_ok or not spec_ok:
    print("[HOLD] F3_1_TARGET_CONTRACT_FAILED")
elif runtime_ok:
    print("[PASS] F3_1_RUNTIME_STATIC_PREFLIGHT_READY")
    print("[NEXT] run one zero-update F3.1 runtime preflight")
else:
    print("[PASS] F3_1_TARGET_CONTRACT_READY")
    print("[HOLD] F3_1_RUNTIME_PATCH_MISSING")
    print(
        "[NEXT] create and preview a source-aware F3.1 "
        "rotation-extension patch"
    )
