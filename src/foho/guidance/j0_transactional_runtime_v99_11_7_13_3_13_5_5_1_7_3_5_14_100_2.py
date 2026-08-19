from __future__ import annotations
import hashlib,math
import torch

FULL_ORDER=('global_hand_rotation','global_hand_translation','selected_so3_residual','global_object_rotation','global_object_translation')
TRAINABLE_ORDER=('global_hand_rotation','global_hand_translation','global_object_rotation','global_object_translation')
EXPECTED_SHAPES={'global_hand_rotation':(4,),'global_hand_translation':(3,),'selected_so3_residual':(6,3),'global_object_rotation':(4,),'global_object_translation':(3,)}

def _digest(value):
    state=hashlib.sha256()
    def visit(item):
        if torch.is_tensor(item):
            tensor=item.detach().cpu().contiguous(); state.update(str(tensor.dtype).encode()); state.update(str(tuple(tensor.shape)).encode()); state.update(tensor.numpy().tobytes())
        elif isinstance(item,dict):
            for key in sorted(item,key=str): state.update(str(key).encode()); visit(item[key])
        elif isinstance(item,(list,tuple)):
            for child in item: visit(child)
        else: state.update(repr(item).encode())
    visit(value); return state.hexdigest()

class J0Controller:
    def __init__(self,runtime):
        self.runtime=runtime; self.registry=runtime.parameter_registry(); self.trainable=runtime.trainable_registry()
        if list(self.registry)!=list(FULL_ORDER): raise ValueError('J0_full_registry_order_mismatch')
        if list(self.trainable)!=list(TRAINABLE_ORDER): raise ValueError('J0_trainable_registry_order_mismatch')
        for name,shape in EXPECTED_SHAPES.items():
            value=self.registry[name]
            if not torch.is_tensor(value) or tuple(value.shape)!=shape: raise ValueError(f'J0_shape_mismatch:{name}:{tuple(value.shape) if torch.is_tensor(value) else None}')
        if any(self.trainable[name] is not self.registry[name] for name in TRAINABLE_ORDER): raise ValueError('J0_trainable_registry_copied_tensor')
        if self.registry['selected_so3_residual'].requires_grad: raise ValueError('J0_H1_residual_must_enter_frozen')
        self.flags={name:bool(value.requires_grad) for name,value in self.registry.items()}
    def set_flags(self):
        for name,value in self.registry.items(): value.requires_grad_(name in TRAINABLE_ORDER)
    def restore_flags(self):
        for name,value in self.registry.items(): value.requires_grad_(self.flags[name])
    def gradients(self):
        result={}
        if self.registry['selected_so3_residual'].grad is not None: raise RuntimeError('J0_frozen_H1_residual_received_gradient')
        for name in TRAINABLE_ORDER:
            grad=self.registry[name].grad
            if grad is None or not bool(torch.isfinite(grad).all()): raise RuntimeError(f'J0_invalid_gradient:{name}')
            maximum=float(grad.detach().abs().max().cpu()); norm=float(torch.linalg.vector_norm(grad.detach()).cpu())
            if maximum<=0.0 or norm<=0.0: raise RuntimeError(f'J0_zero_gradient:{name}')
            result[name]={'max_abs':maximum,'norm':norm}
        return result
    def compute(self):
        loss,metrics=self.runtime.compute_loss()
        if not torch.is_tensor(loss) or not loss.requires_grad or not bool(torch.isfinite(loss.detach())): raise RuntimeError('J0_loss_not_finite_and_differentiable')
        return loss,metrics
    def run(self,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
        if attempts<0: raise ValueError('J0_attempts_must_be_nonnegative')
        if capture_only and (attempts!=0 or backward_only): raise ValueError('J0_capture_requires_zero_and_no_backward')
        if backward_only and attempts!=0: raise ValueError('J0_backward_requires_zero_attempts')
        before_values=_digest(self.registry); before_frozen=_digest(self.runtime.frozen_state()); optimizer=None; trajectory=[]; accepted=0; rolled_back=False
        if capture_only:
            capture=self.runtime.capture(0)
            if _digest(self.registry)!=before_values or _digest(self.runtime.frozen_state())!=before_frozen: raise RuntimeError('J0_capture_changed_state')
            return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,'capture':capture,'gradient_stats':{},'trajectory':[]}
        try:
            self.set_flags(); optimizer=self.runtime.build_optimizer([self.trainable[name] for name in TRAINABLE_ORDER])
            if backward_only:
                snapshot=self.runtime.snapshot(); optimizer.zero_grad(set_to_none=True); loss,metrics=self.compute(); loss.backward(); stats=self.gradients(); optimizer.zero_grad(set_to_none=True); self.runtime.restore(snapshot)
                if _digest(self.registry)!=before_values or _digest(self.runtime.frozen_state())!=before_frozen: raise RuntimeError('J0_backward_changed_state')
                return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,'capture':self.runtime.capture(0),'gradient_stats':stats,'metrics':metrics,'trajectory':[]}
            for attempt in range(1,attempts+1):
                snapshot=self.runtime.snapshot(); stepped=False
                try:
                    optimizer.zero_grad(set_to_none=True); loss,pre=self.compute(); loss.backward(); stats=self.gradients(); optimizer.step(); stepped=True; self.runtime.project_parameters()
                    if _digest(self.runtime.frozen_state())!=before_frozen or self.registry['selected_so3_residual'].grad is not None: raise RuntimeError(f'J0_frozen_owner_changed:{attempt}')
                    post_loss,post=self.compute(); passed=bool(self.runtime.gate_pass(post))
                    trajectory.append({'attempt':attempt,'pre_loss':float(loss.detach().cpu()),'post_loss':float(post_loss.detach().cpu()),'metrics':post,'gradient_stats':stats,'gate_pass':passed})
                    if not passed: self.runtime.restore(snapshot); rolled_back=True; break
                    accepted+=1
                    if checkpoint_every>0 and attempt%checkpoint_every==0: self.runtime.save_checkpoint(attempt,post)
                except Exception:
                    if stepped: self.runtime.restore(snapshot)
                    raise
            return {'updates_completed':accepted,'attempts_completed':len(trajectory),'rolled_back':rolled_back,'trajectory':trajectory,'capture':self.runtime.capture(accepted)}
        finally:
            if optimizer is not None: optimizer.zero_grad(set_to_none=True)
            self.restore_flags()
            if {name:bool(value.requires_grad) for name,value in self.registry.items()}!=self.flags: raise RuntimeError('J0_requires_grad_flags_not_restored')

def run_live(runtime,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
    return J0Controller(runtime).run(attempts,checkpoint_every,capture_only,backward_only)
