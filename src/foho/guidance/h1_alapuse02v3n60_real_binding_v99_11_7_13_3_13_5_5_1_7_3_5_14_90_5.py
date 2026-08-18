from __future__ import annotations

import copy
import hashlib
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from pytorch3d.structures import Meshes
from pytorch3d.transforms import quaternion_to_matrix

from hamer.models.mano_wrapper import MANO
from foho.guidance.h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9 import load_case_resources, interpolate_metric_face_depth
from foho.guidance.h1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4 import H1SelectedFingerMANOProvider
from foho.guidance.h1_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import run_live


class H1DiagnosticComplete(RuntimeError):
    def __init__(self,outcome):
        super().__init__('H1_diagnostic_complete')
        self.outcome=outcome


def _sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fresh(path):
    path=Path(path)
    if path.exists(): raise FileExistsError(str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def _number(value):
    return float(value.detach().cpu()) if torch.is_tensor(value) else float(value)


def register_hshape_vertices(vertices, fixed_T_h2m):
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError('H1_Hshape_vertices_must_be_N_by_3')
    if fixed_T_h2m.shape != (4, 4):
        raise ValueError('H1_T_h2m_must_be_4_by_4')
    return vertices @ fixed_T_h2m[:3, :3].transpose(0, 1) + fixed_T_h2m[:3, 3]


def apply_accepted_h0_pose(registered_vertices, registered_center, scale,
                           accepted_rotation, accepted_translation):
    rotation = quaternion_to_matrix(accepted_rotation.reshape(-1, 4))[0]
    transformed = (scale * (registered_vertices - registered_center)) @ rotation.transpose(0, 1)
    return transformed + registered_center + accepted_translation.reshape(-1, 3)[0]


def _load_carrier(path):
    original=torch.storage._load_from_bytes
    torch.storage._load_from_bytes=lambda blob: torch.load(io.BytesIO(blob),map_location='cpu',weights_only=False)
    try: return np.load(path,allow_pickle=True).item()
    finally: torch.storage._load_from_bytes=original


def load_h1_resources(h0_manifest,h0_source_bundle,h0_policy,h1_policy,provider_path,
                      bridge_path,carrier_path,mano_path,jacobian_path,h0_checkpoint,
                      device,dtype,T_h2m_path=None):
    h0=load_case_resources(h0_manifest,h0_source_bundle,h0_policy,device,dtype)
    policy=json.loads(Path(h1_policy).read_text())
    if policy.get('status')!='PASS': raise ValueError('H1_live_policy_not_PASS')
    bridge=json.loads(Path(bridge_path).read_text())
    composite=bridge.get('composite_local_to_Hshape') or {}
    if not composite: raise ValueError('H1_bridge_composite_missing')
    carrier=_load_carrier(carrier_path); params=carrier.get('pred_mano_params') or {}
    selected=0
    required=('global_orient','hand_pose','betas')
    if any(name not in params for name in required): raise ValueError('carrier_MANO_parameters_incomplete')
    layer=MANO(model_path=str(Path(mano_path).parent),is_rhand=True,use_pca=False,flat_hand_mean=False).to(device)
    provider=H1SelectedFingerMANOProvider(
        layer,
        params['global_orient'][selected:selected+1].to(device=device,dtype=dtype),
        params['hand_pose'][selected:selected+1].to(device=device,dtype=dtype),
        params['betas'][selected:selected+1].to(device=device,dtype=dtype),
        torch.as_tensor(composite['linear'],device=device,dtype=dtype),
        torch.as_tensor(composite['translation'],device=device,dtype=dtype)).to(device)
    checkpoint=torch.load(h0_checkpoint,map_location=device,weights_only=False)
    accepted=checkpoint.get('parameters') or {}
    if set(accepted)!={'global_hand_rotation','global_hand_translation'}:
        raise ValueError('accepted_H0_checkpoint_Rt_mismatch')
    if T_h2m_path is None:
        raise ValueError('H1_fixed_T_h2m_owner_required')
    fixed_T_h2m=torch.as_tensor(np.load(T_h2m_path),device=device,dtype=dtype)
    if fixed_T_h2m.shape!=(4,4) or not bool(torch.isfinite(fixed_T_h2m).all()):
        raise ValueError('H1_fixed_T_h2m_invalid')
    expected_last=torch.tensor([0.0,0.0,0.0,1.0],device=device,dtype=dtype)
    if not torch.allclose(fixed_T_h2m[3],expected_last,atol=1e-6,rtol=0.0):
        raise ValueError('H1_fixed_T_h2m_must_be_affine')
    with np.load(jacobian_path,allow_pickle=False) as packet:
        palm_mask=torch.as_tensor(packet['palm_mask'],device=device,dtype=torch.bool)
    hashes={name:_sha(path) for name,path in {
      'h0_manifest':h0_manifest,'h0_source_bundle':h0_source_bundle,'h0_policy':h0_policy,
      'h1_policy':h1_policy,'provider':provider_path,'bridge':bridge_path,
      'carrier':carrier_path,'mano':mano_path,'jacobian':jacobian_path,
      'h0_checkpoint':h0_checkpoint,'T_h2m':T_h2m_path}.items()}
    return {'h0':h0,'policy':policy,'provider':provider,
            'accepted_rotation':accepted['global_hand_rotation'].to(device=device,dtype=dtype),
            'accepted_translation':accepted['global_hand_translation'].to(device=device,dtype=dtype),
            'fixed_T_h2m':fixed_T_h2m,'palm_mask':palm_mask,'artifact_hashes':hashes}


def bind_live_context(context,resources,output_root):
    if not isinstance(context,dict): raise TypeError('live_context_must_be_dictionary')
    owner=context.get('compute_base_loss_for_mesh')
    if not callable(owner): raise ValueError('mesh_aware_base_loss_owner_required')
    rendering=context.get('rendering') or {}; renderer=rendering.get('renderer')
    image_size=tuple(rendering.get('image_size') or ())
    frozen=context.get('frozen') or {}; base_mesh=frozen.get('mano_mesh_moge')
    scale=frozen.get('global_hand_scale')
    if renderer is None or len(image_size)!=2 or base_mesh is None or scale is None:
        raise ValueError('renderer_image_mesh_and_scale_required')
    provider=resources['provider']; parameter=provider.selected_so3_residual
    h0=resources['h0']; policy=resources['policy']; weights=policy['weights']
    accepted_R=resources['accepted_rotation'].detach().clone()
    accepted_t=resources['accepted_translation'].detach().clone()
    accepted_scale=scale.detach().clone() if torch.is_tensor(scale) else torch.as_tensor(scale,device=parameter.device,dtype=parameter.dtype)
    faces=base_mesh.faces_packed().detach().clone()
    baseline_hshape=provider().detach().clone()[0]
    fixed_T_h2m=resources['fixed_T_h2m'].detach().clone()
    baseline_registered=register_hshape_vertices(baseline_hshape,fixed_T_h2m)
    live_base_vertices=base_mesh.verts_packed().detach()
    if baseline_registered.shape!=live_base_vertices.shape:
        raise ValueError('H1_zero_residual_live_vertex_shape_mismatch')
    zero_identity_max=float((baseline_registered-live_base_vertices).abs().max().detach().cpu())
    if zero_identity_max>1e-4:
        raise ValueError(f'H1_zero_residual_does_not_reproduce_live_base:{zero_identity_max}')
    registered_center=(baseline_registered.min(0).values+baseline_registered.max(0).values)/2.0
    output_root=Path(output_root)
    state={'optimizer':None,'raster_calls':0,'loss_calls':0,'accepted_total':None}

    def parameter_registry(): return {'selected_so3_residual':parameter}

    def current_mesh():
        registered=register_hshape_vertices(provider()[0],fixed_T_h2m)
        transformed=apply_accepted_h0_pose(
            registered,registered_center,accepted_scale,accepted_R,accepted_t)
        return Meshes(verts=[transformed],faces=[faces])

    def frozen_state():
        camera=renderer.rasterizer.cameras
        return {'provider_frozen_digest':provider.frozen_digest(),
                'accepted_H0_rotation':accepted_R,'accepted_H0_translation':accepted_t,
                'accepted_hand_scale':accepted_scale,'GateA_vertices':h0['object_vertices'],
                'GateA_faces':h0['object_faces'],'object_depth':h0['object_depth'],
                'object_valid':h0['object_valid'],'r04':h0['r04'],
                'camera_R':camera.R,'camera_T':camera.T,'baseline_hshape':baseline_hshape,
                'fixed_T_h2m':fixed_T_h2m,'baseline_registered':baseline_registered,
                'registered_center':registered_center,'zero_identity_max':zero_identity_max}

    def rasterize_object():
        state['raster_calls']+=1
        return {'depth':h0['object_depth'],'valid':h0['object_valid'],'r04':h0['r04']}

    def compute_loss(raster):
        state['loss_calls']+=1
        mesh=current_mesh(); base_loss,base=owner(mesh,accepted_t)
        fragments=renderer.rasterizer(mesh); vertices=mesh.verts_packed(); mesh_faces=mesh.faces_packed()
        view_vertices=renderer.rasterizer.cameras.get_world_to_view_transform().transform_points(vertices)
        vertex_depth=view_vertices[:,2].abs()
        hand_depth,hand_valid=interpolate_metric_face_depth(
            fragments.pix_to_face,fragments.bary_coords,mesh_faces,vertex_depth)
        if hand_depth.ndim==3 and hand_depth.shape[0]==1:
            hand_depth=hand_depth[0]; hand_valid=hand_valid[0]
        height,width=image_size
        screen=renderer.rasterizer.cameras.transform_points_screen(
            vertices.unsqueeze(0),image_size=(height,width))[0]
        pad_ids=h0['pad_ids']; pad_xy=screen[pad_ids,:2]; pad_z=vertex_depth[pad_ids]
        r04_yx=torch.nonzero(raster['r04']&raster['valid'],as_tuple=False)
        if r04_yx.numel()==0: raise RuntimeError('H1_r04_support_empty')
        r04_xy=r04_yx[:,[1,0]].to(dtype=pad_xy.dtype)
        distances=torch.cdist(pad_xy,r04_xy); nearest=distances.argmin(1); nearest_yx=r04_yx[nearest]
        target_z=raster['depth'][nearest_yx[:,0],nearest_yx[:,1]]
        image_diagonal=math.sqrt(float(height*height+width*width))
        loss_contact_xy=distances.min(1).values.mean()/image_diagonal
        loss_contact_z=(pad_z-target_z).abs().mean()/h0['object_diagonal']
        loss_zorder,_,zfacts=h0['zorder_module'].dense_valid_zorder_loss(
            hand_depth,raster['depth'],raster['valid'],contact_exempt_mask=raster['r04'],
            margin=float(policy['zorder_margin']),object_diagonal=h0['object_diagonal'])
        overlap=hand_valid&raster['valid']
        loss_collision=(torch.relu(hand_depth[overlap]-raster['depth'][overlap]).mean()/h0['object_diagonal']
                        if bool(overlap.any()) else parameter.sum()*0.0)
        residual=parameter
        loss_pose_prior=residual.square().mean()
        loss_joint_limit=torch.relu(residual.abs()-float(policy['joint_limit_radians'])).square().mean()
        current_hshape=provider()[0]
        palm=resources['palm_mask']
        loss_integrity=(current_hshape[palm]-baseline_hshape[palm]).square().mean()
        pose=provider.composed_hand_pose()
        loss_integrity=loss_integrity+(pose[:,6:]-provider.base_hand_pose[:,6:]).square().mean()
        total=(float(weights['base_observation'])*base_loss+
               float(weights['contact_xy'])*loss_contact_xy+
               float(weights['contact_z'])*loss_contact_z+
               float(weights['zorder'])*loss_zorder+
               float(weights['pose_prior'])*loss_pose_prior+
               float(weights['joint_limit'])*loss_joint_limit+
               float(weights['collision'])*loss_collision+
               float(weights['integrity'])*loss_integrity)
        metrics={'loss_total':_number(total),'loss_base':_number(base_loss),
          'loss_contact_xy':_number(loss_contact_xy),'loss_contact_z':_number(loss_contact_z),
          'loss_zorder':_number(loss_zorder),'loss_pose_prior':_number(loss_pose_prior),
          'loss_joint_limit':_number(loss_joint_limit),'loss_collision':_number(loss_collision),
          'loss_integrity':_number(loss_integrity),'H1_contact_active':True,
          'mesh_aware_base_loss_active':True,'metric_hand_depth_active':bool(hand_valid.any().detach().cpu()),
          'dense_raster_bound':True,'zorder_valid_count':int(zfacts['valid_count']),
          'r04_support_count':int(r04_yx.shape[0]),'collision_overlap_count':int(overlap.sum().detach().cpu()),
          'raster_calls':state['raster_calls'],'loss_calls':state['loss_calls']}
        return total,metrics

    def gate_pass(metrics):
        names=('loss_total','loss_base','loss_contact_xy','loss_contact_z','loss_zorder',
               'loss_pose_prior','loss_joint_limit','loss_collision','loss_integrity')
        if not all(math.isfinite(float(metrics[name])) for name in names): return False
        current=float(metrics['loss_total']); prior=state['accepted_total']
        if prior is not None:
            permitted=prior*(1.0+float(policy['gate']['max_relative_total_regression']))
            if current>permitted+float(policy['gate']['absolute_tolerance']): return False
        state['accepted_total']=current; return True

    def snapshot():
        return {'provider':provider.snapshot(),
                'optimizer':copy.deepcopy(state['optimizer'].state_dict()) if state['optimizer'] is not None else None,
                'accepted_total':state['accepted_total']}

    def restore(value):
        provider.restore(value['provider'])
        if state['optimizer'] is not None and value['optimizer'] is not None:
            state['optimizer'].load_state_dict(value['optimizer'])
        state['accepted_total']=value['accepted_total']

    def build_optimizer(selected):
        if len(selected)!=1 or selected[0] is not parameter:
            raise ValueError('H1_optimizer_requires_exact_selected_residual_identity')
        optimizer=torch.optim.Adam([parameter],lr=float(policy['learning_rate']))
        state['optimizer']=optimizer; return optimizer

    def save_checkpoint(attempt,metrics):
        path=_fresh(output_root/'checkpoints'/f'H1_attempt_{int(attempt):03d}.pt')
        torch.save({'attempt':int(attempt),'selected_so3_residual':parameter.detach().cpu(),
                    'optimizer':state['optimizer'].state_dict() if state['optimizer'] is not None else None,
                    'accepted_H0_rotation':accepted_R.detach().cpu(),
                    'accepted_H0_translation':accepted_t.detach().cpu(),
                    'metrics':metrics,'artifact_hashes':resources['artifact_hashes']},path)
        return str(path)

    def capture(step,raster):
        with torch.no_grad(): _,metrics=compute_loss(raster)
        path=_fresh(output_root/'captures'/f'H1_capture_{int(step):03d}.json')
        path.write_text(json.dumps({'step':int(step),'metrics':metrics,'raster_bound':True},indent=2)+'\n')
        return {'step':int(step),'path':str(path),'raster_bound':True,'metrics':metrics}

    runtime=SimpleNamespace(parameter_registry=parameter_registry,frozen_state=frozen_state,
      rasterize_object=rasterize_object,compute_loss=compute_loss,gate_pass=gate_pass,
      snapshot=snapshot,restore=restore,build_optimizer=build_optimizer,
      save_checkpoint=save_checkpoint,capture=capture)
    bound=dict(context); bound['h1_runtime']=runtime
    bound['metadata']={**dict(context.get('metadata') or {}),'H1_real_binding':True,
                       'artifact_hashes':resources['artifact_hashes']}
    return bound


class BoundH1Callback:
    def __init__(self,binder,attempts,backward_only,capture_only,terminate_after_h1=True):
        self.binder=binder; self.attempts=int(attempts); self.backward_only=bool(backward_only)
        self.capture_only=bool(capture_only); self.terminate_after_h1=bool(terminate_after_h1); self._bound=False

    def bind_live_context(self,context):
        if self._bound: raise RuntimeError('H1_live_context_may_be_bound_once')
        self._bound=True; return self.binder(context)

    def __call__(self,context):
        result=run_live(context['h1_runtime'],attempts=self.attempts,checkpoint_every=1,
                        backward_only=self.backward_only,capture_only=self.capture_only)
        outcome={'handled':True,'result':result}
        if self.terminate_after_h1: raise H1DiagnosticComplete(outcome)
        return outcome


def create_bound_callback(paths,output_root,attempts=0,backward_only=True,capture_only=False,
                          resources_override=None,terminate_after_h1=True):
    def binder(context):
        parameters=context.get('parameters') or {}; reference=parameters.get('global_hand_rotation')
        if reference is None: raise ValueError('live_global_hand_rotation_missing')
        resources=resources_override or load_h1_resources(
            paths['h0_manifest'],paths['h0_source_bundle'],paths['h0_policy'],paths['h1_policy'],
            paths['provider'],paths['bridge'],paths['carrier'],paths['mano'],paths['jacobian'],
            paths['h0_checkpoint'],reference.device,reference.dtype,
            T_h2m_path=paths['T_h2m'])
        return bind_live_context(context,resources,output_root)
    return BoundH1Callback(binder,attempts,backward_only,capture_only,terminate_after_h1)

from pathlib import Path

PROJECT_ROOT=Path('/home/fredcui/Projects/FollowMyHold')
CASE_ROOT=Path('/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2')
HAMER_ROOT=PROJECT_ROOT/'third_party/estimator/hamer'
HAMER_POLICY_ROOT=CASE_ROOT/'gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/selected_seed_and_fresh_hand_zero_step_v99_11_7_13_3_13_5_5_1_7_3_5_14_19/official_hand_chain_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_20/frame_archive_independent_hand_shape_v99_11_7_13_3_13_5_5_1_7_3_5_14_21/official_upper_hand_source_selection_v99_11_7_13_3_13_5_5_1_7_3_5_14_22/fresh_upper_only_HaMeR_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_23'
PATHS={
  'h0_manifest':CASE_ROOT/'gate_d0_H0_real_hook_binding_and_execution_contract_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2/config/alapuse02v3n60_H0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2.json',
  'h0_source_bundle':CASE_ROOT/'gate_d0_H0_exact_source_diff_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_10/reports/exact_H0_source_diff_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_10.json',
  'h0_policy':PROJECT_ROOT/'config/optimization/H0_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4.json',
  'h1_policy':PROJECT_ROOT/'config/optimization/H1_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.json',
  'provider':PROJECT_ROOT/'src/foho/guidance/h1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.py',
  'bridge':CASE_ROOT/'gate_d0_H1_bridge_and_reusable_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4/config/alapuse02v3n60_local_MANO_to_Hshape_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.json',
  'carrier':HAMER_POLICY_ROOT/'generated/alapuse02v3n60upperL_0.npy',
  'mano':HAMER_ROOT/'_DATA/data/mano/MANO_RIGHT.pkl',
  'jacobian':CASE_ROOT/'gate_d0_H1_registered_carrier_provider_and_Jacobian_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3_3/artifacts/index_middle_vertex_Jacobian_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3_3.npz',
  'h0_checkpoint':CASE_ROOT/'gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt',
  'T_h2m':CASE_ROOT/'gate_c_hand_constraint_first_CPU_v99_11_7_13_3_13_5_5_1_7_3_5_14_38/candidates/depth_median_CF_T_Hshape_to_I.npy'}

def create_callback(mode,output_root,resources_override=None):
    modes={'backward-only':(0,True,False),'capture-only':(0,False,True),'optimize':(5,False,False)}
    if mode not in modes: raise ValueError(f'unsupported_H1_mode:{mode}')
    attempts,backward,capture=modes[mode]
    return create_bound_callback(PATHS,output_root,attempts=attempts,backward_only=backward,
                                 capture_only=capture,resources_override=resources_override,
                                 terminate_after_h1=True)
