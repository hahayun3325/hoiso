import importlib.util
import json
import os
from pathlib import Path
import torch

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

factory=load(os.environ['CASE_CALLBACK84'],'h0_case_callback_1484')
target=Path(os.environ['FACTORY_TEST84']); runtime_output=Path(os.environ.get('FACTORY_RUNTIME_OUTPUT84',str(Path(os.environ['BIND84_RUNTIME'])/'CPU_fake_backward_only_v99_11_7_13_3_13_5_5_1_7_3_5_14_84.json')))
failed=[]; errors=[]; checks={}; existing=[str(target)] if target.exists() else []
try:
    rotation=torch.tensor([1.0,0.1,0.0,0.0],dtype=torch.float32); translation=torch.tensor([0.2,-0.1,0.05],dtype=torch.float32)
    scale=torch.tensor([1.0]); object_vertices=torch.tensor([[0.0,0.0,1.0],[1.0,0.0,1.0],[0.0,1.0,1.0]])
    before={'rotation':rotation.clone(),'translation':translation.clone(),'scale':scale.clone(),'object':object_vertices.clone(),'flags':(rotation.requires_grad,translation.requires_grad)}
    calls={'raster':0,'step':0,'capture':0}
    def frozen_state(): return {'scale':scale,'object_vertices':object_vertices}
    def object_owner(): return object_vertices
    def rasterize(vertices): calls['raster']+=1; return {'object_depth':vertices[:,2].clone(),'valid':torch.ones(vertices.shape[0],dtype=torch.bool)}
    class CountingSGD(torch.optim.SGD):
        def step(self,closure=None): calls['step']+=1; return super().step(closure)
    def build(selected):
        selected_values=list(selected.values()) if isinstance(selected,dict) else list(selected)
        return CountingSGD(selected_values,lr=1e-3)
    def compute(raster,config):
        loss=(rotation**2).sum()+(translation**2).sum()+0.0*raster['object_depth'].sum()
        return loss,{'loss_total':loss.detach(),'D0_contact_active':True,'dense_raster_bound':True}
    def gate(metrics): return True
    def snapshot(): return {'rotation':rotation.detach().clone(),'translation':translation.detach().clone()}
    def restore(row):
        with torch.no_grad(): rotation.copy_(row['rotation']); translation.copy_(row['translation'])
    def checkpoint(step,metrics): raise RuntimeError('checkpoint_not_allowed_in_backward_only_test')
    def capture(step,raster): calls['capture']+=1; return {'step':step,'raster_bound':raster is not None}
    hooks={'frozen_state':frozen_state,'object_vertices':object_owner,'rasterize_object':rasterize,'build_optimizer':build,'compute_loss':compute,'gate_pass':gate,'snapshot':snapshot,'restore':restore,'save_checkpoint':checkpoint,'capture':capture}
    context={'owner':'CPU_fake_Phase1','parameters':{'global_hand_rotation':rotation,'global_hand_translation':translation},'frozen':{'scale':scale,'object_vertices':object_vertices},'compute_base_loss':lambda index=0:compute({'object_depth':object_vertices[:,2]},{}),'hooks':hooks,'metadata':{'test':True}}
    callback=factory.create_case_callback(os.environ['H0_PHASE_CONFIG'],runtime_output,updates=0,backward_only=True,capture_only=False)
    outcome=callback(context); result=outcome['result']; stats=result.get('gradient_stats',{})
    checks={'handled_true':outcome.get('handled') is True,'zero_updates':result.get('updates_completed')==0,'no_optimizer_step':calls['step']==0,'raster_cached_once':calls['raster']==1,'capture_once':calls['capture']==1,'rotation_gradient_finite_nonzero':stats.get('global_hand_rotation',{}).get('norm',0)>0,'translation_gradient_finite_nonzero':stats.get('global_hand_translation',{}).get('norm',0)>0,'rotation_value_restored':torch.equal(rotation,before['rotation']),'translation_value_restored':torch.equal(translation,before['translation']),'scale_unchanged':torch.equal(scale,before['scale']),'object_unchanged':torch.equal(object_vertices,before['object']),'trainability_flags_restored':(rotation.requires_grad,translation.requires_grad)==before['flags'],'runtime_output_written':runtime_output.is_file()}
    failed.extend(name for name,value in checks.items() if not value)
except Exception as exc:
    errors.append(f'{type(exc).__name__}:{exc}')
payload={'decision':'pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_84_case_callback_factory_CPU_closed' if not failed and not errors else 'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_84_case_callback_factory_CPU','checks':checks,'failed':failed,'existing':existing,'errors':errors,'GPU_used':False,'optimizer_updates':calls.get('step',0) if 'calls' in locals() else None}
if not existing: target.write_text(json.dumps(payload,indent=2)+'\n')
print(f'decision={payload["decision"]} checks={checks} failed={failed} existing={existing} errors={errors}')
