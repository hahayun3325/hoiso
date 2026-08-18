from __future__ import annotations
import hashlib,math
import torch

ORDER=('global_object_rotation','global_object_translation')

def _digest(value):
    h=hashlib.sha256()
    def add(item):
        if torch.is_tensor(item):
            tensor=item.detach().cpu().contiguous(); h.update(str(tensor.dtype).encode()); h.update(str(tuple(tensor.shape)).encode()); h.update(tensor.numpy().tobytes())
        elif isinstance(item,dict):
            for key in sorted(item): h.update(str(key).encode()); add(item[key])
        elif isinstance(item,(list,tuple)):
            for child in item: add(child)
        else: h.update(repr(item).encode())
    add(value); return h.hexdigest()

class O0Controller:
    def __init__(self,runtime):
        self.runtime=runtime; self.registry=runtime.parameter_registry()
        if list(self.registry)!=list(ORDER): raise ValueError('O0_parameter_order_mismatch')
        self.parameters=[self.registry[name] for name in ORDER]
        if len({id(value) for value in self.parameters})!=2: raise ValueError('O0_parameter_identity_collision')
        if tuple(self.parameters[0].shape)!=(4,) or tuple(self.parameters[1].shape)!=(3,): raise ValueError('O0_parameter_shape_mismatch')
        self.flags={name:bool(value.requires_grad) for name,value in self.registry.items()}
    def set_flags(self):
        for value in self.parameters: value.requires_grad_(True)
    def restore_flags(self):
        for name,value in self.registry.items(): value.requires_grad_(self.flags[name])
    def gradients(self):
        result={}
        for name,value in zip(ORDER,self.parameters):
            grad=value.grad
            if grad is None or not bool(torch.isfinite(grad).all()): raise RuntimeError(f'O0_missing_or_nonfinite_gradient:{name}')
            maximum=float(grad.detach().abs().max().cpu()); norm=float(grad.detach().norm().cpu())
            if maximum<=0.0 or norm<=0.0: raise RuntimeError(f'O0_zero_gradient:{name}')
            result[name]={'max_abs':maximum,'norm':norm}
        return result
    def compute(self):
        loss,metrics=self.runtime.compute_loss()
        if not torch.is_tensor(loss) or not loss.requires_grad or not math.isfinite(float(loss.detach().cpu())):
            raise RuntimeError('O0_loss_not_finite_and_differentiable')
        return loss,metrics
    def run(self,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
        if attempts<0: raise ValueError('O0_attempts_must_be_nonnegative')
        if capture_only and (attempts!=0 or backward_only): raise ValueError('O0_capture_requires_zero_and_no_backward')
        if backward_only and attempts!=0: raise ValueError('O0_backward_requires_zero_attempts')
        before_values=_digest(self.registry); before_frozen=_digest(self.runtime.frozen_state())
        if capture_only:
            capture=self.runtime.capture(0)
            if _digest(self.registry)!=before_values or _digest(self.runtime.frozen_state())!=before_frozen: raise RuntimeError('O0_capture_changed_state')
            return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,'capture':capture,'gradient_stats':{},'trajectory':[]}
        optimizer=None; trajectory=[]; accepted=0; rolled_back=False
        try:
            self.set_flags(); optimizer=self.runtime.build_optimizer(self.parameters)
            if backward_only:
                snapshot=self.runtime.snapshot(); optimizer.zero_grad(set_to_none=True)
                loss,metrics=self.compute(); loss.backward(); stats=self.gradients()
                optimizer.zero_grad(set_to_none=True); self.runtime.restore(snapshot)
                if _digest(self.runtime.frozen_state())!=before_frozen: raise RuntimeError('O0_backward_changed_frozen_state')
                return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,
                        'capture':self.runtime.capture(0),'gradient_stats':stats,'metrics':metrics,'trajectory':[]}
            for attempt in range(1,attempts+1):
                snapshot=self.runtime.snapshot(); stepped=False
                try:
                    optimizer.zero_grad(set_to_none=True); loss,pre=self.compute(); loss.backward(); stats=self.gradients(); optimizer.step(); stepped=True
                    if _digest(self.runtime.frozen_state())!=before_frozen: raise RuntimeError(f'O0_frozen_owner_changed:{attempt}')
                    post_loss,post=self.compute(); passed=bool(self.runtime.gate_pass(post))
                    trajectory.append({'attempt':attempt,'pre_loss':float(loss.detach().cpu()),'post_loss':float(post_loss.detach().cpu()),
                                       'metrics':post,'gradient_stats':stats,'gate_pass':passed})
                    if not passed:
                        self.runtime.restore(snapshot); rolled_back=True; break
                    accepted+=1
                    if checkpoint_every>0 and attempt%checkpoint_every==0: self.runtime.save_checkpoint(attempt,post)
                except Exception:
                    if stepped: self.runtime.restore(snapshot)
                    raise
            return {'updates_completed':accepted,'attempts_completed':len(trajectory),'rolled_back':rolled_back,
                    'trajectory':trajectory,'capture':self.runtime.capture(accepted)}
        finally:
            if optimizer is not None: optimizer.zero_grad(set_to_none=True)
            self.restore_flags()
            if {name:bool(value.requires_grad) for name,value in self.registry.items()}!=self.flags:
                raise RuntimeError('O0_requires_grad_flags_not_restored')

def run_live(runtime,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
    return O0Controller(runtime).run(attempts,checkpoint_every,capture_only,backward_only)
