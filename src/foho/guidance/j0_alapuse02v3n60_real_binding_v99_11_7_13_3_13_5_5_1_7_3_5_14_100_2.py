from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from types import SimpleNamespace
import torch
import foho.guidance.o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3 as o0_owner
from foho.guidance.h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import register_hshape_vertices,apply_accepted_h0_pose
from foho.guidance.j0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2 import run_live

ORDER=('global_hand_rotation','global_hand_translation','selected_so3_residual','global_object_rotation','global_object_translation')
TRAINABLE=('global_hand_rotation','global_hand_translation','global_object_rotation','global_object_translation')
EXPECTED_O0_MANIFEST_SHA256='8267df851e683add480f737cc6b91c0a3c2fb6c15126cb2b81a7b2496714b591'
class J0DiagnosticComplete(RuntimeError):
    def __init__(self,outcome): super().__init__('J0 diagnostic complete'); self.outcome=outcome
def _sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _number(value): return float(value.detach().cpu()) if torch.is_tensor(value) else float(value)
def _fresh(path):
    path=Path(path)
    if path.exists(): raise FileExistsError(f'J0_output_exists:{path}')
    path.parent.mkdir(parents=True,exist_ok=True); return path
def _validate_checkpoint_lineage(checkpoints):
    if list(checkpoints)!=['H0','H1','O0']: raise ValueError('J0_checkpoint_lineage_order_mismatch')
    resolved={}
    for label in ('H0','H1','O0'):
        row=checkpoints[label]
        if not isinstance(row,dict) or set(row)!={'path','sha256'}: raise ValueError(f'J0_checkpoint_schema_mismatch:{label}')
        path=Path(row['path'])
        if not path.is_file(): raise FileNotFoundError(f'J0_checkpoint_missing:{label}:{path}')
        if _sha(path)!=row['sha256']: raise ValueError(f'J0_checkpoint_hash_mismatch:{label}')
        resolved[label]=path
    return resolved

def load_j0_resources(o0_manifest_path,h0_checkpoint,h1_checkpoint,o0_checkpoint,device,dtype):
    odoc=json.loads(Path(o0_manifest_path).read_text()); paths=dict(odoc['paths'])
    paths['h0_checkpoint']=str(h0_checkpoint); paths['h1_checkpoint']=str(h1_checkpoint)
    resources=o0_owner.load_o0_resources(paths,device,dtype)
    checkpoint=torch.load(o0_checkpoint,map_location=device,weights_only=False); parameters=checkpoint.get('parameters') or {}
    if list(parameters)!=['global_object_rotation','global_object_translation']: raise ValueError('J0_O0_checkpoint_Rt_order_mismatch')
    if tuple(parameters['global_object_rotation'].shape)!=(4,) or tuple(parameters['global_object_translation'].shape)!=(3,): raise ValueError('J0_O0_checkpoint_Rt_shape_mismatch')
    resources['o0_checkpoint']=checkpoint
    resources['hashes']={**dict(resources.get('hashes') or {}),'h0_checkpoint':_sha(h0_checkpoint),'h1_checkpoint':_sha(h1_checkpoint),'o0_checkpoint':_sha(o0_checkpoint),'o0_case_manifest':_sha(o0_manifest_path)}
    return resources

