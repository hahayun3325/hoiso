from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import torch


def _state_digest(value):
    digest=hashlib.sha256()
    def add(item):
        if torch.is_tensor(item):
            digest.update(str(tuple(item.shape)).encode())
            digest.update(str(item.dtype).encode())
            digest.update(item.detach().cpu().contiguous().numpy().tobytes())
        elif isinstance(item,dict):
            for key in sorted(item): digest.update(str(key).encode()); add(item[key])
        elif isinstance(item,(list,tuple)):
            for row in item: add(row)
        else: digest.update(repr(item).encode())
    add(value)
    return digest.hexdigest()


class H1Controller:
    PARAMETER_NAME='selected_so3_residual'

    def __init__(self,runtime):
        self.runtime=runtime
        self.registry=runtime.parameter_registry()
        if list(self.registry)!=[self.PARAMETER_NAME]:
            raise ValueError('H1_allowlist_must_be_exact_selected_residual')
        self.parameter=self.registry[self.PARAMETER_NAME]
        if tuple(self.parameter.shape)!=(6,3):
            raise ValueError('H1_selected_residual_must_be_6x3')
        self.original_flag=bool(self.parameter.requires_grad)

    def gradient_stats(self):
        grad=self.parameter.grad
        if grad is None or tuple(grad.shape)!=(6,3):
            raise RuntimeError('missing_selected_residual_gradient')
        if not bool(torch.isfinite(grad).all()):
            raise RuntimeError('nonfinite_selected_residual_gradient')
        nonzero=int((grad!=0).sum().detach().cpu())
        if nonzero!=18:
            raise RuntimeError(f'H1_requires_18_nonzero_gradient_coordinates:{nonzero}')
        return {self.PARAMETER_NAME:{
            'shape':[6,3], 'nonzero_coordinates':nonzero,
            'max_abs':float(grad.detach().abs().max().cpu()),
            'norm':float(grad.detach().norm().cpu())}}

    def compute(self,raster):
        loss,metrics=self.runtime.compute_loss(raster)
        if not torch.is_tensor(loss) or not loss.requires_grad:
            raise RuntimeError('H1_loss_must_be_differentiable_tensor')
        if not math.isfinite(float(loss.detach().cpu())):
            raise RuntimeError('H1_loss_nonfinite')
        return loss,metrics

    def run(self,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
        if attempts<0: raise ValueError('attempts_must_be_nonnegative')
        if capture_only and (attempts!=0 or backward_only):
            raise ValueError('capture_only_requires_zero_attempts_and_no_backward')
        if backward_only and attempts!=0:
            raise ValueError('backward_only_requires_zero_attempts')
        before_parameter=_state_digest(self.registry)
        before_frozen=_state_digest(self.runtime.frozen_state())
        raster=self.runtime.rasterize_object()
        if capture_only:
            capture=self.runtime.capture(0,raster)
            if _state_digest(self.registry)!=before_parameter or _state_digest(self.runtime.frozen_state())!=before_frozen:
                raise RuntimeError('H1_capture_zero_state_changed')
            return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,
                    'capture':capture,'gradient_stats':{},'trajectory':[]}
        optimizer=None; trajectory=[]; accepted=0; rolled_back=False
        try:
            self.parameter.requires_grad_(True)
            optimizer=self.runtime.build_optimizer([self.parameter])
            if backward_only:
                snapshot=self.runtime.snapshot()
                optimizer.zero_grad(set_to_none=True)
                loss,metrics=self.compute(raster); loss.backward()
                stats=self.gradient_stats()
                optimizer.zero_grad(set_to_none=True); self.runtime.restore(snapshot)
                if _state_digest(self.runtime.frozen_state())!=before_frozen:
                    raise RuntimeError('H1_backward_changed_frozen_state')
                return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,
                        'capture':self.runtime.capture(0,raster),'gradient_stats':stats,
                        'metrics':metrics,'trajectory':[]}
            for attempt in range(1,attempts+1):
                snapshot=self.runtime.snapshot(); stepped=False
                try:
                    optimizer.zero_grad(set_to_none=True)
                    loss,pre_metrics=self.compute(raster); loss.backward()
                    stats=self.gradient_stats(); optimizer.step(); stepped=True
                    if _state_digest(self.runtime.frozen_state())!=before_frozen:
                        raise RuntimeError(f'H1_frozen_owner_changed:{attempt}')
                    post_loss,post_metrics=self.compute(raster)
                    passed=bool(self.runtime.gate_pass(post_metrics))
                    trajectory.append({'attempt':attempt,'pre_loss':float(loss.detach().cpu()),
                                       'post_loss':float(post_loss.detach().cpu()),
                                       'metrics':post_metrics,'gradient_stats':stats,'gate_pass':passed})
                    if not passed:
                        self.runtime.restore(snapshot); rolled_back=True; break
                    accepted+=1
                    if checkpoint_every>0 and attempt%checkpoint_every==0:
                        self.runtime.save_checkpoint(attempt,post_metrics)
                except Exception:
                    if stepped: self.runtime.restore(snapshot)
                    raise
            return {'updates_completed':accepted,'attempts_completed':len(trajectory),
                    'rolled_back':rolled_back,'trajectory':trajectory,
                    'capture':self.runtime.capture(accepted,raster)}
        finally:
            if optimizer is not None: optimizer.zero_grad(set_to_none=True)
            self.parameter.requires_grad_(self.original_flag)
            if bool(self.parameter.requires_grad)!=self.original_flag:
                raise RuntimeError('H1_requires_grad_flag_not_restored')


def run_live(runtime,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
    return H1Controller(runtime).run(attempts=attempts,checkpoint_every=checkpoint_every,
                                     capture_only=capture_only,backward_only=backward_only)
