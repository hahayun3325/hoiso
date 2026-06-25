from pathlib import Path
import json
import numpy as np
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/aket01")
source_path = case_root / "partfield/input_mesh_low30k/00000.obj"
pfsep = case_root / "partfield/partseps_low30k"
merge_path = case_root / "partfield/aket01_cluster_merge_manual_v3_geometry_preserving.json"
out_path = case_root / "metrics/gate_a_partfield_v3_vmap_face_coverage_detail.json"

source = trimesh.load(source_path, force="mesh", process=False)
merge = json.loads(merge_path.read_text())

def faces_from_vertex_ids(mesh, vertex_ids):
    vertex_ids = set(map(int, vertex_ids))
    face_ids = []
    for i, face in enumerate(mesh.faces):
        hit = sum(int(v) in vertex_ids for v in face)
        if hit >= 2:
            face_ids.append(i)
    return np.asarray(face_ids, dtype=np.int64)

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
    "case": "aket01",
    "source_faces": int(len(source.faces)),
    "part_face_counts": {k: len(v) for k, v in part_face_sets.items()},
    "selected_faces_total_with_duplicates": int(len(all_faces)),
    "selected_faces_unique": int(len(unique_faces)),
    "duplicate_boundary_faces": int(duplicate_count),
    "unique_face_coverage_ratio": float(len(unique_faces) / max(len(source.faces), 1)),
    "duplicate_ratio_over_selected": float(duplicate_count / max(len(all_faces), 1))
}

out_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
