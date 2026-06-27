from pathlib import Path
import json
import numpy as np

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

verified_path = root / "gate_b_contact/metrics/gate_c_verified_contact_v1.json"
patch_report_path = root / "gate_b_contact/metrics/gate_c_finger_patch_local_region_check.json"
out_path = root / "gate_d_optimization/targets/gate_d_contact_target_dryrun_v1.json"

if not verified_path.exists():
    raise FileNotFoundError(f"Missing verified contact JSON: {verified_path}")
if not patch_report_path.exists():
    raise FileNotFoundError(f"Missing patch report JSON: {patch_report_path}")

verified = json.loads(verified_path.read_text())
patch = json.loads(patch_report_path.read_text())

hand_xyz = np.asarray(patch["nearest_hand_xyz"], dtype=float)
region_xyz = np.asarray(patch["nearest_region_xyz"], dtype=float)

vec = region_xyz - hand_xyz
dist = float(np.linalg.norm(vec))
unit = (vec / max(dist, 1e-8)).tolist()

out = {
    "case_id": case,
    "target_type": "dryrun_contact_attraction_target",
    "source_verified_contact": verified["verified_contacts"][0],
    "contact_pair": {
        "hand": "right",
        "finger": "index",
        "object_region": "base_edge_or_hinge_region",
        "support_parts": ["keyboard_base", "hinge"]
    },
    "nearest_hand_xyz": hand_xyz.tolist(),
    "nearest_region_xyz": region_xyz.tolist(),
    "distance": dist,
    "attraction_direction_hand_to_object": unit,
    "gate_d_allowed_action": "dryrun_only",
    "should_modify_meshes": False,
    "note": "This prepares the contact target for Gate D. It does not optimize or move the hand/object."
}

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, indent=2))

print(json.dumps(out, indent=2))
print("[OK] wrote", out_path)
