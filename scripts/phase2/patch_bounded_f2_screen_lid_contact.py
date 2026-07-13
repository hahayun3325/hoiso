#!/usr/bin/env python3
"""Install an opt-in, bounded Gate-C screen/lid contact loss.

The patch preserves the working F1 implementation. With
FOHO_F2_SCREEN_LID_CONTACT_WEIGHT=0 or no target path, behavior remains F1.
"""

from __future__ import annotations

from pathlib import Path
import sys


DEFAULT_PIPE = Path(
    "third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py"
)
MARKER = "FOHO_F2_SCREEN_LID_TARGET_PRELOAD"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one anchor, found {count}. "
            "The source may have changed; inspect it manually."
        )
    return text.replace(old, new, 1)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PIPE
    if not path.is_file():
        raise FileNotFoundError(path)

    text = path.read_text()

    if MARKER in text:
        raise SystemExit(
            f"[STOP] F2 patch already appears to be installed: {MARKER}"
        )

    required_f1_markers = (
        "FOHO_GATE_A_FIXED_OBJECT_PRELOAD",
        "FOHO_GATE_A_TEXTURE_SAFE_JOINT_JOIN",
        "FOHO_GATE_A_FIXED_OBJECT_FINAL_EXPORT",
    )
    missing = [marker for marker in required_f1_markers if marker not in text]
    if missing:
        raise RuntimeError(
            "Required working F1 patches are missing: " + ", ".join(missing)
        )

    # ---------------------------------------------------------
    # A. Preload Gate-C target and map it to fixed-object vertices.
    # Insert immediately before hand transform initialization.
    # ---------------------------------------------------------
    preload_anchor = (
        "        trans_hand = torch.tensor("
        "[0.0, 0.0, 0.0], device=device)"
    )

    preload_block = r'''        # FOHO_F2_SCREEN_LID_TARGET_PRELOAD
        _foho_f2_target_ply = os.environ.get(
            "FOHO_GATE_C_SCREEN_LID_TARGET", ""
        )
        _foho_f2_weight = float(
            os.environ.get("FOHO_F2_SCREEN_LID_CONTACT_WEIGHT", "0.0")
        )
        _foho_f2_hand_patch_size = int(
            os.environ.get("FOHO_F2_HAND_PATCH_SIZE", "64")
        )
        _foho_f2_target_distance_m = float(
            os.environ.get("FOHO_F2_TARGET_DISTANCE_M", "0.003")
        )
        _foho_f2_huber_beta_m = float(
            os.environ.get("FOHO_F2_HUBER_BETA_M", "0.010")
        )
        _foho_f2_match_tolerance_m = float(
            os.environ.get("FOHO_F2_TARGET_MATCH_TOL_M", "0.0001")
        )

        _foho_f2_target_obj_idx = None
        _foho_f2_hand_patch_idx = None

        if _foho_f2_target_ply and _foho_f2_weight > 0.0:
            if _foho_fixed_obj_mesh_cached is None:
                raise RuntimeError(
                    "F2 requires FOHO_GATE_A_FIXED_OBJECT_PLY."
                )
            if not os.path.isfile(_foho_f2_target_ply):
                raise FileNotFoundError(
                    f"Gate-C target not found: {_foho_f2_target_ply}"
                )

            from pytorch3d.io import IO as _FOHO_F2_IO

            _foho_f2_target_mesh_cached = _FOHO_F2_IO().load_mesh(
                _foho_f2_target_ply,
                device=device,
            )

            # The target is a canonical subset of the fixed Gate-A object.
            # Map every target vertex to its corresponding full-object vertex.
            # Later we extract these indices from transformed_obj_mesh, which
            # guarantees exactly the same object transform and rotation center.
            with torch.no_grad():
                _foho_f2_match_d2, _foho_f2_match_idx, _ = knn_points(
                    _foho_f2_target_mesh_cached.verts_padded(),
                    _foho_fixed_obj_mesh_cached.verts_padded(),
                    K=1,
                )
                _foho_f2_max_match_m = torch.sqrt(
                    torch.clamp(_foho_f2_match_d2.max(), min=0.0)
                ).item()

                if _foho_f2_max_match_m > _foho_f2_match_tolerance_m:
                    raise RuntimeError(
                        "Gate-C target is not an exact-enough subset of the "
                        f"fixed object: max match={_foho_f2_max_match_m:.8f} m, "
                        f"tolerance={_foho_f2_match_tolerance_m:.8f} m"
                    )

                _foho_f2_target_obj_idx = (
                    _foho_f2_match_idx[0, :, 0].long()
                )

            print(
                "[FOHO_F2] preloaded Gate-C screen/lid target; "
                f"target_verts={len(_foho_f2_target_obj_idx)}, "
                f"max_match_m={_foho_f2_max_match_m:.8f}, "
                f"weight={_foho_f2_weight}, "
                f"hand_patch_size={_foho_f2_hand_patch_size}, "
                f"target_distance_m={_foho_f2_target_distance_m}"
            )

'''

    text = replace_once(
        text,
        preload_anchor,
        preload_block + preload_anchor,
        "F2 preload insertion",
    )

    # ---------------------------------------------------------
    # B. Obtain the transformed target directly from the current
    # transformed fixed object.
    # ---------------------------------------------------------
    joint_transform_anchor = (
        "                            transformed_obj_mesh = "
        "transform_mesh_around_center_w_scale("
        "moge_obj_mesh, RT_obj, scale_obj) \n\n"
        "                            selector_debug_dir = "
        'os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")'
    )

    joint_transform_replacement = (
        "                            transformed_obj_mesh = "
        "transform_mesh_around_center_w_scale("
        "moge_obj_mesh, RT_obj, scale_obj) \n\n"
        "                            # "
        "FOHO_F2_SCREEN_LID_TARGET_FROM_FIXED_OBJECT\n"
        "                            transformed_screen_lid_points = None\n"
        "                            if _foho_f2_target_obj_idx is not None:\n"
        "                                transformed_screen_lid_points = (\n"
        "                                    transformed_obj_mesh.verts_packed()[\n"
        "                                        _foho_f2_target_obj_idx\n"
        "                                    ].unsqueeze(0)\n"
        "                                )\n\n"
        "                            selector_debug_dir = "
        'os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")'
    )

    text = replace_once(
        text,
        joint_transform_anchor,
        joint_transform_replacement,
        "F2 transformed-target insertion",
    )

    # ---------------------------------------------------------
    # C. Add bounded contact-band loss after existing F1 distance_loss.
    # PyTorch3D KNN returns squared distance, so convert to meters.
    # Select the nearest hand patch once and keep its indices fixed.
    # ---------------------------------------------------------
    loss_anchor = "                            distance_loss = attract.mean()\n"

    loss_block = r'''
                            # FOHO_F2_SCREEN_LID_CONTACT_LOSS
                            screen_lid_contact_loss = torch.tensor(
                                0.0, device=device
                            )
                            screen_lid_patch_mean_m = torch.tensor(
                                0.0, device=device
                            )
                            screen_lid_patch_min_m = torch.tensor(
                                0.0, device=device
                            )

                            if transformed_screen_lid_points is not None:
                                _foho_f2_hand_to_lid_d2, _, _ = knn_points(
                                    transformed_hand_mesh.verts_padded(),
                                    transformed_screen_lid_points,
                                    K=1,
                                )

                                _foho_f2_hand_to_lid_m = torch.sqrt(
                                    torch.clamp(
                                        _foho_f2_hand_to_lid_d2
                                        .squeeze(0)
                                        .squeeze(-1),
                                        min=1e-12,
                                    )
                                )

                                if _foho_f2_hand_patch_idx is None:
                                    _foho_f2_patch_k = max(
                                        1,
                                        min(
                                            _foho_f2_hand_patch_size,
                                            _foho_f2_hand_to_lid_m.numel(),
                                        ),
                                    )
                                    with torch.no_grad():
                                        _foho_f2_hand_patch_idx = torch.topk(
                                            _foho_f2_hand_to_lid_m.detach(),
                                            k=_foho_f2_patch_k,
                                            largest=False,
                                        ).indices
                                    print(
                                        "[FOHO_F2] locked hand contact patch; "
                                        f"vertices={_foho_f2_patch_k}"
                                    )

                                _foho_f2_patch_dist_m = (
                                    _foho_f2_hand_to_lid_m[
                                        _foho_f2_hand_patch_idx
                                    ]
                                )
                                _foho_f2_target_dist = torch.full_like(
                                    _foho_f2_patch_dist_m,
                                    _foho_f2_target_distance_m,
                                )

                                # A small contact band is safer than pulling
                                # every vertex to zero distance. It can also
                                # discourage points already closer than the
                                # requested safety distance.
                                screen_lid_contact_loss = F.smooth_l1_loss(
                                    _foho_f2_patch_dist_m,
                                    _foho_f2_target_dist,
                                    beta=_foho_f2_huber_beta_m,
                                )
                                screen_lid_patch_mean_m = (
                                    _foho_f2_patch_dist_m.mean()
                                )
                                screen_lid_patch_min_m = (
                                    _foho_f2_patch_dist_m.min()
                                )
'''

    text = replace_once(
        text,
        loss_anchor,
        loss_anchor + loss_block,
        "F2 contact-loss insertion",
    )

    # ---------------------------------------------------------
    # D. Add the new loss without replacing F1 whole-object loss.
    # ---------------------------------------------------------
    total_anchor = "                                10 * distance_loss +\n"
    total_replacement = (
        total_anchor
        + "                                _foho_f2_weight * "
        "screen_lid_contact_loss +\n"
    )

    text = replace_once(
        text,
        total_anchor,
        total_replacement,
        "F2 total-loss insertion",
    )

    # ---------------------------------------------------------
    # E. Replace the single-line joint log with F2 evidence.
    # ---------------------------------------------------------
    lines = text.splitlines()
    candidates = [
        i
        for i, line in enumerate(lines)
        if line.strip().startswith(
            "loss_str = f'Opt step {k}, object loss:"
        )
        and "total_hand_loss" in line
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            "F2 log replacement: expected one joint loss_str line, "
            f"found {len(candidates)}"
        )

    indent = " " * 32
    log_lines = [
        f"{indent}loss_str = (",
        f'{indent}    f"Opt step {{k}}, object loss: {{obj_loss_3.item()}}, "',
        f'{indent}    f"loss_intersection: {{loss_intersection.item()}}, "',
        f'{indent}    f"loss_normal_hoi: {{loss_normal_hoi.item()}}, "',
        f'{indent}    f"loss_disp: {{loss_disp_hoi.item()}}, "',
        f'{indent}    f"distance_loss: {{distance_loss.item()}}, "',
        f'{indent}    f"screen_lid_contact_loss: "',
        f'{indent}    f"{{screen_lid_contact_loss.item()}}, "',
        f'{indent}    f"screen_lid_patch_mean_m: "',
        f'{indent}    f"{{screen_lid_patch_mean_m.item()}}, "',
        f'{indent}    f"screen_lid_patch_min_m: "',
        f'{indent}    f"{{screen_lid_patch_min_m.item()}}, "',
        f'{indent}    f"total_hand_loss: {{hand_loss.item()}}"',
        f"{indent})",
    ]
    lines[candidates[0] : candidates[0] + 1] = log_lines
    text = "\n".join(lines) + "\n"

    path.write_text(text)
    print(f"[OK] installed bounded F2 patch in {path}")


if __name__ == "__main__":
    main()
