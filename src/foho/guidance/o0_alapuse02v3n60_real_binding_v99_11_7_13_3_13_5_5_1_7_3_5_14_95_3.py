from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from types import SimpleNamespace
import torch
from pytorch3d.io import load_ply
from pytorch3d.structures import Meshes
from pytorch3d.transforms import quaternion_to_matrix
from foho.guidance.h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9 import interpolate_metric_face_depth
from foho.guidance.h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import load_h1_resources,register_hshape_vertices,apply_accepted_h0_pose
from foho.guidance.o0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3 import run_live

class O0DiagnosticComplete(RuntimeError):
    def __init__(self,outcome): super().__init__('O0_diagnostic_complete'); self.outcome=outcome
def _sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _number(value): return float(value.detach().cpu()) if torch.is_tensor(value) else float(value)
def _fresh(path):
    path=Path(path)
    if path.exists(): raise FileExistsError(str(path))
    path.parent.mkdir(parents=True,exist_ok=True); return path
def _face_sets(value):
    rows=[]
    if isinstance(value,dict):
        for key,child in value.items():
            if 'face' in str(key).lower() and isinstance(child,list) and child and all(isinstance(item,int) for item in child): rows.append(tuple(sorted(set(child))))
            rows.extend(_face_sets(child))
    elif isinstance(value,list):
        for child in value: rows.extend(_face_sets(child))
    return rows

def load_o0_resources(paths,device,dtype):
    h1=load_h1_resources(paths['h0_manifest'],paths['h0_source_bundle'],paths['h0_policy'],paths['h1_policy'],
      paths['provider'],paths['bridge'],paths['carrier'],paths['mano'],paths['jacobian'],paths['h0_checkpoint'],
      device,dtype,T_h2m_path=paths['T_h2m'])
    provider=h1['provider']; baseline_hshape=provider()[0].detach().clone()
    checkpoint=torch.load(paths['h1_checkpoint'],map_location=device,weights_only=False)
    residual=checkpoint.get('selected_so3_residual')
    if not torch.is_tensor(residual) or tuple(residual.shape)!=(6,3): raise ValueError('O0_H1_residual_shape_mismatch')
    with torch.no_grad(): provider.selected_so3_residual.copy_(residual.to(device=device,dtype=dtype))
    provider.selected_so3_residual.requires_grad_(False)
    object_vertices,object_faces=load_ply(paths['GateA'])
    object_vertices=object_vertices.to(device=device,dtype=dtype); object_faces=object_faces.to(device=device)
    unique=set(_face_sets(json.loads(Path(paths['r04_map']).read_text())))
    if len(unique)!=1: raise ValueError(f'O0_r04_face_owner_not_unique:{len(unique)}')
    r04_face_ids=torch.as_tensor(next(iter(unique)),device=device,dtype=torch.long)
    if r04_face_ids.numel()==0 or int(r04_face_ids.max())>=object_faces.shape[0]: raise ValueError('O0_r04_faces_out_of_range')
    hashes={name:_sha(path) for name,path in paths.items() if Path(path).is_file()}
    return {'h1':h1,'provider':provider,'baseline_hshape':baseline_hshape,'h1_checkpoint':checkpoint,
      'object_vertices':object_vertices,'object_faces':object_faces,'r04_face_ids':r04_face_ids,'hashes':hashes}

