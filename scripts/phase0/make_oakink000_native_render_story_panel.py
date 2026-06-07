from pathlib import Path
from PIL import Image, ImageDraw
import argparse

def find_debug_dir(run_dir):
    hits = sorted((run_dir / "foho_debug").glob("*"))
    hits = [p for p in hits if p.is_dir()]
    return hits[-1] if hits else None

def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

def card(path, title, subtitle="", size=(360, 300)):
    w, h = size
    im_card = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im_card)
    d.text((8, 8), title, fill=(0, 0, 0))
    d.text((8, 28), subtitle[:60], fill=(90, 90, 90))

    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((w - 20, h - 70))
        im_card.paste(im, ((w - im.width)//2, 55))
        d.text((8, h - 18), Path(path).name[:48], fill=(90, 90, 90))
    else:
        d.text((w//2 - 40, h//2), "MISSING", fill=(200, 0, 0))
    return im_card

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    run_dir = Path.home() / "foho_phase0/runs" / args.run_id
    debug_dir = find_debug_dir(run_dir)

    crop = first_existing([
        run_dir / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        run_dir / "cropped_hoi_imgs_wo_bckg/oakink_cropped_hoi_wo_bckg_1.png",
    ])
    inpaint = first_existing([
        run_dir / "ours_inpaint/oakink_inpainted_object.png",
        run_dir / "ours_inpaint/oakink_inpainted.png",
    ])

    images = [
        (crop, "1. HOI crop", "pipeline input crop"),
        (inpaint, "2. Inpaint", "LLM prompt + FLUX"),
        (run_dir / "moge_out/oakink_cropped_hoi/depth_vis.png", "3. MoGe depth", "geometry prior"),
        (run_dir / "moge_out/oakink_cropped_hoi/normal.png", "4. MoGe normal", "target normal"),
        (debug_dir / "rendered_obj_normal_t3_opt0.png" if debug_dir else None, "5. Object native render", "object-only optimization view"),
        (debug_dir / "rendered_normal_t3.png" if debug_dir else None, "6. HOI native render t3", "hand + object"),
        (debug_dir / "rendered_normal_t4.png" if debug_dir else None, "7. HOI native render t4", "after object update"),
        (debug_dir / "rendered_normal_t5.png" if debug_dir else None, "8. HOI native render t5", "later guidance"),
    ]

    cols = 4
    card_w, card_h = 360, 300
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * card_w, rows * card_h + 70), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), f"OakInk000 native render story: {args.label or args.run_id}", fill=(0, 0, 0))
    d.text((10, 34), "Uses pipeline-saved native renderings, not custom PLY camera views.", fill=(140, 0, 0))

    for i, (p, title, subtitle) in enumerate(images):
        c = card(p, title, subtitle, (card_w, card_h))
        x = (i % cols) * card_w
        y = 70 + (i // cols) * card_h
        sheet.paste(c, (x, y))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=95)
    print("[OK] wrote", out)

if __name__ == "__main__":
    main()
