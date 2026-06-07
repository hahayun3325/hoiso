from pathlib import Path
from PIL import Image, ImageDraw
import argparse
import textwrap

def find_debug_dir(run_dir):
    hits = sorted((run_dir / "foho_debug").glob("*"))
    hits = [p for p in hits if p.is_dir()]
    return hits[-1] if hits else None

def image_card(path, title, size=(320, 260)):
    w, h = size
    card = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(card)
    d.text((8, 8), title, fill=(0, 0, 0))
    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((w - 16, h - 42))
        card.paste(im, ((w - im.width)//2, 36))
        d.text((8, h - 18), Path(path).name[:45], fill=(80, 80, 80))
    else:
        d.text((w//2 - 40, h//2), "MISSING", fill=(200, 0, 0))
    return card

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    run_dir = Path.home() / "foho_phase0/runs" / args.run_id
    debug_dir = find_debug_dir(run_dir)

    paths = []
    if debug_dir:
        for name in [
            "rendered_normal_t1.png",
            "rendered_normal_t2.png",
            "rendered_normal_t3.png",
            "rendered_normal_t4.png",
            "rendered_normal_t5.png",
            "rendered_obj_normal_t3_opt0.png",
            "rendered_normal_hand_t2_opt0.png",
            "rendered_normal_hand_t2_opt10.png",
        ]:
            paths.append(debug_dir / name)

    paths += [
        run_dir / "moge_out/oakink_cropped_hoi/depth_vis.png",
        run_dir / "moge_out/oakink_cropped_hoi/normal.png",
        run_dir / "moge_out/oakink_cropped_hoi/mask.png",
    ]

    cols = 4
    card_w, card_h = 320, 260
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * card_w, rows * card_h + 70), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), f"Native debug render sheet: {args.run_id}", fill=(0, 0, 0))
    d.text((10, 34), "These are pipeline-saved images, not custom matplotlib PLY renders.", fill=(120, 0, 0))

    for i, p in enumerate(paths):
        card = image_card(p, f"{i+1}. native output")
        x = (i % cols) * card_w
        y = 70 + (i // cols) * card_h
        sheet.paste(card, (x, y))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=95)
    print("[OK] wrote", out)

if __name__ == "__main__":
    main()
