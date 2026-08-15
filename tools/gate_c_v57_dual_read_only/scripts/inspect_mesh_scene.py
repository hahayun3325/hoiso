#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def mesh_summary(mesh: trimesh.Trimesh) -> dict:
    ext = np.asarray(mesh.extents, dtype=float)
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "centroid": np.asarray(mesh.centroid, dtype=float).tolist(),
        "extents": ext.tolist(),
        "diagonal": float(np.linalg.norm(ext)),
        "is_watertight": bool(mesh.is_watertight),
        "euler_number": int(mesh.euler_number),
        "components": int(len(mesh.split(only_watertight=False))),
    }


def load_world(path: Path):
    obj = trimesh.load(path, process=False)
    scene_info = {"type": type(obj).__name__, "nodes": []}
    if isinstance(obj, trimesh.Scene):
        for node_name in obj.graph.nodes_geometry:
            transform, geom_name = obj.graph[node_name]
            scene_info["nodes"].append({
                "node": str(node_name),
                "geometry": str(geom_name),
                "transform": np.asarray(transform, dtype=float).tolist(),
            })
        dumped = obj.dump(concatenate=True)
        if isinstance(dumped, list):
            if not dumped:
                raise ValueError("scene_has_no_mesh_geometry")
            mesh = trimesh.util.concatenate([x for x in dumped if isinstance(x, trimesh.Trimesh)])
        else:
            mesh = dumped
    elif isinstance(obj, trimesh.Trimesh):
        mesh = obj
    else:
        raise TypeError(f"unsupported_geometry:{type(obj).__name__}")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("world_geometry_not_mesh")
    return mesh, scene_info


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    path = Path(args.input)
    out = Path(args.out)
    report = {"schema": "mesh_scene_inspection_v1", "path": str(path)}
    try:
        if not path.is_file():
            raise FileNotFoundError(path)
        mesh, scene = load_world(path)
        report.update(status="PASS", sha256=sha256(path), scene=scene, world_mesh=mesh_summary(mesh))
    except Exception as exc:
        report.update(status="HOLD", error=f"{type(exc).__name__}:{exc}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
