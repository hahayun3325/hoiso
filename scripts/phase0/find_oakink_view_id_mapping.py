from pathlib import Path
import os
import zipfile
import json
import pickle
import numpy as np

root = Path(os.environ["OAKINK_DIR"]).resolve()
ann = next(iter(sorted(
    list(root.glob("image/anno_v2.1.zip")) +
    list(root.glob("image/anno_v2_1.zip")) +
    list(root.glob("zipped/image/anno_v2.1.zip")) +
    list(root.glob("zipped/image/anno_v2_1.zip"))
)), None)

if ann is None:
    raise SystemExit("[BAD] annotation zip not found")

with zipfile.ZipFile(ann) as zf:
    names = zf.namelist()

    print("===== files possibly containing view mapping =====")
    mapping_hits = [
        n for n in names
        if any(tok in n.lower() for tok in [
            "seq_status", "view", "camera", "cam", "intr", "extr", "meta"
        ])
    ]

    for n in mapping_hits[:200]:
        print(n)

    print("\n===== seq_status content if exists =====")
    for n in names:
        if n.endswith("seq_status.json"):
            print("FOUND", n)
            raw = zf.read(n)
            try:
                data = json.loads(raw.decode("utf-8"))
                print(json.dumps(data if isinstance(data, dict) else data[:3], indent=2)[:3000])
            except Exception as e:
                print("[ERR]", e)
