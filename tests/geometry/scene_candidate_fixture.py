"""Synthetic contract fixture; no model data or original RGB is embedded."""
import struct
import scene_candidates as sc

def build():
    # A triangle in front of the camera. Four branches use separate asset roles.
    ply=(b'ply\nformat binary_little_endian 1.0\nelement vertex 3\n'
         b'property float x\nproperty float y\nproperty float z\nelement face 1\n'
         b'property list uchar int vertex_indices\nend_header\n')
    ply+=struct.pack('<9f',0,0,-2,.1,0,-2,0,.1,-2)+struct.pack('<Biii',3,0,1,2)
    # Reader validates PNG dimensions, not decoding; deliberately a header fixture.
    png=b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\x0dIHDR'+struct.pack('>II',512,512)
    pgm=b'P5\n512 512\n255\n'+bytes(512*512)
    data={'object':ply,'original_rgb':png,'scene_rgb':png,'hand_mask':pgm,'object_mask':pgm,'overlap_mask':pgm}
    for i in sc.IDS:data['hand_'+i]=ply
    resources={}
    for n,b in data.items():
        suffix='ply' if n=='object' or n.startswith('hand_') and not n.endswith('mask') else 'pgm' if n.endswith('mask') else 'png'
        resources[n]=dict(path='assets/'+n+'.'+suffix,**sc.binding(b))
    pin=lambda n:sc.binding(data[n])
    base=dict(case_id='alapuse02v3n60',selected_hand_id='synthetic-hand',full_parent_acceptance=False)
    camera=dict(intrinsics_normalized=[[3,0,.5],[0,3,.5],[0,0,1]],K_integer_pixel_centers=[[1536,0,255.5],[0,1536,255.5],[0,0,1]])
    common=dict(base,frame=sc.FRAME,units=sc.UNITS,selected_candidate=None,accepted_scale=None)
    a=dict(common,object_mesh_binding=pin('object'),camera=camera,
           input_bindings={'prior/saved/original_rgb.png':pin('original_rgb'),'prior/input/hand_only.pgm':pin('hand_mask'),'prior/input/object_only.pgm':pin('object_mask')},candidates=[])
    s=dict(common,candidates=[]);g=dict(common,candidates=[])
    for i,cid in enumerate(sc.IDS[:3]):
        a['candidates'].append(dict(id=cid,accepted=False,hand_mesh_binding=pin('hand_'+cid),
            source_hypothesis=dict(conditional_scale=2+i*.1),hand_transform=[[2,0,0,.1],[0,2,0,0],[0,0,2,0],[0,0,0,1]],hand_reprojection=dict(median=6.0)))
        s['candidates'].append(dict(id=cid,mesh_surface_gap=.01 if i!=1 else 0))
        g['candidates'].append(dict(id=cid,pipeline_admissible=False,surface_crossing_observed=i==1,
            blockers=sc.BLOCKERS+(['transverse_mesh_crossing'] if i==1 else []),
            collision_gate='blocked_transverse_crossing' if i==1 else 'clear_surface_separation_only'))
    r=dict(common,branch=dict(id=sc.IDS[3],source_id='minimum_scale'),accepted=False,
           final_surface=dict(near_pairs=0,gap=.0001),refined_scale=2.2,hand_transform=sc.IDENTITY,hand_reprojection=dict(median=7.0),
           artifact_bindings={'refinement/hand_candidate.ply':pin('hand_minimum_scale_refined')})
    rg=dict(common,audit_binding=sc.binding(sc.encode(r)),candidate_binding=pin('hand_minimum_scale_refined'),
            pipeline_admissible=False,blockers=sc.BLOCKERS,collision_gate='clear_surface_separation_only')
    o=dict(base,units=sc.UNITS,camera_frame='x_right_y_down_z_forward',ply_frame='x_right_y_up_z_backward',
           image_binding=pin('scene_rgb'),intrinsics_normalized=camera['intrinsics_normalized'],
           input_bindings={'input/ambiguous_overlap.pgm':pin('overlap_mask')})
    f=dict(base,camera=camera,object_fit=dict(transform_source_to_fresh_scene=sc.IDENTITY))
    evidence=dict(assembly=a,surface=s,collision=g,refinement=r,refined_gate=rg,observation=o,fit=f)
    for n,obj in evidence.items():
        data[n]=sc.encode(obj);resources[n]=dict(path='evidence/'+n+'.json',**sc.binding(data[n]))
    m=sc.describe(evidence,resources)
    files={'handoff/'+resources[n]['path']:b for n,b in data.items()}
    files['handoff/scene.json']=sc.encode(m)
    return m,files
