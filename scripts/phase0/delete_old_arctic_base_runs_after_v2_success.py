from pathlib import Path
import argparse
import shutil
import json

HOME = Path.home()

CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

def has_file(pattern):
    hits = sorted(pattern)
    return any(p.exists() and p.is_file() and p.stat().st_size > 0 for p in hits)

def verify_v2(case):
    run = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    checks = {
        "crop": has_file((run / "cropped_hoi_imgs").glob(f"{case}_cropped_hoi_*.png")),
        "inpaint": (run / "ours_inpaint" / f"{case}_inpainted_object.png").exists(),
        "obj": (run / "guidance_out" / f"{case}_obj.ply").exists(),
        "hand": (run / "guidance_out" / f"{case}_hand.ply").exists(),
        "selector_native": has_file((run / "foho_debug").glob("**/*selector*native*.png")),
        "selector_exports": has_file((run / "internal_selector_exports").glob("selector_*.ply")),
    }
    return run, checks, all(checks.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    report = []

    print("MODE:", "APPLY_DELETE" if args.apply else "DRY_RUN_ONLY")

    for case in CASES:
        base = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto"
        v2, checks, ok = verify_v2(case)

        print(f"\n===== {case} =====")
        print("base:", base)
        print("v2:", v2)
        print("v2_ok:", ok)
        print("checks:", checks)

        if not base.exists():
            print("[SKIP] base folder does not exist")
            continue

        if not ok:
            print("[SKIP] v2 is not complete enough; not deleting base")
            continue

        # Extra guard: never delete selector_native_v2 folder.
        if "selector_native_v2" in base.name:
            print("[SKIP] guard triggered")
            continue

        size = "unknown"
        print("[DELETE]" if args.apply else "[DRY]", base)
        if args.apply:
            shutil.rmtree(base)

        report.append({
            "case": case,
            "base": str(base),
            "v2": str(v2),
            "v2_checks": checks,
            "deleted": bool(args.apply),
        })

    out = HOME / "foho_phase0/inspection/arctic_phase017/delete_old_arctic_base_runs_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print("\n[OK] wrote", out)

if __name__ == "__main__":
    main()
