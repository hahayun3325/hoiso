from pathlib import Path
import argparse
import json
import numpy as np
import trimesh

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    case_root = Path(args.case_root)
    pfsep = case_root / "partfield/partseps_low30k"
    out_path = Path(args.out)

    rows = []
    for ply in sorted(pfsep.glob("00000_part_*.ply")):
        if "_vmap" in ply.name:
            continue
        cluster_id = int(ply.stem.split("_part_")[-1])
        mesh = trimesh.load(ply, force="mesh", process=False)
        bounds = mesh.bounds
        extent = bounds[1] - bounds[0]
        center = mesh.centroid

        vmap = pfsep / f"00000_part_{cluster_id}_vmap.npy"
        n_vmap = 0
        if vmap.exists():
            n_vmap = len(np.load(vmap, allow_pickle=True).reshape(-1))

        rows.append({
            "cluster_id": cluster_id,
            "ply": str(ply),
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "vmap_vertices": int(n_vmap),
            "center": center.tolist(),
            "bounds": bounds.tolist(),
            "bbox_size": extent.tolist()
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))

if __name__ == "__main__":
    main()
