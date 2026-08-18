from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from pytorch3d.structures import Meshes
from pytorch3d.transforms import quaternion_to_matrix

from foho.guidance.h0_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8 import (
    _array,
    _edge,
    _fresh,
    _overlay,
    _resize,
    _sha,
    _state_digest,
    _title,
)
from foho.guidance.h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import (
    bind_live_context as bind_h1_live_context,
    load_h1_resources,
)


class H1PanelComplete(RuntimeError):
    def __init__(self, result):
        super().__init__('H1_read_only_panel_complete')
        self.result = result


@contextmanager
def _preserve_parameter(parameter):
    value = parameter.detach().clone()
    flag = bool(parameter.requires_grad)
    gradient = None if parameter.grad is None else parameter.grad.detach().clone()
    try:
        yield
    finally:
        with torch.no_grad():
            parameter.copy_(value)
        parameter.requires_grad_(flag)
        if gradient is None:
            parameter.grad = None
        elif parameter.grad is None:
            parameter.grad = gradient.clone()
        else:
            parameter.grad.copy_(gradient)


def _mesh_state(provider, residual, accepted_rotation, accepted_translation, scale,
                faces, renderer, image_size, pad_ids):
    parameter = provider.selected_so3_residual
    with torch.no_grad():
        parameter.copy_(residual.to(device=parameter.device, dtype=parameter.dtype))
        vertices = provider()[0]
        center = (vertices.min(0).values + vertices.max(0).values) / 2.0
        rotation = quaternion_to_matrix(accepted_rotation.reshape(-1, 4))[0]
        transformed = (scale * (vertices - center)) @ rotation.transpose(0, 1)
        transformed = transformed + center + accepted_translation.reshape(-1, 3)[0]
        mesh = Meshes(verts=[transformed], faces=[faces])
        fragments = renderer.rasterizer(mesh)
        mask = torch.squeeze(fragments.pix_to_face[..., 0] >= 0)
        height, width = image_size
        screen = renderer.rasterizer.cameras.transform_points_screen(
            transformed.unsqueeze(0), image_size=(height, width))[0]
        safe_ids = pad_ids[(pad_ids >= 0) & (pad_ids < transformed.shape[0])]
        pad_xy = screen[safe_ids, :2]
    return {'mask': _array(mask).astype(bool), 'pad_xy': _array(pad_xy)}


def _object_mask(resources, renderer):
    h0 = resources['h0']
    vertices = h0['object_vertices']
    faces = h0['object_faces']
    if vertices.ndim == 3:
        vertices = vertices[0]
    if faces.ndim == 3:
        faces = faces[0]
    with torch.no_grad():
        fragments = renderer.rasterizer(Meshes(verts=[vertices], faces=[faces]))
    return _array(torch.squeeze(fragments.pix_to_face[..., 0] >= 0)).astype(bool)


def _trajectory_cell(metrics, size):
    width, height = size
    image = Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((8, 32), 'H1 five-attempt trajectory', fill=(255, 255, 255))
    rows = metrics.get('trajectory') if isinstance(metrics.get('trajectory'), list) else []
    losses = [float(metrics.get('initial_metrics', {}).get('loss_total', 0.0))]
    losses.extend(float(row['post_loss']) for row in rows if isinstance(row, dict) and 'post_loss' in row)
    if len(losses) >= 2:
        low, high = min(losses), max(losses)
        span = max(high - low, 1e-8)
        points = []
        for index, value in enumerate(losses):
            x = 24 + index * (width - 48) / max(len(losses) - 1, 1)
            y = 72 + (high - value) * (height - 150) / span
            points.append((x, y))
        draw.line(points, fill=(80, 220, 255), width=4)
        for point in points:
            draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=(255, 220, 30))
    initial = metrics.get('initial_metrics') or {}
    final = metrics.get('final_metrics') or {}
    y = height - 65
    for key in ('loss_total', 'loss_contact_xy', 'loss_contact_z', 'loss_zorder'):
        if key in initial and key in final:
            draw.text((8, y), f'{key}: {initial[key]:.6g} -> {final[key]:.6g}', fill=(255, 255, 255))
            y += 14
    return image


