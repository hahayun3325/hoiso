from pathlib import Path
import json

DATA = Path("/home/fredcui/foho_phase0")
CASE = "alapuse02_v3"
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases" / CASE
OUT = CASE_ROOT / "metrics"
OUT.mkdir(parents=True, exist_ok=True)

search_roots = [
    DATA / "phase1_diagnostics",
    DATA / "runs",
    DATA / "phase2_gateA_part_recon/cases",
]

keywords = [
    "alapuse02",
    "laptop_use_02",
    "s05",
    "00060",
]

matches = []
for root in search_roots:
    if not root.exists():
        continue
    for p in root.rglob("*"):
        s = str(p)
        if any(k in s for k in keywords):
            matches.append(p)

guidance_like = []
for p in matches:
    s = str(p).lower()
    if "guidance_out" in s or s.endswith(".ply") or s.endswith(".glb") or "manifest" in s:
        guidance_like.append(p)

report = {
    "case": CASE,
    "case_root": str(CASE_ROOT),
    "num_keyword_matches": len(matches),
    "keyword_matches_sample": [str(p) for p in sorted(matches)[:100]],
    "num_guidance_like_matches": len(guidance_like),
    "guidance_like_matches_sample": [str(p) for p in sorted(guidance_like)[:100]],
}

if len(guidance_like) == 0:
    report["decision"] = "NEEDS_GUIDANCE_PIPELINE_RUN"
else:
    report["decision"] = "POSSIBLE_EXISTING_ASSETS_INSPECT_MANUALLY"

out = OUT / "alapuse02_v3_asset_preflight_report.json"
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out)
