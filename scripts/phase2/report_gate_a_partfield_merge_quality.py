from pathlib import Path
import json
import trimesh
import numpy as np

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/aket01")
single_path = case_root / "input/final_object_singleblob.ply"
part_dir = case_root / "part_meshes_partfield_v2"
manifest_path = part_dir / "part_manifest.json"
out_path = case_root / "metrics/gate_a_partfield_v2_quality_report.json"

single = trimesh.load(single_path, force="mesh", process=False)
manifest = json.loads(manifest_path.read_text())

parts = []
for name, info in manifest["parts"].items():
    p = Path(info["path"])
    if p.exists():
        parts.append(trimesh.load(p, force="mesh", process=False))

merged = trimesh.util.concatenate(parts)

single_bounds = single.bounds
merged_bounds = merged.bounds

report = {
    "case": "aket01",
    "single_blob": {
        "path": str(single_path),
        "vertices": int(len(single.vertices)),
        "faces": int(len(single.faces)),
        "bounds": single_bounds.tolist()
    },
    "partfield_merged": {
        "path": str(part_dir),
        "vertices": int(len(merged.vertices)),
        "faces": int(len(merged.faces)),
        "bounds": merged_bounds.tolist(),
        "num_named_parts": len(parts),
        "part_names": list(manifest["parts"].keys())
    },
    "bbox_size_single": (single_bounds[1] - single_bounds[0]).tolist(),
    "bbox_size_merged": (merged_bounds[1] - merged_bounds[0]).tolist(),
    "note": "This checks whether PartField merged parts preserve a reasonable object extent. It is not a GT CD/F-score evaluation yet."
}

out_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
