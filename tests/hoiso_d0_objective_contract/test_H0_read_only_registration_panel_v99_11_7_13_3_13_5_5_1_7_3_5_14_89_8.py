import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from foho.guidance.h0_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8 import H0PanelComplete, ReadOnlyPanelCallback


class Mesh:
    def __init__(self, vertices):
        self.vertices = vertices
        self.faces = torch.tensor([[0, 1, 2]], dtype=torch.long)
    def verts_packed(self): return self.vertices
    def faces_packed(self): return self.faces


class Cameras:
    R = torch.eye(3).unsqueeze(0)
    T = torch.zeros(1, 3)
    def get_world_to_view_transform(self): return self
    def transform_points(self, points): return points
    def transform_points_screen(self, points, image_size=None):
        result = points.clone(); result[..., :2] = result[..., :2] + 3.0; return result


class Fragments:
    def __init__(self):
        self.pix_to_face = torch.full((1, 8, 8, 1), -1, dtype=torch.long)
        self.pix_to_face[0, 2, 2, 0] = 0
        self.bary_coords = torch.zeros((1, 8, 8, 1, 3), dtype=torch.float32)
        self.bary_coords[0, 2, 2, 0] = torch.tensor([1.0, 0.0, 0.0])


class Rasterizer:
    def __init__(self): self.cameras = Cameras()
    def __call__(self, mesh): return Fragments()


class Renderer:
    def __init__(self): self.rasterizer = Rasterizer()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--receipt', required=True); args = parser.parse_args()
    receipt = Path(args.receipt); failed = []; errors = []; checks = {}
    try:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); crop = root/'crop.png'; metrics = root/'metrics.csv'; checkpoint = root/'step5.pt'; panel = root/'panel.png'
            Image.fromarray(np.full((8, 8, 3), 120, dtype=np.uint8)).save(crop)
            metrics.write_text('step,loss_total,loss_base,loss_contact_xy,loss_contact_z,loss_zorder\n5,1.0,0.5,0.2,0.2,0.1\n')
            rotation = torch.tensor([1.0, 0.0, 0.0, 0.0]); translation = torch.zeros(3)
            torch.save({'step':5, 'parameters':{'global_hand_rotation':torch.tensor([0.99, 0.1, 0.0, 0.0]),
                                                'global_hand_translation':torch.tensor([1.0, 0.0, 0.0])}}, checkpoint)
            object_depth = torch.ones(8, 8); object_valid = torch.ones(8, 8, dtype=torch.bool)
            r04 = torch.zeros(8, 8, dtype=torch.bool); r04[2, 2] = True
            vertices = torch.tensor([[0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]])
            resources = {'pad_ids':torch.tensor([0, 1]), 'object_depth':object_depth,
                         'object_valid':object_valid, 'r04':r04}
            def compute_base_loss(index=0):
                moved = vertices.clone(); moved[:, 0] += translation[0]
                mask = torch.zeros(8, 8); column = min(6, 2 + int(round(float(translation[0])))); mask[2:5, column:column+2] = 1
                normal = torch.zeros(8, 8, 3); normal[..., 2] = 1
                return (rotation.square().sum() + translation.square().sum()), {
                    'transformed_hand_mesh':Mesh(moved), 'rendered_normal_hand':normal,
                    'rendered_disp_hand':torch.ones(8, 8), 'sil_mano_hand':mask,
                    'opt_2d_kps':torch.zeros(21, 2)}
            context = {'parameters':{'global_hand_rotation':rotation, 'global_hand_translation':translation},
                       'frozen':{'scale':torch.ones(1)}, 'compute_base_loss':compute_base_loss,
                       'rendering':{'renderer':Renderer(), 'image_size':(8, 8)},
                       'hooks':{'frozen_state':lambda:{'scale':torch.ones(1)},
                                'object_vertices':lambda:vertices,
                                'rasterize_object':lambda value:{'depth':object_depth, 'valid':object_valid, 'r04':r04}}}
            holder = {'resources':resources}
            callback = ReadOnlyPanelCallback(lambda value:value, holder, checkpoint, crop, metrics, panel)
            bound = callback.bind_live_context(context)
            before = {'rotation':rotation.clone(), 'translation':translation.clone()}
            outcome = None
            try: callback(bound)
            except H0PanelComplete as complete: outcome = complete.result
            second_bind_rejected = False
            try: callback.bind_live_context(context)
            except RuntimeError: second_bind_rejected = True
            checks = {'panel_written':panel.is_file(), 'panel_size':Image.open(panel).size == (32, 16),
                      'early_termination':outcome.get('early_termination_requested') is True,
                      'zero_updates':outcome.get('optimizer_updates') == 0,
                      'zero_new_gradients':outcome.get('new_gradient_count') == 0,
                      'parameters_restored':outcome.get('parameters_restored') is True and torch.equal(rotation, before['rotation']) and torch.equal(translation, before['translation']),
                      'flags_restored':outcome.get('trainability_flags_restored') is True,
                      'gradient_state_restored':outcome.get('gradient_state_restored') is True,
                      'frozen_unchanged':outcome.get('frozen_unchanged') is True,
                      'positive_depth_both':outcome.get('initial_positive_depth_pixels', 0) > 0 and outcome.get('final_positive_depth_pixels', 0) > 0,
                      'r04_nonempty':outcome.get('r04_pixels', 0) > 0,
                      'object_raster_nonempty':outcome.get('object_pixels', 0) > 0,
                      'overlap_count_reported':isinstance(outcome.get('hand_object_overlap_pixels'), int),
                      'registration_panel_kind':outcome.get('panel_kind') == 'same_camera_hand_object_registration_v1',
                      'second_bind_rejected':second_bind_rejected}
            failed.extend(name for name, value in checks.items() if not value)
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    payload = {'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8_H0_read_only_panel_CPU_closed'
                           if not failed and not errors else
                           'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8_H0_read_only_panel_CPU'),
               'checks':checks, 'failed':failed, 'errors':errors, 'GPU_used':False, 'optimizer_updates':0}
    if not receipt.exists():
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(payload))


if __name__ == '__main__': main()
