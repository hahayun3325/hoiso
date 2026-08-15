from pathlib import Path

HOME = Path.home()

CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

for case in CASES:
    base = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto"
    v2 = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    print(f"\n===== {case} =====")

    checks = {
        "base_crop": list((base / "cropped_hoi_imgs").glob(f"{case}_cropped_hoi_*.png")),
        "v2_crop": list((v2 / "cropped_hoi_imgs").glob(f"{case}_cropped_hoi_*.png")),
        "base_inpaint": list((base / "ours_inpaint").glob(f"{case}_inpainted_object.png")),
        "v2_inpaint": list((v2 / "ours_inpaint").glob(f"{case}_inpainted_object.png")),
        "base_native": list((base / "foho_debug").glob(f"**/*selector*native*.png")),
        "v2_native": list((v2 / "foho_debug").glob(f"**/*selector*native*.png")),
        "v2_exports": list((v2 / "internal_selector_exports").glob("selector_*.ply")),
        "v2_final": list((v2 / "guidance_out").glob("*.ply")),
    }

    for name, hits in checks.items():
        print(f"{name}: {len(hits)}")
        for h in sorted(hits)[:6]:
            print("  ", h)