def bind_live_context(context,resources,output_root,policy):
    if not isinstance(context,dict): raise TypeError('O0_live_context_must_be_mapping')
    parameters=context.get('parameters') or {}
    if list(parameters)!=['global_object_rotation','global_object_translation']: raise ValueError('O0_live_Rt_order_mismatch')
    rotation=parameters['global_object_rotation']; translation=parameters['global_object_translation']
    if tuple(rotation.shape)!=(4,) or tuple(translation.shape)!=(3,): raise ValueError('O0_live_Rt_shape_mismatch')
    base_owner=context.get('compute_base_loss_for_object_mesh')
    if not callable(base_owner): raise ValueError('O0_base_loss_owner_required')
    rendering=context.get('rendering') or {}; renderer=rendering.get('renderer'); image_size=tuple(rendering.get('image_size') or ())
    frozen=context.get('frozen') or {}; base_hand=frozen.get('mano_mesh_moge'); hand_scale=frozen.get('global_hand_scale'); object_scale=frozen.get('global_object_scale')
    if renderer is None or len(image_size)!=2 or base_hand is None or hand_scale is None or object_scale is None: raise ValueError('O0_render_and_frozen_owners_required')
    provider=resources['provider']; h1=resources['h1']; output_root=Path(output_root); weights=policy['weights']
    gatea_vertices=resources['object_vertices']; gatea_faces=resources['object_faces']
    gatea_center=(gatea_vertices.min(0).values+gatea_vertices.max(0).values)/2.0
    def current_object_mesh():
        matrix=quaternion_to_matrix(rotation)
        scale=torch.as_tensor(object_scale,device=rotation.device,dtype=rotation.dtype).reshape(-1)[0]
        posed=((gatea_vertices-gatea_center)*scale)@matrix.transpose(0,1)+gatea_center+translation
        return Meshes(verts=[posed],faces=[gatea_faces])
    fixed_T=h1['fixed_T_h2m'].detach(); baseline_registered=register_hshape_vertices(resources['baseline_hshape'],fixed_T)
    registered_center=(baseline_registered.min(0).values+baseline_registered.max(0).values)/2.0
    accepted_scale=hand_scale.detach().clone() if torch.is_tensor(hand_scale) else torch.as_tensor(hand_scale,device=rotation.device,dtype=rotation.dtype)
    with torch.no_grad():
        registered=register_hshape_vertices(provider()[0],fixed_T)
        accepted_vertices=apply_accepted_h0_pose(registered,registered_center,accepted_scale,h1['accepted_rotation'],h1['accepted_translation']).detach()
        accepted_hand=Meshes(verts=[accepted_vertices],faces=[base_hand.faces_packed().detach().clone()])
        hand_fragments=renderer.rasterizer(accepted_hand); camera=renderer.rasterizer.cameras
        hand_view=camera.get_world_to_view_transform().transform_points(accepted_vertices); hand_vertex_depth=hand_view[:,2].abs()
        hand_depth,hand_valid=interpolate_metric_face_depth(hand_fragments.pix_to_face,hand_fragments.bary_coords,accepted_hand.faces_packed(),hand_vertex_depth)
        if hand_depth.ndim==3 and hand_depth.shape[0]==1: hand_depth,hand_valid=hand_depth[0],hand_valid[0]
        height,width=image_size; screen=camera.transform_points_screen(accepted_vertices.unsqueeze(0),image_size=(height,width))[0]
        pad_ids=h1['h0']['pad_ids']; pad_xy=screen[pad_ids,:2].detach(); pad_z=hand_vertex_depth[pad_ids].detach()
        initial_mesh=current_object_mesh(); initial_vertices=initial_mesh.verts_packed().detach(); initial_faces=initial_mesh.faces_packed().detach()
        vertex_error=float((initial_vertices-resources['object_vertices']).abs().max().cpu()) if initial_vertices.shape==resources['object_vertices'].shape else float('inf')
        faces_exact=initial_faces.shape==resources['object_faces'].shape and bool(torch.equal(initial_faces,resources['object_faces']))
        if vertex_error>1e-4 or not faces_exact: raise ValueError(f'O0_zero_update_GateA_identity_failed:{vertex_error}:{faces_exact}')
    initial={'rotation':rotation.detach().clone(),'translation':translation.detach().clone()}
    diagonal=torch.linalg.vector_norm(resources['object_vertices'].max(0).values-resources['object_vertices'].min(0).values)
    state={'optimizer':None,'accepted_total':None,'loss_calls':0,'raster_calls':0}

    def parameter_registry(): return {'global_object_rotation':rotation,'global_object_translation':translation}
    def frozen_state():
        camera=renderer.rasterizer.cameras
        return {'accepted_H1_vertices':accepted_vertices,'accepted_H1_faces':accepted_hand.faces_packed(),
          'GateA_vertices':resources['object_vertices'],'GateA_faces':resources['object_faces'],
          'global_object_scale':object_scale,'camera_R':camera.R,'camera_T':camera.T,
          'artifact_hashes':resources['hashes'],'zero_identity_error':vertex_error}
    def evaluate():
        state['loss_calls']+=1; mesh=current_object_mesh(); state['raster_calls']+=1
        base_loss,base=base_owner(mesh); fragments=renderer.rasterizer(mesh)
        vertices=mesh.verts_packed(); faces=mesh.faces_packed(); camera=renderer.rasterizer.cameras
        view=camera.get_world_to_view_transform().transform_points(vertices); vertex_depth=view[:,2].abs()
        object_depth,object_valid=interpolate_metric_face_depth(fragments.pix_to_face,fragments.bary_coords,faces,vertex_depth)
        if object_depth.ndim==3 and object_depth.shape[0]==1: object_depth,object_valid=object_depth[0],object_valid[0]
        face_image=fragments.pix_to_face[0,...,0] if fragments.pix_to_face.ndim==4 else fragments.pix_to_face[...,0]
        r04=torch.zeros_like(face_image,dtype=torch.bool)
        for face_id in resources['r04_face_ids']: r04|=face_image==face_id
        r04_yx=torch.nonzero(r04&object_valid,as_tuple=False)
        if r04_yx.numel()==0: raise RuntimeError('O0_dynamic_r04_support_empty')
        r04_xy=r04_yx[:,[1,0]].to(dtype=pad_xy.dtype); distances=torch.cdist(pad_xy,r04_xy)
        nearest_yx=r04_yx[distances.argmin(1)]; target_z=object_depth[nearest_yx[:,0],nearest_yx[:,1]]
        contact_xy=distances.min(1).values.mean()/math.sqrt(float(height*height+width*width))
        contact_z=(pad_z-target_z).abs().mean()/diagonal
        zorder,_,zfacts=h1['h0']['zorder_module'].dense_valid_zorder_loss(hand_depth,object_depth,object_valid,
          contact_exempt_mask=r04,margin=float(policy['zorder_margin']),object_diagonal=diagonal)
        overlap=hand_valid&object_valid
        collision=(torch.relu(hand_depth[overlap]-object_depth[overlap]).mean()/diagonal if bool(overlap.any()) else rotation.sum()*0.0)
        trust=(rotation-initial['rotation']).square().mean()+torch.linalg.vector_norm(translation-initial['translation'])/diagonal
        quaternion_norm=(torch.linalg.vector_norm(rotation)-1.0).square()
        total=(float(weights['base'])*base_loss+float(weights['contact_xy'])*contact_xy+
          float(weights['contact_z'])*contact_z+float(weights['zorder'])*zorder+
          float(weights['collision'])*collision+float(weights['trust'])*trust+
          float(weights['quaternion_norm'])*quaternion_norm)
        metrics={'loss_total':_number(total),'loss_base':_number(base_loss),'loss_contact_xy':_number(contact_xy),
          'loss_contact_z':_number(contact_z),'loss_zorder':_number(zorder),'loss_collision':_number(collision),
          'loss_trust':_number(trust),'loss_quaternion_norm':_number(quaternion_norm),
          'O0_dynamic_object_raster':True,'accepted_H1_hand_frozen':True,'r04_support_count':int(r04_yx.shape[0]),
          'zorder_valid_count':int(zfacts['valid_count']),'collision_overlap_count':int(overlap.sum().cpu()),
          'raster_calls':state['raster_calls'],'loss_calls':state['loss_calls'],'zero_identity_error':vertex_error}
        return total,metrics
    def gate_pass(metrics):
        names=('loss_total','loss_base','loss_contact_xy','loss_contact_z','loss_zorder','loss_collision','loss_trust','loss_quaternion_norm')
        if not all(math.isfinite(float(metrics[name])) for name in names) or metrics['r04_support_count']<=0: return False
        current=float(metrics['loss_total']); prior=state['accepted_total']
        if prior is not None and current>prior*(1+float(policy['gate']['max_relative_total_regression']))+float(policy['gate']['absolute_tolerance']): return False
        state['accepted_total']=current; return True
    def snapshot():
        return {'values':{name:value.detach().clone() for name,value in parameter_registry().items()},
          'flags':{name:bool(value.requires_grad) for name,value in parameter_registry().items()},
          'optimizer':copy.deepcopy(state['optimizer'].state_dict()) if state['optimizer'] is not None else None,
          'accepted_total':state['accepted_total']}
    def restore(value):
        with torch.no_grad():
            for name,parameter in parameter_registry().items(): parameter.copy_(value['values'][name])
        for name,parameter in parameter_registry().items(): parameter.requires_grad_(value['flags'][name])
        if state['optimizer'] is not None and value['optimizer'] is not None: state['optimizer'].load_state_dict(value['optimizer'])
        state['accepted_total']=value['accepted_total']
    def build_optimizer(selected):
        expected=[rotation,translation]
        if not isinstance(selected,list) or len(selected)!=2 or any(actual is not wanted for actual,wanted in zip(selected,expected)):
            raise ValueError('O0_optimizer_requires_exact_ordered_live_Rt')
        optimizer=torch.optim.Adam([{'params':[rotation],'lr':float(policy['rotation_learning_rate'])},
                                    {'params':[translation],'lr':float(policy['translation_learning_rate'])}])
        state['optimizer']=optimizer; return optimizer
    def save_checkpoint(attempt,metrics):
        path=_fresh(output_root/'checkpoints'/f'O0_attempt_{int(attempt):03d}.pt')
        torch.save({'attempt':int(attempt),'parameters':{name:value.detach().cpu() for name,value in parameter_registry().items()},
          'metrics':metrics,'optimizer':state['optimizer'].state_dict() if state['optimizer'] is not None else None,
          'accepted_H1_checkpoint_sha256':resources['hashes']['h1_checkpoint'],'artifact_hashes':resources['hashes']},path)
        return str(path)
    def capture(step):
        with torch.no_grad(): _,metrics=evaluate()
        path=_fresh(output_root/'captures'/f'O0_capture_{int(step):03d}.json')
        path.write_text(json.dumps({'step':int(step),'metrics':metrics,'dynamic_raster':True},indent=2)+'\n')
        return {'step':int(step),'path':str(path),'dynamic_raster':True,'metrics':metrics}
    runtime=SimpleNamespace(parameter_registry=parameter_registry,frozen_state=frozen_state,compute_loss=evaluate,
      gate_pass=gate_pass,snapshot=snapshot,restore=restore,build_optimizer=build_optimizer,
      save_checkpoint=save_checkpoint,capture=capture)
    bound=dict(context); bound['o0_runtime']=runtime; bound['metadata']={**dict(context.get('metadata') or {}),
      'O0_real_binding':True,'GateA_object_owned_by_binder':True,'accepted_H1_checkpoint_sha256':resources['hashes']['h1_checkpoint']}
    return bound

