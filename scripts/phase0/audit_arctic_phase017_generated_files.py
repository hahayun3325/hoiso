from pathlib import Path
import re
import os

HOME = Path.home()

runs = {
    "arctic_abox01_gpt55_auto": "abox01",
    "arctic_aket01_gpt55_auto": "aket01",
    "arctic_ascis01_gpt55_auto": "ascis01",
    "arctic_alapuse01_gpt55_auto": "alapuse01",
    "arctic_amicuse01_gpt55_auto": "amicuse01",
}

roots = [
    HOME / "foho_phase0",
    HOME / "Projects/FollowMyHold",
    Path("/tmp"),
]

patterns = [
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.ply",
    "*.glb",
    "*.obj",
    "*.csv",
    "*.json",
    "*.txt",
    "*.log",
]

def safe_rglob(root, pat):
    try:
        return list(root.rglob(pat))
    except Exception:
        return []

def is_interesting(path, run_id, case_id):
    s = str(path).lower()
    names = [
        run_id.lower(),
        case_id.lower(),
        "arctic",
        "cropped",
        "inpaint",
        "hunyuan",
        "guidance",
        "rendered_normal",
        "selector",
        "moge",
        "hamer",
        "mano",
    ]
    return any(x in s for x in names)

out_dir = HOME / "foho_phase0/inspection/arctic_phase017"
out_dir.mkdir(parents=True, exist_ok=True)
report = out_dir / "arctic_phase017_file_audit.txt"

lines = []

for run_id, case_id in runs.items():
    lines.append("\n" + "=" * 80)
    lines.append(f"{run_id} / {case_id}")
    lines.append("=" * 80)

    run_dir = HOME / "foho_phase0/runs" / run_id
    log = HOME / "foho_phase0/logs" / f"{run_id}.log"

    lines.append(f"run_dir: {run_dir} exists={run_dir.exists()}")
    lines.append(f"log: {log} exists={log.exists()}")

    if run_dir.exists():
        files = [p for p in run_dir.rglob("*") if p.is_file()]
        lines.append(f"files_under_expected_run_dir: {len(files)}")
        for p in sorted(files)[:80]:
            lines.append(f"  EXPECTED_DIR_FILE {p}")

    lines.append("\n-- log output/path hints --")
    if log.exists():
        text = log.read_text(errors="ignore")
        for line in text.splitlines():
            if re.search(r"Reconstructed object|Finished processing|saved|wrote|exported|guidance_out|hunyuan|cropped|inpaint|selector|rendered_normal|\.ply|\.png", line, re.I):
                lines.append("  " + line[:500])

    lines.append("\n-- global search hits --")
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for pat in patterns:
            for p in safe_rglob(root, pat):
                if p.is_file() and is_interesting(p, run_id, case_id):
                    hits.append(p)

    # de-duplicate and sort by mtime descending
    hits = sorted(set(hits), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    for p in hits[:120]:
        try:
            size = p.stat().st_size
        except Exception:
            size = -1
        lines.append(f"  HIT size={size:>10} {p}")

report.write_text("\n".join(lines))
print("[OK] wrote", report)
print(report)
