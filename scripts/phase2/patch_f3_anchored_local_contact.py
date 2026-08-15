#!/usr/bin/env python3
"""Install the opt-in F3 anchored local-contact branch.

Behavior is unchanged unless FOHO_F3_STAGE1=1. In F3 mode, the existing
phase-2 parameter list is discarded and the optimizer is constructed from
[trans_hand] only. The fixed Gate-A object and all non-translation hand
variables are detached/frozen.

Run without --apply to preview the unified diff.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import shutil
from pathlib import Path


DEFAULT_PIPE = Path(
    "third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py"
)
MARKER = "FOHO_F3_STAGE1_BEGIN"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one anchor, found {count}. "
            "The pipeline source may have changed; inspect it before editing."
        )
    return text.replace(old, new, 1)


PRELOAD_ANCHOR = (
    "        trans_hand = torch.tensor("
    "[0.0, 0.0, 0.0], device=device)"
)

PRELOAD_BLOCK = r'''        # FOHO_F3_STAGE1_BEGIN
        # FOHO_F3_LOAD_CONTACT_SPEC
        _foho_f3_enabled = (
            os.environ.get("FOHO_F3_STAGE1", "0") == "1"
        )
        _foho_f3_preflight_only = (
            os.environ.get("FOHO_F3_PREFLIGHT_ONLY", "0") == "1"
        )
        _foho_f3_root = os.environ.get("FOHO_F3_ROOT", "")
        _foho_f3_translation_lr = float(
            os.environ.get("FOHO_F3_TRANSLATION_LR", "0.002")
        )
        _foho_f3_steps = int(
            os.environ.get("FOHO_F3_STEPS", "10")
        )
        _foho_f3_contact_weight = float(
            os.environ.get("FOHO_F3_CONTACT_WEIGHT", "10.0")
        )
        _foho_f3_2d_weight = float(
            os.environ.get("FOHO_F3_2D_KPS_WEIGHT", "0.0001")
        )
        _foho_f3_trans_reg_weight = float(
            os.environ.get("FOHO_F3_TRANS_REG_WEIGHT", "0.01")
        )
        _foho_f3_target_distance_m = float(
            os.environ.get("FOHO_F3_TARGET_DISTANCE_M", "0.003")
        )
        _foho_f3_huber_beta_m = float(
            os.environ.get("FOHO_F3_HUBER_BETA_M", "0.010")
        )
        _foho_f3_max_translation_delta_m = float(
            os.environ.get(
                "FOHO_F3_MAX_TRANSLATION_DELTA_M", "0.060"
            )
        )
        _foho_f3_match_tolerance_m = float(
            os.environ.get("FOHO_F3_TARGET_MATCH_TOL_M", "0.0001")
        )
        _foho_f3_log_every = max(
            1, int(os.environ.get("FOHO_F3_LOG_EVERY", "5"))
        )

        _foho_f3_target_obj_idx = None
        _foho_f3_tip_idx = None
        _foho_f3_trans_hand_anchor = None

        if _foho_f3_enabled:
            import json as _foho_f3_json
            import numpy as _foho_f3_np
            from pytorch3d.io import IO as _FOHO_F3_IO

            if _foho_fixed_obj_mesh_cached is None:
                raise RuntimeError(
                    "F3 requires FOHO_GATE_A_FIXED_OBJECT_PLY."
                )
            if not _foho_f3_root:
                raise RuntimeError("F3 requires FOHO_F3_ROOT.")

            _foho_f3_spec_path = os.path.join(
                _foho_f3_root, "inputs", "F3_contact_spec.json"
            )
            _foho_f3_ids_path = os.path.join(
                _foho_f3_root,
                "inputs",
                "F3_local_lid_target_vertex_ids.npy",
            )
            _foho_f3_lid_ply = (
                os.environ.get("FOHO_F3_CANONICAL_LID_PLY", "")
                or os.environ.get(
                    "FOHO_GATE_C_SCREEN_LID_TARGET", ""
                )
            )

            for _foho_f3_required in (
                _foho_f3_spec_path,
                _foho_f3_ids_path,
                _foho_f3_lid_ply,
            ):
                if not os.path.isfile(_foho_f3_required):
                    raise FileNotFoundError(
                        f"F3 required input missing: "
                        f"{_foho_f3_required}"
                    )

            with open(
                _foho_f3_spec_path, "r", encoding="utf-8"
            ) as _foho_f3_file:
                _foho_f3_spec = _foho_f3_json.load(
                    _foho_f3_file
                )

            if (
                _foho_f3_spec.get("target_spec_status")
                != "PASS_CANONICAL_LOCAL_TARGET"
                or not _foho_f3_spec.get(
                    "target_approved_geometrically", False
                )
            ):
                raise RuntimeError(
                    "F3 target has not passed the canonical "
                    "local-target audit."
                )

            if (
                not _foho_f3_preflight_only
                and not _foho_f3_spec.get(
                    "approved_for_f3_stage1", False
                )
            ):
                raise RuntimeError(
                    "F3 execution is not authorized in "
                    "F3_contact_spec.json."
                )

            _foho_f3_tip_ids = _foho_f3_spec.get(
                "primary_mano_tip_vertex_ids",
                _foho_f3_spec.get("mano_tip_vertex_ids", []),
            )
            if not _foho_f3_tip_ids:
                raise RuntimeError(
                    "F3 primary fingertip IDs are missing."
                )
            if any(
                int(_idx) < 0 or int(_idx) >= 778
                for _idx in _foho_f3_tip_ids
            ):
                raise RuntimeError(
                    "F3 fingertip IDs are outside MANO-778 space."
                )

            # FOHO_F3_LOAD_LOCAL_TARGET_IDS
            _foho_f3_local_ids_np = (
                _foho_f3_np.load(_foho_f3_ids_path)
                .astype(_foho_f3_np.int64)
                .reshape(-1)
            )
            if _foho_f3_local_ids_np.size < 4:
                raise RuntimeError(
                    "F3 local target contains fewer than four vertices."
                )

            _foho_f3_lid_mesh = (
                _FOHO_F3_IO()
                .load_mesh(_foho_f3_lid_ply, device=device)
            )
            _foho_f3_lid_vertices = (
                _foho_f3_lid_mesh.verts_packed()
            )
            if (
                _foho_f3_local_ids_np.min() < 0
                or _foho_f3_local_ids_np.max()
                >= _foho_f3_lid_vertices.shape[0]
            ):
                raise RuntimeError(
                    "F3 target IDs are outside the canonical "
                    "lid vertex range."
                )

            _foho_f3_local_ids = torch.as_tensor(
                _foho_f3_local_ids_np,
                dtype=torch.long,
                device=device,
            )
            _foho_f3_selected_lid = (
                _foho_f3_lid_vertices[_foho_f3_local_ids]
                .unsqueeze(0)
            )

            # Map lid-local IDs into the frozen full Gate-A object.
            with torch.no_grad():
                (
                    _foho_f3_match_d2,
                    _foho_f3_match_idx,
                    _,
                ) = knn_points(
                    _foho_f3_selected_lid,
                    _foho_fixed_obj_mesh_cached.verts_padded(),
                    K=1,
                )
                _foho_f3_max_match_m = torch.sqrt(
                    torch.clamp(
                        _foho_f3_match_d2.max(), min=0.0
                    )
                ).item()
                if (
                    _foho_f3_max_match_m
                    > _foho_f3_match_tolerance_m
                ):
                    raise RuntimeError(
                        "F3 target is not an exact-enough subset "
                        "of the fixed object: "
                        f"{_foho_f3_max_match_m:.8f} m"
                    )
                _foho_f3_target_obj_idx = (
                    _foho_f3_match_idx[0, :, 0].long()
                )

            _foho_f3_tip_idx = torch.as_tensor(
                [int(_idx) for _idx in _foho_f3_tip_ids],
                dtype=torch.long,
                device=device,
            )
            print(
                "[FOHO_F3_LOAD_CONTACT_SPEC] "
                f"tips={_foho_f3_tip_ids}, "
                f"target_vertices="
                f"{len(_foho_f3_target_obj_idx)}, "
                f"max_match_m={_foho_f3_max_match_m:.8f}, "
                f"preflight_only={_foho_f3_preflight_only}"
            )
'''

OPTIMIZER_ANCHOR = (
    "                        joint_optimizer = "
    "torch.optim.AdamW(params_guidance_hoi, eps=1e-4)"
)

OPTIMIZER_BLOCK = r'''                        if _foho_f3_enabled:
                            # FOHO_F3_FREEZE_OBJECT
                            if _foho_f3_trans_hand_anchor is None:
                                _foho_f3_trans_hand_anchor = (
                                    trans_hand.detach().clone()
                                )

                            noise_pred_obj = (
                                noise_pred_obj.detach().clone()
                            )
                            scale_obj = scale_obj.detach().clone()
                            rotation_obj = (
                                rotation_obj.detach().clone()
                            )
                            trans_obj = trans_obj.detach().clone()
                            scale_hand = scale_hand.detach().clone()
                            rotation_hand = (
                                rotation_hand.detach().clone()
                            )
                            trans_hand = (
                                trans_hand.detach().clone()
                                .requires_grad_(True)
                            )

                            # FOHO_F3_OPTIMIZER
                            f3_optimizer = torch.optim.AdamW(
                                [trans_hand],
                                lr=_foho_f3_translation_lr,
                                eps=1e-4,
                            )
                            _foho_active_optimizer = f3_optimizer
                            _foho_f3_steps_this_outer = (
                                0
                                if _foho_f3_preflight_only
                                else _foho_f3_steps
                            )

                            _foho_f3_optimizer_ids = {
                                id(_parameter)
                                for _group in f3_optimizer.param_groups
                                for _parameter in _group["params"]
                            }
                            if _foho_f3_optimizer_ids != {
                                id(trans_hand)
                            }:
                                raise RuntimeError(
                                    "F3 optimizer contains a parameter "
                                    "other than trans_hand."
                                )

                            # FOHO_F3_TRAINABLES
                            print(
                                "[FOHO_F3_TRAINABLES]",
                                ["trans_hand"],
                            )
                            print(
                                "[PASS] "
                                "F3_RUNTIME_TRAINABLES_TRANS_HAND_ONLY"
                            )
                        else:
                            joint_optimizer = torch.optim.AdamW(
                                params_guidance_hoi, eps=1e-4
                            )
                            _foho_active_optimizer = joint_optimizer
                            _foho_f3_steps_this_outer = (
                                optimization_steps_joint
                            )'''

LOOP_OLD = '''                        for k in range(optimization_steps_joint):
                            joint_optimizer.zero_grad()'''

LOOP_NEW = '''                        for k in range(_foho_f3_steps_this_outer):
                            _foho_active_optimizer.zero_grad()'''

RENDER_ANCHOR = '''                            # rendering normal and disparity maps
                            # FOHO_GATE_A_TEXTURE_SAFE_JOINT_JOIN'''

F3_LOSS_BLOCK = r'''                            # FOHO_F3_LOCAL_CONTACT_LOSS
                            _foho_f3_contact_loss = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f3_tip_mean_m = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f3_tip_min_m = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f3_translation_delta_loss = (
                                torch.tensor(0.0, device=device)
                            )

                            if _foho_f3_enabled:
                                if (
                                    _foho_f3_target_obj_idx is None
                                    or _foho_f3_tip_idx is None
                                ):
                                    raise RuntimeError(
                                        "F3 target/tip mapping is missing."
                                    )
                                if (
                                    int(
                                        _foho_f3_tip_idx.max().item()
                                    )
                                    >= transformed_hand_mesh
                                    .verts_packed()
                                    .shape[0]
                                ):
                                    raise RuntimeError(
                                        "F3 fingertip ID exceeds the "
                                        "runtime hand vertex count."
                                    )

                                _foho_f3_target_points = (
                                    transformed_obj_mesh
                                    .verts_packed()[
                                        _foho_f3_target_obj_idx
                                    ]
                                    .detach()
                                    .unsqueeze(0)
                                )
                                _foho_f3_tip_points = (
                                    transformed_hand_mesh
                                    .verts_packed()[
                                        _foho_f3_tip_idx
                                    ]
                                    .unsqueeze(0)
                                )
                                (
                                    _foho_f3_tip_d2,
                                    _,
                                    _,
                                ) = knn_points(
                                    _foho_f3_tip_points,
                                    _foho_f3_target_points,
                                    K=1,
                                )
                                _foho_f3_tip_distance_m = (
                                    torch.sqrt(
                                        torch.clamp(
                                            _foho_f3_tip_d2
                                            .squeeze(0)
                                            .squeeze(-1),
                                            min=1e-12,
                                        )
                                    )
                                )
                                _foho_f3_target_distance = (
                                    torch.full_like(
                                        _foho_f3_tip_distance_m,
                                        _foho_f3_target_distance_m,
                                    )
                                )
                                _foho_f3_contact_loss = (
                                    F.smooth_l1_loss(
                                        _foho_f3_tip_distance_m,
                                        _foho_f3_target_distance,
                                        beta=_foho_f3_huber_beta_m,
                                    )
                                )
                                _foho_f3_tip_mean_m = (
                                    _foho_f3_tip_distance_m.mean()
                                )
                                _foho_f3_tip_min_m = (
                                    _foho_f3_tip_distance_m.min()
                                )
                                _foho_f3_translation_delta_loss = (
                                    (
                                        trans_hand
                                        - _foho_f3_trans_hand_anchor
                                    )
                                    .pow(2)
                                    .mean()
                                )

'''

TOTAL_OLD = '''                            total_loss = (
                                w_intersection * loss_intersection +
                                10 * distance_loss +
                                _foho_f2_weight * screen_lid_contact_loss +
                                10 * loss_normal_hoi +
                                10 * loss_disp_hoi +
                                10 * loss_silhouette_hoi +
                                1e-3 * obj_verts_loss_3 +
                                1 * obj_loss_3 +
                                1e-3 * loss_obj_reg +
                                1e-3 * hand_loss
                            )'''

TOTAL_NEW = '''                            if _foho_f3_enabled:
                                total_loss = (
                                    _foho_f3_contact_weight
                                    * _foho_f3_contact_loss
                                    + _foho_f3_2d_weight
                                    * loss_2d_kps
                                    + _foho_f3_trans_reg_weight
                                    * _foho_f3_translation_delta_loss
                                )
                            else:
                                total_loss = (
                                    w_intersection * loss_intersection +
                                    10 * distance_loss +
                                    _foho_f2_weight * screen_lid_contact_loss +
                                    10 * loss_normal_hoi +
                                    10 * loss_disp_hoi +
                                    10 * loss_silhouette_hoi +
                                    1e-3 * obj_verts_loss_3 +
                                    1 * obj_loss_3 +
                                    1e-3 * loss_obj_reg +
                                    1e-3 * hand_loss
                                )'''

NAN_ANCHOR = '''                            if torch.isnan(total_loss):'''

F3_LOG_BLOCK = r'''                            if (
                                _foho_f3_enabled
                                and k % _foho_f3_log_every == 0
                            ):
                                print(
                                    "[FOHO_F3] "
                                    f"k={k}, "
                                    f"contact_loss="
                                    f"{_foho_f3_contact_loss.item():.8f}, "
                                    f"tip_mean_m="
                                    f"{_foho_f3_tip_mean_m.item():.6f}, "
                                    f"tip_min_m="
                                    f"{_foho_f3_tip_min_m.item():.6f}, "
                                    f"trans_delta_loss="
                                    f"{_foho_f3_translation_delta_loss.item():.8f}, "
                                    f"total_loss={total_loss.item():.8f}"
                                )

'''

STEP_OLD = '''                            total_loss.backward()
                            joint_optimizer.step()'''

STEP_NEW = r'''                            total_loss.backward()
                            _foho_active_optimizer.step()

                            if _foho_f3_enabled:
                                with torch.no_grad():
                                    _foho_f3_delta = (
                                        trans_hand
                                        - _foho_f3_trans_hand_anchor
                                    )
                                    _foho_f3_delta_norm = (
                                        torch.linalg.vector_norm(
                                            _foho_f3_delta
                                        )
                                    )
                                    if (
                                        _foho_f3_delta_norm.item()
                                        > _foho_f3_max_translation_delta_m
                                    ):
                                        _foho_f3_scale = (
                                            _foho_f3_max_translation_delta_m
                                            / torch.clamp(
                                                _foho_f3_delta_norm,
                                                min=1e-12,
                                            )
                                        )
                                        trans_hand.copy_(
                                            _foho_f3_trans_hand_anchor
                                            + _foho_f3_delta
                                            * _foho_f3_scale
                                        )
                            # FOHO_F3_STAGE1_END'''


def patch_text(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            "F3 marker already exists; refusing to patch twice."
        )

    for required in (
        "FOHO_GATE_A_FIXED_OBJECT_PRELOAD",
        "FOHO_F2_SCREEN_LID_CONTACT_LOSS",
        "params_guidance_hoi",
    ):
        if required not in text:
            raise RuntimeError(
                f"Required existing source marker is missing: "
                f"{required}"
            )

    text = replace_once(
        text,
        PRELOAD_ANCHOR,
        PRELOAD_BLOCK + PRELOAD_ANCHOR,
        "F3 preload insertion",
    )
    text = replace_once(
        text,
        OPTIMIZER_ANCHOR,
        OPTIMIZER_BLOCK,
        "F3 optimizer insertion",
    )
    text = replace_once(
        text,
        LOOP_OLD,
        LOOP_NEW,
        "F3 loop insertion",
    )
    text = replace_once(
        text,
        RENDER_ANCHOR,
        F3_LOSS_BLOCK + RENDER_ANCHOR,
        "F3 local-loss insertion",
    )
    text = replace_once(
        text,
        TOTAL_OLD,
        TOTAL_NEW,
        "F3 total-loss branch",
    )
    text = replace_once(
        text,
        NAN_ANCHOR,
        F3_LOG_BLOCK + NAN_ANCHOR,
        "F3 metric logging",
    )
    text = replace_once(
        text,
        STEP_OLD,
        STEP_NEW,
        "F3 optimizer step",
    )

    compile(text, "<patched pipelines.py>", "exec")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pipe", type=Path, default=DEFAULT_PIPE
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the patch after creating a backup.",
    )
    args = parser.parse_args()

    if not args.pipe.is_file():
        raise FileNotFoundError(args.pipe)

    original = args.pipe.read_text()
    patched = patch_text(original)

    print(
        "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                patched.splitlines(keepends=True),
                fromfile=str(args.pipe),
                tofile=str(args.pipe) + ".F3",
            )
        )
    )

    if not args.apply:
        candidate = Path("/tmp/pipelines.py.F3_candidate")
        candidate.write_text(patched)
        print(f"[CHECK] candidate: {candidate}")
        print("[CHECK] review the diff; rerun with --apply")
        return

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = args.pipe.with_name(
        args.pipe.name + f".before_F3_{timestamp}"
    )
    shutil.copy2(args.pipe, backup)
    args.pipe.write_text(patched)
    print(f"[OK] backup: {backup}")
    print(f"[OK] patched: {args.pipe}")


if __name__ == "__main__":
    main()
