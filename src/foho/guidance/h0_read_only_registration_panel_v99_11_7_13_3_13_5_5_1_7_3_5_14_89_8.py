from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

from foho.guidance.h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9 import bind_live_context, load_case_resources
from foho.guidance.h0_metric_face_depth_v99_11_7_13_3_13_5_5_1_7_3_5_14_85 import interpolate_metric_face_depth


class H0PanelComplete(RuntimeError):
    def __init__(self, result):
        super().__init__('H0_read_only_panel_complete')
        self.result = result


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fresh(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _array(value):
    if torch.is_tensor(value):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def _image2(value):
    value = np.squeeze(_array(value))
    if value.ndim != 2:
        raise ValueError(f'expected_2d_image:{value.shape}')
    return value


def _rgb(value):
    value = np.squeeze(_array(value))
    if value.ndim != 3 or value.shape[-1] < 3:
        raise ValueError(f'expected_RGB_tensor:{value.shape}')
    value = value[..., :3].astype(np.float64)
    finite = np.isfinite(value)
    if not finite.any():
        return np.zeros((*value.shape[:2], 3), dtype=np.uint8)
    if float(np.nanmin(value)) < 0.0:
        value = (value + 1.0) * 0.5
    if float(np.nanmax(value)) > 1.0:
        scale = float(np.nanpercentile(np.abs(value[finite]), 99.0)) or 1.0
        value = value / scale
    return np.clip(np.nan_to_num(value), 0.0, 1.0).mul(255).astype(np.uint8) if hasattr(value, 'mul') else (np.clip(np.nan_to_num(value), 0.0, 1.0) * 255).astype(np.uint8)


def _resize(array, size, nearest=False):
    array = np.asarray(array)
    if array.dtype == bool:
        image = Image.fromarray(array.astype(np.uint8) * 255)
        return np.asarray(image.resize(size, Image.Resampling.NEAREST)) > 0
    if array.ndim == 2:
        image = Image.fromarray(array.astype(np.float32), mode='F')
        return np.asarray(image.resize(size, Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR))
    image = Image.fromarray(array.astype(np.uint8))
    return np.asarray(image.resize(size, Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR))


def _edge(mask):
    mask = np.asarray(mask, dtype=bool)
    eroded = mask.copy()
    eroded[1:, :] &= mask[:-1, :]
    eroded[:-1, :] &= mask[1:, :]
    eroded[:, 1:] &= mask[:, :-1]
    eroded[:, :-1] &= mask[:, 1:]
    return mask & ~eroded


def _overlay(base, mask, color, alpha=0.48):
    result = np.asarray(base, dtype=np.float32).copy()
    mask = np.asarray(mask, dtype=bool)
    result[mask] = (1.0-alpha) * result[mask] + alpha * np.asarray(color, dtype=np.float32)
    return np.clip(result, 0, 255).astype(np.uint8)


def _title(array, title):
    image = Image.fromarray(np.asarray(array, dtype=np.uint8)).convert('RGB')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 24), fill=(0, 0, 0))
    draw.text((6, 6), title, fill=(255, 255, 255))
    return image


def _metrics_rows(path):
    with Path(path).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('metrics_csv_empty')
    return rows


def _state_digest(value):
    digest = hashlib.sha256()
    seen = set()
    def visit(item):
        identity = id(item)
        if identity in seen:
            digest.update(b'<cycle>')
            return
        if torch.is_tensor(item):
            tensor = item.detach().contiguous().cpu()
            digest.update(str(tensor.dtype).encode())
            digest.update(str(tuple(tensor.shape)).encode())
            digest.update(tensor.numpy().tobytes())
            return
        if isinstance(item, dict):
            seen.add(identity)
            for key in sorted(item, key=str):
                digest.update(str(key).encode()); visit(item[key])
            return
        if isinstance(item, (list, tuple)):
            seen.add(identity)
            for row in item: visit(row)
            return
        if hasattr(item, 'verts_packed') and hasattr(item, 'faces_packed'):
            visit(item.verts_packed()); visit(item.faces_packed()); return
        digest.update(repr(item).encode())
    visit(value)
    return digest.hexdigest()


