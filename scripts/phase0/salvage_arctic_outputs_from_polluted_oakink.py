from pathlib import Path
import shutil
import json

HOME = Path.home()

SRC_ROOT = HOME / "foho_phase0/runs/oakink000_gpt55_short"

CASES = {
    "arctic_abox01_gpt55_auto": "abox01",
    "arctic_aket01_gpt55_auto": "aket01",
    "arctic_ascis01_gpt55_auto": "ascis01",
    "arctic_alapuse01_gpt55_auto": "alapuse01",
    "arctic_amicuse01_gpt55_auto": "amicuse01",
}

SUBDIRS_WITH_CASE_FILES = [
    "aligned_mano",
    "cropped_hand_masks",
    "cropped_hoi_imgs",
    "cropped_hoi_imgs_wo_bckg",
    "guidance_out",
    "h2m_transformations",
    "hamer_out",
    "hunyuan_hoi_out",
    "masked_obj_imgs",
    "original_imgs",
    "ours_inpaint",
]

MOGE_SUBDIR = "moge_out"

def copy_file(src: Path, dst: Path, manifest):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    manifest.append({
        "type": "file",
        "src": str(src),
        "dst": str(dst),
        "size": src.stat().st_size,
    })

def copy_dir(src: Path, dst: Path, manifest):
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    manifest.append({
        "type": "dir",
        "src": str(src),
        "dst": str(dst),
    })

def main():
    if not SRC_ROOT.exists():
        raise FileNotFoundError(f"Missing polluted source root: {SRC_ROOT}")

    all_manifest = []

    for run_id, case_id in CASES.items():
        print(f"\n===== salvage {run_id} / {case_id} =====")
        dst_root = HOME / "foho_phase0/runs" / run_id
        dst_root.mkdir(parents=True, exist_ok=True)

        manifest = []

        # Copy normal case-prefixed files.
        for sub in SUBDIRS_WITH_CASE_FILES:
            src_dir = SRC_ROOT / sub
            dst_dir = dst_root / sub
            if not src_dir.exists():
                print("[MISS DIR]", src_dir)
                continue

            hits = sorted(src_dir.glob(f"{case_id}*"))
            for src in hits:
                if src.is_file():
                    dst = dst_dir / src.name
                    copy_file(src, dst, manifest)
                    print("[COPY]", src, "->", dst)

        # Copy MoGe folder, usually case_id_cropped_hoi.
        moge_src_root = SRC_ROOT / MOGE_SUBDIR
        if moge_src_root.exists():
            for src in sorted(moge_src_root.glob(f"{case_id}_cropped_hoi*")):
                if src.is_dir():
                    dst = dst_root / MOGE_SUBDIR / src.name
                    copy_dir(src, dst, manifest)
                    print("[COPYDIR]", src, "->", dst)

        # Copy FOHO debug folder, usually timestamp_exp_objCASE_inpainted.
        debug_src_root = SRC_ROOT / "foho_debug"
        if debug_src_root.exists():
            for src in sorted(debug_src_root.glob(f"*exp_obj{case_id}_inpainted*")):
                if src.is_dir():
                    dst = dst_root / "foho_debug" / src.name
                    copy_dir(src, dst, manifest)
                    print("[COPYDIR]", src, "->", dst)

        # Keep existing manual prompt CSV in destination; do not overwrite it.
        prompt = dst_root / "manual_gemini_responses.csv"
        print("[PROMPT]", prompt, "exists=", prompt.exists())

        report = dst_root / "salvage_manifest_from_oakink000_gpt55_short.json"
        report.write_text(json.dumps(manifest, indent=2))
        print("[OK] wrote", report)
        print("[COUNT]", len(manifest), "entries")

        all_manifest.extend({
            "run_id": run_id,
            "case_id": case_id,
            **x,
        } for x in manifest)

    out_dir = HOME / "foho_phase0/inspection/arctic_phase017"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_report = out_dir / "salvage_manifest_all_arctic_from_oakink000_gpt55_short.json"
    all_report.write_text(json.dumps(all_manifest, indent=2))
    print("\n[OK] wrote", all_report)

if __name__ == "__main__":
    main()
