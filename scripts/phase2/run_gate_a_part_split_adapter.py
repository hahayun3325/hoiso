from pathlib import Path
import argparse, json
import numpy as np
import trimesh

def export_part(mesh, face_ids, out_path):
    face_ids = np.asarray(face_ids, dtype=np.int64)
    if len(face_ids) == 0:
        return None
    sub = mesh.submesh([face_ids], append=True, repair=False)
    sub.export(out_path)
    return {
        "path": str(out_path),
        "num_vertices": int(len(sub.vertices)),
        "num_faces": int(len(sub.faces)),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--object-mesh", required=True)
    ap.add_argument("--part-schema", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--mode", default="schema_bbox", choices=["schema_bbox"])
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load(args.object_mesh, force="mesh", process=False)
    schema = json.loads(Path(args.part_schema).read_text())
    part_names = [p["part_name"] for p in schema["main_parts"]]

    face_centers = mesh.triangles_center
    z = face_centers[:, 2]
    zmin, zmax = float(z.min()), float(z.max())
    zn = (z - zmin) / max(zmax - zmin, 1e-8)

    # aket01 smoke-test split:
    # lower/middle object -> body, upper-middle -> neck, top -> cap.
    # label_face is represented as a copy/subset of front-ish body faces for now.
    labels = {}
    if args.case == "aket01":
        labels["body"] = np.where(zn <= 0.78)[0]
        labels["neck"] = np.where((zn > 0.78) & (zn <= 0.90))[0]
        labels["cap"] = np.where(zn > 0.90)[0]
        labels["label_face"] = labels["body"]
    else:
        # fallback: export whole mesh as first part only
        labels[part_names[0]] = np.arange(len(mesh.faces))

    manifest = {
        "case": args.case,
        "mode": args.mode,
        "object_mesh": args.object_mesh,
        "part_schema": args.part_schema,
        "note": "schema_bbox is a smoke-test split, not final PartField/SAM2 result.",
        "parts": {}
    }

    for name in part_names:
        if name not in labels:
            manifest["parts"][name] = {
                "path": None,
                "num_vertices": 0,
                "num_faces": 0,
                "status": "not_exported_in_schema_bbox_mode"
            }
            continue

        out_path = out_dir / f"{name}.ply"
        info = export_part(mesh, labels[name], out_path)
        if info is None:
            info = {"path": None, "num_vertices": 0, "num_faces": 0}
        info["status"] = "exported"
        manifest["parts"][name] = info

    manifest_path = out_dir / "part_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Export a simple combined scene for visual checking.
    scene = trimesh.Scene()
    for name, info in manifest["parts"].items():
        if info["path"] and Path(info["path"]).exists():
            scene.add_geometry(trimesh.load(info["path"], force="mesh"), node_name=name)
    scene.export(out_dir / "part_scene.glb")

    print(json.dumps(manifest, indent=2))
    print("[OK] wrote", manifest_path)
    print("[OK] wrote", out_dir / "part_scene.glb")

if __name__ == "__main__":
    main()
