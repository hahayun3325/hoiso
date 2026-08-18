import importlib.util,json,os
from pathlib import Path
import torch

spec=importlib.util.spec_from_file_location('_o0_runtime_candidate',os.environ['O0_RUNTIME_CANDIDATE'])
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class FakeRuntime:
    def __init__(self,gate=True):
        self.r=torch.nn.Parameter(torch.tensor([1.0,0.1,0.1,0.1]),requires_grad=False)
        self.t=torch.nn.Parameter(torch.tensor([0.1,0.2,0.3]),requires_grad=False)
        self.fixed=torch.arange(5,dtype=torch.float32); self.optimizer=None; self.gate=gate
        self.loss_calls=0; self.captures=[]; self.checkpoints=[]; self.accepted=None
    def parameter_registry(self): return {'global_object_rotation':self.r,'global_object_translation':self.t}
    def frozen_state(self): return {'accepted_H1':self.fixed,'scale':torch.tensor(1.0)}
    def compute_loss(self):
        self.loss_calls+=1; loss=(self.r*torch.tensor([1.,2.,3.,4.])).sum()+(self.t*torch.tensor([2.,3.,5.])).sum()
        return loss,{'loss_total':float(loss.detach()),'dynamic_raster':True,'raster_call':self.loss_calls}
    def gate_pass(self,metrics): return self.gate
    def snapshot(self): return {'r':self.r.detach().clone(),'t':self.t.detach().clone(),'flags':(self.r.requires_grad,self.t.requires_grad),'accepted':self.accepted}
    def restore(self,value):
        with torch.no_grad(): self.r.copy_(value['r']); self.t.copy_(value['t'])
        self.r.requires_grad_(value['flags'][0]); self.t.requires_grad_(value['flags'][1]); self.accepted=value['accepted']
    def build_optimizer(self,selected):
        if len(selected)!=2 or selected[0] is not self.r or selected[1] is not self.t: raise ValueError('identity_order')
        self.optimizer=torch.optim.SGD(selected,lr=1e-3); return self.optimizer
    def save_checkpoint(self,attempt,metrics): self.checkpoints.append(attempt)
    def capture(self,step): self.captures.append(step); return {'step':step,'dynamic_raster':True}

out=Path(os.environ['O0_CPU_RECEIPT']); errors=[]
try:
    backward_runtime=FakeRuntime(); backward=module.run_live(backward_runtime,backward_only=True)
    capture_runtime=FakeRuntime(); capture=module.run_live(capture_runtime,capture_only=True)
    optimize_runtime=FakeRuntime(); optimize=module.run_live(optimize_runtime,attempts=5)
    reject_runtime=FakeRuntime(gate=False); before=(reject_runtime.r.detach().clone(),reject_runtime.t.detach().clone()); rejected=module.run_live(reject_runtime,attempts=5)
    copied_rejected=False
    try: backward_runtime.build_optimizer([backward_runtime.r.clone(),backward_runtime.t])
    except ValueError: copied_rejected=True
    checks={'backward_zero_updates':backward['updates_completed']==0,'exact_gradient_keys':set(backward['gradient_stats'])==set(module.ORDER),
      'all_gradients_finite_nonzero':all(row['norm']>0 and row['max_abs']>0 for row in backward['gradient_stats'].values()),
      'capture_zero_updates':capture['updates_completed']==0 and capture['gradient_stats']=={},
      'five_attempts_and_updates':optimize['attempts_completed']==5 and optimize['updates_completed']==5,
      'post_update_recompute':optimize_runtime.loss_calls>=10,'five_checkpoints':optimize_runtime.checkpoints==[1,2,3,4,5],
      'rejection_rolls_back':rejected['rolled_back'] and rejected['updates_completed']==0 and torch.equal(reject_runtime.r,before[0]) and torch.equal(reject_runtime.t,before[1]),
      'flags_restored':not backward_runtime.r.requires_grad and not backward_runtime.t.requires_grad and not optimize_runtime.r.requires_grad and not optimize_runtime.t.requires_grad,
      'frozen_unchanged':torch.equal(optimize_runtime.fixed,torch.arange(5,dtype=torch.float32)),'copied_parameter_rejected':copied_rejected}
    failed=[name for name,value in checks.items() if not value]
    payload={'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3_2_O0_transactional_CPU_closed' if not failed else
      'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3_2_recheck_O0_transactional_CPU'),
      'checks':checks,'failed':failed,'errors':errors,'GPU_used':False,'optimizer_updates':0}
    if not out.exists(): out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n')
except Exception as exc: errors.append(f'{type(exc).__name__}:{exc}')
print(json.dumps(json.loads(out.read_text()) if out.is_file() else {'decision':'hold_before_O0_CPU','errors':errors}))
