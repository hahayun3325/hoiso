#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import shutil
from pathlib import Path


TARGET_CODE = "handopt_start_step = config().handopt_start_step"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--pipeline",
        type=Path,
        default=Path(
            "third_party/Hunyuan3D-2/"
            "hy3dgen/shapegen/pipelines.py"
        ),
    )
    args = parser.parse_args()

    path = args.pipeline
    if not path.is_file():
        raise RuntimeError(f"pipeline source missing: {path}")

    before = path.read_text(encoding="utf-8")

    # Make the patch idempotent.
    if "FOHO_HANDOPT_START_STEP" in before:
        print("[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_ALREADY_INSTALLED")
        return

    lines = before.splitlines(keepends=True)
    matches: list[int] = []

    for index, line in enumerate(lines):
        # Ignore an optional trailing source comment.
        code = line.split("#", 1)[0].strip()
        if code == TARGET_CODE:
            matches.append(index)

    if len(matches) != 1:
        nearby = [
            (i + 1, line.rstrip("\r\n"))
            for i, line in enumerate(lines)
            if "handopt_start_step" in line
        ]
        raise RuntimeError(
            "expected exactly one handopt assignment; "
            f"found {len(matches)}; nearby={nearby}"
        )

    index = matches[0]
    old_line = lines[index]

    indent = old_line[: len(old_line) - len(old_line.lstrip())]
    if old_line.endswith("\r\n"):
        nl = "\r\n"
    elif old_line.endswith("\n"):
        nl = "\n"
    else:
        nl = "\n"

    replacement = (
        f"{indent}handopt_start_step = int({nl}"
        f"{indent}    os.environ.get({nl}"
        f'{indent}        "FOHO_HANDOPT_START_STEP",{nl}'
        f"{indent}        str(config().handopt_start_step),{nl}"
        f"{indent}    ){nl}"
        f"{indent}){nl}"
    )

    lines[index] = replacement
    after = "".join(lines)

    # Refuse to produce syntactically invalid source.
    compile(after, str(path), "exec")

    diff = "".join(
        difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile=str(path),
            tofile=str(path) + " (F3.1 handopt-entry override)",
        )
    )

    if not args.apply:
        print(diff)
        print("[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_V3_PREVIEW_READY")
        return

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(
        f"{path.name}.before_f31_handopt_override.{stamp}"
    )
    shutil.copy2(path, backup)
    path.write_text(after, encoding="utf-8")

    # Confirm the written file is still valid Python.
    compile(path.read_text(encoding="utf-8"), str(path), "exec")

    print("[PASS] F3_1_HANDOPT_ENTRY_OVERRIDE_V3_APPLIED")
    print(f"[INFO] backup={backup}")


if __name__ == "__main__":
    main()
