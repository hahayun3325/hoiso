from __future__ import annotations
import argparse,hashlib,json,math,os,pickle,subprocess,sys
from pathlib import Path
from typing import Any

class SelectedHandRegistrationError(RuntimeError): pass

def sha(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic(path: str|Path,payload: dict[str,Any])->None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix(target.suffix+'.tmp')
    temporary.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    os.replace(temporary,target)

def inventory_rows(path: str|Path)->list[Path]:
    source=Path(path); packet=json.loads(source.read_text())
    if packet.get('decision')!='foundation_stage_artifact_inventory_closed':
        raise SelectedHandRegistrationError('inventory not closed:'+str(source))
    rows=[]
    for output_root in packet.get('output_roots',[]):
        for record in output_root.get('files',[]):
            owner=Path(record.get('path',''))
            if not owner.is_file() or sha(owner)!=record.get('sha256'):
                raise SelectedHandRegistrationError('inventory asset mismatch:'+str(owner))
            rows.append(owner)
    if len(rows)!=packet.get('file_count'):
        raise SelectedHandRegistrationError('inventory file count mismatch:'+str(source))
    return rows

def unique(rows,role,predicate):
    matches=[path for path in rows if predicate(path)]
    if len(matches)!=1:
        raise SelectedHandRegistrationError(role+'_count:'+str(len(matches)))
    return matches[0]

def load_packet(path: Path):
    import numpy as np
    value=np.load(path,allow_pickle=True)
    return value.item() if isinstance(value,np.ndarray) and value.shape==() else value

def resolve_field(packet,path):
    value=packet
    for token in str(path).split('/'):
        if token and token!='root': value=value[token]
    return value

def resolve_owners(*,preprocess_inventory,hamer_inventory,h2m_inventory,
                   moge_inventory,case_id):
    preprocess_rows=inventory_rows(preprocess_inventory)
    owner_path=unique(preprocess_rows,'selected_hand_owner',
      lambda p:p.name.endswith('_selected_hand_owner.json'))
    owner=json.loads(owner_path.read_text()); owner_sha=sha(owner_path)
    if owner.get('decision')!='Q0_selected_detector_to_hand_mask_closed':
        raise SelectedHandRegistrationError('selected hand owner not closed')
    if not isinstance(owner.get('selected_hand_id'),str) or not owner['selected_hand_id']:
        raise SelectedHandRegistrationError('selected hand id absent')
    if type(owner.get('canonical_is_right')) is not bool:
        raise SelectedHandRegistrationError('canonical side absent')
    crop_record=(owner.get('artifacts') or {}).get('crop') or {}
    mask_record=(owner.get('artifacts') or {}).get('hand_mask') or {}
    crop=Path(crop_record.get('path','')); mask=Path(mask_record.get('path',''))
    for role,path,expected in [('crop',crop,crop_record.get('sha256')),
                               ('hand_mask',mask,mask_record.get('sha256'))]:
        if not path.is_file() or sha(path)!=expected:
            raise SelectedHandRegistrationError(role+' owner mismatch')
    hamer_rows=inventory_rows(hamer_inventory)
    candidate=unique(hamer_rows,'HaMeR_packet',lambda p:p.name==crop.stem+'.npy')
    hamer_owner_path=unique(hamer_rows,'selected_HaMeR_owner',
      lambda p:p.name==crop.stem+'_selected_hamer_owner.json')
    hamer_owner=json.loads(hamer_owner_path.read_text())
    if hamer_owner.get('decision')!='selected_hand_HaMeR_candidate_closed':
        raise SelectedHandRegistrationError('selected HaMeR owner not closed')
    if hamer_owner.get('selected_hand_id')!=owner.get('selected_hand_id'):
        raise SelectedHandRegistrationError('selected hand identity changed at HaMeR')
    h2m_rows=inventory_rows(h2m_inventory); moge_rows=inventory_rows(moge_inventory)
    h2m=unique(h2m_rows,'H2M',lambda p:p.name==case_id+'_hoi_mesh.npy')
    points=unique(moge_rows,'MoGe_points',lambda p:p.name=='points.exr')
    return {'selected_hand_id':owner['selected_hand_id'],
      'selected_side':'right' if owner['canonical_is_right'] else 'left',
      'selected_owner':str(owner_path),'selected_owner_sha256':owner_sha,
      'crop':str(crop),'hand_mask':str(mask),'candidate':str(candidate),
      'selected_hamer_owner':str(hamer_owner_path),'H2M':str(h2m),'moge_points':str(points)}

def run_command(arguments):
    return subprocess.run(arguments,check=True,text=True)

def is_frame_i_policy(policy):
    return policy.get('schema')=='tracehoi.HandSpecificFrameIPolicy.v1'

def frame_i_solver_arguments(*,solver_script,paths,runtime_policy,result,report):
    return [sys.executable,str(solver_script),'--candidate',str(paths['candidate']),
      '--target',str(paths['target']),'--moge-points',str(paths['points']),
      '--hand-mask',str(paths['mask']),'--config',str(runtime_policy),
      '--result-out',str(result),'--report-out',str(report)]

def execute_frame_i_candidate(*,root,owners,target,policy,solver_script,
                              vitpose_module_root,case_id,launcher):
    import numpy as np
    if policy.get('candidate_execution_authorized') is not True:
        raise SelectedHandRegistrationError(
          'hand-specific Frame-I case execution is not authorized by the policy')
    required={'packet_fields','joint_map_21','scale_multiplier_bounds',
      'rotation_component_bounds_radians','minimum_visible_joints',
      'minimum_anchor_joints','anchor_window_radius_px',
      'minimum_positive_camera_depth_fraction','maximum_keypoint_nrmse',
      'maximum_anchor_nrmse','maximum_surface_nrmse',
      'minimum_projected_vertex_mask_fraction'}
    if not required.issubset(policy):
        raise SelectedHandRegistrationError('hand-specific Frame-I policy incomplete')
    paths={'candidate':Path(owners['candidate']),'target':target,
      'points':Path(owners['moge_points']),'mask':Path(owners['hand_mask'])}
    policy.update({'expected_candidate_sha256':sha(paths['candidate']),
      'expected_target_sha256':sha(paths['target']),
      'expected_points_sha256':sha(paths['points']),
      'expected_hand_mask_sha256':sha(paths['mask']),
      'object_H2M_provenance_only':{'path':owners['H2M'],
        'sha256':sha(owners['H2M']),'applied_to_hand':False}})
    runtime_policy=root/'selected_hand_frame_i.json'; atomic(runtime_policy,policy)
    result=root/'selected_hand_frame_i_candidate.npz'
    report=root/'selected_hand_frame_i_candidate_report.json'
    launcher(frame_i_solver_arguments(solver_script=solver_script,paths=paths,
      runtime_policy=runtime_policy,result=result,report=report))
    report_packet=json.loads(report.read_text())
    if report_packet.get('decision')!='hand_specific_frame_I_candidate_result_written':
        raise SelectedHandRegistrationError('hand-specific Frame-I candidate did not close')
    if report_packet.get('object_H2M_applied_to_hand') is not False:
        raise SelectedHandRegistrationError('foreign object H2M entered the hand transform')
    with np.load(result,allow_pickle=False) as data:
        vertices=np.asarray(data['aligned_vertices_moge_Nx3'],dtype=float)
        positive=float(np.asarray(data['positive_camera_depth_fraction']).reshape(()))
        proper=bool(np.asarray(data['proper_sim3']).reshape(()))
    from foho.automation.mano_geometry_gate import audit_vertices
    geometry=audit_vertices(vertices,expected_vertices=778)
    if not proper: raise SelectedHandRegistrationError('hand transform is not proper Sim(3)')
    if positive<float(policy['minimum_positive_camera_depth_fraction']):
        raise SelectedHandRegistrationError('positive camera depth below policy')
    mano=Path(vitpose_module_root)/'_DATA/data/mano'/(
      'MANO_RIGHT.pkl' if owners['selected_side']=='right' else 'MANO_LEFT.pkl')
    with mano.open('rb') as stream:
        faces=np.asarray(pickle.load(stream,encoding='latin1')['f'],dtype=np.int64)
    import trimesh
    mesh=root/(case_id+'_selected_registered_mano_moge.ply')
    trimesh.Trimesh(vertices=vertices,faces=faces,process=False).export(mesh)
    receipt={'schema':'tracehoi.SelectedHandFrameIRegistration.v1','case_id':case_id,
      'selected_hand_id':owners['selected_hand_id'],'selected_side':owners['selected_side'],
      'owners':owners,'runtime_policy':str(runtime_policy),
      'runtime_policy_sha256':sha(runtime_policy),'result':str(result),
      'result_sha256':sha(result),'report':str(report),'report_sha256':sha(report),
      'registered_mesh':str(mesh),'registered_mesh_sha256':sha(mesh),
      'registered_mesh_frame':'native_MoGe','object_H2M_applied_to_hand':False,
      'positive_camera_depth_fraction':positive,'geometry':geometry,
      'part_preference_control':'deferred_to_fresh_Frame_I_with_Gate_A_parts',
      'authorizes_frame_i':False,'authorizes_installation':False,
      'decision':'selected_hand_frame_I_candidate_written'}
    atomic(root/'selected_hand_registration_receipt.json',receipt)
    return receipt

def execute(*,preprocess_inventory,hamer_inventory,h2m_inventory,moge_inventory,
            vitpose_script,vitpose_module_root,solver_script,policy_template,
            output_dir,case_id='alapuse02v3n60',device='cuda:0',launcher=run_command):
    import numpy as np
    root=Path(output_dir)
    root.mkdir(parents=True,exist_ok=True)
    occupied=[path for path in root.iterdir() if path.name!='stage_inventory.json']
    if occupied: raise SelectedHandRegistrationError('registration output root is nonempty')
    owners=resolve_owners(preprocess_inventory=preprocess_inventory,
      hamer_inventory=hamer_inventory,h2m_inventory=h2m_inventory,
      moge_inventory=moge_inventory,case_id=case_id)
    image=Path(owners['crop'])
    from PIL import Image
    with Image.open(image) as opened: size=[int(opened.width),int(opened.height)]
    target_dir=root/'vitpose'; target_dir.mkdir(parents=True,exist_ok=True)
    for side in ('left','right'):
        cfg={'expected_image_sha256':sha(image),'vitpose_module_root':str(Path(vitpose_module_root).resolve()),
          'device':device,'handedness':side,'visibility_confidence_threshold':0.30,
          'require_exactly_one_pose':True,'expected_image_size_wh':size}
        cfg_path=target_dir/(side+'_config.json'); atomic(cfg_path,cfg)
        target_path=target_dir/(side+'_target.npz'); report_path=target_dir/(side+'_report.json')
        launcher([sys.executable,str(vitpose_script),'--image',str(image),'--config',str(cfg_path),
          '--target-out',str(target_path),'--report-out',str(report_path)])
        target_report=json.loads(report_path.read_text())
        if target_report.get('decision')!='pass_v99_11_7_5_independent_full_image_vitpose_target':
            raise SelectedHandRegistrationError('ViTPose target did not close:'+side)
        if target_report.get('handedness')!=side:
            raise SelectedHandRegistrationError('ViTPose report side mismatch:'+side)
        with np.load(target_path,allow_pickle=False) as target_packet:
            if str(np.asarray(target_packet['handedness']).reshape(()))!=side:
                raise SelectedHandRegistrationError('ViTPose target side mismatch:'+side)
    target=target_dir/(owners['selected_side']+'_target.npz')
    policy=json.loads(Path(policy_template).read_text())
    if is_frame_i_policy(policy):
        return execute_frame_i_candidate(root=root,owners=owners,target=target,
          policy=policy,solver_script=solver_script,
          vitpose_module_root=vitpose_module_root,case_id=case_id,launcher=launcher)
    required={'packet_fields','global_max_final_reprojection_rmse_px','positive_scale_bounds',
      'translation_lower_xyz','translation_upper_xyz','metric_point_to_surface_weight',
      'metric_residual_clip','metric_max_points','metric_sample_seed','minimum_visible_joints'}
    if not required.issubset(policy):
        raise SelectedHandRegistrationError('selected registration policy incomplete')
    candidate=Path(owners['candidate']); packet=load_packet(candidate)
    raw=resolve_field(packet,policy['packet_fields']['camera_translation'])
    if hasattr(raw,'detach'): raw=raw.detach().cpu()
    if hasattr(raw,'numpy'): raw=raw.numpy()
    translation=np.asarray(raw,dtype=float).reshape(-1,3)[0]
    if not np.isfinite(translation).all():
        raise SelectedHandRegistrationError('HaMeR initialization is nonfinite')
    initialization=root/'initialization.npz'
    np.savez_compressed(initialization,relative_metric_scale=np.asarray(1.0),translation_xyz=translation)
    paths={'candidate':candidate,'target':target,'H2M':Path(owners['H2M']),
      'points':Path(owners['moge_points']),'mask':Path(owners['hand_mask']),
      'initialization':initialization}
    policy.update({'expected_candidate_sha256':sha(paths['candidate']),
      'expected_target_sha256':sha(paths['target']),'expected_H2M_sha256':sha(paths['H2M']),
      'expected_points_sha256':sha(paths['points']),'expected_hand_mask_sha256':sha(paths['mask']),
      'expected_initialization_sha256':sha(paths['initialization'])})
    runtime_policy=root/'selected_hand_CPU_7DoF.json'; atomic(runtime_policy,policy)
    result=root/'selected_hand_CPU_7DoF.npz'; report=root/'selected_hand_CPU_7DoF_report.json'
    launcher([sys.executable,str(solver_script),'--candidate',str(paths['candidate']),
      '--target',str(paths['target']),'--H2M',str(paths['H2M']),
      '--moge-points',str(paths['points']),'--hand-mask',str(paths['mask']),
      '--initialization',str(initialization),'--config',str(runtime_policy),
      '--result-out',str(result),'--report-out',str(report)])
    report_packet=json.loads(report.read_text())
    if report_packet.get('decision')!='pass_v99_11_7_13_3_6_CPU_7DoF_global_hand_alignment_raw_result':
        raise SelectedHandRegistrationError('CPU registration did not close')
    rmse=float(report_packet['full_image_reprojection_rmse_px'])
    limit=float(policy['global_max_final_reprojection_rmse_px'])
    if not math.isfinite(rmse) or rmse>limit:
        raise SelectedHandRegistrationError('registered hand exceeds reprojection policy')
    from foho.automation.mano_geometry_gate import audit_vertices
    with np.load(result,allow_pickle=False) as data:
        vertices=np.asarray(data['aligned_vertices_camera_Nx3'],dtype=float)
        positive=float(np.asarray(data['positive_depth_fraction']).reshape(()))
    geometry=audit_vertices(vertices,expected_vertices=778)
    if positive<=0.95: raise SelectedHandRegistrationError('positive depth below policy')
    mano=Path(vitpose_module_root)/'_DATA/data/mano'/('MANO_RIGHT.pkl' if owners['selected_side']=='right' else 'MANO_LEFT.pkl')
    with mano.open('rb') as stream: faces=np.asarray(pickle.load(stream,encoding='latin1')['f'],dtype=np.int64)
    import trimesh
    mesh=root/(case_id+'_selected_registered_mano.ply')
    trimesh.Trimesh(vertices=vertices,faces=faces,process=False).export(mesh)
    receipt={'schema':'tracehoi.SelectedHandRegistration.v1','case_id':case_id,
      'selected_hand_id':owners['selected_hand_id'],'selected_side':owners['selected_side'],
      'owners':owners,'runtime_policy':str(runtime_policy),'runtime_policy_sha256':sha(runtime_policy),
      'result':str(result),'result_sha256':sha(result),'report':str(report),'report_sha256':sha(report),
      'registered_mesh':str(mesh),'registered_mesh_sha256':sha(mesh),
      'full_image_reprojection_rmse_px':rmse,'reprojection_limit_px':limit,
      'positive_depth_fraction':positive,'geometry':geometry,
      'decision':'selected_hand_registration_closed'}
    atomic(root/'selected_hand_registration_receipt.json',receipt)
    return receipt

def main():
    parser=argparse.ArgumentParser()
    for name in ('preprocess_inventory','hamer_inventory','h2m_inventory','moge_inventory',
                 'vitpose_script','vitpose_module_root','solver_script','policy_template','output_dir'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--case_id',default='alapuse02v3n60'); parser.add_argument('--device',default='cuda:0')
    args=parser.parse_args(); got=execute(**vars(args)); print(json.dumps(got,indent=2))
if __name__=='__main__': main()
