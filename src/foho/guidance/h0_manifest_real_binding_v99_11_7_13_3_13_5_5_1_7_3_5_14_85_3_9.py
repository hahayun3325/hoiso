from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import torch
from pytorch3d.io import load_ply

from foho.guidance.h0_case_callback_factory_v99_11_7_13_3_13_5_5_1_7_3_5_14_84 import create_case_callback
from foho.guidance.h0_complete_hook_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_1 import build_complete_h0_hooks
from foho.guidance.h0_metric_face_depth_v99_11_7_13_3_13_5_5_1_7_3_5_14_85 import interpolate_metric_face_depth


class H0DiagnosticComplete(RuntimeError):
    def __init__(self, outcome):
        super().__init__('H0_diagnostic_complete')
        self.outcome = outcome


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifact(manifest, name):
    row = (manifest.get('artifacts') or {}).get(name) or {}
    path = Path(row.get('path', ''))
    if not path.is_file():
        raise FileNotFoundError(f'H0_artifact_missing:{name}:{path}')
    if row.get('sha256') != _sha(path):
        raise RuntimeError(f'H0_artifact_hash_mismatch:{name}')
    return path


def _number(value):
    if torch.is_tensor(value):
        return float(value.detach().cpu())
    return float(value)


def _fresh(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_case_resources(manifest_path, source_bundle_path, policy_path, device, dtype):
    manifest = json.loads(Path(manifest_path).read_text())
    policy = json.loads(Path(policy_path).read_text())
    source_bundle = json.loads(Path(source_bundle_path).read_text())
    if manifest.get('case_id') != 'alapuse02v3n60':
        raise ValueError('unexpected_case_id')
    if manifest.get('trainable') != ['global_hand_rotation', 'global_hand_translation']:
        raise ValueError('H0_trainable_order_mismatch')
    if policy.get('status') != 'PASS':
        raise ValueError('global_H0_policy_not_PASS')

    phase_path = _artifact(manifest, 'H0_PHASE_CONFIG')
    finger_path = _artifact(manifest, 'H0_FINGER_MAP')
    object_map_path = _artifact(manifest, 'OBJECT_PATCH_MAP')
    dense_path = _artifact(manifest, 'DENSE_PACKET')
    expansion_path = _artifact(manifest, 'EXPANSION_PACKET')
    hook_path = _artifact(manifest, 'H0_HOOK_BUNDLE')
    zorder_path = _artifact(manifest, 'H0_ZORDER')

    fingers = json.loads(finger_path.read_text())
    object_map = json.loads(object_map_path.read_text())
    if object_map.get('status') != 'PASS':
        raise ValueError('object_patch_map_not_PASS')
    pad_ids = []
    for name in ('index', 'middle'):
        pad_ids.extend((fingers.get('fingers', {}).get(name) or {}).get('contact_pad_vertex_ids', []))
    if not pad_ids:
        raise ValueError('index_middle_contact_pad_empty')

    with np.load(dense_path, allow_pickle=False) as packet:
        object_depth = np.asarray(packet['object_depth'])
        object_valid = np.asarray(packet['object_depth_valid'], dtype=bool)
    with np.load(expansion_path, allow_pickle=False) as packet:
        r04 = np.asarray(packet['r04_pixels'], dtype=bool)
    if object_depth.shape != object_valid.shape or object_depth.shape != r04.shape:
        raise ValueError('dense_r04_shape_mismatch')
    if not np.any(object_valid & np.isfinite(object_depth) & (object_depth > 0)):
        raise ValueError('dense_object_depth_empty')
    if not np.any(r04 & object_valid):
        raise ValueError('r04_support_empty')

    verified = (source_bundle.get('frozen_object_owner') or {}).get('verified') or []
    verified = [row for row in verified if row.get('hash_matches') is True]
    if len(verified) != 1:
        raise ValueError('exactly_one_frozen_GateA_mesh_required')
    object_mesh_path = Path(verified[0]['path'])
    if _sha(object_mesh_path) != verified[0]['actual_sha256']:
        raise RuntimeError('frozen_GateA_mesh_hash_mismatch')
    object_vertices, object_faces = load_ply(str(object_mesh_path))
    object_vertices = object_vertices.to(device=device, dtype=dtype)
    object_faces = object_faces.to(device=device)
    diagonal = torch.linalg.vector_norm(object_vertices.max(0).values-object_vertices.min(0).values)
    if not bool(torch.isfinite(diagonal)) or float(diagonal) <= 0:
        raise ValueError('invalid_object_diagonal')

    return {
        'phase_config_path':phase_path,
        'hook_module':_load_module(hook_path, '_h0_hook_bundle_live'),
        'zorder_module':_load_module(zorder_path, '_h0_zorder_live'),
        'pad_ids':torch.as_tensor(sorted(set(pad_ids)), device=device, dtype=torch.long),
        'object_depth':torch.as_tensor(object_depth, device=device, dtype=dtype),
        'object_valid':torch.as_tensor(object_valid, device=device, dtype=torch.bool),
        'r04':torch.as_tensor(r04, device=device, dtype=torch.bool),
        'object_vertices':object_vertices,
        'object_faces':object_faces,
        'object_diagonal':diagonal,
        'policy':policy,
        'artifact_hashes':{name:(manifest['artifacts'][name]['sha256']) for name in manifest.get('artifacts', {})},
    }


def bind_live_context(context, resources, output_root):
    if not isinstance(context, dict):
        raise TypeError('live_context_must_be_dictionary')
    parameters = context.get('parameters') or {}
    if list(parameters) != ['global_hand_rotation', 'global_hand_translation']:
        raise ValueError('live_global_Rt_order_mismatch')
    rotation = parameters['global_hand_rotation']
    translation = parameters['global_hand_translation']
    rendering = context.get('rendering') or {}
    renderer = rendering.get('renderer')
    image_size = tuple(rendering.get('image_size') or ())
    if renderer is None or len(image_size) != 2:
        raise ValueError('renderer_and_image_size_required')

    output_root = Path(output_root)
    policy = resources['policy']
    weights = policy['weights']
    initial = {name:value.detach().clone() for name,value in parameters.items()}
    state = {'optimizer':None, 'raster_calls':0, 'loss_calls':0,
             'last_metrics':None, 'accepted_total':None}

    def frozen_state():
        frozen = context.get('frozen') or {}
        mano = frozen.get('mano_mesh_moge')
        camera = renderer.rasterizer.cameras
        result = {
            'global_hand_scale':frozen.get('global_hand_scale'),
            'scale_obj':frozen.get('scale_obj'),
            'trans_obj':frozen.get('trans_obj'),
            'rotation_obj':frozen.get('rotation_obj'),
            'GateA_vertices':resources['object_vertices'],
            'GateA_faces':resources['object_faces'],
            'camera_R':camera.R,
            'camera_T':camera.T,
            'object_depth':resources['object_depth'],
            'object_valid':resources['object_valid'],
            'r04':resources['r04'],
        }
        if mano is not None:
            result['mano_base_vertices'] = mano.verts_packed()
            result['mano_base_faces'] = mano.faces_packed()
        return result

    def object_vertices():
        return resources['object_vertices']

    def rasterize_object(vertices):
        if vertices is not resources['object_vertices']:
            raise RuntimeError('frozen_object_identity_mismatch')
        state['raster_calls'] += 1
        return {'depth':resources['object_depth'], 'valid':resources['object_valid'],
                'r04':resources['r04']}

    def evaluate(raster, config):
        state['loss_calls'] += 1
        base_loss, base = context['compute_base_loss'](state['loss_calls'])
        mesh = base['transformed_hand_mesh']
        fragments = renderer.rasterizer(mesh)
        vertices = mesh.verts_packed()
        faces = mesh.faces_packed()
        view_vertices = renderer.rasterizer.cameras.get_world_to_view_transform().transform_points(vertices)
        vertex_depth = -view_vertices[:, 2]
        hand_depth, hand_valid = interpolate_metric_face_depth(
            fragments.pix_to_face, fragments.bary_coords, faces, vertex_depth)
        if hand_depth.ndim == 3 and hand_depth.shape[0] == 1:
            hand_depth = hand_depth[0]
            hand_valid = hand_valid[0]

        height, width = image_size
        screen = renderer.rasterizer.cameras.transform_points_screen(
            vertices.unsqueeze(0), image_size=(height, width))[0]
        pad_ids = resources['pad_ids']
        if int(pad_ids.max()) >= vertices.shape[0]:
            raise IndexError('contact_pad_vertex_out_of_range')
        pad_xy = screen[pad_ids, :2]
        pad_depth = vertex_depth[pad_ids]
        r04_yx = torch.nonzero(raster['r04'] & raster['valid'], as_tuple=False)
        if r04_yx.numel() == 0:
            raise RuntimeError('r04_valid_support_empty')
        r04_xy = r04_yx[:, [1, 0]].to(dtype=pad_xy.dtype)
        distances = torch.cdist(pad_xy, r04_xy)
        nearest = distances.argmin(dim=1)
        nearest_yx = r04_yx[nearest]
        target_depth = raster['depth'][nearest_yx[:, 0], nearest_yx[:, 1]]
        image_diagonal = math.sqrt(float(height*height + width*width))
        contact_xy = distances.min(dim=1).values.mean()/image_diagonal
        contact_z = (pad_depth-target_depth).abs().mean()/resources['object_diagonal']

        zorder_loss, _, zfacts = resources['zorder_module'].dense_valid_zorder_loss(
            hand_depth, raster['depth'], raster['valid'],
            contact_exempt_mask=raster['r04'],
            margin=float(policy['zorder_margin']),
            object_diagonal=resources['object_diagonal'])
        hand_positive = hand_valid.bool() & torch.isfinite(hand_depth) & (hand_depth > 0)
        object_positive = raster['valid'].bool() & torch.isfinite(raster['depth']) & (raster['depth'] > 0)
        overlap = hand_positive & object_positive
        exempt_overlap = overlap & raster['r04'].bool()
        nonexempt_overlap = overlap & ~raster['r04'].bool()
        trust_rotation = (rotation-initial['global_hand_rotation']).pow(2).mean()
        trust_translation = torch.linalg.vector_norm(
            translation-initial['global_hand_translation'])/resources['object_diagonal']
        trust = trust_rotation+trust_translation
        total = (float(weights['base'])*base_loss +
                 float(weights['contact_xy'])*contact_xy +
                 float(weights['contact_z'])*contact_z +
                 float(weights['zorder'])*zorder_loss +
                 float(weights['trust'])*trust)
        metrics = {
            'loss_total':_number(total), 'loss_base':_number(base_loss),
            'loss_contact_xy':_number(contact_xy), 'loss_contact_z':_number(contact_z),
            'loss_zorder':_number(zorder_loss), 'loss_trust':_number(trust),
            'D0_contact_active':True, 'dense_raster_bound':True,
            'metric_hand_depth_active':bool(hand_valid.any().detach().cpu()),
            'zorder_valid_count':int(zfacts['valid_count']),
            'zorder_candidate_count':int(zfacts['candidate_count']),
            'hand_depth_valid_count':int(hand_positive.sum().detach().cpu()),
            'object_depth_valid_count':int(object_positive.sum().detach().cpu()),
            'zorder_overlap_count':int(overlap.sum().detach().cpu()),
            'zorder_exempt_overlap_count':int(exempt_overlap.sum().detach().cpu()),
            'zorder_nonexempt_overlap_count':int(nonexempt_overlap.sum().detach().cpu()),
            'r04_support_count':int(r04_yx.shape[0]),
            'raster_calls':state['raster_calls'], 'loss_calls':state['loss_calls'],
        }
        state['last_metrics'] = metrics
        return total, metrics

    def gate_pass(metrics):
        numeric = [metrics[name] for name in
                   ('loss_total','loss_base','loss_contact_xy','loss_contact_z','loss_zorder','loss_trust')]
        if not all(math.isfinite(float(value)) for value in numeric):
            return False
        if metrics.get('r04_support_count', 0) <= 0:
            return False
        prior = state['accepted_total']
        current = float(metrics['loss_total'])
        if prior is not None:
            permitted = prior*(1.0+float(policy['gate']['max_relative_total_regression']))
            if current > permitted+float(policy['gate']['absolute_tolerance']):
                return False
        state['accepted_total'] = current
        return True

    def snapshot():
        return {
            'values':{name:value.detach().clone() for name,value in parameters.items()},
            'flags':{name:bool(value.requires_grad) for name,value in parameters.items()},
            'optimizer':copy.deepcopy(state['optimizer'].state_dict()) if state['optimizer'] is not None else None,
            'accepted_total':state['accepted_total'],
        }

    def restore(snapshot_value):
        with torch.no_grad():
            for name,value in parameters.items():
                value.copy_(snapshot_value['values'][name])
        for name,value in parameters.items():
            value.requires_grad_(snapshot_value['flags'][name])
        if state['optimizer'] is not None and snapshot_value['optimizer'] is not None:
            state['optimizer'].load_state_dict(snapshot_value['optimizer'])
        state['accepted_total'] = snapshot_value['accepted_total']

    def save_checkpoint(step, metrics):
        path = _fresh(output_root/'checkpoints'/f'H0_step_{int(step):03d}.pt')
        torch.save({'step':int(step),
                    'parameters':{name:value.detach().cpu() for name,value in parameters.items()},
                    'optimizer':state['optimizer'].state_dict() if state['optimizer'] is not None else None,
                    'metrics':metrics, 'artifact_hashes':resources['artifact_hashes']}, path)
        return str(path)

    def capture(step, raster):
        with torch.no_grad():
            _, metrics = evaluate(raster, {})
        path = _fresh(output_root/'captures'/f'H0_capture_{int(step):03d}.json')
        path.write_text(json.dumps({'step':int(step),'metrics':metrics,
                                    'raster_bound':True},indent=2)+'\n')
        return {'step':int(step),'path':str(path),'raster_bound':True,'metrics':metrics}

    owners = {
        'frozen_state':frozen_state, 'object_vertices':object_vertices,
        'rasterize_object':rasterize_object, 'compute_loss':evaluate,
        'gate_pass':gate_pass, 'snapshot':snapshot, 'restore':restore,
        'save_checkpoint':save_checkpoint, 'capture':capture,
    }
    hooks = build_complete_h0_hooks(parameters, owners, float(policy['learning_rate']))
    original_builder = hooks['build_optimizer']
    def build_optimizer(selected):
        optimizer = original_builder(selected)
        state['optimizer'] = optimizer
        return optimizer
    hooks['build_optimizer'] = build_optimizer
    bound = dict(context)
    bound['hooks'] = hooks
    bound['metadata'] = {**dict(context.get('metadata') or {}),
                         'H0_real_binding':True,
                         'artifact_hashes':resources['artifact_hashes']}
    return bound


class BoundCaseCallback:
    def __init__(self, inner, binder, terminate_after_h0=True):
        self.inner = inner
        self.binder = binder
        self.terminate_after_h0 = bool(terminate_after_h0)
        self.binding = dict(getattr(inner, 'binding', {}))
        self._bound = False

    def bind_live_context(self, context):
        if self._bound:
            raise RuntimeError('H0_live_context_may_be_bound_once')
        self._bound = True
        return self.binder(context)

    def __call__(self, context):
        outcome = self.inner(context)
        if self.terminate_after_h0:
            raise H0DiagnosticComplete(outcome)
        return outcome


def create_bound_callback(manifest_path, source_bundle_path, policy_path,
                          output_root, updates=0, backward_only=True,
                          capture_only=False, resources_override=None,
                          terminate_after_h0=True):
    manifest = json.loads(Path(manifest_path).read_text())
    phase_config = _artifact(manifest, 'H0_PHASE_CONFIG')
    output_root = Path(output_root)
    runtime_output = output_root/'runtime_result.json'
    inner = create_case_callback(phase_config, runtime_output,
                                 updates=int(updates),
                                 backward_only=bool(backward_only),
                                 capture_only=bool(capture_only))
    def binder(context):
        parameters = context.get('parameters') or {}
        first = parameters.get('global_hand_rotation')
        if first is None:
            raise ValueError('global_hand_rotation_missing')
        resources = resources_override
        if resources is None:
            resources = load_case_resources(manifest_path, source_bundle_path,
                                            policy_path, first.device, first.dtype)
        return bind_live_context(context, resources, output_root)
    return BoundCaseCallback(inner, binder, terminate_after_h0=terminate_after_h0)
