"""Portable diagnostic scene reader. Standard library only; no model imports.

Meshes are ALREADY in scene coordinates. Source transforms are provenance only.
Version 1 never authorizes production placement, even for separated surfaces.
"""
import hashlib,json,math,os,re,stat,struct
from pathlib import Path

FRAME='N7_PLY_x_right_y_up_z_backward'
UNITS='MoGe_predicted_metric_scale_not_independently_verified'
IDENTITY=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
TO_CAMERA=[[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]]
BLOCKERS=['selected_hand_mask_requires_review','scene_scale_unidentified','geometric_accuracy_unverified','physical_contact_unverified']
IDS=['primary','minimum_scale','maximum_scale','minimum_scale_refined']
EVIDENCE=['assembly','surface','collision','refinement','refined_gate','observation','fit']
ASSETS=['object','hand_primary','hand_minimum_scale','hand_maximum_scale','hand_minimum_scale_refined','original_rgb','scene_rgb','hand_mask','object_mask','overlap_mask']
def require(ok,why):
    if not ok:raise ValueError(why)
def binding(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def encode(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def parse(b):
    def pairs(rows):
        d={}
        for k,v in rows:require(k not in d,'duplicate_json_key');d[k]=v
        return d
    def bad(v):raise ValueError('nonfinite_json')
    return json.loads(b,object_pairs_hook=pairs,parse_constant=bad)
def regular(p,cap):
    p=Path(p).absolute()
    for q in [*reversed(p.parents),p]:require(not stat.S_ISLNK(q.lstat().st_mode),'symlink_resource')
    key=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    a=p.stat();require(stat.S_ISREG(a.st_mode) and a.st_size<=cap,'resource_bound')
    fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        require(key(a)==key(os.fstat(fd)),'resource_changed')
        with os.fdopen(fd,'rb',closefd=False) as f:b=f.read(cap+1)
        require(len(b)<=cap and key(a)==key(os.fstat(fd))==key(p.stat()),'resource_changed')
        return b
    finally:os.close(fd)
def resource(root,item):
    require(set(item)=={'path','bytes','sha256'},'resource_record')
    n=item['path'];require(isinstance(n,str) and re.fullmatch(r'(assets|evidence)/[a-z0-9_]+\.(ply|png|pgm|json)',n),'resource_path')
    b=regular(root/n,16*1024**2);require(binding(b)=={k:item[k] for k in ['bytes','sha256']},'resource_binding')
    return b
def matrix(m,rows,cols):
    require(isinstance(m,list) and len(m)==rows and all(isinstance(r,list) and len(r)==cols for r in m),'matrix_shape')
    require(all(type(x) in (int,float) and math.isfinite(x) for r in m for x in r),'matrix_finite')
    if rows==4:require(m[3]==[0,0,0,1],'affine_transform')
def mesh(b):
    end=b.find(b'end_header\n');require(0<end<4096,'mesh_header');end+=11
    lines=[x for x in b[:end].decode('ascii').splitlines() if not x.startswith('comment ')]
    require(len(lines)==9 and lines[:2]==['ply','format binary_little_endian 1.0'] and lines[3:6]==['property float x','property float y','property float z'] and lines[7:]==['property list uchar int vertex_indices','end_header'],'mesh_layout')
    n=int(lines[2].removeprefix('element vertex '));f=int(lines[6].removeprefix('element face '))
    require(0<n<=80000 and 0<f<=160000 and len(b)==end+n*12+f*13,'mesh_size')
    vertices=tuple(struct.iter_unpack('<fff',b[end:end+n*12]));faces=tuple(struct.iter_unpack('<Biii',b[end+n*12:]))
    require(all(math.isfinite(x) for p in vertices for x in p),'mesh_finite')
    require(all(a==3 and 0<=min(i,j,k)<=max(i,j,k)<n for a,i,j,k in faces),'mesh_faces')
    return vertices,tuple((i,j,k) for a,i,j,k in faces)
def project_scene_point(point,K):
    require(len(point)==3 and all(math.isfinite(x) for x in point),'point_finite')
    matrix(K,3,3);x,y,z=point;require(z<0,'point_behind_camera')
    return [(K[0][0]*x+K[0][1]*(-y))/(-z)+K[0][2],(K[1][0]*x+K[1][1]*(-y))/(-z)+K[1][2]]
def describe(ev,resources):
    require(set(ev)==set(EVIDENCE),'evidence_roles');require(set(resources)==set(EVIDENCE+ASSETS),'resource_roles')
    a,s,g,r,rg,o,f=[ev[n] for n in EVIDENCE]
    case=a['case_id'];hand=a['selected_hand_id']
    require(all(x['case_id']==case and x['selected_hand_id']==hand for x in ev.values()),'case_or_hand_mismatch')
    require(all(x['full_parent_acceptance'] is False for x in ev.values()),'evidence_admission')
    require(a['frame']==s['frame']==r['frame']==FRAME and a['units']==s['units']==r['units']==o['units']==UNITS,'evidence_frame')
    require(o['camera_frame']=='x_right_y_down_z_forward' and o['ply_frame']=='x_right_y_up_z_backward','observation_frame')
    require(a['selected_candidate'] is s['selected_candidate'] is g['selected_candidate'] is r['selected_candidate'] is rg['selected_candidate'] is None,'evidence_selection')
    require(a['accepted_scale'] is s['accepted_scale'] is g['accepted_scale'] is r['accepted_scale'] is rg['accepted_scale'] is None,'evidence_scale')
    pin=lambda name:{k:resources[name][k] for k in ['bytes','sha256']}
    require(rg['audit_binding']==pin('refinement') and rg['candidate_binding']==pin('hand_minimum_scale_refined'),'refinement_gate_binding')
    require(rg['pipeline_admissible'] is False and rg['blockers']==BLOCKERS and rg['collision_gate']=='clear_surface_separation_only','refinement_gate')
    require(a['object_mesh_binding']==pin('object') and o['image_binding']==pin('scene_rgb'),'scene_object_binding')
    require(a['input_bindings']['prior/saved/original_rgb.png']==pin('original_rgb') and a['input_bindings']['prior/input/hand_only.pgm']==pin('hand_mask') and a['input_bindings']['prior/input/object_only.pgm']==pin('object_mask'),'image_mask_bindings')
    require(o['input_bindings']['input/ambiguous_overlap.pgm']==pin('overlap_mask'),'overlap_binding')
    require(r['artifact_bindings']['refinement/hand_candidate.ply']==pin('hand_minimum_scale_refined'),'refined_mesh_binding')
    require([x['id'] for x in a['candidates']]==[x['id'] for x in g['candidates']]==[x['id'] for x in s['candidates']]==IDS[:3],'candidate_ids')
    candidates=[]
    for c,gate,surface in zip(a['candidates'],g['candidates'],s['candidates']):
        require(c['accepted'] is False and gate['pipeline_admissible'] is False,'candidate_admission')
        require(c['hand_mesh_binding']==pin('hand_'+c['id']),'hand_binding')
        expected=BLOCKERS+(['transverse_mesh_crossing'] if gate['surface_crossing_observed'] else [])
        require(gate['blockers']==expected,'candidate_blockers')
        require(gate['collision_gate']==('blocked_transverse_crossing' if gate['surface_crossing_observed'] else 'clear_surface_separation_only'),'candidate_collision')
        candidates.append(dict(id=c['id'],hand_asset='hand_'+c['id'],source_candidate=c['id'],source_stage='Q9n6Ew3P',
            conditional_scale=c['source_hypothesis']['conditional_scale'],source_to_scene_provenance_only=c['hand_transform'],
            reprojection=c['hand_reprojection'],unsigned_surface_gap=surface['mesh_surface_gap'],
            collision_gate=gate['collision_gate'],blockers=expected,accepted=False,pipeline_admissible=False))
    require(r['branch']['id']==IDS[3] and r['branch']['source_id']=='minimum_scale' and r['accepted'] is False and r['final_surface']['near_pairs']==0,'refined_candidate')
    candidates.append(dict(id=IDS[3],hand_asset='hand_'+IDS[3],source_candidate='minimum_scale',source_stage='T4r9Hz6T',
        conditional_scale=r['refined_scale'],source_to_scene_provenance_only=r['hand_transform'],reprojection=r['hand_reprojection'],
        unsigned_surface_gap=r['final_surface']['gap'],collision_gate=rg['collision_gate'],blockers=BLOCKERS,accepted=False,pipeline_admissible=False))
    for c in candidates:
        matrix(c['source_to_scene_provenance_only'],4,4)
        require(type(c['conditional_scale']) in (int,float) and math.isfinite(c['conditional_scale']) and c['conditional_scale']>0,'candidate_scale')
        require(math.isfinite(c['unsigned_surface_gap']) and c['unsigned_surface_gap']>=0,'surface_gap')
    K=a['camera']['K_integer_pixel_centers'];matrix(K,3,3)
    require(a['camera']['intrinsics_normalized']==o['intrinsics_normalized']==f['camera']['intrinsics_normalized'],'camera_mismatch')
    require(K==[[o['intrinsics_normalized'][0][0]*512,0,255.5],[0,o['intrinsics_normalized'][1][1]*512,255.5],[0,0,1]],'camera_pixel_convention')
    return dict(schema='tracehoi.DiagnosticSceneBundle.v1',case_id=case,selected_hand_id=hand,
        geometry_state='scene_coordinates_already_transformed',scene_frame=FRAME,camera_frame='x_right_y_down_z_forward',
        scene_to_camera=TO_CAMERA,mesh_model_matrix=IDENTITY,units=UNITS,image_size=[512,512],camera_K=K,
        resources=resources,object_asset='object',object_source_to_scene_provenance_only=f['object_fit']['transform_source_to_fresh_scene'],
        candidates=candidates,selected_candidate=None,accepted_scale=None,placement_ready=False,pipeline_placement_committed=False,
        full_parent_acceptance=False,scale_identified=False,physical_contact_verified=False,mask_review_required=True,
        limitations=['Meshes already contain their scene transforms; do not apply provenance transforms again.',
            'All candidates are diagnostic. Surface separation does not establish placement or physical contact.',
            'Scale bounds are sensitivity bounds, not a confidence interval. Mask and learned scene scale are unverified.'])
def inspect_bundle(manifest_path,expected_sha256,expected_case_id):
    p=Path(manifest_path).absolute();b=regular(p,1024**2)
    require(isinstance(expected_sha256,str) and re.fullmatch('[0-9a-f]{64}',expected_sha256),'expected_manifest_digest')
    require(binding(b)['sha256']==expected_sha256,'manifest_binding');m=parse(b)
    require(m.get('schema')=='tracehoi.DiagnosticSceneBundle.v1' and m.get('case_id')==expected_case_id,'manifest_identity')
    require(set(m.get('resources',{}))==set(EVIDENCE+ASSETS),'resource_roles')
    require(len({x['path'] for x in m['resources'].values()})==len(m['resources']),'duplicate_resource_path')
    data={n:resource(p.parent,item) for n,item in m['resources'].items()}
    ev={n:parse(data[n]) for n in EVIDENCE}
    require(m==describe(ev,m['resources']),'scene_contract')
    for n in ['object']+['hand_'+i for i in IDS]:mesh(data[n])
    for n in ['original_rgb','scene_rgb']:
        require(data[n][:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[n][16:24])==(512,512),'image_dimensions')
    for n in ['hand_mask','object_mask','overlap_mask']:
        require(data[n].startswith(b'P5\n512 512\n255\n') and len(data[n])==262159,'mask_dimensions')
    require(not any(x and y for x,y in zip(data['hand_mask'][15:],data['object_mask'][15:])),'mask_overlap')
    return m,data
def load_candidate(manifest_path,*,expected_sha256,expected_case_id,candidate_id,purpose):
    require(purpose in ('diagnostic','placement'),'explicit_purpose_required')
    m,data=inspect_bundle(manifest_path,expected_sha256,expected_case_id)
    require(candidate_id in IDS,'unknown_candidate')
    c=next(x for x in m['candidates'] if x['id']==candidate_id)
    if purpose=='placement':raise ValueError('placement_blocked:'+','.join(c['blockers']))
    # Return immutable asset bytes, not lazily opened paths that could change.
    return dict(case_id=m['case_id'],candidate_id=candidate_id,purpose=purpose,accepted=False,
        frame=m['scene_frame'],camera_K=m['camera_K'],scene_to_camera=[row[:] for row in TO_CAMERA],
        hand_model_matrix=[r[:] for r in IDENTITY],object_model_matrix=[r[:] for r in IDENTITY],
        hand_mesh_bytes=data[c['hand_asset']],object_mesh_bytes=data['object'],diagnostics=c)
def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--sha256',required=True);p.add_argument('--case',required=True);p.add_argument('--candidate',choices=IDS,required=True);p.add_argument('--purpose',choices=['diagnostic','placement'],required=True)
    a=p.parse_args();r=load_candidate(a.manifest,expected_sha256=a.sha256,expected_case_id=a.case,candidate_id=a.candidate,purpose=a.purpose)
    r['hand_mesh_binding']=binding(r.pop('hand_mesh_bytes'));r['object_mesh_binding']=binding(r.pop('object_mesh_bytes'));print(encode(r).decode(),end='')
if __name__=='__main__':main()

