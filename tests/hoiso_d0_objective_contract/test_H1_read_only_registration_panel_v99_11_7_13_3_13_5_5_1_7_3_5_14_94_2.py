import ast
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from foho.guidance.h1_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2 import (
    _preserve_parameter,
    compose_h1_panel,
)


def main():
    receipt = Path(os.environ['CPU1943'])
    errors = []
    checks = {}
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            crop = root / 'crop.png'
            metrics = root / 'metrics.json'
            panel = root / 'panel.png'
            Image.fromarray(np.full((32, 32, 3), 90, dtype=np.uint8)).save(crop)
            metrics.write_text(json.dumps({
                'initial_metrics': {'loss_total': 10.0, 'loss_contact_xy': 2.0, 'loss_contact_z': 1.0, 'loss_zorder': 0.5},
                'final_metrics': {'loss_total': 8.0, 'loss_contact_xy': 1.5, 'loss_contact_z': 0.8, 'loss_zorder': 0.4},
                'trajectory': [{'post_loss': 9.0}, {'post_loss': 8.0}]}) + '\n')
            state0 = {'mask': np.eye(32, dtype=bool), 'pad_xy': np.array([[8, 8], [9, 9]])}
            state1 = {'mask': np.fliplr(np.eye(32, dtype=bool)), 'pad_xy': np.array([[12, 12], [13, 13]])}
            outcome = compose_h1_panel(crop, state0, state1, np.ones((32, 32), dtype=bool),
                                       np.eye(32, dtype=bool), metrics, panel)
            checks['eight_panel_compositor'] = outcome.get('cell_count') == 8 and outcome.get('panel_size') == [128, 64]
            checks['fresh_panel_written'] = panel.is_file()
        parameter = torch.nn.Parameter(torch.zeros(6, 3), requires_grad=False)
        parameter.grad = torch.ones_like(parameter)
        original_grad = parameter.grad.clone()
        with _preserve_parameter(parameter):
            parameter.requires_grad_(True)
            with torch.no_grad():
                parameter.add_(2.0)
            parameter.grad.zero_()
        checks['parameter_value_restored'] = bool(torch.equal(parameter, torch.zeros_like(parameter)))
        checks['trainability_restored'] = parameter.requires_grad is False
        checks['gradient_restored'] = bool(torch.equal(parameter.grad, original_grad))
        project = Path('/home/fredcui/Projects/FollowMyHold')
        module = project / 'src/foho/guidance/h1_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2.py'
        launcher = project / 'src/foho/guidance/run_alapuse02v3n60_h1_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2.py'
        module_text = module.read_text()
        launcher_text = launcher.read_text()
        ast.parse(module_text)
        ast.parse(launcher_text)
        checks['no_backward_optimizer_or_checkpoint_write'] = not any(
            token in module_text for token in ('.backward(', 'torch.optim', 'optimizer.step(', 'torch.save('))
        checks['launcher_has_no_optimize_mode'] = '--mode' not in launcher_text and 'pass_H1_read_only_same_camera_panel' in launcher_text
        checks['explicit_callback_forwarding'] = 'invoke_callback_capable_target(run_hunyuan_w_guid, callback, kwargs)' in launcher_text
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    failed = [name for name, value in checks.items() if not value]
    payload = {'decision': ('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_3_H1_panel_CPU_closed'
                            if not failed and not errors else 'review_required_14_94_3_H1_panel_CPU'),
               'checks': checks, 'failed': failed, 'missing': [],
               'existing': [str(receipt)] if receipt.exists() else [], 'errors': errors,
               'H1': {'authorized': 1, 'spent': 1, 'executable': False},
               'GPU_used': False, 'optimizer_updates': 0}
    if not receipt.exists():
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(payload))


if __name__ == '__main__':
    main()
