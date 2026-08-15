#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def require(condition,message,failed):
    if not condition: failed.append(message)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--semantics',required=True)
    parser.add_argument('--finger-map',required=True)
    parser.add_argument('--object-map',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(); paths={k:Path(v) for k,v in vars(args).items() if k!='output'}; output=Path(args.output)
    failed=[]; missing=[str(p) for p in paths.values() if not p.is_file()]
    if missing:
        print(json.dumps({'decision':'hold_missing_compiler_inputs','failed':failed,'missing':missing,'errors':[]})); return
    semantics=json.loads(paths['semantics'].read_text()); finger=json.loads(paths['finger_map'].read_text()); obj=json.loads(paths['object_map'].read_text())
    require(finger.get('status')=='PASS','finger_map_status_PASS',failed)
    require(obj.get('status')=='PASS','object_map_status_PASS',failed)
    require(bool(finger.get('source_hashes')),'finger_source_hashes',failed)
    require(bool(obj.get('source_hashes')),'object_source_hashes',failed)
    active=semantics.get('active',{}); finger_names=active.get('hand_regions',[])
    finger_rows=finger.get('fingers',{}); selected=[]
    for name in finger_names:
        row=finger_rows.get(name)
        require(isinstance(row,dict),f'finger_owner:{name}',failed)
        if isinstance(row,dict):
            require(bool(row.get('contact_pad_vertex_ids')),f'contact_pad:{name}',failed)
            require(bool(row.get('joint_names')),f'joint_names:{name}',failed)
            require(bool(row.get('joint_parameter_indices')),f'joint_parameter_indices:{name}',failed)
            selected.append({'name':name,**row})
    part=active.get('object_part'); region=active.get('object_region')
    region_row=((obj.get('parts') or {}).get(part,{}).get('regions') or {}).get(region)
    require(isinstance(region_row,dict),f'object_region_owner:{part}/{region}',failed)
    if isinstance(region_row,dict): require(bool(region_row.get('face_ids')),f'object_face_ids:{part}/{region}',failed)
    if failed:
        print(json.dumps({'decision':'review_required_geometry_maps','failed':failed,'missing':missing,'errors':[]})); return
    plan={
      'schema':'hoiso_compiled_objective_adapter_v1',
      'source':{name:{'path':str(path),'sha256':digest(path)} for name,path in paths.items()},
      'semantic_owner':active,
      'geometry':{'active_fingers':selected,'active_object_patch':region_row,'forbidden':obj.get('forbidden',{})},
      'phase_parameter_allowlists':{
        'selected_finger_hand_probe':{'enable':[x for row in selected for x in row['joint_parameter_indices']],'freeze':['hand_shape','hand_scale','hand_global_Rt','all_unlisted_hand_joints','all_object_parameters']},
        'object_phase':{'enable':obj.get('object_phase_parameter_indices',[]),'freeze':['all_hand_parameters','object_scale','all_unlisted_object_parameters']},
        'joint_phase':{'enable':'requires_separate_joint_policy_and_live_parameter_binding','freeze':['hand_shape','hand_scale','object_scale']},
      },
      'loss_routing':{
        'base':['ordered_keypoints','allowed_hand_silhouette','MoGe_hand_depth_normal','pose_trust_region'],
        'semantic':['selected_contact_gap','forbidden_clearance','collision_penetration'],
        'z_order':{'mode':'per_pixel_mixed','validity':'finite_positive_in_frame_hand_depth AND finite_positive_in_frame_dense_object_depth','invalid_weight':0},
        'weight_policy':'globally_frozen_dimensionless_policy; semantic confidence selects active/hypothesis/diagnostic tier only',
      },
      'hard_runtime_assertions':['freeze_all_before_allowlist','every enabled index exists exactly once','no forbidden parameter requires_grad','GateA hash unchanged','finite losses and gradients','checkpoint rollback on gate regression'],
      'optimizer_authorized':False,
    }
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'decision':'pass_semantics_compiled_to_exact_geometry','output':str(output),'optimizer_authorized':False,'failed':[],'missing':[],'errors':[]}))

if __name__=='__main__': main()
