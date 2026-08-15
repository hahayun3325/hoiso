#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import py_compile
import re
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

pattern = re.compile(
    r"^(?P<indent>[ \\t]*)handopt_start_step\\s*=\\s*"
    r"(?P<expr>[^#\\n]+?)(?:\\s*#.*)?$",
    re.MULTILINE,
)
matches = list(pattern.finditer(before))
if len(matches) != 1:
    raise RuntimeError(
        f"expected exactly one simple handopt_start_step assignment; found {len(matches)}"
    )

match = matches[0]
indent = match.group("indent")
expr = match.group("expr").strip()
replacement = (
    f"{indent}handopt_start_step = int(\\n"
    f"{indent}    os.environ.get(\\n"
    f"{indent}        \\\"FOHO_HANDOPT_START_STEP\\\",\\n"
    f"{indent}        str({expr}),\\n"
    f"{indent}    )\\n"
    f"{indent})"
)
after = before[:match.start()] + replacement + before[match.end():]

if not args.apply:
    print("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=str(path), tofile=str(path) + " (handopt-entry preview)",
    )))
    print("[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_PREVIEW_READY")
else:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(after)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    backup = path.with_name(path.name + ".before_f31_handopt_entry")
    shutil.copy2(path, backup)
    path.write_text(after)
    print(f"[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_APPLIED backup={backup}")
