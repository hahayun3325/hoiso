from pathlib import Path
import shutil
import os

view_id = int(os.environ["VIEW_ID"])

ROOT = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90/anno"
OUT = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/selected_south_east_frame90"
OAK = Path(os.environ["OAKINK_DIR"]).resolve()

SEQ = "A01023_0001_0002__2021-10-12-17-13-00__0__90"
suffix = f"{SEQ}__{view_id}.pkl"

files = {
    "hand_v.pkl": ROOT / "hand_v" / suffix,
    "hand_j.pkl": ROOT / "hand_j" / suffix,
    "general_info.pkl": ROOT / "general_info" / suffix,
    "obj_transf.pkl": ROOT / "obj_transf" / suffix,
    "cam_intr.pkl": ROOT / "cam_intr" / suffix,
}

OUT.mkdir(parents=True, exist_ok=True)

for name, src in files.items():
    if not src.exists():
        raise FileNotFoundError(src)
    shutil.copy2(src, OUT / name)
    print("[OK]", src, "->", OUT / name)

img = OAK / "image/stream_release_v2/A01023_0001_0002/2021-10-12-17-13-00/south_east_color_90.png"
if img.exists():
    shutil.copy2(img, OUT / "image.png")
    print("[OK]", img, "->", OUT / "image.png")

(OUT / "view_id.txt").write_text(str(view_id) + "\n")
print("[OK] selected view_id:", view_id)
print("[OK] output:", OUT)
