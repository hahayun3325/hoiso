from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
out_dir = case_root / "gt_reference/frame_consistency"
out_dir.mkdir(parents=True, exist_ok=True)

items = [
    ("phase0 input", Path("/home/fredcui/foho_phase0/inputs/arctic_phase017/alapuse01.jpg")),
    ("official GT 2D overlay", Path("/home/fredcui/foho_phase0/inspection/arctic_phase017/gt_overlay_all_cases/alapuse01_gt_2d_official_overlay.jpg")),
    ("selector_v41 full image", Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/original_imgs/alapuse01_full_image_1.png")),
    ("selector_v41 cropped HOI", Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/cropped_hoi_imgs/alapuse01_cropped_hoi_1.png")),
    ("selector_v41 HaMeR all", Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/hamer_out/alapuse01_all.jpg")),
]

thumbs = []
W, H = 420, 360

for title, p in items:
    if not p.exists():
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((10, 10), f"MISSING:\n{p}", fill=(255, 0, 0))
    else:
        im = Image.open(p).convert("RGB")
        im.thumbnail((W, H - 40))
        img = Image.new("RGB", (W, H), "white")
        x = (W - im.width) // 2
        y = 35
        img.paste(im, (x, y))
        d = ImageDraw.Draw(img)
        d.text((10, 10), title, fill=(0, 0, 0))
    thumbs.append(img)

panel = Image.new("RGB", (W * len(thumbs), H), "white")
for i, img in enumerate(thumbs):
    panel.paste(img, (i * W, 0))

out = out_dir / "alapuse01_frame_consistency_panel.jpg"
panel.save(out, quality=95)
print("[OK] wrote", out)
