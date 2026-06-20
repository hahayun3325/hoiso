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

MANIFEST = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance/arctic5_selector_performance_manifest.csv")
OUT_DIR = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(MANIFEST)
rows = []

for _, r in df.iterrows():
    row = r.to_dict()
    if not bool(r["exists"]):
        row.update({
            "status": "missing_mesh",
            "contact_min_mm": None,
            "contact_p5_mm": None,
            "contact_mean_mm": None,
            "contact_count_5mm": None,
            "object_inside_hand_ratio": None,
            "object_inside_hand_max_depth_mm": None,
            "hand_inside_object_ratio": None,
            "hand_inside_object_max_depth_mm": None,
            "components": None,
            "largest_component_fraction": None,
            "bbox_diag_mm": None,
            "selector_v4_gate": "missing_mesh",
        })
        rows.append(row)
        continue

    hand_p = Path(r["hand_mesh"])
    obj_p = Path(r["object_mesh"])

    hand = trimesh.load(hand_p, force="mesh")
    obj = trimesh.load(obj_p, force="mesh")

    hand_v = np.asarray(hand.vertices)
    obj_v = np.asarray(obj.vertices)

    tree_obj = cKDTree(obj_v)
    d, _ = tree_obj.query(hand_v, k=1)
    d_mm = d * 1000.0

    comps = obj.split(only_watertight=False)
    areas = np.array([c.area for c in comps]) if comps else np.array([])
    largest_fraction = float(areas.max() / areas.sum()) if areas.size and areas.sum() > 0 else None
    bbox_diag_mm = float(np.linalg.norm(obj.bounds[1] - obj.bounds[0]) * 1000.0)

    row.update({
        "status": "ok",
        "contact_min_mm": float(np.min(d_mm)),
        "contact_p5_mm": float(np.percentile(d_mm, 5)),
        "contact_mean_mm": float(np.mean(d_mm)),
        "contact_count_5mm": int(np.sum(d_mm <= 5.0)),
        "components": int(len(comps)),
        "largest_component_fraction": largest_fraction,
        "bbox_diag_mm": bbox_diag_mm,
        "igl_available": bool(igl is not None),
    })

    if igl is not None and len(hand.faces) > 0 and len(obj.faces) > 0:
        obj_to_hand_sd = igl.signed_distance(obj_v, hand_v, np.asarray(hand.faces))[0]
        hand_to_obj_sd = igl.signed_distance(hand_v, obj_v, np.asarray(obj.faces))[0]

        obj_inside_hand = obj_to_hand_sd < 0
        hand_inside_obj = hand_to_obj_sd < 0

        row.update({
            "object_inside_hand_ratio": float(np.mean(obj_inside_hand)),
            "object_inside_hand_max_depth_mm": float(np.max((-obj_to_hand_sd[obj_inside_hand]) * 1000.0)) if np.any(obj_inside_hand) else 0.0,
            "hand_inside_object_ratio": float(np.mean(hand_inside_obj)),
            "hand_inside_object_max_depth_mm": float(np.max((-hand_to_obj_sd[hand_inside_obj]) * 1000.0)) if np.any(hand_inside_obj) else 0.0,
        })
    else:
        row.update({
            "object_inside_hand_ratio": None,
            "object_inside_hand_max_depth_mm": None,
            "hand_inside_object_ratio": None,
            "hand_inside_object_max_depth_mm": None,
        })

    severe_floating = row["contact_p5_mm"] > 20.0
    severe_penetration = False
    if row["object_inside_hand_ratio"] is not None:
        severe_penetration = (
            row["object_inside_hand_ratio"] > 0.03 or
            row["hand_inside_object_ratio"] > 0.20 or
            row["object_inside_hand_max_depth_mm"] > 10.0 or
            row["hand_inside_object_max_depth_mm"] > 10.0
        )

    low_integrity = False
    if largest_fraction is not None:
        low_integrity = (len(comps) > 100) or (largest_fraction < 0.65)

    if severe_penetration:
        gate = "reject_severe_penetration"
    elif severe_floating:
        gate = "reject_severe_floating"
    elif low_integrity:
        gate = "warning_low_integrity"
    else:
        gate = "pass"

    row["severe_floating"] = bool(severe_floating)
    row["severe_penetration"] = bool(severe_penetration)
    row["low_integrity"] = bool(low_integrity)
    row["selector_v4_gate"] = gate

    rows.append(row)

out = pd.DataFrame(rows)
csv_path = OUT_DIR / "arctic5_selector_physical_metrics.csv"
json_path = OUT_DIR / "arctic5_selector_physical_metrics.json"

out.to_csv(csv_path, index=False)
json_path.write_text(json.dumps(rows, indent=2))

print("[OK] wrote", csv_path)
print("[OK] wrote", json_path)
print(out[[
    "case", "method", "exists", "contact_p5_mm", "contact_mean_mm",
    "object_inside_hand_ratio", "hand_inside_object_ratio",
    "components", "largest_component_fraction", "selector_v4_gate"
]].to_string(index=False))
