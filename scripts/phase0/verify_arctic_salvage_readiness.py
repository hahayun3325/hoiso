from pathlib import Path

HOME = Path.home()

RUNS = {
    "arctic_abox01_gpt55_auto": "abox01",
    "arctic_aket01_gpt55_auto": "aket01",
    "arctic_ascis01_gpt55_auto": "ascis01",
    "arctic_alapuse01_gpt55_auto": "alapuse01",
    "arctic_amicuse01_gpt55_auto": "amicuse01",
}

def first_glob(root, pat):
    hits = sorted(Path(root).glob(pat))
    return hits[0] if hits else None

all_ok = True

for run_id, case_id in RUNS.items():
    run = HOME / "foho_phase0/runs" / run_id
    debug = first_glob(run / "foho_debug", f"*exp_obj{case_id}_inpainted*")

    required = {
        "prompt_csv": run / "manual_gemini_responses.csv",
        "crop": first_glob(run / "cropped_hoi_imgs", f"{case_id}_cropped_hoi_*.png"),
        "inpaint": run / "ours_inpaint" / f"{case_id}_inpainted_object.png",
        "hunyuan": run / "hunyuan_hoi_out" / f"{case_id}_hoi_mesh.ply",
        "final_obj": run / "guidance_out" / f"{case_id}_obj.ply",
        "final_hand": run / "guidance_out" / f"{case_id}_hand.ply",
        "debug_dir": debug,
        "render_t3": debug / "rendered_obj_normal_t3_opt0.png" if debug else None,
        "render_t4": debug / "rendered_normal_t4.png" if debug else None,
        "render_t5": debug / "rendered_normal_t5.png" if debug else None,
    }

    print(f"\n===== {run_id} / {case_id} =====")
    for name, path in required.items():
        ok = path is not None and Path(path).exists() and (Path(path).is_dir() or Path(path).stat().st_size > 0)
        print(("[OK]  " if ok else "[MISS]") + f"{name:12s} {path}")
        if not ok:
            all_ok = False

print("\nRESULT:", "READY_FOR_PANEL" if all_ok else "NEEDS_RERUN_OR_PATCH")
raise SystemExit(0 if all_ok else 1)
