from pathlib import Path
import argparse
import trimesh

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pfsep", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pfsep = Path(args.pfsep)
    out = Path(args.out)

    colors = [
        [255, 80, 80, 255],
        [80, 255, 80, 255],
        [80, 80, 255, 255],
        [255, 255, 80, 255],
        [255, 80, 255, 255],
        [80, 255, 255, 255],
        [255, 160, 80, 255],
        [160, 80, 255, 255],
    ]

    scene = trimesh.Scene()

    ply_files = []
    for p in sorted(pfsep.glob("00000_part_*.ply")):
        if "_vmap" not in p.name:
            ply_files.append(p)

    for i, ply in enumerate(ply_files):
        mesh = trimesh.load(ply, force="mesh", process=False)
        mesh.visual.vertex_colors = colors[i % len(colors)]
        scene.add_geometry(mesh, node_name=f"part_{i}")

    out.parent.mkdir(parents=True, exist_ok=True)
    scene.export(out)

    print("[OK] wrote", out)
    print("num_parts:", len(ply_files))

if __name__ == "__main__":
    main()
