from pathlib import Path
import argparse
import json
import trimesh
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-root", required=True)
    ap.add_argument("--part-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    case_root = Path(args.case_root)
    source_path = case_root / "partfield/input_mesh_low30k/00000.obj"
    part_dir = Path(args.part_dir)
    manifest_path = part_dir / "part_manifest.json"
    out_path = Path(args.out)

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
        "case": manifest["case"],
        "reference": "low30k_source_obj",
        "source_mesh": {
            "path": str(source_path),
            "vertices": int(len(source.vertices)),
            "faces": int(len(source.faces)),
            "bounds": source_bounds.tolist(),
            "bbox_size": source_extent.tolist()
        },
        "partfield_vmap_merged": {
            "path": str(part_dir),
            "vertices": int(len(merged.vertices)),
            "faces": int(len(merged.faces)),
            "bounds": merged_bounds.tolist(),
            "bbox_size": merged_extent.tolist(),
            "num_named_parts": len(parts),
            "part_names": list(manifest["parts"].keys())
        },
        "face_coverage_ratio_vs_low30k_with_duplicates": float(len(merged.faces) / max(len(source.faces), 1)),
        "bbox_size_ratio": (merged_extent / np.maximum(source_extent, 1e-8)).tolist(),
        "note": "Coordinate-consistent sanity check using low30k source mesh and vmap-exported named parts."
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
