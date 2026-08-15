from pathlib import Path
import argparse
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

parser = argparse.ArgumentParser()
parser.add_argument("--case", required=True)
parser.add_argument("--run-root", required=True)
parser.add_argument("--out-root", required=True)
args = parser.parse_args()

case = args.case
run_root = Path(args.run_root)
out_root = Path(args.out_root)
(out_root / "metrics").mkdir(parents=True, exist_ok=True)
(out_root / "visuals").mkdir(parents=True, exist_ok=True)

hand_path = run_root / "guidance_out" / f"{case}_hand.ply"
obj_path = run_root / "guidance_out" / f"{case}_obj.ply"

report = {
    "case": case,
    "run_root": str(run_root),
    "hand_path": str(hand_path),
    "obj_path": str(obj_path),
    "exists": {
        "hand": hand_path.exists(),
        "object": obj_path.exists(),
    },
}

if not hand_path.exists() or not obj_path.exists():
    report["decision"] = "FAIL_MISSING_GUIDANCE_OUT"
    (out_root / "metrics" / f"{case}_triage_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0)

hand = trimesh.load(hand_path, process=False)
obj = trimesh.load(obj_path, process=False)

if isinstance(hand, trimesh.Scene):
    hand = trimesh.util.concatenate([g for g in hand.geometry.values() if hasattr(g, "vertices")])
if isinstance(obj, trimesh.Scene):
    obj = trimesh.util.concatenate([g for g in obj.geometry.values() if hasattr(g, "vertices")])

hand_ext = hand.bounding_box.extents
obj_ext = obj.bounding_box.extents

report["bbox"] = {
    "hand_extents": hand_ext.tolist(),
    "object_extents": obj_ext.tolist(),
    "hand_longest": float(hand_ext.max()),
    "object_longest": float(obj_ext.max()),
    "object_over_hand_longest_ratio": float(obj_ext.max() / max(hand_ext.max(), 1e-8)),
}

# MANO fingertip indices used in earlier checks.
fingertip_idx = [744, 320, 443, 554, 671]
fingertip_names = ["thumb", "index", "middle", "ring", "pinky"]

if len(hand.vertices) > max(fingertip_idx):
    fingertips = np.asarray(hand.vertices)[fingertip_idx]
    tree = cKDTree(np.asarray(obj.vertices))
    d, _ = tree.query(fingertips)
    report["fingertip_to_object_cm"] = {
        name: float(dist * 100.0) for name, dist in zip(fingertip_names, d)
    }
    report["fingertip_min_cm"] = float(d.min() * 100.0)
    report["fingertip_mean_cm"] = float(d.mean() * 100.0)
else:
    report["fingertip_error"] = f"hand has only {len(hand.vertices)} vertices"

components = obj.split(only_watertight=False)
components = sorted(components, key=lambda c: -len(c.vertices))
report["num_components"] = len(components)
report["top_components"] = []
for i, c in enumerate(components[:8]):
    report["top_components"].append({
        "rank": i,
        "vertices": int(len(c.vertices)),
        "vertex_fraction": float(len(c.vertices) / max(len(obj.vertices), 1)),
        "bbox_extents": c.bounding_box.extents.tolist(),
        "bbox_longest": float(c.bounding_box.extents.max()),
        "bbox_centroid": c.bounding_box.centroid.tolist(),
    })

# Simple triage decision.
min_cm = report.get("fingertip_min_cm", 1e9)
obj_long = report["bbox"]["object_longest"]
ratio = report["bbox"]["object_over_hand_longest_ratio"]

if min_cm <= 12.5 and obj_long < 1.0 and ratio < 4.0:
    decision = "PASS_SHARED_FRAME_CANDIDATE"
elif obj_long > 1.5 or ratio >= 4.0:
    decision = "FAIL_OVERSIZED_OR_CONTAMINATED_OBJECT"
else:
    decision = "FAIL_DISTANCE_OR_VISUAL_CHECK_NEEDED"

report["decision"] = decision

# Export visual scene.
hand.visual.vertex_colors = [255, 80, 80, 180]
obj.visual.vertex_colors = [80, 140, 255, 180]
scene = trimesh.Scene([obj, hand])
scene_path = out_root / "visuals" / f"{case}_triage_hand_vs_object.glb"
scene.export(scene_path)
report["visual_scene"] = str(scene_path)

(out_root / "metrics" / f"{case}_triage_report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