def bind_live_context(context,resources,output_root,policy):
    if not isinstance(context,dict): raise TypeError('J0_live_context_must_be_mapping')
    parameters=context.get('parameters') or {}
    if list(parameters)!=list(TRAINABLE): raise ValueError('J0_live_parameter_order_mismatch')
    hr,ht,orr,ot=[parameters[name] for name in TRAINABLE]
    if [tuple(value.shape) for value in (hr,ht,orr,ot)]!=[(4,),(3,),(4,),(3,)]: raise ValueError('J0_live_parameter_shape_mismatch')
    if len({id(value) for value in (hr,ht,orr,ot)})!=4: raise ValueError('J0_live_parameter_identity_collision')
    frozen=context.get('frozen') or {}; hand_scale=frozen.get('global_hand_scale'); object_scale=frozen.get('global_object_scale'); base_hand=frozen.get('mano_mesh_moge')
    hand_base=context.get('compute_base_loss_for_hand_mesh'); object_base=context.get('compute_base_loss_for_object_mesh')
    rendering=context.get('rendering') or {}; renderer=rendering.get('renderer'); image_size=tuple(rendering.get('image_size') or ())
    if hand_scale is None or object_scale is None or base_hand is None or not callable(hand_base) or not callable(object_base): raise ValueError('J0_live_frozen_or_base_owner_missing')
    provider=resources['provider']; residual=provider.selected_so3_residual; h1=resources['h1']; o0=resources['o0_checkpoint']; output_root=Path(output_root)
    accepted_object=o0['parameters']
    with torch.no_grad():
        hr.copy_(h1['accepted_rotation'].to(device=hr.device,dtype=hr.dtype)); ht.copy_(h1['accepted_translation'].to(device=ht.device,dtype=ht.dtype))
        orr.copy_(accepted_object['global_object_rotation'].to(device=orr.device,dtype=orr.dtype)); ot.copy_(accepted_object['global_object_translation'].to(device=ot.device,dtype=ot.dtype))
    residual.requires_grad_(False)
    initial={name:value.detach().clone() for name,value in {**parameters,'selected_so3_residual':residual}.items()}
    accepted_scale=hand_scale.detach().clone() if torch.is_tensor(hand_scale) else torch.as_tensor(hand_scale,device=hr.device,dtype=hr.dtype)
    object_scale_tensor=object_scale.detach().clone() if torch.is_tensor(object_scale) else torch.as_tensor(object_scale,device=orr.device,dtype=orr.dtype)
    custom_hand=resources.get('hand_mesh_owner'); custom_object=resources.get('object_mesh_owner'); custom_joint=resources.get('joint_metrics_owner')
    if custom_hand is None:
        fixed_T=h1['fixed_T_h2m'].detach(); baseline_registered=register_hshape_vertices(resources['baseline_hshape'],fixed_T)
        registered_center=(baseline_registered.min(0).values+baseline_registered.max(0).values)/2.0
    else: fixed_T=registered_center=None
    object_vertices=resources['object_vertices']; object_faces=resources['object_faces']; object_center=(object_vertices.min(0).values+object_vertices.max(0).values)/2.0
    diagonal=torch.linalg.vector_norm(object_vertices.max(0).values-object_vertices.min(0).values).clamp_min(1e-12)
    state={'optimizer':None,'accepted_total':None,'loss_calls':0,'hand_rasters':0,'object_rasters':0}
    def current_hand_mesh():
        if custom_hand is not None: return custom_hand(provider,hr,ht,accepted_scale,base_hand)
        registered=register_hshape_vertices(provider()[0],fixed_T)
        vertices=apply_accepted_h0_pose(registered,registered_center,accepted_scale,hr,ht)
        return o0_owner.Meshes(verts=[vertices],faces=[base_hand.faces_packed()])
    def current_object_mesh():
        if custom_object is not None: return custom_object(object_vertices,object_faces,orr,ot,object_scale_tensor)
        matrix=o0_owner.quaternion_to_matrix(orr); scale=object_scale_tensor.reshape(-1)[0]
        vertices=((object_vertices-object_center)*scale)@matrix.transpose(0,1)+object_center+ot
        return o0_owner.Meshes(verts=[vertices],faces=[object_faces])
    def default_joint(hand_mesh,object_mesh):
        if renderer is None or len(image_size)!=2: raise ValueError('J0_renderer_and_image_size_required')
        hand_fragments=renderer.rasterizer(hand_mesh); object_fragments=renderer.rasterizer(object_mesh); state['hand_rasters']+=1; state['object_rasters']+=1
        camera=renderer.rasterizer.cameras; hand_vertices=hand_mesh.verts_packed(); object_vertices_now=object_mesh.verts_packed()
        hand_z=camera.get_world_to_view_transform().transform_points(hand_vertices)[:,2].abs(); object_z=camera.get_world_to_view_transform().transform_points(object_vertices_now)[:,2].abs()
        hand_depth,hand_valid=o0_owner.interpolate_metric_face_depth(hand_fragments.pix_to_face,hand_fragments.bary_coords,hand_mesh.faces_packed(),hand_z)
        object_depth,object_valid=o0_owner.interpolate_metric_face_depth(object_fragments.pix_to_face,object_fragments.bary_coords,object_mesh.faces_packed(),object_z)
        if hand_depth.ndim==3 and hand_depth.shape[0]==1: hand_depth,hand_valid=hand_depth[0],hand_valid[0]
        if object_depth.ndim==3 and object_depth.shape[0]==1: object_depth,object_valid=object_depth[0],object_valid[0]
        height,width=image_size; screen=camera.transform_points_screen(hand_vertices.unsqueeze(0),image_size=(height,width))[0]; pad_ids=h1['h0']['pad_ids']
        pad_xy=screen[pad_ids,:2]; pad_z=hand_z[pad_ids]
        face_image=object_fragments.pix_to_face[0,...,0] if object_fragments.pix_to_face.ndim==4 else object_fragments.pix_to_face[...,0]
        r04=torch.zeros_like(face_image,dtype=torch.bool)
        for face_id in resources['r04_face_ids']: r04|=face_image==face_id
        r04_yx=torch.nonzero(r04&object_valid,as_tuple=False)
        if r04_yx.numel()==0: raise RuntimeError('J0_dynamic_r04_support_empty')
        r04_xy=r04_yx[:,[1,0]].to(dtype=pad_xy.dtype); distances=torch.cdist(pad_xy,r04_xy); nearest=r04_yx[distances.argmin(1)]
        contact_xy=distances.min(1).values.mean()/math.sqrt(float(height*height+width*width)); contact_z=(pad_z-object_depth[nearest[:,0],nearest[:,1]]).abs().mean()/diagonal
        zorder,_,facts=h1['h0']['zorder_module'].dense_valid_zorder_loss(hand_depth,object_depth,object_valid,contact_exempt_mask=r04,margin=float(policy.get('zorder_margin',0.0)),object_diagonal=diagonal)
        overlap=hand_valid&object_valid; collision=(torch.relu(hand_depth[overlap]-object_depth[overlap]).mean()/diagonal if bool(overlap.any()) else hr.sum()*0.0+orr.sum()*0.0)
        return {'contact_xy':contact_xy,'contact_z':contact_z,'zorder':zorder,'collision':collision,'r04_support_count':int(r04_yx.shape[0]),'zorder_valid_count':int(facts['valid_count'])}
    def parameter_registry(): return {'global_hand_rotation':hr,'global_hand_translation':ht,'selected_so3_residual':residual,'global_object_rotation':orr,'global_object_translation':ot}
    def trainable_registry(): return {name:parameter_registry()[name] for name in TRAINABLE}
    def frozen_state():
        return {'selected_so3_residual':residual,'global_hand_scale':accepted_scale,'global_object_scale':object_scale_tensor,'artifact_hashes':resources['hashes'],'hand_faces':base_hand.faces_packed(),'object_faces':object_faces}
    def compute_loss():
        state['loss_calls']+=1; hand_mesh=current_hand_mesh(); object_mesh=current_object_mesh()
        hand_loss,hand_metrics=hand_base(hand_mesh,ht); object_loss,object_metrics=object_base(object_mesh)
        joint=(custom_joint or default_joint)(hand_mesh,object_mesh)
        hand_trust=(hr-initial['global_hand_rotation']).square().mean()+torch.linalg.vector_norm(ht-initial['global_hand_translation'])/diagonal
        object_trust=(orr-initial['global_object_rotation']).square().mean()+torch.linalg.vector_norm(ot-initial['global_object_translation'])/diagonal
        quaternion_norm=(torch.linalg.vector_norm(hr)-1).square()+(torch.linalg.vector_norm(orr)-1).square(); weights=policy['weights']
        total=float(weights['hand_base'])*hand_loss+float(weights['object_base'])*object_loss+float(weights['contact_xy'])*joint['contact_xy']+float(weights['contact_z'])*joint['contact_z']+float(weights['zorder'])*joint['zorder']+float(weights['collision'])*joint['collision']+float(weights['hand_trust'])*hand_trust+float(weights['object_trust'])*object_trust+float(weights['quaternion_norm'])*quaternion_norm
        metrics={'loss_total':_number(total),'loss_hand_base':_number(hand_loss),'loss_object_base':_number(object_loss),'loss_contact_xy':_number(joint['contact_xy']),'loss_contact_z':_number(joint['contact_z']),'loss_zorder':_number(joint['zorder']),'loss_collision':_number(joint['collision']),'loss_hand_trust':_number(hand_trust),'loss_object_trust':_number(object_trust),'loss_quaternion_norm':_number(quaternion_norm),'r04_support_count':int(joint.get('r04_support_count',1)),'zorder_valid_count':int(joint.get('zorder_valid_count',1)),'joint_hand_and_object_recomputed':True,'loss_calls':state['loss_calls']}
        return total,metrics
    def gate_pass(metrics):
        if not all(math.isfinite(float(value)) for key,value in metrics.items() if key.startswith('loss_')) or metrics['r04_support_count']<=0: return False
        current=float(metrics['loss_total']); prior=state['accepted_total']; gate=policy['gate']
        if prior is not None and current>prior*(1+float(gate['max_relative_total_regression']))+float(gate['absolute_tolerance']): return False
        state['accepted_total']=current; return True
    def snapshot():
        return {'values':{name:value.detach().clone() for name,value in parameter_registry().items()},'flags':{name:bool(value.requires_grad) for name,value in parameter_registry().items()},'optimizer':copy.deepcopy(state['optimizer'].state_dict()) if state['optimizer'] is not None else None,'accepted_total':state['accepted_total']}
    def restore(value):
        with torch.no_grad():
            for name,parameter in parameter_registry().items(): parameter.copy_(value['values'][name])
        for name,parameter in parameter_registry().items(): parameter.requires_grad_(value['flags'][name])
        if state['optimizer'] is not None and value['optimizer'] is not None: state['optimizer'].load_state_dict(value['optimizer'])
        state['accepted_total']=value['accepted_total']
    def build_optimizer(selected):
        expected=[parameters[name] for name in TRAINABLE]
        if not isinstance(selected,list) or len(selected)!=4 or any(actual is not wanted for actual,wanted in zip(selected,expected)): raise ValueError('J0_optimizer_requires_exact_ordered_live_Rt')
        rates=policy['learning_rates']; optimizer=torch.optim.Adam([{'params':[parameters[name]],'lr':float(rates[name])} for name in TRAINABLE]); state['optimizer']=optimizer; return optimizer
    def project_parameters():
        with torch.no_grad():
            hr.div_(torch.linalg.vector_norm(hr).clamp_min(1e-12)); orr.div_(torch.linalg.vector_norm(orr).clamp_min(1e-12))
    def save_checkpoint(attempt,metrics):
        path=_fresh(output_root/'checkpoints'/f'J0_attempt_{int(attempt):03d}.pt')
        torch.save({'attempt':int(attempt),'parameters':{name:value.detach().cpu() for name,value in trainable_registry().items()},'selected_so3_residual':residual.detach().cpu(),'metrics':metrics,'artifact_hashes':resources['hashes']},path); return str(path)
    def capture(step):
        with torch.no_grad(): _,metrics=compute_loss()
        path=_fresh(output_root/'captures'/f'J0_capture_{int(step):03d}.json'); path.write_text(json.dumps({'step':int(step),'metrics':metrics,'joint_recomputed':True},indent=2)+'\n')
        return {'step':int(step),'path':str(path),'metrics':metrics,'joint_recomputed':True}
    runtime=SimpleNamespace(parameter_registry=parameter_registry,trainable_registry=trainable_registry,frozen_state=frozen_state,compute_loss=compute_loss,gate_pass=gate_pass,snapshot=snapshot,restore=restore,build_optimizer=build_optimizer,project_parameters=project_parameters,save_checkpoint=save_checkpoint,capture=capture)
    bound=dict(context); bound['j0_runtime']=runtime; bound['current_hand_mesh']=current_hand_mesh; bound['current_object_mesh']=current_object_mesh; bound['metadata']={**dict(context.get('metadata') or {}),'J0_real_binding':True,'H0_H1_O0_lineage_hashes':resources['hashes']}
    return bound

