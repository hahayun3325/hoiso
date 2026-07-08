"""Split a single N-cluster PartField labeled mesh into per-cluster part
files + vertex maps, matching aket01's partseps_low30k/00000_part_{id}.ply
+ _vmap.npy convention. Labels from run_part_clustering.py are PER-FACE,
not per-vertex — confirmed via shape mismatch (label count == face count)."""
from pathlib import Path
import argparse
import numpy as np
import trimesh

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-mesh", required=True, help="low30k source .obj")
    ap.add_argument("--cluster-labels", required=True, help="cluster_out/00000_0_NN.npy")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load(args.source_mesh, force="mesh", process=False)
    labels = np.load(args.cluster_labels, allow_pickle=True).reshape(-1)

    print(f"[INFO] mesh: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
          f"labels: {labels.shape}, unique clusters: {sorted(set(labels.tolist()))}")

    if len(labels) == len(mesh.faces):
        print("[INFO] confirmed: labels are PER-FACE")
        per_face = True
    elif len(labels) == len(mesh.vertices):
        print("[INFO] confirmed: labels are PER-VERTEX")
        per_face = False
    else:
        raise SystemExit(
            f"[ERROR] label count ({len(labels)}) matches neither face count "
            f"({len(mesh.faces)}) nor vertex count ({len(mesh.vertices)})."
        )

    # Also write a correctly per-face-colored visualization while we're at it.
    import matplotlib.cm as cm
    unique = sorted(set(labels.tolist()))
    cmap = cm.get_cmap("tab20", len(unique))
    color_lookup = {cid: (np.array(cmap(i)[:3]) * 255).astype(np.uint8) for i, cid in enumerate(unique)}

    for cid in unique:
        if per_face:
            face_ids = np.where(labels == cid)[0]
            vertex_ids = np.unique(mesh.faces[face_ids].reshape(-1))
        else:
            vertex_ids = np.where(labels == cid)[0]
            face_mask = np.isin(mesh.faces, vertex_ids).sum(axis=1) >= 2
            face_ids = np.where(face_mask)[0]

        if len(face_ids) == 0:
            print(f"[WARN] cluster {cid}: no faces, skipping")
            continue
        sub = mesh.submesh([face_ids], append=True, repair=False)
        sub.export(out_dir / f"00000_part_{cid}.ply")
        np.save(out_dir / f"00000_part_{cid}_vmap.npy", vertex_ids)
        print(f"[OK] cluster {cid}: {len(vertex_ids)} verts, {len(face_ids)} faces")

    # Corrected full-mesh visualization, colored per-face this time.
    face_colors = np.zeros((len(mesh.faces), 4), dtype=np.uint8)
    face_colors[:, 3] = 255
    for cid in unique:
        idx = np.where(labels == cid)[0] if per_face else None
        if idx is not None:
            face_colors[idx, :3] = color_lookup[cid]
    viz = mesh.copy()
    viz.visual.face_colors = face_colors
    viz_path = out_dir / f"00000_clusters_colored_CORRECTED.ply"
    viz.export(viz_path)
    print(f"[OK] wrote corrected per-face-colored viz: {viz_path}")

if __name__ == "__main__":
    main()
