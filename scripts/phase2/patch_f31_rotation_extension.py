#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import py_compile
import shutil
import tempfile
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
parser.add_argument(
    "--pipeline",
    default="third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py",
)
args = parser.parse_args()

path = Path(args.pipeline)
before = path.read_text()
after = before

# 1. Reuse the proven F3 branch only when F3.1 is enabled, with a separate
#    opt-in and F3.1 filenames/root.  F3 itself stays unchanged when disabled.
old = '''        if _foho_f3_enabled:
            import json as _foho_f3_json
'''
new = '''        # FOHO_F3_1_STAGE1_BEGIN
        _foho_f31_enabled = (
            os.environ.get("FOHO_F3_1_STAGE1", "0") == "1"
        )
        if _foho_f31_enabled and _foho_f3_enabled:
            raise RuntimeError(
                "FOHO_F3_STAGE1 and FOHO_F3_1_STAGE1 are mutually exclusive"
            )
        if _foho_f31_enabled:
            _foho_f3_enabled = True
            _foho_f3_preflight_only = (
                os.environ.get("FOHO_F3_1_PREFLIGHT_ONLY", "0") == "1"
            )
            _foho_f3_root = os.environ.get("FOHO_F3_1_ROOT", "")
            _foho_f3_translation_lr = float(
                os.environ.get(
                    "FOHO_F3_1_TRANSLATION_LR", _foho_f3_translation_lr
                )
            )
            _foho_f3_steps = int(
                os.environ.get("FOHO_F3_1_STEPS", _foho_f3_steps)
            )
            _foho_f31_rotation_lr = float(
                os.environ.get("FOHO_F3_1_ROTATION_LR", "0.001")
            )
            _foho_f31_max_rotation_rad = float(
                os.environ.get("FOHO_F3_1_MAX_ROTATION_DELTA_DEG", "10")
            ) * torch.pi / 180.0
        else:
            _foho_f31_rotation_lr = None
            _foho_f31_max_rotation_rad = None
        _foho_f31_rotation_delta_hand = None
        # FOHO_F3_1_STAGE1_END

        if _foho_f3_enabled:
            import json as _foho_f3_json
'''
after = replace_once(after, old, new, "F3.1 opt-in insertion")

# 2. Load F3.1's approved contact specification and target IDs when selected.
old = '''            _foho_f3_spec_path = os.path.join(
                _foho_f3_root, "inputs", "F3_contact_spec.json"
            )
            _foho_f3_ids_path = os.path.join(
                _foho_f3_root,
                "inputs",
                "F3_local_lid_target_vertex_ids.npy",
            )
'''
new = '''            _foho_f3_spec_name = (
                "F3_1_contact_spec.json"
                if _foho_f31_enabled else "F3_contact_spec.json"
            )
            _foho_f3_ids_name = (
                "F3_1_local_lid_target_vertex_ids.npy"
                if _foho_f31_enabled else "F3_local_lid_target_vertex_ids.npy"
            )
            _foho_f3_spec_path = os.path.join(
                _foho_f3_root, "inputs", _foho_f3_spec_name
            )
            _foho_f3_ids_path = os.path.join(
                _foho_f3_root, "inputs", _foho_f3_ids_name
            )
'''
after = replace_once(after, old, new, "F3.1 input-name insertion")

# 3. F3.1 alone gets exactly two trainables: hand translation and a local
#    axis-angle delta.  The old F3 optimizer remains byte-for-byte behaviour.
old = '''                            # FOHO_F3_OPTIMIZER
                            f3_optimizer = torch.optim.AdamW(
                                [trans_hand],
                                lr=_foho_f3_translation_lr,
                                eps=1e-4,
                            )
                            _foho_active_optimizer = f3_optimizer
'''
new = '''                            # FOHO_F3_OPTIMIZER
                            if _foho_f31_enabled:
                                _foho_f31_rotation_delta_hand = torch.zeros(
                                    3,
                                    device=device,
                                    dtype=trans_hand.dtype,
                                    requires_grad=True,
                                )
                                f3_optimizer = torch.optim.AdamW(
                                    [
                                        {
                                            "params": [trans_hand],
                                            "lr": _foho_f3_translation_lr,
                                        },
                                        {
                                            "params": [
                                                _foho_f31_rotation_delta_hand
                                            ],
                                            "lr": _foho_f31_rotation_lr,
                                        },
                                    ],
                                    eps=1e-4,
                                )
                                print(
                                    "[PASS] "
                                    "F3_1_RUNTIME_TRAINABLES_TRANS_PLUS_ROT_DELTA_ONLY"
                                )
                            else:
                                f3_optimizer = torch.optim.AdamW(
                                    [trans_hand],
                                    lr=_foho_f3_translation_lr,
                                    eps=1e-4,
                                )
                            _foho_active_optimizer = f3_optimizer
'''
after = replace_once(after, old, new, "two-trainable optimizer insertion")

