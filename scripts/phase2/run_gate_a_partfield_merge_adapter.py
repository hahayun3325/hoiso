from pathlib import Path
import argparse
import json
import trimesh

def load_cluster(pfsep: Path, cluster_id: int):
    path = pfsep / f"00000_part_{cluster_id}.ply"
    if not path.exists():
        raise FileNotFoundError(path)
    return trimesh.load(path, force="mesh", process=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--pfsep", required=True)
    ap.add_argument("--merge-json", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    pfsep = Path(args.pfsep)
    merge = json.loads(Path(args.merge_json).read_text())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "case": args.case,
        "source": "partfield_low30k",
        "merge_json": args.merge_json,
        "note": "Named part meshes are produced by manual merging of PartField over-segmented clusters.",
        "parts": {}
    }

    scene = trimesh.Scene()

    for part_name, cluster_ids in merge["physical_parts"].items():
        if part_name == "noise_or_uncertain":
            continue
        meshes = [load_cluster(pfsep, cid) for cid in cluster_ids]
        merged = trimesh.util.concatenate(meshes)
        out_path = out_dir / f"{part_name}.ply"
        merged.export(out_path)

        scene.add_geometry(merged, node_name=part_name)

        manifest["parts"][part_name] = {
            "cluster_ids": cluster_ids,
            "path": str(out_path),
            "num_vertices": int(len(merged.vertices)),
            "num_faces": int(len(merged.faces))
        }

    manifest_path = out_dir / "part_manifest.json"
    scene_path = out_dir / "part_scene.glb"

    manifest_path.write_text(json.dumps(manifest, indent=2))
    scene.export(scene_path)

    print(json.dumps(manifest, indent=2))
    print("[OK] wrote", manifest_path)
    print("[OK] wrote", scene_path)

if __name__ == "__main__":
    main()
