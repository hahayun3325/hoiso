import importlib.util, json, os, tempfile
from pathlib import Path
import torch

controller_path=Path(os.environ['H0_CONTROLLER']); target=Path(os.environ['CONTROLLER_TEST_REPORT'])
spec=importlib.util.spec_from_file_location('h0_controller',controller_path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class FakeRuntime:
    def __init__(self):
        self.r=torch.nn.Parameter(torch.tensor([0.4,0.0,0.0])); self.t=torch.nn.Parameter(torch.tensor([0.0,0.3,0.0])); self.scale=torch.nn.Parameter(torch.tensor([1.0])); self.art=torch.nn.Parameter(torch.zeros(2)); self.obj=torch.nn.Parameter(torch.tensor([2.0])); self.raster_calls=0; self.checkpoints=[]
    def parameter_registry(self): return {'global_hand_rotation':self.r,'global_hand_translation':self.t,'global_hand_scale':self.scale,'mano_articulation':self.art,'object_pose':self.obj}
    def object_vertices(self): return self.obj
    def rasterize_object(self,vertices): self.raster_calls+=1; return {'depth':vertices.detach().clone(),'call':self.raster_calls}
    def build_optimizer(self,selected): return torch.optim.SGD(selected,lr=0.25)
    def compute_loss(self,raster,config):
        loss=(self.r**2).sum()+(self.t**2).sum(); return loss,{'finite':True,'raster_call':raster['call']}
    def gate_pass(self,metrics): return True
    def snapshot(self): return {name:value.detach().clone() for name,value in self.parameter_registry().items()}
    def restore(self,snapshot):
        with torch.no_grad():
            for name,value in snapshot.items(): self.parameter_registry()[name].copy_(value)
    def save_checkpoint(self,step,metrics): self.checkpoints.append(step)
    def capture(self,step,raster): return {'step':step,'raster_call':raster['call']}

with tempfile.TemporaryDirectory() as directory:
    config_path=Path(directory)/'h0.json'; config={'schema':'hoiso_phase_objective_v1','phase':'H0_global_hand_Rt','status':'PASS','optimizer_authorized':False,'parameter_allowlist':{'enable':['global_hand_rotation','global_hand_translation'],'freeze':['global_hand_scale','mano_articulation','object_pose']},'sources':{}}
    config_path.write_text(json.dumps(config)); phase=module.phase_loader.load_phase_config(config_path,'H0_global_hand_Rt')
    zero=FakeRuntime(); zero_before=module.state_digest(zero.parameter_registry()); zero_result=module.H0Controller(phase,zero).run(0,capture_only=True); zero_after=module.state_digest(zero.parameter_registry())
    live=FakeRuntime(); frozen_before=module.state_digest({'scale':live.scale,'art':live.art,'obj':live.obj}); selected_before=module.state_digest({'r':live.r,'t':live.t}); live_result=module.H0Controller(phase,live).run(2,checkpoint_every=1); frozen_after=module.state_digest({'scale':live.scale,'art':live.art,'obj':live.obj}); selected_after=module.state_digest({'r':live.r,'t':live.t})
checks={'zero_updates_bitwise':zero_before==zero_after and zero_result['updates_completed']==0,'zero_raster_once':zero.raster_calls==1,'two_updates_completed':live_result['updates_completed']==2 and not live_result['rolled_back'],'selected_parameters_changed':selected_before!=selected_after,'frozen_parameters_unchanged':frozen_before==frozen_after,'fixed_object_raster_once':live.raster_calls==1,'two_checkpoints':live.checkpoints==[1,2]}
payload={'decision':'pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_71_thin_H0_controller_CPU_closed' if all(checks.values()) else 'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_71_thin_H0_controller_CPU','checks':checks,'zero_result':zero_result,'live_result':live_result,'failed':[name for name,value in checks.items() if not value],'missing':[],'existing':[],'errors':[]}
target.write_text(json.dumps(payload,indent=2)+'\n'); print(json.dumps({'decision':payload['decision'],'failed':payload['failed']}))
