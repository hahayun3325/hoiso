import json
import math
import os
from pathlib import Path

import torch

from foho.guidance.h1_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import run_live


class FakeRuntime:
    def __init__(self,gate=True):
        self.p=torch.nn.Parameter(torch.zeros(6,3),requires_grad=False)
        self.fixed=torch.arange(6,dtype=torch.float32); self.optimizer=None
        self.gate=gate; self.raster_calls=0; self.checkpoints=[]; self.captures=[]
    def parameter_registry(self): return {'selected_so3_residual':self.p}
    def frozen_state(self): return {'fixed':self.fixed}
    def rasterize_object(self): self.raster_calls+=1; return {'bound':True}
    def compute_loss(self,raster):
        weights=torch.arange(1,19,dtype=self.p.dtype).reshape(6,3)
        loss=(self.p*weights).sum()+self.p.square().sum()
        return loss,{'loss_total':float(loss.detach()),'H1_contact_active':True,
                     'mesh_aware_base_loss_active':True,'dense_raster_bound':bool(raster['bound'])}
    def gate_pass(self,metrics): return self.gate
    def snapshot(self):
        return {'p':self.p.detach().clone(),'flag':bool(self.p.requires_grad),
                'optimizer':self.optimizer.state_dict() if self.optimizer is not None else None}
    def restore(self,value):
        with torch.no_grad(): self.p.copy_(value['p'])
        self.p.requires_grad_(value['flag'])
        if self.optimizer is not None and value['optimizer'] is not None: self.optimizer.load_state_dict(value['optimizer'])
    def build_optimizer(self,selected):
        if len(selected)!=1 or selected[0] is not self.p: raise ValueError('identity')
        self.optimizer=torch.optim.SGD(selected,lr=1e-3,momentum=0.9); return self.optimizer
    def save_checkpoint(self,step,metrics): self.checkpoints.append(step)
    def capture(self,step,raster): self.captures.append(step); return {'step':step,'raster_bound':True}


receipt=Path(os.environ['CPU90521']); errors=[]; checks={}
try:
    backward=FakeRuntime(); before=backward.p.detach().clone()
    b=run_live(backward,attempts=0,backward_only=True)
    capture=FakeRuntime(); c=run_live(capture,attempts=0,capture_only=True)
    optimize=FakeRuntime(); o=run_live(optimize,attempts=2)
    reject=FakeRuntime(gate=False); reject_before=reject.p.detach().clone(); r=run_live(reject,attempts=2)
    root=Path('/home/fredcui/Projects/FollowMyHold')
    binder=(root/'src/foho/guidance/h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py').read_text()
    launcher=(root/'src/foho/guidance/run_alapuse02v3n60_d0_h1_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py').read_text()
    policy=json.loads((root/'config/optimization/H1_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.json').read_text())
    stats=b.get('gradient_stats',{}).get('selected_so3_residual',{})
    checks={
      'backward_zero_updates':b.get('updates_completed')==0 and torch.equal(before,backward.p.detach()),
      'exact_18_finite_nonzero_gradients':stats.get('nonzero_coordinates')==18 and math.isfinite(float(stats.get('norm',float('nan')))) and stats.get('norm',0)>0,
      'requires_grad_restored':backward.p.requires_grad is False,
      'capture_zero_state':c.get('updates_completed')==0 and capture.raster_calls==1 and not capture.checkpoints,
      'two_accepted_attempts':o.get('updates_completed')==2 and o.get('attempts_completed')==2 and optimize.checkpoints==[1,2],
      'rejection_rolls_back':r.get('rolled_back') is True and torch.equal(reject_before,reject.p.detach()),
      'object_raster_once_per_run':all(x.raster_calls==1 for x in (backward,capture,optimize,reject)),
      'binder_calls_provider':all(token in binder for token in ('H1SelectedFingerMANOProvider','compute_base_loss_for_mesh','selected_so3_residual','accepted_rotation','accepted_translation')),
      'binder_has_metric_contact_and_zorder':all(token in binder for token in ('interpolate_metric_face_depth','dense_valid_zorder_loss','loss_contact_xy','loss_contact_z')),
      'launcher_has_three_modes':all(token in launcher for token in ('backward-only','capture-only','optimize')),
      'launcher_passes_explicit_callback':'invoke_callback_capable_target' in launcher,
      'policy_PASS_ground_truth_free':policy.get('status')=='PASS' and policy.get('ground_truth_fields')==[],
    }
except Exception as exc: errors.append(f'{type(exc).__name__}:{exc}')
failed=[k for k,v in checks.items() if not v]
payload={'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5_2_1_H1_runtime_binding_CPU_closed'
                     if not receipt.exists() and not failed and not errors else 'review_required_14_90_5_2_1_recheck_H1_runtime_binding_CPU'),
         'checks':checks,'failed':failed,'missing':[],'existing':[str(receipt)] if receipt.exists() else [],
         'errors':errors,'GPU_used':False,'optimizer_updates':0}
if not receipt.exists(): receipt.write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload))
