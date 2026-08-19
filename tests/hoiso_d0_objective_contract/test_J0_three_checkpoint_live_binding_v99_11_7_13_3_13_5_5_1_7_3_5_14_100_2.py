import importlib.util,json,os,sys,tempfile
from pathlib import Path
import torch

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module
runtime_name='foho.guidance.j0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2'
runtime=load(runtime_name,os.environ['J0_RUNTIME_CANDIDATE'])
binder=load('_j0_binder_candidate',os.environ['J0_BINDER_CANDIDATE'])
policy=json.loads(Path(os.environ['J0_POLICY_CANDIDATE']).read_text())
class Mesh:
    def __init__(self,vertices,faces): self.vertices=vertices; self.faces=faces
    def verts_packed(self): return self.vertices
    def faces_packed(self): return self.faces
class Provider:
    def __init__(self): self.selected_so3_residual=torch.nn.Parameter(torch.arange(18,dtype=torch.float32).reshape(6,3)/1000,requires_grad=False)
def make():
    provider=Provider(); faces=torch.tensor([[0,1,2]],dtype=torch.long); object_vertices=torch.tensor([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    hr=torch.nn.Parameter(torch.tensor([0.,1.,0.,0.]),requires_grad=False); ht=torch.nn.Parameter(torch.tensor([9.,9.,9.]),requires_grad=False)
    orr=torch.nn.Parameter(torch.tensor([0.,1.,0.,0.]),requires_grad=False); ot=torch.nn.Parameter(torch.tensor([-9.,-9.,-9.]),requires_grad=False)
    accepted_hr=torch.tensor([1.,0.,0.,0.]); accepted_ht=torch.tensor([0.1,0.2,0.3]); accepted_or=torch.tensor([1.,0.,0.,0.]); accepted_ot=torch.tensor([-0.1,0.1,0.2])
    def hand_mesh_owner(provider,rotation,translation,scale,base): return Mesh(provider.selected_so3_residual[:3]+translation+rotation[:3],faces)
    def object_mesh_owner(vertices,faces,rotation,translation,scale): return Mesh(vertices+translation+rotation[:3],faces)
    def hand_base(mesh,translation):
        loss=mesh.verts_packed().square().mean()+translation.square().mean(); return loss,{'hand':loss}
    def object_base(mesh):
        loss=mesh.verts_packed().square().mean(); return loss,{'object':loss}
    def joint(hand,object):
        delta=hand.verts_packed().mean(0)-object.verts_packed().mean(0); shared=delta.square().mean()
        return {'contact_xy':shared,'contact_z':shared*0.5,'zorder':shared*0.25,'collision':shared*0.125,'r04_support_count':3,'zorder_valid_count':3}
    context={'parameters':{'global_hand_rotation':hr,'global_hand_translation':ht,'global_object_rotation':orr,'global_object_translation':ot},'frozen':{'global_hand_scale':torch.tensor(1.),'global_object_scale':torch.tensor(1.),'mano_mesh_moge':Mesh(torch.zeros(3,3),faces)},'compute_base_loss_for_hand_mesh':hand_base,'compute_base_loss_for_object_mesh':object_base,'rendering':{},'metadata':{}}
    resources={'provider':provider,'h1':{'accepted_rotation':accepted_hr,'accepted_translation':accepted_ht},'o0_checkpoint':{'parameters':{'global_object_rotation':accepted_or,'global_object_translation':accepted_ot}},'object_vertices':object_vertices,'object_faces':faces,'hashes':{'H0':'h0','H1':'h1','O0':'o0'},'hand_mesh_owner':hand_mesh_owner,'object_mesh_owner':object_mesh_owner,'joint_metrics_owner':joint}
    return context,resources,(accepted_hr,accepted_ht,accepted_or,accepted_ot)
errors=[]; checks={}
try:
    with tempfile.TemporaryDirectory() as directory:
        lineage_root=Path(directory)/'lineage'; lineage_root.mkdir(); lineage={}
        for label,payload in (('H0',b'h0'),('H1',b'h1'),('O0',b'o0')):
            path=lineage_root/f'{label}.pt'; path.write_bytes(payload); lineage[label]={'path':str(path),'sha256':binder._sha(path)}
        lineage_exact=list(binder._validate_checkpoint_lineage(lineage))==['H0','H1','O0']
        (lineage_root/'H1.pt').write_bytes(b'tampered'); tamper_rejected=False
        try: binder._validate_checkpoint_lineage(lineage)
        except ValueError: tamper_rejected=True
        context,resources,accepted=make(); original=[context['parameters'][name] for name in runtime.TRAINABLE_ORDER]
        bound=binder.bind_live_context(context,resources,Path(directory)/'main',policy); registry=bound['j0_runtime'].parameter_registry()
        identity=all(bound['j0_runtime'].trainable_registry()[name] is original[index] for index,name in enumerate(runtime.TRAINABLE_ORDER))
        values=all(torch.equal(registry[name],accepted[index]) for index,name in enumerate(runtime.TRAINABLE_ORDER))
        residual_before=registry['selected_so3_residual'].detach().clone(); backward=runtime.run_live(bound['j0_runtime'],backward_only=True)
        capture_context,capture_resources,_=make(); capture_bound=binder.bind_live_context(capture_context,capture_resources,Path(directory)/'capture',policy); capture=runtime.run_live(capture_bound['j0_runtime'],capture_only=True)
        optimize_context,optimize_resources,_=make(); optimize_bound=binder.bind_live_context(optimize_context,optimize_resources,Path(directory)/'optimize',policy); optimize=runtime.run_live(optimize_bound['j0_runtime'],attempts=2)
        reject_context,reject_resources,_=make(); reject_bound=binder.bind_live_context(reject_context,reject_resources,Path(directory)/'reject',policy); before={name:value.detach().clone() for name,value in reject_bound['j0_runtime'].parameter_registry().items()}; reject_bound['j0_runtime'].gate_pass=lambda metrics:False; rejected=runtime.run_live(reject_bound['j0_runtime'],attempts=1)
        checks={'three_checkpoint_hashes_exact':lineage_exact,'tampered_checkpoint_rejected':tamper_rejected,'four_same_live_tensor_objects':identity,'accepted_H1_and_O0_values_loaded':values,'four_finite_nonzero_gradients':list(backward['gradient_stats'])==list(runtime.TRAINABLE_ORDER) and all(row['norm']>0 for row in backward['gradient_stats'].values()),'H1_residual_frozen':registry['selected_so3_residual'].grad is None and torch.equal(registry['selected_so3_residual'],residual_before),'capture_zero_updates':capture['updates_completed']==0,'two_updates_and_joint_recompute':optimize['updates_completed']==2 and all(row['metrics']['joint_hand_and_object_recomputed'] for row in optimize['trajectory']),'rejection_restores_all_five':rejected['rolled_back'] and all(torch.equal(reject_bound['j0_runtime'].parameter_registry()[name],value) for name,value in before.items()),'checkpoint_count_two':len(list((Path(directory)/'optimize'/'checkpoints').glob('J0_attempt_*.pt')))==2}
except Exception as exc: errors.append(f'{type(exc).__name__}:{exc}')
passed=not errors and checks and all(checks.values()); payload={'schema':'foho.J0ThreeCheckpointLiveBindingCPU.v1','decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_4_2_J0_live_binding_CPU_closed' if passed else 'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_4_2_recheck_J0_live_binding'),'checks':checks,'failed':([] if passed else [k for k,v in checks.items() if not v]),'errors':errors,'GPU_used':False,'optimizer_updates':0}
out=Path(os.environ['BIND_CPU_OUT'])
if not out.exists(): out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload))
