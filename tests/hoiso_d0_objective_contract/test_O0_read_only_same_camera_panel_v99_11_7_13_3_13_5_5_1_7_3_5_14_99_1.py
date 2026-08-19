from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image


spec = importlib.util.spec_from_file_location("_o0_panel_candidate", os.environ["O0_PANEL_CANDIDATE"])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

output = Path(os.environ["O0_PANEL_CPU_RECEIPT"])
errors = []
try:
    rgb = Image.new("RGB", (32, 24), (20, 30, 40))
    hand = np.zeros((24, 32), dtype=bool)
    initial = np.zeros((24, 32), dtype=bool)
    final = np.zeros((24, 32), dtype=bool)
    r04 = np.zeros((24, 32), dtype=bool)
    hand[2:8, 3:10] = True
    initial[8:20, 4:15] = True
    final[7:19, 10:24] = True
    r04[10:13, 12:16] = True
    evaluation = {
        "attempts_completed": 5,
        "updates_completed": 5,
        "trajectory": [{"metrics": {"loss_total": float(value)}} for value in (10, 8, 7, 6, 5)],
        "final_metrics": {"r04_support_count": 12, "zorder_valid_count": 3},
    }
    copies = [value.copy() for value in (hand, initial, final, r04)]
    panel = module.build_panel(rgb, hand, initial, final, r04, evaluation)
    checks = {
        "eight_panel_shape": panel.size == (128, 48),
        "inputs_unchanged": all(np.array_equal(a, b) for a, b in zip(copies, (hand, initial, final, r04))),
        "panel_nonempty": bool(np.asarray(panel).var() > 0),
        "callback_has_no_optimizer_API": not hasattr(module.O0ReadOnlyPanelCallback, "optimizer"),
    }
    failed = [name for name, value in checks.items() if not value]
    payload = {
        "decision": "pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_1_O0_panel_CPU_closed" if not failed else "review_required_14_99_1_O0_panel_CPU",
        "checks": checks,
        "failed": failed,
        "errors": [],
        "GPU_used": False,
        "optimizer_updates": 0,
    }
except Exception as exc:
    payload = {
        "decision": "review_required_14_99_1_O0_panel_CPU",
        "checks": {},
        "failed": ["CPU_fixture"],
        "errors": [f"{type(exc).__name__}:{exc}"],
        "GPU_used": False,
        "optimizer_updates": 0,
    }
if not output.exists():
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
print(json.dumps(payload))
