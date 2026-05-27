from pathlib import Path
import trimesh

comp_dir = Path.home() / "foho_phase0/inspection/prompt_ablation/components"
out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation/components_render"
out_dir.mkdir(parents=True, exist_ok=True)

for path in sorted(comp_dir.glob("*.ply")):
    mesh = trimesh.load(path, process=False)
    png = mesh.scene().save_image(resolution=(1024, 1024))
    out = out_dir / f"{path.stem}.png"
    out.write_bytes(png)
    print("[OK]", out)
