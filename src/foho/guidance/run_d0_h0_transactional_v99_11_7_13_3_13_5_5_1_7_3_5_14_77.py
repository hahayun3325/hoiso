#!/usr/bin/env python3
import argparse, hashlib, importlib, importlib.util, json, math
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[3]

def load_file(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot_load_module:{path}')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

phase_loader=load_file(PROJECT_ROOT/'tools/hoiso_d0_objective_contract/phase_config_loader.py','hoiso_phase_loader_77')
raster_owner=load_file(PROJECT_ROOT/'tools/hoiso_d0_objective_contract/dense_raster_schedule.py','hoiso_raster_schedule_77')

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

def flag_snapshot(registry):
    return {name:bool(parameter.requires_grad) for name,parameter in registry.items()}

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
        self.original_flags=flag_snapshot(self.registry)
        self.schedule=raster_owner.DenseRasterSchedule(runtime.rasterize_object,object_frozen=True)

    def set_H0_flags(self):
        for name,parameter in self.registry.items(): parameter.requires_grad_(name in self.enabled)

    def restore_flags(self):
        for name,parameter in self.registry.items(): parameter.requires_grad_(self.original_flags[name])

    def frozen_state(self):
        return {'parameters':{name:value for name,value in self.registry.items() if name not in self.enabled},'runtime_frozen':self.runtime.frozen_state(),'object_vertices':self.runtime.object_vertices()}

    def gradient_stats(self):
        stats={}
        for name,parameter in self.registry.items():
            grad=parameter.grad
            if name in self.enabled:
                if grad is None or not bool(grad.detach().isfinite().all()): raise RuntimeError(f'missing_or_nonfinite_selected_gradient:{name}')
                maximum=float(grad.detach().abs().max().cpu()); norm=float(grad.detach().norm().cpu())
                if maximum<=0.0 or norm<=0.0: raise RuntimeError(f'zero_selected_gradient:{name}')
                stats[name]={'max_abs':maximum,'norm':norm}
            elif grad is not None and bool((grad.detach()!=0).any()):
                raise RuntimeError(f'forbidden_gradient:{name}')
        return stats

    def compute(self,raster):
        loss,metrics=self.runtime.compute_loss(raster,self.config)
        if not hasattr(loss,'backward') or not math.isfinite(float(loss.detach().cpu())): raise RuntimeError('nonfinite_or_nondifferentiable_loss')
        return loss,metrics

    def run(self,updates,checkpoint_every=1,capture_only=False,backward_only=False):
        if updates<0: raise ValueError('updates_must_be_nonnegative')
        if capture_only and (updates!=0 or backward_only): raise ValueError('capture_only_requires_zero_updates_and_no_backward')
        if backward_only and updates!=0: raise ValueError('backward_only_requires_zero_updates')
        before_all=state_digest(self.registry); before_frozen=state_digest(self.frozen_state()); raster=self.schedule.for_forward(self.runtime.object_vertices())
        if capture_only:
            capture=self.runtime.capture(0,raster)
            if state_digest(self.registry)!=before_all or state_digest(self.frozen_state())!=before_frozen: raise RuntimeError('zero_update_integrity_failed')
            return {'updates_completed':0,'rolled_back':False,'capture':capture,'gradient_stats':{}}
        optimizer=None; trajectory=[]; completed=0; rolled_back=False
        try:
            self.set_H0_flags(); optimizer=self.runtime.build_optimizer(self.selected)
            if backward_only:
                snapshot=self.runtime.snapshot(); optimizer.zero_grad(set_to_none=True)
                loss,metrics=self.compute(raster); loss.backward(); stats=self.gradient_stats(); optimizer.zero_grad(set_to_none=True); self.runtime.restore(snapshot)
                return {'updates_completed':0,'rolled_back':False,'capture':self.runtime.capture(0,raster),'gradient_stats':stats,'metrics':metrics}
            for step in range(1,updates+1):
                snapshot=self.runtime.snapshot(); stepped=False
                try:
                    optimizer.zero_grad(set_to_none=True); loss,pre_metrics=self.compute(raster); loss.backward(); stats=self.gradient_stats(); optimizer.step(); stepped=True
                    if state_digest(self.frozen_state())!=before_frozen: raise RuntimeError(f'frozen_owner_changed:{step}')
                    post_loss,post_metrics=self.compute(raster)
                    passed=bool(self.runtime.gate_pass(post_metrics))
                    trajectory.append({'step':step,'pre_loss':float(loss.detach().cpu()),'post_loss':float(post_loss.detach().cpu()),'metrics':post_metrics,'gradient_stats':stats,'gate_pass':passed})
                    if not passed:
                        self.runtime.restore(snapshot); rolled_back=True; break
                    completed=step
                    if checkpoint_every>0 and step%checkpoint_every==0: self.runtime.save_checkpoint(step,post_metrics)
                except Exception:
                    if stepped: self.runtime.restore(snapshot)
                    raise
            return {'updates_completed':completed,'rolled_back':rolled_back,'trajectory':trajectory,'capture':self.runtime.capture(completed,raster)}
        finally:
            if optimizer is not None: optimizer.zero_grad(set_to_none=True)
            self.restore_flags()
            if flag_snapshot(self.registry)!=self.original_flags: raise RuntimeError('requires_grad_flags_not_restored')

def run_live(phase_config,runtime,updates,checkpoint_every=1,capture_only=False,backward_only=False):
    return H0Controller(phase_config,runtime).run(updates,checkpoint_every,capture_only,backward_only)

def main(argv=None):
    parser=argparse.ArgumentParser(description='Transactional D0-aware H0 controller')
    parser.add_argument('--phase-config',required=True); parser.add_argument('--engine-adapter',required=True)
    parser.add_argument('--updates',type=int,required=True); parser.add_argument('--checkpoint-every',type=int,default=1)
    parser.add_argument('--capture-only',action='store_true'); parser.add_argument('--backward-only',action='store_true'); parser.add_argument('--output',required=True)
    args,remaining=parser.parse_known_args(argv); config=phase_loader.load_phase_config(args.phase_config,'H0_global_hand_Rt'); factory=load_engine_factory(args.engine_adapter); runtime=factory(args,remaining,config)
    result=run_live(config,runtime,args.updates,args.checkpoint_every,args.capture_only,args.backward_only); output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,default=str)+'\n'); print(json.dumps({'updates_completed':result['updates_completed'],'rolled_back':result['rolled_back'],'output':str(output)}))

if __name__=='__main__': main()
