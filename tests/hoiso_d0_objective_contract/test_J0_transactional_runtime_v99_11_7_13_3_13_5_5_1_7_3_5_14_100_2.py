import importlib.util,json,os
from pathlib import Path
import torch

spec=importlib.util.spec_from_file_location('_j0_runtime_candidate',os.environ['J0_RUNTIME_CANDIDATE'])
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class FakeRuntime:
    def __init__(self,gate=True):
        self.hr=torch.nn.Parameter(torch.tensor([1.0,0.1,0.1,0.1]),requires_grad=False); self.ht=torch.nn.Parameter(torch.tensor([0.1,0.2,0.3]),requires_grad=False)
        self.residual=torch.nn.Parameter(torch.arange(18,dtype=torch.float32).reshape(6,3)/1000.0,requires_grad=False)
        self.orot=torch.nn.Parameter(torch.tensor([1.0,-0.1,0.1,-0.1]),requires_grad=False); self.ot=torch.nn.Parameter(torch.tensor([-0.1,0.2,-0.3]),requires_grad=False)
        self.fixed=torch.arange(7,dtype=torch.float32); self.optimizer=None; self.allow=gate; self.loss_calls=0; self.checkpoints=[]
    def parameter_registry(self): return {'global_hand_rotation':self.hr,'global_hand_translation':self.ht,'selected_so3_residual':self.residual,'global_object_rotation':self.orot,'global_object_translation':self.ot}
    def trainable_registry(self): return {name:self.parameter_registry()[name] for name in module.TRAINABLE_ORDER}
    def frozen_state(self): return {'selected_so3_residual':self.residual,'fixed':self.fixed}
    def compute_loss(self):
        self.loss_calls+=1; loss=(self.hr*torch.tensor([1.,2.,3.,4.])).sum()+(self.ht*torch.tensor([2.,3.,5.])).sum()+(self.orot*torch.tensor([2.,1.,4.,3.])).sum()+(self.ot*torch.tensor([5.,3.,2.])).sum()
        return loss,{'loss_total':float(loss.detach()),'joint_raster_recomputed':True,'loss_call':self.loss_calls}
    def gate_pass(self,metrics): return self.allow
    def snapshot(self): return {'values':{name:value.detach().clone() for name,value in self.parameter_registry().items()},'flags':{name:value.requires_grad for name,value in self.parameter_registry().items()},'optimizer':self.optimizer.state_dict() if self.optimizer else None}
    def restore(self,state):
        with torch.no_grad():
            for name,value in self.parameter_registry().items(): value.copy_(state['values'][name])
        for name,value in self.parameter_registry().items(): value.requires_grad_(state['flags'][name])
        if self.optimizer is not None and state['optimizer'] is not None: self.optimizer.load_state_dict(state['optimizer'])
    def build_optimizer(self,selected):
        wanted=[self.parameter_registry()[name] for name in module.TRAINABLE_ORDER]
        if len(selected)!=4 or any(a is not b for a,b in zip(selected,wanted)): raise ValueError('J0_optimizer_requires_exact_live_order')
        self.optimizer=torch.optim.SGD(selected,lr=1e-4); return self.optimizer
    def project_parameters(self):
        with torch.no_grad():
            self.hr.div_(torch.linalg.vector_norm(self.hr).clamp_min(1e-12)); self.orot.div_(torch.linalg.vector_norm(self.orot).clamp_min(1e-12))
    def save_checkpoint(self,attempt,metrics): self.checkpoints.append(attempt)
    def capture(self,step): return {'step':step,'joint_raster':True}

out=Path(os.environ['CORE_CPU']); errors=[]; checks={}
try:
    backward_runtime=FakeRuntime(); before_residual=backward_runtime.residual.detach().clone(); backward=module.run_live(backward_runtime,backward_only=True)
    capture_runtime=FakeRuntime(); capture=module.run_live(capture_runtime,capture_only=True)
    optimize_runtime=FakeRuntime(); optimize=module.run_live(optimize_runtime,attempts=5)
    reject_runtime=FakeRuntime(gate=False); before={name:value.detach().clone() for name,value in reject_runtime.parameter_registry().items()}; rejected=module.run_live(reject_runtime,attempts=5)
    copied_rejected=False
    try: backward_runtime.build_optimizer([backward_runtime.hr.clone(),backward_runtime.ht,backward_runtime.orot,backward_runtime.ot])
    except ValueError: copied_rejected=True
    checks={
      'full_and_trainable_orders_exact':module.FULL_ORDER==('global_hand_rotation','global_hand_translation','selected_so3_residual','global_object_rotation','global_object_translation') and module.TRAINABLE_ORDER==('global_hand_rotation','global_hand_translation','global_object_rotation','global_object_translation'),
      'backward_zero_updates':backward['updates_completed']==0 and backward['attempts_completed']==0,
      'four_exact_gradient_keys':list(backward['gradient_stats'])==list(module.TRAINABLE_ORDER),
      'all_trainable_gradients_finite_nonzero':all(row['norm']>0 and row['max_abs']>0 for row in backward['gradient_stats'].values()),
      'H1_residual_frozen_and_unchanged':backward_runtime.residual.grad is None and torch.equal(backward_runtime.residual,before_residual),
      'capture_zero_updates':capture['updates_completed']==0 and capture['gradient_stats']=={},
      'five_attempts_and_updates':optimize['attempts_completed']==5 and optimize['updates_completed']==5,
      'post_update_recompute':optimize_runtime.loss_calls>=10,
      'five_checkpoints':optimize_runtime.checkpoints==[1,2,3,4,5],
      'rejection_restores_all_five':rejected['rolled_back'] and rejected['updates_completed']==0 and all(torch.equal(reject_runtime.parameter_registry()[name],value) for name,value in before.items()),
      'quaternions_projected':abs(float(torch.linalg.vector_norm(optimize_runtime.hr))-1.0)<1e-6 and abs(float(torch.linalg.vector_norm(optimize_runtime.orot))-1.0)<1e-6,
      'requires_grad_flags_restored':all(not value.requires_grad for value in optimize_runtime.parameter_registry().values()),
      'copied_tensor_rejected':copied_rejected,
    }
except Exception as exc:
    errors.append(f'{type(exc).__name__}:{exc}')
passed=not errors and checks and all(checks.values())
payload={'schema':'foho.J0TransactionalCoreCPU.v1','decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_3_J0_transactional_core_CPU_closed' if passed else 'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_3_recheck_J0_transactional_core'),'checks':checks,'failed':([] if passed else [k for k,v in checks.items() if not v]),'errors':errors,'GPU_used':False,'optimizer_updates':0}
if not out.exists(): out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload))
