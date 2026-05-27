from pathlib import Path
import trimesh

run = Path.home() / "foho_phase0/runs/smoke_018_prompt_rect_guidance_debug_exports"
out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke018_debug_renders"
out_dir.mkdir(parents=True, exist_ok=True)

mesh_paths = list((run / "foho_debug").rglob("*.ply"))
mesh_paths += list((run / "guidance_out").rglob("*.ply"))

for path in sorted(mesh_paths):
    try:
        mesh = trimesh.load(path, process=False)
        scene = mesh if isinstance(mesh, trimesh.Scene) else mesh.scene()
        rel = path.relative_to(run).as_posix().replace("/", "__").replace(".", "_")
        out = out_dir / f"{rel}.png"
        out.write_bytes(scene.save_image(resolution=(1024, 1024)))
        print("[OK]", path, "->", out)
    except Exception as e:
        print("[BAD]", path, repr(e))
