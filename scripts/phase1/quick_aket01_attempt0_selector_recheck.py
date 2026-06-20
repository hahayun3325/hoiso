#!/usr/bin/env python
from pathlib import Path
import json
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree

try:
    import igl
except Exception:
    igl = None

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
OUT_DIR = ROOT / "docs/phase1/step3_prompt_refined_rerun/aket01_attempt0"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HAND = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt/selector_v4_recheck/io_alignment/aket01_partaware_v2_attempt0/pred_hand_aligned.ply")
OBJ = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt/selector_v4_recheck/io_alignment/aket01_partaware_v2_attempt0/pred_object_aligned.ply")

if not HAND.exists():
    raise FileNotFoundError(HAND)
if not OBJ.exists():
    raise FileNotFoundError(OBJ)

hand = trimesh.load(HAND, force="mesh")
obj = trimesh.load(OBJ, force="mesh")

hand_v = np.asarray(hand.vertices)
obj_v = np.asarray(obj.vertices)

tree_obj = cKDTree(obj_v)
d_hand_to_obj, _ = tree_obj.query(hand_v, k=1)
d_mm = d_hand_to_obj * 1000.0

report = {
    "sample_id": "aket01_partaware_v2_attempt0",
    "case": "aket01",
    "method": "partaware_v2_attempt0",
    "hand_mesh": str(HAND),
    "object_mesh": str(OBJ),
    "contact_min_mm": float(np.min(d_mm)),
    "contact_p5_mm": float(np.percentile(d_mm, 5)),
    "contact_mean_mm": float(np.mean(d_mm)),
    "contact_count_5mm": int(np.sum(d_mm <= 5.0)),
    "num_hand_vertices": int(len(hand_v)),
    "num_object_vertices": int(len(obj_v)),
}

if igl is not None and len(hand.faces) > 0 and len(obj.faces) > 0:
    obj_to_hand_ret = igl.signed_distance(obj_v, hand_v, np.asarray(hand.faces))
    hand_to_obj_ret = igl.signed_distance(hand_v, obj_v, np.asarray(obj.faces))

    obj_to_hand_sd = obj_to_hand_ret[0]
    hand_to_obj_sd = hand_to_obj_ret[0]

    obj_inside_hand = obj_to_hand_sd < 0
    hand_inside_obj = hand_to_obj_sd < 0

    report.update({
        "igl_available": True,
        "object_inside_hand_ratio": float(np.mean(obj_inside_hand)),
        "object_inside_hand_max_depth_mm": float(np.max((-obj_to_hand_sd[obj_inside_hand]) * 1000.0)) if np.any(obj_inside_hand) else 0.0,
        "hand_inside_object_ratio": float(np.mean(hand_inside_obj)),
        "hand_inside_object_max_depth_mm": float(np.max((-hand_to_obj_sd[hand_inside_obj]) * 1000.0)) if np.any(hand_inside_obj) else 0.0,
    })
else:
    report.update({
        "igl_available": False,
        "object_inside_hand_ratio": None,
        "object_inside_hand_max_depth_mm": None,
        "hand_inside_object_ratio": None,
        "hand_inside_object_max_depth_mm": None,
    })

severe_floating = report["contact_p5_mm"] > 20.0

severe_penetration = False
if report["igl_available"]:
    severe_penetration = (
        report["object_inside_hand_ratio"] > 0.03 or
        report["hand_inside_object_ratio"] > 0.20 or
        report["object_inside_hand_max_depth_mm"] > 10.0 or
        report["hand_inside_object_max_depth_mm"] > 10.0
    )

if severe_penetration:
    decision = "reject_attempt0_severe_penetration"
elif severe_floating:
    decision = "reject_attempt0_severe_floating"
else:
    decision = "accepted_after_prompt_refined_rerun_candidate"

report["severe_floating"] = bool(severe_floating)
report["severe_penetration"] = bool(severe_penetration)
report["quick_decision"] = decision

json_path = OUT_DIR / "aket01_attempt0_quick_selector_recheck.json"
csv_path = OUT_DIR / "aket01_attempt0_quick_selector_recheck.csv"

json_path.write_text(json.dumps(report, indent=2))
pd.DataFrame([report]).to_csv(csv_path, index=False)

print(json.dumps(report, indent=2))
print("[OK] wrote", json_path)
print("[OK] wrote", csv_path)
