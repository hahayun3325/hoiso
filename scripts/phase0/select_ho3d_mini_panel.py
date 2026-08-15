import csv
from pathlib import Path
from collections import defaultdict

src = Path.home() / "foho_phase0/logs/phase0_13_ho3d_detector_preflight.csv"
out = Path.home() / "foho_phase0/inspection/ho3d_mini_panel.csv"

rows = []
with src.open() as f:
    reader = csv.DictReader(f)
    for r in reader:
        path = r.get("path") or r.get("image_path") or list(r.values())[1]
        vals = list(r.values())
        # tolerate different column names
        ok_text = ",".join(vals).lower()
        if "true,true,true" in ok_text:
            seq = Path(path).parts[-3]
            rows.append((seq, path))

by_seq = defaultdict(list)
for seq, path in rows:
    by_seq[seq].append(path)

selected = []
for seq in sorted(by_seq):
    selected.append((seq, by_seq[seq][len(by_seq[seq]) // 2]))

with out.open("w") as f:
    f.write("sequence,image_path\n")
    for seq, path in selected[:20]:
        f.write(f"{seq},{path}\n")

print("[OK] wrote", out)
print("selected:", len(selected[:20]))
for seq, path in selected[:20]:
    print(seq, path)
