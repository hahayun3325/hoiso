from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_part_aware_root_contract.py"
THR = ROOT / "config" / "root_audit_thresholds.json"

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    src = trimesh.creation.box(extents=[1.0, 0.6, 0.2])
    src_path = td / "src.ply"; src.export(src_path)
    tgt = src.copy(); tgt_path = td / "tgt.ply"; tgt.export(tgt_path)
    corr = np.column_stack([np.arange(len(src.vertices)), np.arange(len(src.vertices))])
    corr_path = td / "corr.npy"; np.save(corr_path, corr)
    out = td / "out"
    cmd = [sys.executable, str(SCRIPT), "--source", str(src_path), "--target", str(tgt_path), "--out-dir", str(out), "--thresholds", str(THR), "--lineage-mode", "fixed_partition", "--correspondence", str(corr_path), "--samples", "4000"]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    rep = json.loads((out / "root_contract_report.json").read_text())
    assert rep["classification"] == "ROOT_IDENTITY_CONFIRMED", rep

    moved = src.copy()
    T = trimesh.transformations.rotation_matrix(np.deg2rad(10), [0, 0, 1])
    T[:3, :3] *= 1.1
    T[:3, 3] = [0.2, -0.1, 0.05]
    moved.apply_transform(T)
    moved_path = td / "moved.ply"; moved.export(moved_path)
    out2 = td / "out2"
    cmd2 = [sys.executable, str(SCRIPT), "--source", str(src_path), "--target", str(moved_path), "--out-dir", str(out2), "--thresholds", str(THR), "--lineage-mode", "fixed_partition", "--correspondence", str(corr_path), "--samples", "4000"]
    subprocess.check_call(cmd2, stdout=subprocess.DEVNULL)
    rep2 = json.loads((out2 / "root_contract_report.json").read_text())
    assert rep2["classification"] == "SAME_GEOMETRY_NONIDENTITY_ROOT", rep2
print("[PASS] smoke_test")
