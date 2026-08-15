from pathlib import Path
from PIL import Image, ImageDraw
import argparse
import re

def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

def find_debug_dir(run_dir):
    hits = sorted((run_dir / "foho_debug").glob("*"))
    hits = [p for p in hits if p.is_dir()]
    return hits[-1] if hits else None

def read_selector_info(log_path):
    out = {
        "selected": "unknown",
        "before": "?",
        "current": "?",
        "text": "selected: unknown",
    }
    if not Path(log_path).exists():
        return out

    text = Path(log_path).read_text(errors="ignore")
    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([a-zA-Z0-9_]+)",
        text,
    )
    if m:
        before, current, margin, selected = m[-1]
        out["before"] = before
        out["current"] = current
        out["selected"] = selected
        out["text"] = f"before={before}, after={current}, selected={selected}"
        return out

    hits = re.findall(r"selected=([a-zA-Z0-9_]+)", text)
    if hits:
        out["selected"] = hits[-1]
        out["text"] = f"selected={hits[-1]}"
    return out

def card(path, title, subtitle="", selected=False, size=(380, 310)):
    w, h = size
    out = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(out)
    d.text((8, 8), title, fill=(0, 0, 0))
    d.text((8, 30), subtitle[:82], fill=(90, 90, 90))

    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((w - 24, h - 82))
        out.paste(im, ((w - im.width)//2, 62))
        d.text((8, h - 18), Path(path).name[:54], fill=(90, 90, 90))
    else:
        d.text((w//2 - 40, h//2), "MISSING", fill=(200, 0, 0))

    if selected:
        d.rectangle([2, 2, w - 3, h - 3], outline=(255, 0, 0), width=6)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--label", default="OakInk split000")
    ap.add_argument("--log", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    run_dir = Path.home() / "foho_phase0/runs" / args.run_id
    debug_dir = find_debug_dir(run_dir)

    log_path = Path(args.log) if args.log else Path.home() / "foho_phase0/logs" / f"{args.run_id}.log"
    info = read_selector_info(log_path)

    crop = first_existing([
        run_dir / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        run_dir / "cropped_hoi_imgs_wo_bckg/oakink_cropped_hoi_wo_bckg_1.png",
    ])
    inpaint = first_existing([
        run_dir / "ours_inpaint/oakink_inpainted_object.png",
        run_dir / "ours_inpaint/oakink_inpainted.png",
    ])

    before_img = debug_dir / "foho_selector_before_phase42_native.png"
    after_img = debug_dir / "foho_selector_phase42_before_joint_native.png"

    if info["selected"] == "before_phase42":
        selected_img = before_img
    elif info["selected"] in ["phase42_before_joint", "phase42", "current"]:
        selected_img = after_img
    else:
        selected_img = first_existing([
            debug_dir / "foho_selector_selected_before_joint_native.png",
            before_img,
            after_img,
        ])

    items = [
        (crop, "1. HOI crop", "pipeline crop", False),
        (inpaint, "2. Inpaint", "LLM prompt + FLUX", False),
        (before_img, "3. Before Phase 4.2", f"frag={info['before']}", info["selected"] == "before_phase42"),
        (after_img, "4. After Phase 4.2", f"frag={info['current']}", info["selected"] in ["phase42_before_joint", "phase42", "current"]),
        (selected_img, "5. Selector choice", info["text"], True),
        (debug_dir / "rendered_normal_t5.png", "6. Final HOI native render", "left=rendered HOI, right=MoGe target", False),
    ]

    card_w, card_h = 380, 310
    sheet = Image.new("RGB", (card_w * len(items), card_h + 72), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), args.label, fill=(0, 0, 0))
    d.text((10, 34), "Native renderer panel: selector candidates use pipeline camera, not custom PLY rendering.", fill=(140, 0, 0))

    for i, item in enumerate(items):
        sheet.paste(card(*item, size=(card_w, card_h)), (i * card_w, 72))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=95)
    print("[OK] wrote", out)

if __name__ == "__main__":
    main()