def _render_state(context, resources, index):
    with torch.no_grad():
        base_loss, aux = context['compute_base_loss'](index)
        mesh = aux['transformed_hand_mesh']
        renderer = context['rendering']['renderer']
        fragments = renderer.rasterizer(mesh)
        vertices = mesh.verts_packed()
        faces = mesh.faces_packed()
        view_vertices = renderer.rasterizer.cameras.get_world_to_view_transform().transform_points(vertices)
        vertex_depth = view_vertices[:, 2]
        hand_depth, hand_valid = interpolate_metric_face_depth(
            fragments.pix_to_face, fragments.bary_coords, faces, vertex_depth)
        hand_depth = torch.squeeze(hand_depth)
        hand_valid = torch.squeeze(hand_valid)
        height, width = tuple(context['rendering']['image_size'])
        screen = renderer.rasterizer.cameras.transform_points_screen(
            vertices.unsqueeze(0), image_size=(height, width))[0]
        pad_xy = screen[resources['pad_ids'], :2]
    return {
        'base_loss': float(base_loss.detach().cpu()),
        'normal': _rgb(aux['rendered_normal_hand']),
        'silhouette': _image2(aux['sil_mano_hand']) > 0.5,
        'hand_depth': _image2(hand_depth),
        'hand_valid': _image2(hand_valid).astype(bool),
        'pad_xy': _array(pad_xy),
    }


