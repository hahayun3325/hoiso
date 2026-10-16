import importlib.util, json, os
from pathlib import Path
import torch

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

bundle=load(os.environ['HOOK_BUNDLE8531'],'h0_bundle_148531')
controller=load(os.environ['H0_CONTROLLER'],'h0_controller_148531')
runtime_owner=load(os.environ['H0_RUNTIME'],'h0_runtime_148531')
target=Path(os.environ['BUNDLE_TEST_RECEIPT8531'])
runtime_output=target.with_name('CPU_backward_only_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1.json')
existing=[str(p) for p in (target,runtime_output) if p.exists()]
errors=[]; failed=[]; checks={}; calls={'raster':0,'checkpoint':0,'capture':0}
try:
    config=controller.phase_loader.load_phase_config(os.environ['H0_PHASE_CONFIG'],'H0_global_hand_Rt')
    rotation=torch.tensor([1.0,0.1,0.0,0.0],dtype=torch.float32)
    translation=torch.tensor([0.2,-0.1,0.05],dtype=torch.float32)
    scale=torch.tensor([1.0]); object_vertices=torch.tensor([[0.,0.,1.],[1.,0.,1.],[0.,1.,1.]])
    parameters={'global_hand_rotation':rotation,'global_hand_translation':translation}
    before={k:v.detach().clone() for k,v in parameters.items()}; before_flags={k:v.requires_grad for k,v in parameters.items()}
    frozen_before={'scale':scale.detach().clone(),'object':object_vertices.detach().clone()}
    def frozen_state(): return {'scale':scale,'object':object_vertices}
    def object_owner(): return object_vertices
    def rasterize(vertices):
        calls['raster']+=1
        return {'object_depth':vertices[:,2],'object_depth_valid':torch.ones(vertices.shape[0],dtype=torch.bool)}
    def compute_loss(raster,phase):
        loss=(rotation**2).sum()+(translation**2).sum()+0.0*raster['object_depth'].sum()
        return loss,{'D0_contact_active':True,'dense_valid_zorder_active':True,'loss_total':float(loss.detach())}
    def gate_pass(metrics): return bool(metrics['D0_contact_active'] and metrics['dense_valid_zorder_active'])
    def snapshot(): return {k:v.detach().clone() for k,v in parameters.items()}
    def restore(row):
        with torch.no_grad():
            for k,v in parameters.items(): v.copy_(row[k])
    def checkpoint(step,metrics): calls['checkpoint']+=1
    def capture(step,raster): calls['capture']+=1; return {'step':step,'raster_bound':raster is not None}
    owners={'frozen_state':frozen_state,'object_vertices':object_owner,'rasterize_object':rasterize,
            'compute_loss':compute_loss,'gate_pass':gate_pass,'snapshot':snapshot,'restore':restore,
            'save_checkpoint':checkpoint,'capture':capture}
    hooks=bundle.build_complete_h0_hooks(parameters,owners,1e-4)
    context={'owner':'CPU_fake_Phase1','parameters':parameters,'frozen':frozen_state(),
             'compute_base_loss':lambda index=0:compute_loss(rasterize(object_vertices),config),
             'hooks':hooks,'metadata':{'test':True}}
    runtime=runtime_owner.create_from_live_context(context,config)
    result=controller.run_live(config,runtime,0,checkpoint_every=1,capture_only=False,backward_only=True)
    stats=result.get('gradient_stats',{})
    missing_rejected=False
    try: bundle.build_complete_h0_hooks(parameters,{k:v for k,v in owners.items() if k!='capture'},1e-4)
    except ValueError: missing_rejected=True
    foreign_rejected=False
    try: hooks['build_optimizer']({'global_hand_rotation':rotation.clone(),'global_hand_translation':translation})
    except RuntimeError: foreign_rejected=True
    checks={
        'exact_ten_hook_names':set(hooks)==bundle.REQUIRED_HOOK_NAMES and len(hooks)==10,
        'backward_only_zero_updates':result.get('updates_completed')==0,
        'not_rolled_back':result.get('rolled_back') is False,
        'rotation_gradient_finite_nonzero':stats.get('global_hand_rotation',{}).get('norm',0)>0,
        'translation_gradient_finite_nonzero':stats.get('global_hand_translation',{}).get('norm',0)>0,
        'parameters_restored':all(torch.equal(parameters[k],before[k]) for k in parameters),
        'trainability_flags_restored':all(parameters[k].requires_grad==before_flags[k] for k in parameters),
        'frozen_scale_unchanged':torch.equal(scale,frozen_before['scale']),
        'frozen_object_unchanged':torch.equal(object_vertices,frozen_before['object']),
        'raster_called_once':calls['raster']==1,
        'checkpoint_not_called':calls['checkpoint']==0,
        'capture_called_once':calls['capture']==1,
        'missing_owner_rejected':missing_rejected,
        'foreign_parameter_identity_rejected':foreign_rejected,
    }
    failed=[k for k,v in checks.items() if not v]
    if not existing:
        runtime_output.write_text(json.dumps(result,indent=2,default=str)+'\n')
except Exception as exc:
    errors.append(f'{type(exc).__name__}:{exc}')
decision=('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_reusable_hook_bundle_CPU_closed'
          if not failed and not existing and not errors else
          'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_reusable_hook_bundle_CPU')
payload={'decision':decision,'checks':checks,'calls':calls,'failed':failed,
         'existing':existing,'errors':errors,'GPU_used':False,'optimizer_updates':0}
if not existing:
    target.write_text(json.dumps(payload,indent=2)+'\n')
print(f'decision={decision} checks={checks} failed={failed} existing={existing} errors={errors}')
