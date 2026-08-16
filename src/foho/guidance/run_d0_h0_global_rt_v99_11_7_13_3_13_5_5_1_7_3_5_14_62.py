#!/usr/bin/env python3
import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[3]

def load_file(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot_load_module:{path}')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

phase_loader=load_file(PROJECT_ROOT/'tools/hoiso_d0_objective_contract/phase_config_loader.py','hoiso_phase_loader')
raster_owner=load_file(PROJECT_ROOT/'tools/hoiso_d0_objective_contract/dense_raster_schedule.py','hoiso_raster_schedule')

def state_digest(value):
    h=hashlib.sha256()
    def add(item):
        if hasattr(item,'detach') and hasattr(item,'cpu'):
            tensor=item.detach().cpu().contiguous(); h.update(str(tuple(tensor.shape)).encode()); h.update(str(tensor.dtype).encode()); h.update(tensor.numpy().tobytes())
        elif isinstance(item,dict):
            for key in sorted(item): h.update(str(key).encode()); add(item[key])
        elif isinstance(item,(list,tuple)):
            for child in item: add(child)
        else: h.update(repr(item).encode())
    add(value); return h.hexdigest()

def load_engine_factory(specification):
    if ':' not in specification: raise ValueError('engine_adapter_must_be_module_colon_factory')
    module_name,factory_name=specification.split(':',1); module=importlib.import_module(module_name); factory=getattr(module,factory_name,None)
    if not callable(factory): raise ValueError(f'engine_factory_not_callable:{specification}')
    return factory

class H0Controller:
    def __init__(self,phase_config,runtime):
        self.config=phase_config; self.runtime=runtime; self.registry=runtime.parameter_registry()
        self.selected=phase_loader.resolve_allowlist(phase_config,self.registry)
        self.enabled=set(phase_config['_normalized']['enabled_parameter_names'])
        if self.enabled!={'global_hand_rotation','global_hand_translation'}: raise ValueError(f'H0_allowlist_must_be_global_Rt_only:{sorted(self.enabled)}')
        for name,parameter in self.registry.items(): parameter.requires_grad_(name in self.enabled)
        self.schedule=raster_owner.DenseRasterSchedule(runtime.rasterize_object,object_frozen=True)

    def frozen_state(self):
        return {'parameters':{name:value for name,value in self.registry.items() if name not in self.enabled},'object_vertices':self.runtime.object_vertices()}

    def run(self,updates,checkpoint_every=1,capture_only=False):
        if updates<0: raise ValueError('updates_must_be_nonnegative')
        if capture_only and updates!=0: raise ValueError('capture_only_requires_zero_updates')
        before_all=state_digest(self.registry); before_frozen=state_digest(self.frozen_state()); raster=self.schedule.for_forward(self.runtime.object_vertices())
        if updates==0:
            capture=self.runtime.capture(0,raster)
            if state_digest(self.registry)!=before_all or state_digest(self.frozen_state())!=before_frozen: raise RuntimeError('zero_update_integrity_failed')
            return {'updates_completed':0,'rolled_back':False,'capture':capture}
        optimizer=self.runtime.build_optimizer(self.selected); last_snapshot=self.runtime.snapshot(); completed=0; rolled_back=False; trajectory=[]
        for step in range(1,updates+1):
            optimizer.zero_grad(set_to_none=True); loss,metrics=self.runtime.compute_loss(raster,self.config)
            if not hasattr(loss,'backward') or not math.isfinite(float(loss.detach().cpu())): raise RuntimeError(f'nonfinite_or_nondifferentiable_loss:{step}')
            loss.backward()
            for name,parameter in self.registry.items():
                grad=parameter.grad
                if name in self.enabled:
                    if grad is None or not bool(grad.detach().isfinite().all()): raise RuntimeError(f'missing_or_nonfinite_selected_gradient:{name}:{step}')
                elif grad is not None and bool((grad.detach()!=0).any()): raise RuntimeError(f'forbidden_gradient:{name}:{step}')
            optimizer.step(); completed=step
            if state_digest(self.frozen_state())!=before_frozen: raise RuntimeError(f'frozen_owner_changed:{step}')
            passed=bool(self.runtime.gate_pass(metrics)); trajectory.append({'step':step,'loss':float(loss.detach().cpu()),'metrics':metrics,'gate_pass':passed})
            if not passed:
                self.runtime.restore(last_snapshot); rolled_back=True; break
            last_snapshot=self.runtime.snapshot()
            if checkpoint_every>0 and step%checkpoint_every==0: self.runtime.save_checkpoint(step,metrics)
        return {'updates_completed':completed,'rolled_back':rolled_back,'trajectory':trajectory,'capture':self.runtime.capture(completed,raster)}

def main(argv=None):
    parser=argparse.ArgumentParser(description='Thin D0-aware H0 global hand R/t controller')
    parser.add_argument('--phase-config',required=True); parser.add_argument('--engine-adapter',required=True)
    parser.add_argument('--updates',type=int,required=True); parser.add_argument('--checkpoint-every',type=int,default=1)
    parser.add_argument('--capture-only',action='store_true'); parser.add_argument('--output',required=True)
    args,remaining=parser.parse_known_args(argv); config=phase_loader.load_phase_config(args.phase_config,'H0_global_hand_Rt'); factory=load_engine_factory(args.engine_adapter); runtime=factory(args,remaining,config)
    result=H0Controller(config,runtime).run(args.updates,args.checkpoint_every,args.capture_only); output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,default=str)+'\n'); print(json.dumps({'updates_completed':result['updates_completed'],'rolled_back':result['rolled_back'],'output':str(output)}))

if __name__=='__main__': main()
