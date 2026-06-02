from pathlib import Path
import argparse
import shutil

def copy_tree(src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        print("[WARN] missing source dir:", src)
        return
    for p in src.iterdir():
        if p.is_file():
            shutil.copy2(p, dst / p.name)
            print("[COPY]", p, "->", dst / p.name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument(
        "--baseline",
        default=str(Path.home() / "foho_phase0/runs/oakink_000_baseline"),
    )
    ap.add_argument("--clean_downstream", action="store_true")
    args = ap.parse_args()

    base = Path(args.baseline).expanduser()
    run = Path.home() / f"foho_phase0/runs/{args.run_id}"
    run.mkdir(parents=True, exist_ok=True)

    # Keep manual_gemini_responses.csv and config untouched.
    if args.clean_downstream:
        for d in [
            "ours_inpaint",
            "moge_out",
            "hunyuan_hoi_out",
            "h2m_transformations",
            "hamer_out",
            "aligned_mano",
            "guidance_out",
            "foho_debug",
            "fallback_out",
        ]:
            target = run / d
            if target.exists():
                print("[REMOVE]", target)
                shutil.rmtree(target)

    for d in [
        "original_imgs",
        "masked_obj_imgs",
        "cropped_hoi_imgs",
        "cropped_hoi_imgs_wo_bckg",
        "cropped_hand_masks",
    ]:
        print("\n===== seeding", d, "=====")
        copy_tree(base / d, run / d)

    print("\n[OK] seeded preprocessing assets")
    print("[RUN]", run)

if __name__ == "__main__":
    main()