class BoundJ0Callback:
    def __init__(self,binder,attempts,backward_only,capture_only): self.binder=binder; self.attempts=int(attempts); self.backward_only=bool(backward_only); self.capture_only=bool(capture_only); self._bound=False
    def bind_live_context(self,context):
        if self._bound: raise RuntimeError('J0_context_may_be_bound_once')
        self._bound=True; return self.binder(context)
    def __call__(self,context):
        bound_context=self.bind_live_context(context)
        result=run_live(bound_context['j0_runtime'],attempts=self.attempts,checkpoint_every=1,backward_only=self.backward_only,capture_only=self.capture_only)
        raise J0DiagnosticComplete({'handled':True,'result':result})
class BypassPriorPhase:
    def __init__(self,phase): self.phase=phase
    def bind_live_context(self,context): return context
    def __call__(self,context): return {'handled':True,'result':{'updates_completed':0,'reason':f'accepted_{self.phase}_state_loaded_by_J0'}}

def create_callback(mode,output_root,j0_case_manifest,o0_case_manifest,resources_override=None):
    modes={'backward-only':(0,True,False),'capture-only':(0,False,True),'optimize':(5,False,False)}
    if mode not in modes: raise ValueError(f'unsupported_J0_mode:{mode}')
    case=json.loads(Path(j0_case_manifest).read_text()); paths=case['paths']; checkpoints=case['checkpoints']; policy=json.loads(Path(paths['j0_policy_target']).read_text())
    resolved=_validate_checkpoint_lineage(checkpoints)
    if _sha(o0_case_manifest)!=EXPECTED_O0_MANIFEST_SHA256: raise ValueError('J0_O0_case_manifest_hash_mismatch')
    attempts,backward,capture=modes[mode]
    def binder(context):
        reference=(context.get('parameters') or {}).get('global_hand_rotation')
        if reference is None: raise ValueError('J0_live_hand_rotation_missing')
        resources=resources_override or load_j0_resources(o0_case_manifest,resolved['H0'],resolved['H1'],resolved['O0'],reference.device,reference.dtype)
        return bind_live_context(context,resources,output_root,policy)
    return BypassPriorPhase('H1_hand'),BypassPriorPhase('O0_object'),BoundJ0Callback(binder,attempts,backward,capture)