def compose_h1_panel(crop_path, initial, final, object_mask, r04, metrics_path, panel_path):
    crop = np.asarray(Image.open(crop_path).convert('RGB'))
    height, width = crop.shape[:2]
    size = (width, height)
    initial_mask = _resize(initial['mask'], size, nearest=True)
    final_mask = _resize(final['mask'], size, nearest=True)
    laptop_mask = _resize(object_mask, size, nearest=True)
    r04_mask = _resize(r04, size, nearest=True)

    initial_overlay = _overlay(crop, initial_mask, (40, 220, 80))
    final_overlay = _overlay(crop, final_mask, (235, 40, 170))
    laptop_overlay = _overlay(crop, laptop_mask, (20, 210, 235), alpha=0.42)
    laptop_overlay[_edge(laptop_mask)] = (20, 255, 255)
    combined = _overlay(crop, laptop_mask, (20, 210, 235), alpha=0.30)
    combined = _overlay(combined, final_mask, (235, 40, 170), alpha=0.44)
    difference = crop.copy()
    difference[_edge(initial_mask)] = (40, 255, 80)
    difference[_edge(final_mask)] = (255, 40, 190)

    support = _overlay(crop, r04_mask & laptop_mask, (20, 210, 235), alpha=0.55)
    support_image = Image.fromarray(support)
    support_draw = ImageDraw.Draw(support_image)
    for xy in np.asarray(initial['pad_xy']):
        x, y = float(xy[0]), float(xy[1])
        support_draw.ellipse((x - 3, y - 3, x + 3, y + 3), outline=(40, 255, 80), width=2)
    for xy in np.asarray(final['pad_xy']):
        x, y = float(xy[0]), float(xy[1])
        support_draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 220, 30))

    metrics = json.loads(Path(metrics_path).read_text())
    cells = [
        _title(crop, 'A  observed cropped RGB'),
        _title(initial_overlay, 'B  H1 initial hand (green)'),
        _title(final_overlay, 'C  H1 accepted step 5 hand (magenta)'),
        _title(laptop_overlay, 'D  fixed Gate-A laptop (cyan)'),
        _title(combined, 'E  final H1 hand + fixed laptop'),
        _title(difference, 'F  initial green / final magenta'),
        _title(np.asarray(support_image), 'G  r04 + selected pad support'),
        _title(np.asarray(_trajectory_cell(metrics, size)), 'H  accepted trajectory and metrics'),
    ]
    canvas = Image.new('RGB', (width * 4, height * 2), (0, 0, 0))
    for index, cell in enumerate(cells):
        canvas.paste(cell, ((index % 4) * width, (index // 4) * height))
    panel_path = _fresh(panel_path)
    temporary = panel_path.with_suffix(panel_path.suffix + '.partial')
    canvas.save(temporary, format='PNG')
    temporary.replace(panel_path)
    return {'panel_path': str(panel_path), 'panel_sha256': _sha(panel_path),
            'panel_size': list(canvas.size), 'cell_count': 8,
            'initial_pixels': int(initial_mask.sum()), 'final_pixels': int(final_mask.sum()),
            'laptop_pixels': int(laptop_mask.sum()), 'r04_pixels': int((r04_mask & laptop_mask).sum())}


class ReadOnlyH1PanelCallback:
    def __init__(self, binder, holder, checkpoint_path, crop_path, metrics_path, panel_path):
        self.binder = binder
        self.holder = holder
        self.checkpoint_path = Path(checkpoint_path)
        self.crop_path = Path(crop_path)
        self.metrics_path = Path(metrics_path)
        self.panel_path = Path(panel_path)
        self._bound = False
        self._invoked = False

    def bind_live_context(self, context):
        if self._bound:
            raise RuntimeError('H1_panel_context_may_be_bound_once')
        self._bound = True
        return self.binder(context)

    def __call__(self, context):
        if self._invoked:
            raise RuntimeError('H1_panel_callback_may_be_invoked_once')
        self._invoked = True
        resources = self.holder.get('resources')
        if not isinstance(resources, dict):
            raise RuntimeError('H1_panel_resources_not_bound')
        checkpoint = torch.load(self.checkpoint_path, map_location='cpu', weights_only=False)
        residual = checkpoint.get('selected_so3_residual')
        if checkpoint.get('attempt') != 5 or not torch.is_tensor(residual) or tuple(residual.shape) != (6, 3):
            raise ValueError('H1_panel_checkpoint_contract_mismatch')
        rendering = context.get('rendering') or {}
        frozen = context.get('frozen') or {}
        renderer = rendering.get('renderer')
        image_size = tuple(rendering.get('image_size') or ())
        base_mesh = frozen.get('mano_mesh_moge')
        scale = frozen.get('global_hand_scale')
        runtime = context.get('h1_runtime')
        if renderer is None or len(image_size) != 2 or base_mesh is None or scale is None or runtime is None:
            raise ValueError('H1_panel_live_render_owners_missing')
        provider = resources['provider']
        parameter = provider.selected_so3_residual
        original_parameter = parameter.detach().clone()
        original_flag = bool(parameter.requires_grad)
        accepted_rotation = resources['accepted_rotation']
        accepted_translation = resources['accepted_translation']
        scale = scale.detach().clone() if torch.is_tensor(scale) else torch.as_tensor(scale, device=parameter.device, dtype=parameter.dtype)
        faces = base_mesh.faces_packed().detach().clone()
        pad_ids = resources['h0']['pad_ids']
        before = _state_digest(runtime.frozen_state())
        result = None
        with _preserve_parameter(parameter):
            initial = _mesh_state(provider, torch.zeros_like(parameter), accepted_rotation,
                                  accepted_translation, scale, faces, renderer, image_size, pad_ids)
            final = _mesh_state(provider, residual, accepted_rotation, accepted_translation,
                                scale, faces, renderer, image_size, pad_ids)
            laptop = _object_mask(resources, renderer)
            raster = runtime.rasterize_object()
            result = compose_h1_panel(self.crop_path, initial, final, laptop,
                                      _array(raster['r04']), self.metrics_path, self.panel_path)
        after = _state_digest(runtime.frozen_state())
        result.update({'checkpoint': str(self.checkpoint_path),
                       'checkpoint_sha256': _sha(self.checkpoint_path),
                       'selected_residual_norm': float(torch.linalg.vector_norm(residual)),
                       'parameter_restored': bool(torch.equal(parameter.detach(), original_parameter)),
                       'trainability_flag_restored': bool(parameter.requires_grad) == original_flag,
                       'frozen_digest_before': before, 'frozen_digest_after': after,
                       'frozen_unchanged': before == after, 'new_gradient_count': 0,
                       'optimizer_updates': 0, 'checkpoint_writes': 0,
                       'early_termination_requested': True})
        raise H1PanelComplete(result)


def create_h1_panel_callback(paths, output_root, checkpoint_path, crop_path,
                             metrics_path, panel_path, resources_override=None):
    holder = {}
    def binder(context):
        parameters = context.get('parameters') or {}
        reference = parameters.get('global_hand_rotation')
        if reference is None:
            raise ValueError('live_global_hand_rotation_missing')
        resources = resources_override or load_h1_resources(
            paths['h0_manifest'], paths['h0_source_bundle'], paths['h0_policy'], paths['h1_policy'],
            paths['provider'], paths['bridge'], paths['carrier'], paths['mano'], paths['jacobian'],
            paths['h0_checkpoint'], reference.device, reference.dtype)
        holder['resources'] = resources
        return bind_h1_live_context(context, resources, Path(output_root) / 'read_only_runtime')
    return ReadOnlyH1PanelCallback(binder, holder, checkpoint_path, crop_path,
                                   metrics_path, panel_path)
