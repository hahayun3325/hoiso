from pathlib import Path
import re
import csv

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

RUNS = [
    "arctic_abox01_gpt55_auto",
    "arctic_aket01_gpt55_auto",
    "arctic_ascis01_gpt55_auto",
    "arctic_alapuse01_gpt55_auto",
    "arctic_amicuse01_gpt55_auto",
]

BAD_RE = re.compile(
    r"No such file|FileNotFoundError|CalledProcessError|CUDA out of memory|"
    r"before_frag=999|referenced before assignment|Traceback|RuntimeError|SyntaxError",
    re.I,
)

def first_glob(base, patterns):
    base = Path(base)
    for pat in patterns:
        hits = sorted(base.glob(pat))
        hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
        if hits:
            return hits[0]
    return None

def all_glob(base, patterns):
    out = []
    base = Path(base)
    for pat in patterns:
        out.extend([h for h in sorted(base.glob(pat)) if h.is_file() and h.stat().st_size > 0])
    return out

def parse_env(path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(errors="ignore").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def parse_selector(text):
    # New OakInk-style selector lines.
    m = re.findall(
        r"before_frag=([0-9.]+),\s*(?:current_frag|after_frag)=([0-9.]+).*?selected=([A-Za-z0-9_]+)",
        text,
    )
    if m:
        before, after, selected = m[-1]
        return before, after, selected

    # Fallback: selected=...; applied before joint step ...
    m2 = re.findall(r"\[FOHO_INTERNAL_SELECTOR\]\s+selected=([A-Za-z0-9_]+); applied before joint step", text)
    if m2:
        return "", "", m2[-1]

    return "", "", ""

rows = []

for run_id in RUNS:
    cfg = ROOT / f"configs/generated/pipeline.phase0.{run_id}.env"
    env = parse_env(cfg)
    run_dir = HOME / "foho_phase0/runs" / run_id
    log = HOME / "foho_phase0/logs" / f"{run_id}.log"
    text = log.read_text(errors="ignore") if log.exists() else ""

    before_frag, after_frag, selected = parse_selector(text)

    crop = first_glob(run_dir, ["cropped_hoi_imgs/*.png", "**/cropped_hoi_imgs/*.png"])
    inpaint = first_glob(run_dir, ["ours_inpaint/*.png", "**/ours_inpaint/*.png"])
    initial_mesh = first_glob(run_dir, ["hunyuan_hoi_out/*.ply", "**/hunyuan_hoi_out/*.ply"])
    final_obj = first_glob(run_dir, ["guidance_out/*obj*.ply", "**/guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])
    final_hand = first_glob(run_dir, ["guidance_out/*hand*.ply", "**/guidance_out/*hand*.ply", "guidance_out/test_hand.ply"])

    native_before = first_glob(run_dir, ["foho_debug/**/*before_phase42*native*.png", "**/*before_phase42*native*.png"])
    native_after = first_glob(run_dir, ["foho_debug/**/*phase42_before_joint*native*.png", "**/*phase42_before_joint*native*.png"])
    final_native = first_glob(run_dir, ["foho_debug/**/rendered_normal_t5.png", "foho_debug/**/rendered_normal_t*.png"])

    export_dir = Path(env.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", ""))
    if not export_dir.is_absolute():
        export_dir = run_dir / "internal_selector_exports"

    selector_exports = all_glob(export_dir, ["*.ply", "**/*.ply"])

    bad = bool(BAD_RE.search(text))
    finished = "Finished processing" in text or "Finished processing all images" in text or "Reconstructed object" in text

    output_ok = bool(crop and inpaint and (final_obj or final_native))
    selector_ok = bool(selected or native_before or native_after or selector_exports)

    rows.append({
        "run_id": run_id,
        "cfg_exists": cfg.exists(),
        "log_exists": log.exists(),
        "finished": finished,
        "bad_pattern": bad,
        "output_ok": output_ok,
        "selector_ok": selector_ok,
        "before_frag": before_frag,
        "after_frag": after_frag,
        "selected": selected,
        "crop": str(crop or ""),
        "inpaint": str(inpaint or ""),
        "initial_mesh": str(initial_mesh or ""),
        "final_obj": str(final_obj or ""),
        "final_hand": str(final_hand or ""),
        "native_before": str(native_before or ""),
        "native_after": str(native_after or ""),
        "final_native": str(final_native or ""),
        "selector_export_count": len(selector_exports),
        "log": str(log),
    })

out_dir = HOME / "foho_phase0/inspection/arctic_phase017"
out_dir.mkdir(parents=True, exist_ok=True)

csv_path = out_dir / "arctic_phase017_gpt55_auto_robust_verify.csv"
md_path = out_dir / "arctic_phase017_gpt55_auto_robust_verify.md"

with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

with md_path.open("w") as f:
    f.write("# ARCTIC Phase 0.17 GPT-5.5 Auto Robust Verification\n\n")
    f.write("| run_id | finished | bad | output_ok | selector_ok | before_frag | after_frag | selected |\n")
    f.write("|---|---:|---:|---:|---:|---:|---:|---|\n")
    for r in rows:
        f.write(
            f"| {r['run_id']} | {r['finished']} | {r['bad_pattern']} | "
            f"{r['output_ok']} | {r['selector_ok']} | {r['before_frag']} | "
            f"{r['after_frag']} | {r['selected']} |\n"
        )

print("[OK] wrote", csv_path)
print("[OK] wrote", md_path)
print(md_path.read_text())

print("\n===== missing-details report =====")
for r in rows:
    print(f"\n===== {r['run_id']} =====")
    for k in ["crop", "inpaint", "initial_mesh", "final_obj", "final_hand", "native_before", "native_after", "final_native"]:
        print(f"{k}: {r[k] or '[MISSING]'}")
