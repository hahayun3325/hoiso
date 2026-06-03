from pathlib import Path
import argparse
import json
import shutil

from foho.selection.object_selector import ObjectCandidate, select_object_candidate

ap = argparse.ArgumentParser()
ap.add_argument("--out_dir", required=True)
ap.add_argument("--candidate", action="append", nargs=3, metavar=("NAME", "MESH", "STAGE"))
args = ap.parse_args()

out_dir = Path(args.out_dir).expanduser()
out_dir.mkdir(parents=True, exist_ok=True)

candidates = []
for name, mesh, stage in args.candidate:
    mesh_path = Path(mesh).expanduser()
    if not mesh_path.exists():
        print("[SKIP missing]", name, mesh_path)
        continue
    candidates.append(ObjectCandidate(name=name, mesh_path=mesh_path, source_stage=stage))

result = select_object_candidate(candidates)

selected_copy = out_dir / "selected_phase42_object.ply"
shutil.copy2(result.selected_mesh_path, selected_copy)

report = {
    "selected_name": result.selected_name,
    "selected_mesh_path": str(result.selected_mesh_path),
    "selected_copy": str(selected_copy),
    "scores": result.scores,
}

report_path = out_dir / "phase42_object_selection_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] selected:", result.selected_name)
print("[OK] wrote:", selected_copy)
print("[OK] wrote:", report_path)
