#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import py_compile
import shutil
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
parser.add_argument(
    "--pipeline",
    default="third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py",
)
args = parser.parse_args()

path = Path(args.pipeline)
before = path.read_text()

if "FOHO_HANDOPT_START_STEP" in before:
    raise RuntimeError("FOHO_HANDOPT_START_STEP is already installed")

old = "        handopt_start_step = config().handopt_start_step\\n"
new = """        handopt_start_step = int(
            os.environ.get(
                \"FOHO_HANDOPT_START_STEP\",
                str(config().handopt_start_step),
            )
        )
"""

count = before.count(old)
if count != 1:
    raise RuntimeError(
        f"expected exactly one known handopt assignment; found {count}"
    )
after = before.replace(old, new, 1)

if not args.apply:
    print("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=str(path), tofile=str(path) + " (handopt-entry preview)",
    )))
    print("[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_V2_PREVIEW_READY")
else:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(after)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    backup = path.with_name(path.name + ".before_f31_handopt_entry_v2")
    shutil.copy2(path, backup)
    path.write_text(after)
    print(f"[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_V2_APPLIED backup={backup}")
