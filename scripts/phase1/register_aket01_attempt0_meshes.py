#!/usr/bin/env python
from pathlib import Path
import argparse
import json
import os
import shutil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hand", required=True, help="Path to new hand mesh")
    ap.add_argument("--object", required=True, help="Path to new object mesh")
    ap.add_argument("--copy", action="store_true", help="Copy instead of symlink")
    args = ap.parse_args()

    hand = Path(args.hand).expanduser().resolve()
    obj = Path(args.object).expanduser().resolve()

    if not hand.exists():
        raise FileNotFoundError(f"hand mesh not found: {hand}")
    if not obj.exists():
        raise FileNotFoundError(f"object mesh not found: {obj}")

    attempt = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt")
    recheck = attempt / "selector_v4_recheck/io_alignment/aket01_partaware_v2_attempt0"
    recheck.mkdir(parents=True, exist_ok=True)

    dst_hand = recheck / "pred_hand_aligned.ply"
    dst_obj = recheck / "pred_object_aligned.ply"

    for dst in [dst_hand, dst_obj]:
        if dst.exists() or dst.is_symlink():
            dst.unlink()

    if args.copy:
        shutil.copy2(hand, dst_hand)
        shutil.copy2(obj, dst_obj)
        mode = "copy"
    else:
        os.symlink(hand, dst_hand)
        os.symlink(obj, dst_obj)
        mode = "symlink"

    state_p = attempt / "rerun_state.json"
    state = json.loads(state_p.read_text())
    state["state"] = "attempt0_meshes_registered_for_selector_v4_recheck"
    state["registration_status"] = "registered"
    state["registered_selector_input_dir"] = str(recheck)
    state["registered_hand_mesh"] = str(hand)
    state["registered_object_mesh"] = str(obj)
    state["registration_mode"] = mode
    state["next_step"] = "run_selector_v4_recheck"
    state_p.write_text(json.dumps(state, indent=2))

    report = {
        "case_id": "aket01",
        "attempt": 0,
        "registration_status": "registered",
        "mode": mode,
        "source_hand": str(hand),
        "source_object": str(obj),
        "registered_hand": str(dst_hand),
        "registered_object": str(dst_obj),
    }
    report_p = attempt / "selector_v4_recheck/decision/mesh_registration_report.json"
    report_p.parent.mkdir(parents=True, exist_ok=True)
    report_p.write_text(json.dumps(report, indent=2))

    print("[OK] registered meshes")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
