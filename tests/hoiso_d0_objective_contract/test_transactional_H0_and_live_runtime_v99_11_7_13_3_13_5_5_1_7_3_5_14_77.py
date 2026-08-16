import importlib.util, json, os, tempfile
from pathlib import Path
import torch

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

controller=load(Path(os.environ['SAFE_CONTROLLER77']),'transactional_h0_77'); adapter=load(Path(os.environ['ADAPTER_SOURCE77']),'live_runtime_77')
target=Path(os.environ['CPU_TEST77'])

class FakeRuntime:
    def __init__(self,gate_limit=10.0,mutate_frozen=False):
        self.r=torch.nn.Parameter(torch.tensor([0.4])); self.t=torch.nn.Parameter(torch.tensor([0.3])); self.scale=torch.nn.Parameter(torch.tensor([1.0])); self.art=torch.nn.Parameter(torch.zeros(2)); self.obj=torch.nn.Parameter(torch.tensor([2.0])); self.raster_calls=0; self.checkpoints=[]; self.gate_limit=gate_limit; self.mutate_frozen=mutate_frozen
    def parameter_registry(self): return {'global_hand_rotation':self.r,'global_hand_translation':self.t,'global_hand_scale':self.scale,'mano_articulation':self.art,'object_pose':self.obj}
    def object_vertices(self): return self.obj
    def rasterize_object(self,vertices): self.raster_calls+=1; return {'depth':vertices.detach().clone(),'call':self.raster_calls}
    def build_optimizer(self,selected):
        base=torch.optim.SGD(selected,lr=0.25)
        if not self.mutate_frozen: return base
        owner=self
        class Mutating:
            def zero_grad(self,**kwargs): return base.zero_grad(**kwargs)
            def step(self):
                result=base.step()
                with torch.no_grad(): owner.obj.add_(1.0)
                return result
        return Mutating()
    def compute_loss(self,raster,config):
        loss=(self.r**2).sum()+(self.t**2).sum(); return loss,{'score':float(loss.detach()),'raster_call':raster['call']}
    def gate_pass(self,metrics): return metrics['score']<=self.gate_limit
    def snapshot(self): return {name:value.detach().clone() for name,value in self.parameter_registry().items()}
    def restore(self,snapshot):
        with torch.no_grad():
            for name,value in snapshot.items(): self.parameter_registry()[name].copy_(value)
    def save_checkpoint(self,step,metrics): self.checkpoints.append({'step':step,'score':metrics['score']})
    def capture(self,step,raster): return {'step':step,'raster_call':raster['call']}

with tempfile.TemporaryDirectory() as directory:
    config_path=Path(directory)/'h0.json'; config={'schema':'hoiso_phase_objective_v1','phase':'H0_global_hand_Rt','status':'PASS','optimizer_authorized':False,'parameter_allowlist':{'enable':['global_hand_rotation','global_hand_translation'],'freeze':['global_hand_scale','mano_articulation','object_pose']},'sources':{}}
    config_path.write_text(json.dumps(config)); phase=controller.phase_loader.load_phase_config(config_path,'H0_global_hand_Rt')

    zero=FakeRuntime(); zero_flags={n:p.requires_grad for n,p in zero.parameter_registry().items()}; zero_before=controller.state_digest(zero.parameter_registry()); zero_result=controller.run_live(phase,zero,0,capture_only=True); zero_after=controller.state_digest(zero.parameter_registry()); zero_flags_after={n:p.requires_grad for n,p in zero.parameter_registry().items()}
    backward=FakeRuntime(); backward_flags=controller.flag_snapshot(backward.parameter_registry()); backward_before=controller.state_digest(backward.parameter_registry()); backward_result=controller.run_live(phase,backward,0,backward_only=True); backward_after=controller.state_digest(backward.parameter_registry()); backward_flags_after=controller.flag_snapshot(backward.parameter_registry())
    live=FakeRuntime(); live_flags=controller.flag_snapshot(live.parameter_registry()); live_result=controller.run_live(phase,live,2,checkpoint_every=1); live_flags_after=controller.flag_snapshot(live.parameter_registry())
    rejected=FakeRuntime(gate_limit=0.05); rejected_flags=controller.flag_snapshot(rejected.parameter_registry()); rejected_before=controller.state_digest(rejected.parameter_registry()); rejected_result=controller.run_live(phase,rejected,1); rejected_after=controller.state_digest(rejected.parameter_registry()); rejected_flags_after=controller.flag_snapshot(rejected.parameter_registry())
    mutated=FakeRuntime(mutate_frozen=True); mutated_flags=controller.flag_snapshot(mutated.parameter_registry()); mutated_before=controller.state_digest(mutated.parameter_registry()); mutation_raised=False
    try: controller.run_live(phase,mutated,1)
    except RuntimeError as exc: mutation_raised='frozen_owner_changed' in str(exc)
    mutated_after=controller.state_digest(mutated.parameter_registry()); mutated_flags_after=controller.flag_snapshot(mutated.parameter_registry())

    params=live.parameter_registry(); hooks={'object_vertices':live.object_vertices,'rasterize_object':live.rasterize_object,'build_optimizer':live.build_optimizer,'compute_loss':live.compute_loss,'gate_pass':live.gate_pass,'snapshot':live.snapshot,'restore':live.restore,'save_checkpoint':live.save_checkpoint,'capture':live.capture}
    wrapped=adapter.create_from_live_context({'parameters':params,'hooks':hooks,'owner':'CPU_fake'},phase)
    adapter_methods=['parameter_registry','object_vertices','rasterize_object','build_optimizer','compute_loss','gate_pass','snapshot','restore','save_checkpoint','capture']

checks={
    'zero_capture_bitwise_and_flags':zero_before==zero_after and zero_flags==zero_flags_after and zero_result['updates_completed']==0,
    'backward_only_no_update':backward_before==backward_after and backward_flags==backward_flags_after and backward_result['updates_completed']==0,
    'finite_nonzero_Rt_gradients':set(backward_result['gradient_stats'])=={'global_hand_rotation','global_hand_translation'} and all(v['norm']>0 for v in backward_result['gradient_stats'].values()),
    'two_post_gated_updates':live_result['updates_completed']==2 and not live_result['rolled_back'] and live_flags==live_flags_after and [c['step'] for c in live.checkpoints]==[1,2],
    'post_update_metrics_change':live_result['trajectory'][0]['pre_loss']!=live_result['trajectory'][0]['post_loss'],
    'failed_gate_rolls_back':rejected_result['rolled_back'] and rejected_result['updates_completed']==0 and rejected_before==rejected_after and rejected_flags==rejected_flags_after,
    'frozen_mutation_rolls_back_before_raise':mutation_raised and mutated_before==mutated_after and mutated_flags==mutated_flags_after,
    'adapter_returns_exact_live_references':wrapped.parameter_registry()['global_hand_rotation'] is live.r,
    'adapter_implements_ten_methods':all(callable(getattr(wrapped,name,None)) for name in adapter_methods),
    'fixed_object_raster_once_per_controller':zero.raster_calls==1 and backward.raster_calls==1 and live.raster_calls==1,
}
payload={'decision':'pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_77_transactional_controller_and_adapter_CPU_closed' if all(checks.values()) else 'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_77_transactional_controller_and_adapter_CPU','checks':checks,'backward_result':backward_result,'live_result':live_result,'rejected_result':rejected_result,'failed':[name for name,value in checks.items() if not value],'missing':[],'existing':[],'errors':[]}
target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(payload,indent=2,default=str)+'\n'); print(json.dumps({'decision':payload['decision'],'failed':payload['failed']}))
