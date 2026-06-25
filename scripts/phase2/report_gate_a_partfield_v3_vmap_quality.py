from pathlib import Path
import json
import trimesh
import numpy as np

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/aket01")
source_path = case_root / "partfield/input_mesh_low30k/00000.obj"
part_dir = case_root / "part_meshes_partfield_v3_vmap"
manifest_path = part_dir / "part_manifest.json"
out_path = case_root / "metrics/gate_a_partfield_v3_vmap_quality_report.json"

source = trimesh.load(source_path, force="mesh", process=False)
manifest = json.loads(manifest_path.read_text())

parts = []
for name, info in manifest["parts"].items():
    p = Path(info["path"])
    if p.exists():
        parts.append(trimesh.load(p, force="mesh", process=False))

merged = trimesh.util.concatenate(parts)

source_bounds = source.bounds
merged_bounds = merged.bounds
source_extent = source_bounds[1] - source_bounds[0]
merged_extent = merged_bounds[1] - merged_bounds[0]

report = {
    "case": "aket01",
    "reference": "low30k_source_obj",
    "source_mesh": {
        "path": str(source_path),
        "vertices": int(len(source.vertices)),
        "faces": int(len(source.faces)),
        "bounds": source_bounds.tolist(),
        "bbox_size": source_extent.tolist()
    },
    "partfield_v3_vmap_merged": {
        "path": str(part_dir),
        "vertices": int(len(merged.vertices)),
        "faces": int(len(merged.faces)),
        "bounds": merged_bounds.tolist(),
        "bbox_size": merged_extent.tolist(),
        "num_named_parts": len(parts),
        "part_names": list(manifest["parts"].keys())
    },
    "face_coverage_ratio_vs_low30k": float(len(merged.faces) / max(len(source.faces), 1)),
    "bbox_size_ratio": (merged_extent / np.maximum(source_extent, 1e-8)).tolist(),
    "note": "v3 keeps residual_uncertain to preserve geometry for Gate A no-regression."
}

out_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
