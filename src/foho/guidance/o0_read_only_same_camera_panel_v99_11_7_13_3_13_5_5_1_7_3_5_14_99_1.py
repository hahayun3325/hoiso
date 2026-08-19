from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter
from pytorch3d.structures import Meshes

from foho.guidance.h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import (
    apply_accepted_h0_pose,
    register_hshape_vertices,
)
from foho.guidance.o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3 import (
    load_o0_resources,
)


class O0PanelComplete(RuntimeError):
    def __init__(self, result):
        super().__init__("O0_panel_complete")
        self.result = result


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _tensor_digest(value):
    h = hashlib.sha256()

    def add(item):
        if torch.is_tensor(item):
            tensor = item.detach().cpu().contiguous()
            h.update(str(tensor.dtype).encode())
            h.update(str(tuple(tensor.shape)).encode())
            h.update(tensor.numpy().tobytes())
        elif isinstance(item, dict):
            for key in sorted(item):
                h.update(str(key).encode())
                add(item[key])
        elif isinstance(item, (list, tuple)):
            for child in item:
                add(child)
        else:
            h.update(repr(item).encode())

    add(value)
    return h.hexdigest()


def _mask(renderer, mesh):
    fragments = renderer.rasterizer(mesh)
    return fragments, fragments.pix_to_face[0, ..., 0].ge(0)


def _overlay(rgb, masks_and_colors, alpha=0.58):
    array = np.asarray(rgb.convert("RGB"), dtype=np.float32).copy()
    for mask, color in masks_and_colors:
        use = np.asarray(mask, dtype=bool)
        color_array = np.asarray(color, dtype=np.float32)
        array[use] = array[use] * (1.0 - alpha) + color_array * alpha
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), "RGB")


def _outline(mask):
    image = Image.fromarray(np.asarray(mask, dtype=np.uint8) * 255, "L")
    dilated = np.asarray(image.filter(ImageFilter.MaxFilter(5))) > 0
    eroded = np.asarray(image.filter(ImageFilter.MinFilter(5))) > 0
    return np.logical_and(dilated, np.logical_not(eroded))


def _label(image, text):
    result = image.copy()
    ImageDraw.Draw(result).rectangle((0, 0, result.width, 22), fill=(0, 0, 0))
    ImageDraw.Draw(result).text((6, 5), text, fill=(255, 255, 255))
    return result


def _metric_panel(size, evaluation):
    width, height = size
    panel = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(panel)
    trajectory = evaluation.get("trajectory") or []
    values = [float(row["metrics"]["loss_total"]) for row in trajectory]
    if values:
        low, high = min(values), max(values)
        span = max(high - low, 1e-12)
        points = []
        for index, value in enumerate(values):
            x = 28 + index * max(width - 56, 1) / max(len(values) - 1, 1)
            y = 55 + (high - value) * max(height - 110, 1) / span
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=(80, 220, 255), width=4)
        for point in points:
            x, y = point
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 230, 20))
        draw.text((8, height - 48), f"loss_total {values[0]:.6g} -> {values[-1]:.6g}", fill=(255, 255, 255))
    final = (evaluation.get("final_metrics") or {})
    draw.text((8, height - 30), f"attempts={evaluation.get('attempts_completed')} updates={evaluation.get('updates_completed')}", fill=(255, 255, 255))
    draw.text((8, height - 15), f"r04={final.get('r04_support_count')} zorder={final.get('zorder_valid_count')}", fill=(255, 255, 255))
    return _label(panel, "H O0 trajectory and final metrics")


