from pathlib import Path

roots = [Path("src"), Path("scripts"), Path("third_party/Hunyuan3D-2")]
patterns = [
    "rendered_normal",
    "rendered_obj_normal",
    "foho_debug",
    "save_image",
    "plt.savefig",
    "imageio",
    "normal_map",
    "silhouette",
    "faces_per_pixel",
    "MeshRenderer",
    "RasterizationSettings",
    "FoVPerspectiveCameras",
    "look_at_view_transform",
    "TexturesVertex",
    "SoftSilhouetteShader",
    "HardPhongShader",
    "pyrender",
]

out = Path.home() / "foho_phase0/inspection/rendering_code_search/rendering_keywords_no_rg.txt"
out.parent.mkdir(parents=True, exist_ok=True)

lines_out = []
for root in roots:
    if not root.exists():
        continue
    for p in root.rglob("*.py"):
        try:
            text = p.read_text(errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(text, start=1):
            if any(k in line for k in patterns):
                lines_out.append(f"{p}:{i}: {line}")

out.write_text("\n".join(lines_out) + "\n")
print("[OK] wrote", out)
print("[INFO] hits:", len(lines_out))
