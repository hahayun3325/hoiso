from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

ADAPTER = '''\
import numpy as np

def load_context(config):
    return {"zero": np.asarray(config["zero"], dtype=float), "cols": {k: np.asarray(v, dtype=float) for k,v in config["cols"].items()}}

def project_keypoints(context, deltas):
    y = context["zero"].copy()
    for k,v in deltas.items():
        y = y + context["cols"][k] * float(v)
    return y

def metadata(context):
    return {"synthetic": True}
'''



def run(cmd):
    subprocess.run([sys.executable, *map(str, cmd)], check=True)


def scenario(root: Path, name: str, target: np.ndarray, expected_route: str, zero: np.ndarray, cols: dict[str, np.ndarray]):
    t = root / name
    t.mkdir()
    adapter = t / "adapter.py"
    adapter.write_text(ADAPTER)
    np.save(t / "target.npy", target)
    np.save(t / "zero.npy", zero)
    np.save(t / "conf.npy", np.ones(zero.shape[0]))
    manifest = t / "manifest.csv"
    with manifest.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name","group","step","bound","enabled","authorizes","source_locator","notes"])
        w.writerow(["a","active_articulation",0.01,0.10,1,1,"synthetic",""])
        w.writerow(["tx","translation",0.001,0.01,1,1,"synthetic",""])
    thresholds = t / "thresholds.json"
    thresholds.write_text((ROOT / "config/articulation_adequacy_thresholds.json").read_text())
    cfg = {
        "adapter": str(adapter),
        "adapter_context": {"zero": zero.tolist(), "cols": {k:v.tolist() for k,v in cols.items()}},
        "target_keypoints": str(t / "target.npy"),
        "expected_zero_keypoints": str(t / "zero.npy"),
        "confidence": str(t / "conf.npy"),
        "normalization_scale_px": 10.0,
        "parameter_manifest": str(manifest),
        "thresholds": str(thresholds),
        "fd_step_multipliers": [0.5,1.0,2.0],
        "base_step_multiplier": 1.0,
        "known_branch_e_translation_rejected": True,
        "group_l2_limits": {"translation": 0.01},
        "analysis_blocks": {
            "active_articulation": ["active_articulation"],
            "translation_only": ["translation"],
            "translation_plus_active": ["translation","active_articulation"],
            "all_articulation_upper_bound": ["active_articulation"],
            "diagnostic_full_upper_bound": ["translation","active_articulation"]
        },
        "authorizing_blocks": ["active_articulation","translation_plus_active"]
    }
    (t / "cfg.json").write_text(json.dumps(cfg))
    run([SCRIPTS / "preflight_articulation_probe.py", "--config", t/"cfg.json", "--out-dir", t/"pre"])
    run([SCRIPTS / "collect_fd_jacobian.py", "--config", t/"cfg.json", "--preflight", t/"pre/preflight.json", "--out-dir", t/"fd"])
    run([SCRIPTS / "analyze_articulation_adequacy.py", "--config", t/"cfg.json", "--preflight-dir", t/"pre", "--fd-dir", t/"fd", "--out-dir", t/"ana"])
    run([SCRIPTS / "decide_articulation_route.py", "--preflight", t/"pre/preflight.json", "--fd", t/"fd/fd_collection.json", "--analysis", t/"ana/analysis_summary.json", "--out-dir", t/"decision"])
    dec = json.loads((t / "decision/decision.json").read_text())
    assert dec["route"] == expected_route, (name, dec)
    print(f"[PASS] synthetic {name}: {expected_route}")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        zero = np.array([[10.,10.],[20.,10.],[30.,10.],[40.,10.]])
        col_a = np.array([[0.,1.],[0.,-1.],[0.,1.],[0.,-1.]]) * 80.0
        col_t = np.array([[1.,0.],[1.,0.],[1.,0.],[1.,0.]]) * 1000.0
        cols = {"a": col_a, "tx": col_t}
        scenario(root, "route_a", zero + col_a * 0.06,
                 "ROUTE_A_PREREGISTER_BOUNDED_ACTIVE_ARTICULATION_TRIAL", zero, cols)
        scenario(root, "route_b", zero + col_a * 0.06 + col_t * 0.004,
                 "ROUTE_B_PREREGISTER_BOUNDED_TRANSLATION_PLUS_ACTIVE_ARTICULATION_TRIAL", zero, cols)
        orth = np.array([[1.,0.],[-1.,0.],[1.,0.],[-1.,0.]]) * 8.0
        scenario(root, "route_c", zero + orth,
                 "ROUTE_C_AUDIT_ALTERNATE_SAME_RUN_HAND_CANDIDATES", zero, cols)


if __name__ == "__main__":
    main()
