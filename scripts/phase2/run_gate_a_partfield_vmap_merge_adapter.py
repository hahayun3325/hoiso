from pathlib import Path
import argparse
import json
import numpy as np
import trimesh

def faces_from_vertex_ids(mesh, vertex_ids):
    vertex_ids = set(map(int, vertex_ids))
    face_ids = []
    for i, face in enumerate(mesh.faces):
        # Keep face if at least 2 of 3 vertices belong to this cluster.
        hit = sum(int(v) in vertex_ids for v in face)
        if hit >= 2:
            face_ids.append(i)
    return np.asarray(face_ids, dtype=np.int64)

def export_part_from_vmaps(source_mesh, pfsep, cluster_ids, out_path):
    all_vertex_ids = []
    for cid in cluster_ids:
        vmap_path = pfsep / f"00000_part_{cid}_vmap.npy"
        if not vmap_path.exists():
            raise FileNotFoundError(vmap_path)
        arr = np.load(vmap_path, allow_pickle=True).astype(int).reshape(-1)
        all_vertex_ids.extend(arr.tolist())

    all_vertex_ids = np.unique(np.asarray(all_vertex_ids, dtype=np.int64))
    face_ids = faces_from_vertex_ids(source_mesh, all_vertex_ids)

    if len(face_ids) == 0:
        raise RuntimeError(f"No faces selected for {out_path}")

    part_mesh = source_mesh.submesh([face_ids], append=True, repair=False)
    part_mesh.export(out_path)

    return {
        "path": str(out_path),
        "cluster_ids": cluster_ids,
        "num_vmap_vertices": int(len(all_vertex_ids)),
        "num_faces": int(len(part_mesh.faces)),
        "num_vertices": int(len(part_mesh.vertices))
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--source-mesh", required=True)
    ap.add_argument("--pfsep", required=True)
    ap.add_argument("--merge-json", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    source_mesh = trimesh.load(args.source_mesh, force="mesh", process=False)
    pfsep = Path(args.pfsep)
    merge = json.loads(Path(args.merge_json).read_text())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scene = trimesh.Scene()
    manifest = {
        "case": args.case,
        "source": "partfield_low30k_vmap",
        "source_mesh": args.source_mesh,
        "merge_json": args.merge_json,
        "note": "Part meshes are exported from source OBJ using PartField vmap vertex ids, preserving source coordinates.",
        "parts": {}
    }

    for part_name, cluster_ids in merge["physical_parts"].items():
        if part_name == "noise_or_uncertain":
            continue
        out_path = out_dir / f"{part_name}.ply"
        info = export_part_from_vmaps(source_mesh, pfsep, cluster_ids, out_path)
        manifest["parts"][part_name] = info
        scene.add_geometry(trimesh.load(out_path, force="mesh", process=False), node_name=part_name)

    manifest_path = out_dir / "part_manifest.json"
    scene_path = out_dir / "part_scene.glb"

    manifest_path.write_text(json.dumps(manifest, indent=2))
    scene.export(scene_path)

    print(json.dumps(manifest, indent=2))
    print("[OK] wrote", manifest_path)
    print("[OK] wrote", scene_path)

if __name__ == "__main__":
    main()