def build_panel(rgb, hand_mask, initial_object_mask, final_object_mask, r04_mask, evaluation):
    rgb = rgb.convert("RGB")
    hand = np.asarray(hand_mask, dtype=bool)
    initial = np.asarray(initial_object_mask, dtype=bool)
    final = np.asarray(final_object_mask, dtype=bool)
    r04 = np.asarray(r04_mask, dtype=bool)
    initial_outline = _outline(initial)
    final_outline = _outline(final)
    panels = [
        _label(rgb, "A observed cropped RGB"),
        _label(_overlay(rgb, [(hand, (0, 230, 80))]), "B accepted H1 hand (fixed, green)"),
        _label(_overlay(rgb, [(initial, (0, 220, 235))]), "C Gate-A O0 initial laptop (cyan)"),
        _label(_overlay(rgb, [(final, (235, 30, 190))]), "D accepted O0 final laptop (magenta)"),
        _label(_overlay(rgb, [(hand, (0, 230, 80)), (initial, (0, 220, 235))]), "E fixed H1 hand + initial laptop"),
        _label(_overlay(rgb, [(hand, (0, 230, 80)), (final, (235, 30, 190))]), "F fixed H1 hand + final laptop"),
        _label(_overlay(rgb, [(initial_outline, (0, 220, 235)), (final_outline, (235, 30, 190)), (r04, (255, 225, 0))], alpha=0.9), "G initial/final outlines + final r04 support"),
        _metric_panel(rgb.size, evaluation),
    ]
    width, height = rgb.size
    sheet = Image.new("RGB", (4 * width, 2 * height), (0, 0, 0))
    for index, panel in enumerate(panels):
        sheet.paste(panel, ((index % 4) * width, (index // 4) * height))
    return sheet


class O0ReadOnlyPanelCallback:
    def __init__(self, case_manifest, checkpoint, evaluation, rgb, panel, receipt):
        self.case_manifest = Path(case_manifest)
        self.checkpoint = Path(checkpoint)
        self.evaluation = Path(evaluation)
        self.rgb = Path(rgb)
        self.panel = Path(panel)
        self.receipt = Path(receipt)
        self._used = False

    def bind_live_context(self, context):
        return context

    def __call__(self, context):
        if self._used:
            raise RuntimeError("O0_panel_callback_may_run_once")
        self._used = True
        if self.panel.exists() or self.receipt.exists():
            raise FileExistsError("O0_panel_outputs_must_be_fresh")
        manifest = json.loads(self.case_manifest.read_text())
        paths = manifest["paths"]
        parameters = context.get("parameters") or {}
        if list(parameters) != ["global_object_rotation", "global_object_translation"]:
            raise ValueError("O0_panel_parameter_order_mismatch")
        rotation = parameters["global_object_rotation"]
        translation = parameters["global_object_translation"]
        current_object_mesh = context.get("current_object_mesh")
        rendering = context.get("rendering") or {}
        renderer = rendering.get("renderer")
        frozen = context.get("frozen") or {}
        base_hand = frozen.get("mano_mesh_moge")
        hand_scale = frozen.get("global_hand_scale")
        if not callable(current_object_mesh) or renderer is None or base_hand is None or hand_scale is None:
            raise ValueError("O0_panel_live_owners_missing")
        resources = load_o0_resources(paths, rotation.device, rotation.dtype)
        h1 = resources["h1"]
        provider = resources["provider"]
        fixed_T = h1["fixed_T_h2m"].detach()
        baseline_registered = register_hshape_vertices(resources["baseline_hshape"], fixed_T)
        registered_center = (baseline_registered.min(0).values + baseline_registered.max(0).values) / 2.0
        accepted_scale = hand_scale.detach().clone() if torch.is_tensor(hand_scale) else torch.as_tensor(hand_scale, device=rotation.device, dtype=rotation.dtype)
        checkpoint = torch.load(self.checkpoint, map_location=rotation.device, weights_only=False)
        final_parameters = checkpoint.get("parameters") or {}
        if set(final_parameters) != {"global_object_rotation", "global_object_translation"}:
            raise ValueError("O0_panel_checkpoint_parameter_schema")
        evaluation = json.loads(self.evaluation.read_text())
        initial_values = {name: value.detach().clone() for name, value in parameters.items()}
        initial_flags = {name: bool(value.requires_grad) for name, value in parameters.items()}
        initial_grads = {name: None if value.grad is None else value.grad.detach().clone() for name, value in parameters.items()}
        frozen_before = _tensor_digest({"base_hand": base_hand.verts_packed(), "hand_scale": hand_scale, "h1": resources["h1_checkpoint"]})
        try:
            with torch.no_grad():
                registered = register_hshape_vertices(provider()[0], fixed_T)
                accepted_vertices = apply_accepted_h0_pose(
                    registered,
                    registered_center,
                    accepted_scale,
                    h1["accepted_rotation"],
                    h1["accepted_translation"],
                ).detach()
                accepted_hand = Meshes(verts=[accepted_vertices], faces=[base_hand.faces_packed().detach().clone()])
                _, hand_mask = _mask(renderer, accepted_hand)
                _, initial_object_mask = _mask(renderer, current_object_mesh())
                for name, value in parameters.items():
                    value.copy_(final_parameters[name].to(device=value.device, dtype=value.dtype))
                final_mesh = current_object_mesh()
                final_fragments, final_object_mask = _mask(renderer, final_mesh)
                face_ids = final_fragments.pix_to_face[0, ..., 0]
                r04_mask = torch.isin(face_ids, resources["r04_face_ids"]) & face_ids.ge(0)
            source = Image.open(self.rgb).convert("RGB")
            expected_size = (int(hand_mask.shape[1]), int(hand_mask.shape[0]))
            if source.size != expected_size:
                source = source.resize(expected_size, Image.Resampling.BILINEAR)
            sheet = build_panel(
                source,
                hand_mask.detach().cpu().numpy(),
                initial_object_mask.detach().cpu().numpy(),
                final_object_mask.detach().cpu().numpy(),
                r04_mask.detach().cpu().numpy(),
                evaluation,
            )
            self.panel.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(self.panel)
        finally:
            with torch.no_grad():
                for name, value in parameters.items():
                    value.copy_(initial_values[name])
            for name, value in parameters.items():
                value.requires_grad_(initial_flags[name])
                value.grad = None if initial_grads[name] is None else initial_grads[name].clone()
        frozen_after = _tensor_digest({"base_hand": base_hand.verts_packed(), "hand_scale": hand_scale, "h1": resources["h1_checkpoint"]})
        restored = all(torch.equal(parameters[name].detach(), initial_values[name]) for name in parameters)
        flags_restored = all(bool(parameters[name].requires_grad) == initial_flags[name] for name in parameters)
        result = {
            "panel": str(self.panel),
            "panel_sha256": _sha(self.panel),
            "checkpoint": str(self.checkpoint),
            "checkpoint_sha256": _sha(self.checkpoint),
            "accepted_H1_checkpoint_sha256": resources["hashes"]["h1_checkpoint"],
            "hand_pixels": int(hand_mask.sum().detach().cpu()),
            "initial_object_pixels": int(initial_object_mask.sum().detach().cpu()),
            "final_object_pixels": int(final_object_mask.sum().detach().cpu()),
            "final_r04_pixels": int(r04_mask.sum().detach().cpu()),
            "object_parameters_restored": restored,
            "requires_grad_flags_restored": flags_restored,
            "frozen_digest_before": frozen_before,
            "frozen_digest_after": frozen_after,
            "optimizer_updates": 0,
        }
        raise O0PanelComplete(result)
