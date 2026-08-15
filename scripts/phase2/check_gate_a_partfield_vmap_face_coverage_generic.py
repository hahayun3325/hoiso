from pathlib import Path
import argparse
import json
import numpy as np
import trimesh

def faces_from_vertex_ids(mesh, vertex_ids):
    vertex_ids = set(map(int, vertex_ids))
    face_ids = []
    for i, face in enumerate(mesh.faces):
        hit = sum(int(v) in vertex_ids for v in face)
        if hit >= 2:
            face_ids.append(i)
    return np.asarray(face_ids, dtype=np.int64)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-root", required=True)
    ap.add_argument("--merge-json", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    case_root = Path(args.case_root)
    source_path = case_root / "partfield/input_mesh_low30k/00000.obj"
    pfsep = case_root / "partfield/partseps_low30k"
    merge_path = Path(args.merge_json)
    out_path = Path(args.out)

    source = trimesh.load(source_path, force="mesh", process=False)
    merge = json.loads(merge_path.read_text())

    part_face_sets = {}
    all_faces = []

    for part_name, cluster_ids in merge["physical_parts"].items():
        vertex_ids = []
        for cid in cluster_ids:
            arr = np.load(pfsep / f"00000_part_{cid}_vmap.npy", allow_pickle=True).astype(int).reshape(-1)
            vertex_ids.extend(arr.tolist())
        face_ids = faces_from_vertex_ids(source, np.unique(vertex_ids))
        part_face_sets[part_name] = set(face_ids.tolist())
        all_faces.extend(face_ids.tolist())

    unique_faces = set(all_faces)
    duplicate_count = len(all_faces) - len(unique_faces)

    report = {
        "case": merge["case"],
        "source_faces": int(len(source.faces)),
        "part_face_counts": {k: len(v) for k, v in part_face_sets.items()},
        "selected_faces_total_with_duplicates": int(len(all_faces)),
        "selected_faces_unique": int(len(unique_faces)),
        "duplicate_boundary_faces": int(duplicate_count),
        "unique_face_coverage_ratio": float(len(unique_faces) / max(len(source.faces), 1)),
        "duplicate_ratio_over_selected": float(duplicate_count / max(len(all_faces), 1))
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