class BoundO0Callback:
    def __init__(self,binder,attempts,backward_only,capture_only,terminate=True):
        self.binder=binder; self.attempts=int(attempts); self.backward_only=bool(backward_only); self.capture_only=bool(capture_only); self.terminate=bool(terminate); self._bound=False
    def bind_live_context(self,context):
        if self._bound: raise RuntimeError('O0_context_may_be_bound_once')
        self._bound=True; return self.binder(context)
    def __call__(self,context):
        bound = self.bind_live_context(context)
        result=run_live(bound['o0_runtime'],attempts=self.attempts,checkpoint_every=1,
          backward_only=self.backward_only,capture_only=self.capture_only)
        outcome={'handled':True,'result':result}
        if self.terminate: raise O0DiagnosticComplete(outcome)
        return outcome

class BypassLegacyHand:
    def bind_live_context(self,context): return context
    def __call__(self,context): return {'handled':True,'result':{'updates_completed':0,'reason':'accepted_H1_hand_is_reconstructed_and_frozen_by_O0'}}

def create_callback(mode,output_root,manifest_path,resources_override=None):
    modes={'backward-only':(0,True,False),'capture-only':(0,False,True),'optimize':(5,False,False)}
    if mode not in modes: raise ValueError(f'unsupported_O0_mode:{mode}')
    doc=json.loads(Path(manifest_path).read_text()); paths=doc['paths']; policy=json.loads(Path(paths['o0_policy']).read_text())
    attempts,backward,capture=modes[mode]
    def binder(context):
        parameters=context.get('parameters') or {}; reference=parameters.get('global_object_rotation')
        if reference is None: raise ValueError('O0_live_rotation_missing')
        resources=resources_override or load_o0_resources(paths,reference.device,reference.dtype)
        return bind_live_context(context,resources,output_root,policy)
    return BypassLegacyHand(),BoundO0Callback(binder,attempts,backward,capture,True)