# 4. Compose the bounded local delta with the frozen base quaternion at both
#    the optimization and debug/export transforms.
old = '''                            RT_hand = torch.eye(4, device=device)
                            RT_hand[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                            RT_hand[:3, 3] = trans_hand
'''
new = '''                            RT_hand = torch.eye(4, device=device)
                            if _foho_f31_enabled:
                                _foho_f31_base_rot = quaternion_to_matrix(
                                    rotation_hand
                                ).float().squeeze(0)
                                _foho_f31_delta_rot = axis_angle_to_matrix(
                                    _foho_f31_rotation_delta_hand.unsqueeze(0)
                                ).squeeze(0)
                                RT_hand[:3, :3] = (
                                    _foho_f31_delta_rot @ _foho_f31_base_rot
                                )
                            else:
                                RT_hand[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                            RT_hand[:3, 3] = trans_hand
'''
after = replace_once(after, old, new, "F3.1 optimization transform insertion")

old = '''                    RT_debug = torch.eye(4, device=device)
                    RT_debug[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                    RT_debug[:3, 3] = trans_hand
'''
new = '''                    RT_debug = torch.eye(4, device=device)
                    if _foho_f31_enabled:
                        _foho_f31_debug_base_rot = quaternion_to_matrix(
                            rotation_hand
                        ).float().squeeze(0)
                        _foho_f31_debug_delta_rot = axis_angle_to_matrix(
                            _foho_f31_rotation_delta_hand.unsqueeze(0)
                        ).squeeze(0)
                        RT_debug[:3, :3] = (
                            _foho_f31_debug_delta_rot @ _foho_f31_debug_base_rot
                        )
                    else:
                        RT_debug[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                    RT_debug[:3, 3] = trans_hand
'''
after = replace_once(after, old, new, "F3.1 debug transform insertion")

# 5. Keep the local rotation within 10 degrees immediately after each step.
old = '''                            if _foho_f3_enabled:
                                with torch.no_grad():
                                    _foho_f3_delta = (
'''
new = '''                            if _foho_f31_enabled:
                                with torch.no_grad():
                                    _foho_f31_norm = torch.linalg.vector_norm(
                                        _foho_f31_rotation_delta_hand
                                    )
                                    if _foho_f31_norm > _foho_f31_max_rotation_rad:
                                        _foho_f31_rotation_delta_hand.mul_(
                                            _foho_f31_max_rotation_rad
                                            / _foho_f31_norm
                                        )

                            if _foho_f3_enabled:
                                with torch.no_grad():
                                    _foho_f3_delta = (
'''
after = replace_once(after, old, new, "F3.1 rotation-bound insertion")

# Static preflight requires a distinct runtime-plan marker.
old = '''                            print(
                                '[FOHO_F3_RUNTIME_PLAN] '
                                f'outer_step={i}, '
                                f'inner_steps={_foho_f3_steps_this_outer}'
                            )
'''
new = '''                            print(
                                '[FOHO_F3_RUNTIME_PLAN] '
                                f'outer_step={i}, '
                                f'inner_steps={_foho_f3_steps_this_outer}'
                            )
                            if _foho_f31_enabled:
                                print(
                                    '[FOHO_F3_1_RUNTIME_PLAN] '
                                    f'outer_step={i}, '
                                    f'inner_steps={_foho_f3_steps_this_outer}, '
                                    f'max_rotation_rad={_foho_f31_max_rotation_rad}'
                                )
'''
after = replace_once(after, old, new, "F3.1 runtime-plan insertion")

if after == before:
    raise RuntimeError("no source change was generated")

if not args.apply:
    print("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=str(path), tofile=str(path) + " (F3.1 preview)",
    )))
    print("[PASS] F3_1_ROTATION_PATCH_PREVIEW_READY")
else:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(after)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    backup = path.with_name(path.name + ".before_f31_rotation")
    shutil.copy2(path, backup)
    path.write_text(after)
    print(f"[PASS] F3_1_ROTATION_PATCH_APPLIED backup={backup}")