def compose_registration_panel(crop_path, initial, final, object_depth, object_valid, r04, metrics_csv, output_path):
    crop = np.asarray(Image.open(crop_path).convert('RGB'))
    height, width = crop.shape[:2]
    size = (width, height)
    initial_mask = _resize(initial['silhouette'], size, nearest=True)
    final_mask = _resize(final['silhouette'], size, nearest=True)
    r04_mask = _resize(r04, size, nearest=True)
    object_valid = _resize(object_valid, size, nearest=True)
    object_depth = _resize(object_depth, size)
    hand_depth = _resize(final['hand_depth'], size)
    hand_valid = _resize(final['hand_valid'], size, nearest=True)

    cell_a = crop.copy()
    cell_b = _overlay(crop, initial_mask, (40, 220, 80))
    cell_c = _overlay(crop, final_mask, (235, 40, 170))
    cell_d = crop.copy()
    cell_d[_edge(initial_mask)] = (40, 255, 80)
    cell_d[_edge(final_mask)] = (255, 40, 190)
    d_image = Image.fromarray(cell_d)
    d_draw = ImageDraw.Draw(d_image)
    def centroid(mask):
        points = np.argwhere(mask)
        return None if not len(points) else (float(points[:, 1].mean()), float(points[:, 0].mean()))
    c0, c1 = centroid(initial_mask), centroid(final_mask)
    if c0 and c1:
        d_draw.line((c0[0], c0[1], c1[0], c1[1]), fill=(255, 220, 0), width=3)
        d_draw.ellipse((c1[0]-4, c1[1]-4, c1[0]+4, c1[1]+4), fill=(255, 220, 0))
    cell_d = np.asarray(d_image)

    cell_e = _overlay(crop, r04_mask & object_valid, (20, 210, 235), alpha=0.55)
    e_image = Image.fromarray(cell_e)
    e_draw = ImageDraw.Draw(e_image)
    for index, xy in enumerate(np.asarray(final['pad_xy'])):
        x, y = float(xy[0]), float(xy[1])
        color = (255, 80, 40) if index % 2 == 0 else (255, 220, 30)
        e_draw.ellipse((x-3, y-3, x+3, y+3), fill=color)
    cell_e = np.asarray(e_image)

    support = hand_valid & object_valid & ~r04_mask & np.isfinite(hand_depth) & np.isfinite(object_depth)
    delta = np.zeros_like(hand_depth, dtype=np.float64)
    delta[support] = hand_depth[support] - object_depth[support]
    scale = float(np.percentile(np.abs(delta[support]), 95.0)) if support.any() else 1.0
    scale = max(scale, 1e-8)
    normalized = np.clip(delta / scale, -1.0, 1.0)
    cell_f = np.zeros((height, width, 3), dtype=np.uint8)
    cell_f[..., 0] = (np.clip(normalized, 0, 1) * 255).astype(np.uint8)
    cell_f[..., 2] = (np.clip(-normalized, 0, 1) * 255).astype(np.uint8)
    cell_f[..., 1] = (support.astype(np.uint8) * 45)
    rows = _metrics_rows(metrics_csv)
    f_image = Image.fromarray(cell_f)
    f_draw = ImageDraw.Draw(f_image)
    last = rows[-1]
    keys = [key for key in ('loss_total','loss_base','loss_contact_xy','loss_contact_z','loss_zorder') if key in last]
    y = 32
    for key in keys:
        f_draw.text((6, y), f'{key}: {last[key]}', fill=(255, 255, 255)); y += 15
    cell_f = np.asarray(f_image)

    object_overlay = _overlay(crop, object_valid, (20, 210, 235), alpha=0.48)
    object_overlay[_edge(object_valid)] = (20, 255, 255)
    combined_overlay = _overlay(crop, object_valid, (20, 210, 235), alpha=0.36)
    combined_overlay = _overlay(combined_overlay, final_mask, (235, 40, 170), alpha=0.40)
    combined_overlay[_edge(object_valid)] = (20, 255, 255)
    combined_overlay[_edge(final_mask)] = (255, 40, 190)

    cells = [
        _title(cell_a, 'A  observed cropped RGB'),
        _title(cell_b, 'B  initial MANO hand (green)'),
        _title(cell_c, 'C  H0 step-5 MANO hand (magenta)'),
        _title(cell_d, 'D  initial green / final magenta'),
        _title(object_overlay, 'E  fixed Gate-A laptop mesh raster (cyan)'),
        _title(combined_overlay, 'F  laptop cyan + final hand magenta'),
        _title(cell_e, 'G  r04 cyan + selected pad vertices'),
        _title(cell_f, 'H  metric depth delta + final losses'),
    ]
    canvas = Image.new('RGB', (width * 4, height * 2), color=(0, 0, 0))
    for index, image in enumerate(cells):
        canvas.paste(image, ((index % 4) * width, (index // 3) * height))
    output_path = _fresh(output_path)
    temporary = output_path.with_suffix(output_path.suffix + '.partial')
    canvas.save(temporary, format='PNG')
    temporary.replace(output_path)
    return {'panel_path': str(output_path), 'panel_sha256': _sha(output_path),
            'panel_size': list(canvas.size), 'support_pixels': int(support.sum()),
            'r04_pixels': int((r04_mask & object_valid).sum()),
            'object_pixels': int(object_valid.sum()),
            'hand_object_overlap_pixels': int((final_mask & object_valid).sum()),
            'panel_kind': 'same_camera_hand_object_registration_v1'}


class ReadOnlyPanelCallback:
    def __init__(self, binder, resource_holder, checkpoint_path, crop_path, metrics_csv, panel_path):
        self.binder = binder
        self.resource_holder = resource_holder
        self.checkpoint_path = Path(checkpoint_path)
        self.crop_path = Path(crop_path)
        self.metrics_csv = Path(metrics_csv)
        self.panel_path = Path(panel_path)
        self._bound = False
        self._invoked = False

    def bind_live_context(self, context):
        if self._bound:
            raise RuntimeError('H0_panel_context_may_be_bound_once')
        self._bound = True
        return self.binder(context)

    def __call__(self, context):
        if self._invoked:
            raise RuntimeError('H0_panel_callback_may_be_invoked_once')
        self._invoked = True
        parameters = context.get('parameters') or {}
        if list(parameters) != ['global_hand_rotation', 'global_hand_translation']:
            raise ValueError('panel_live_Rt_order_mismatch')
        resources = self.resource_holder.get('resources')
        if not isinstance(resources, dict):
            raise RuntimeError('panel_resources_not_bound')
        hooks = context.get('hooks') or {}
        required_hooks = {'frozen_state', 'object_vertices', 'rasterize_object'}
        if not required_hooks.issubset(hooks):
            raise RuntimeError('panel_read_only_hooks_missing')
        try:
            checkpoint = torch.load(self.checkpoint_path, map_location='cpu', weights_only=False)
        except TypeError:
            checkpoint = torch.load(self.checkpoint_path, map_location='cpu')
        if checkpoint.get('step') != 5 or set(checkpoint.get('parameters') or {}) != set(parameters):
            raise ValueError('panel_checkpoint_contract_mismatch')
        original = {name: value.detach().clone() for name, value in parameters.items()}
        flags = {name: bool(value.requires_grad) for name, value in parameters.items()}
        gradients = {name: None if value.grad is None else value.grad.detach().clone() for name, value in parameters.items()}
        frozen_before = _state_digest(hooks['frozen_state']())
        result = None
        try:
            initial = _render_state(context, resources, 0)
            with torch.no_grad():
                for name, value in parameters.items():
                    saved = checkpoint['parameters'][name].to(device=value.device, dtype=value.dtype)
                    if saved.shape != value.shape or not bool(torch.isfinite(saved).all()):
                        raise ValueError(f'invalid_checkpoint_parameter:{name}')
                    value.copy_(saved)
            final = _render_state(context, resources, 1)
            raster = hooks['rasterize_object'](hooks['object_vertices']())
            panel = compose_registration_panel(self.crop_path, initial, final,
                                      _array(raster['depth']), _array(raster['valid']),
                                      _array(raster['r04']), self.metrics_csv, self.panel_path)
            deltas = {name: float(torch.linalg.vector_norm(
                checkpoint['parameters'][name].to(dtype=original[name].dtype)-original[name].cpu()))
                for name in parameters}
            result = {**panel, 'checkpoint': str(self.checkpoint_path),
                      'checkpoint_sha256': _sha(self.checkpoint_path),
                      'parameter_delta_norms': deltas,
                      'initial_positive_depth_pixels': int((initial['hand_valid'] & (initial['hand_depth'] > 0)).sum()),
                      'final_positive_depth_pixels': int((final['hand_valid'] & (final['hand_depth'] > 0)).sum()),
                      'new_gradient_count': 0, 'optimizer_updates': 0,
                      'early_termination_requested': True}
        finally:
            with torch.no_grad():
                for name, value in parameters.items():
                    value.copy_(original[name])
            for name, value in parameters.items():
                value.requires_grad_(flags[name])
                before = gradients[name]
                if before is None and value.grad is not None:
                    value.grad = None
                elif before is not None:
                    if value.grad is None:
                        value.grad = before.clone()
                    else:
                        value.grad.copy_(before)
        frozen_after = _state_digest(hooks['frozen_state']())
        result['parameters_restored'] = all(torch.equal(parameters[name], original[name]) for name in parameters)
        result['trainability_flags_restored'] = all(parameters[name].requires_grad == flags[name] for name in parameters)
        result['gradient_state_restored'] = all(
            (gradients[name] is None and parameters[name].grad is None) or
            (gradients[name] is not None and parameters[name].grad is not None and torch.equal(parameters[name].grad, gradients[name]))
            for name in parameters)
        result['frozen_digest_before'] = frozen_before
        result['frozen_digest_after'] = frozen_after
        result['frozen_unchanged'] = frozen_before == frozen_after
        raise H0PanelComplete(result)


def create_panel_callback(manifest_path, source_bundle_path, policy_path, output_root,
                          checkpoint_path, crop_path, metrics_csv, panel_path,
                          resources_override=None):
    output_root = Path(output_root)
    holder = {}
    def binder(context):
        parameters = context.get('parameters') or {}
        first = parameters.get('global_hand_rotation')
        if first is None:
            raise ValueError('global_hand_rotation_missing')
        resources = resources_override
        if resources is None:
            resources = load_case_resources(manifest_path, source_bundle_path,
                                            policy_path, first.device, first.dtype)
        holder['resources'] = resources
        return bind_live_context(context, resources, output_root / 'read_only_runtime')
    return ReadOnlyPanelCallback(binder, holder, checkpoint_path, crop_path,
                                 metrics_csv, panel_path)
