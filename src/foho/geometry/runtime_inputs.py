"""Fresh-scene CPU data preparation for the opt-in joint-flow handoff.

No native imports or model execution. Numeric files require an explicit runtime
adapter; they are not silently passed to the legacy pickle-based loader.
"""
import ast,base64,hashlib,io,json,math,struct,zipfile
from pathlib import Path
PURPOSE='runtime_input_preparation'
SCHEMA='tracehoi.RuntimeInputs.v1'
def require(ok,msg):
    if not ok:raise ValueError(msg)
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def enc(o):return (json.dumps(o,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def finite(v):return type(v) in (int,float) and math.isfinite(v)
def matrix(m,r,c):return isinstance(m,list) and len(m)==r and all(isinstance(v,list) and len(v)==c and all(finite(x) for x in v) for v in m)
def pgm(raw,size):
    w,h=size;head=('P5\n%d %d\n255\n'%(w,h)).encode();require(raw.startswith(head) and len(raw)==len(head)+w*h,'mask_layout')
    b=raw[len(head):];require(set(b)<={0,255},'mask_not_binary');return [x>0 for x in b]
def pgm_bytes(mask,size):return ('P5\n%d %d\n255\n'%tuple(size)).encode()+bytes(255 if x else 0 for x in mask)
def numeric_npy(values,shape):
    require(math.prod(shape)==len(values) and all(finite(x) for x in values),'numeric_array')
    text=repr(dict(descr='<f4',fortran_order=False,shape=tuple(shape)))
    head=(text+' '*((64-(10+len(text)+1)%64)%64)+'\n').encode()
    return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(head))+head+struct.pack('<%df'%len(values),*values)
def transform(v,T):return [sum(T[i][j]*v[j] for j in range(3))+T[i][3] for i in range(3)]
def object_check(native,placed,T,reader):
    require(matrix(T,4,4) and T[3]==[0,0,0,1],'object_transform')
    A=[r[:3] for r in T[:3]];g=[[sum(A[k][i]*A[k][j] for k in range(3)) for j in range(3)] for i in range(3)];s2=sum(g[i][i] for i in range(3))/3
    det=sum(A[0][j]*(A[1][(j+1)%3]*A[2][(j+2)%3]-A[1][(j+2)%3]*A[2][(j+1)%3]) for j in range(3))
    require(s2>0 and det>0 and max(abs(g[i][j]-(s2 if i==j else 0)) for i in range(3) for j in range(3))<1e-8,'object_not_proper_similarity')
    v,f=reader.mesh(native);q,h=reader.mesh(placed);require(len(v)==len(q) and f==h,'object_topology')
    error=max(abs(x-y) for a,b in zip(v,q) for x,y in zip(transform(a,T),b));require(error<1e-6,'object_transform_mismatch')
    return dict(vertices=len(v),faces=len(f),max_coordinate_error=error,scale=math.sqrt(s2),all_vertices_checked=True)
def camera_check(camera,obs):
    K=camera['K'];w,h=camera['image_size'];require([w,h]==[512,512] and matrix(K,3,3) and K[2]==[0,0,1] and K[0][1]==K[1][0]==0 and K[0][0]>0 and K[1][1]>0,'camera_matrix')
    require(camera['camera_frame']=='x_right_y_down_z_forward' and camera['scene_frame']=='N7_PLY_x_right_y_up_z_backward','camera_frame')
    kn=obs['intrinsics_normalized'];expected=[[kn[0][0]*w,0,kn[0][2]*w-.5],[0,kn[1][1]*h,kn[1][2]*h-.5],[0,0,1]]
    require(max(abs(K[i][j]-expected[i][j]) for i in range(3) for j in range(3))<1e-6,'fresh_camera_mismatch')
    require(all(obs[k] is False for k in ['prior_scene_reused','prior_camera_reused','prior_alignment_transforms_reused']),'old_scene_reuse')
    return dict(K_integer_pixel_centers=K,image_size_wh=[w,h],scene_to_opencv=[[1,0,0],[0,-1,0],[0,0,-1]],pixel_centers='integer_xy',renderer_adapter_verified=False,
        renderer_requirement='Prove transform_points_screen agrees with these integer-center pixels before native execution; do not copy a legacy camera.')
def scene_mesh(points,valid,labels,size,max_relative_jump=.02):
    w,h=size;require(len(points)==3*w*h and len(valid)==len(labels)==w*h,'scene_shape')
    ids=[i for i in range(w*h) if valid[i] and labels[i] in (1,2)];lookup={i:j for j,i in enumerate(ids)}
    vertices=[];max_projection_error=0
    for i in ids:
        p=points[i*3:i*3+3];require(all(finite(x) for x in p) and p[2]>0,'scene_point');vertices.append([p[0],-p[1],-p[2]])
    faces=[];rejected_label=0;rejected_depth=0
    for y in range(h-1):
        for x in range(w-1):
            a=y*w+x;b=a+1;c=a+w;d=c+1
            for tri in [(a,c,b),(b,c,d)]:
                if not all(i in lookup for i in tri):continue
                if len({labels[i] for i in tri})!=1:rejected_label+=1;continue
                z=[points[3*i+2] for i in tri]
                if max(z)-min(z)>max_relative_jump*min(z):rejected_depth+=1;continue
                faces.append([lookup[i] for i in tri])
    require(bool(faces),'empty_scene_surface')
    return vertices,faces,dict(vertices=len(vertices),triangles=len(faces),excluded_label_seams=rejected_label,excluded_depth_jumps=rejected_depth,max_relative_depth_jump=max_relative_jump,
        construction='two fixed triangles per pixel cell; valid same-class support only; winding toward camera',surface_is_observation_proxy=True,closed_surface=False,renderer_verified=False),ids

def read_sources(folder,sha,reader):
    p=Path(folder);raw=reader.regular(p/'inputs.json',1024**2);require(pin(raw)['sha256']==sha,'source_receipt_hash');m=json.loads(raw)
    require(m['schema']=='tracehoi.RuntimeInputSources.v1','source_schema');files={}
    for n,b in m['files'].items():
        require(Path(n).name==n,'source_path');v=reader.regular(p/n,16*1024**2);require(pin(v)==b,'source_binding:'+n);files[n]=v
    required={'handoff.json','handoff_files.json','centered_state.json','native_hand.ply','hand_initial.ply','object.ply','object_native.ply','scene.html','prediction.json','target.json','request.json','camera.json','maps.npz','membership.npz','image.png','fit.json','observation.json','hand_mask.pgm','object_mask.pgm','overlap_mask.pgm','initialization.json','optimizer_input.json'}
    require(set(files)==required,'source_inventory');return m,files

def build(folder,sha,reader,visual,*,purpose):
    require(purpose==PURPOSE,'runtime_inputs_purpose_required');source,f=read_sources(folder,sha,reader)
    handoff=json.loads(f['handoff.json']);hm=json.loads(f['handoff_files.json'])['members'];fit=json.loads(f['fit.json']);obs=json.loads(f['observation.json']);cam=json.loads(f['camera.json']);pred=json.loads(f['prediction.json']);req=json.loads(f['request.json']);target=json.loads(f['target.json'])
    require(handoff['native_handoff_complete'] and handoff['initialization_ready'] and not handoff['contact_terms_used'] and not handoff['rectified_flow_executed'],'handoff_scope')
    for n in ['handoff.json','centered_state.json','native_hand.ply','hand_initial.ply','object.ply','scene.html','initialization.json','optimizer_input.json','image.png']:require(pin(f[n])==hm[n],'handoff_member:'+n)
    for name,key in [('object_native.ply','saved/object_native.ply'),('maps.npz','scene/maps.npz'),('membership.npz','scene/membership.npz'),('observation.json','scene/observation.json'),('prediction.json','saved/hand/prediction.json'),('target.json','saved/target/target.json'),('image.png','saved/original_rgb.png')]:require(pin(f[name])==fit['input_bindings'][key],'fresh_fit_binding:'+name)
    for name,key in [('hand_mask.pgm','input/hand_only.pgm'),('object_mask.pgm','input/object_only.pgm'),('overlap_mask.pgm','input/ambiguous_overlap.pgm')]:require(pin(f[name])==obs['input_bindings'][key],'fresh_mask_binding:'+name)
    require(cam['source_observation_binding']==pin(f['observation.json']),'camera_observation')
    case=handoff['case_id'];require(all(j['case_id']==case for j in [fit,obs,pred,req,target]),'case_identity')
    require(pred['selected_hand_id']==req['selected_hand_id']==target['selected_hand_id']==obs['selected_hand_id'],'selected_hand_identity')
    require(pred['request_binding']==pin(f['request.json']) and req['image_binding']==target['image_binding']==pin(f['image.png']),'guidance_image')
    require(pred['joint_order']=='OpenPose21' and pred['joint_map_21']==list(range(21)) and pred['canonical_is_right'] and not pred['pixels_mirrored'] and req['right']==[1],'guidance_joint_order')
    xy=pred['predicted_keypoints_crop'];require(matrix(xy,21,2) and all(0<=v<512 for p in xy for v in p),'guidance_points')
    require(fit['object_fit']['geometry_frame']==cam['scene_frame'] and not fit['object_fit']['old_transform_reused'],'object_frame')
    T=fit['object_fit']['transform_source_to_fresh_scene'];object_audit=object_check(f['object_native.ply'],f['object.ply'],T,reader);camera=camera_check(cam,obs)
    size=cam['image_size'];w,h=size;hand=pgm(f['hand_mask.pgm'],size);obj=pgm(f['object_mask.pgm'],size);overlap=pgm(f['overlap_mask.pgm'],size)
    require(not any(a+b+c>1 for a,b,c in zip(hand,obj,overlap)),'support_masks_overlap')
    labels=[1 if a else 2 if b else 3 if c else 0 for a,b,c in zip(hand,obj,overlap)]
    maps=visual.arrays(f['maps.npz'],{'points_camera.npy':('<f4',[h,w,3]),'depth.npy':('<f4',[h,w]),'normal_camera.npy':('<f4',[h,w,3]),'valid.npy':('|b1',[h,w]),'intrinsics_normalized.npy':('<f4',[3,3])})
    valid=maps['valid.npy'];points=maps['points_camera.npy'];require(maps['intrinsics_normalized.npy']==[x for row in obs['intrinsics_normalized'] for x in row],'map_camera')
    with zipfile.ZipFile(io.BytesIO(f['membership.npz'])) as z:
        require(len(z.namelist())==2 and set(z.namelist())=={'pixel_indices.npy','support_labels.npy'},'membership_inventory')
        n=obs['counts']['exported_points'];idx=visual.npy(z.read('pixel_indices.npy'),'<i8',[n]);lab=visual.npy(z.read('support_labels.npy'),'|u1',[n])
    expected=[i for i in range(w*h) if valid[i] and labels[i]];require(idx==expected and lab==[labels[i] for i in idx],'membership_mask_mismatch')
    K=cam['K'];errors=[];depth_errors=[]
    for i in idx:
        p=points[3*i:3*i+3];require(all(finite(v) for v in p) and p[2]>0,'invalid_observed_point')
        errors.extend([abs(K[0][0]*p[0]/p[2]+K[0][2]-i%w),abs(K[1][1]*p[1]/p[2]+K[1][2]-i//w)]);depth_errors.append(abs(p[2]-maps['depth.npy'][i]))
    require(max(errors)<.001 and max(depth_errors)<1e-6,'fresh_map_projection')
    sv,sf,sa,ids=scene_mesh(points,valid,labels,size)
    counts=dict(hand=sum(a and v for a,v in zip(hand,valid)),object=sum(a and v for a,v in zip(obj,valid)),ambiguous=sum(a and v for a,v in zip(overlap,valid)))
    require(counts==dict(hand=obs['counts']['hand_only'],object=obs['counts']['object_only'],ambiguous=obs['counts']['ambiguous_overlap']),'support_counts')
    guidance=dict(schema='tracehoi.NumericHaMeRGuidance.v1',case_id=case,selected_hand_id=pred['selected_hand_id'],frame='original_unmasked_crop_integer_pixels_xy',joint_order='OpenPose21',mano_2d_kps=xy,source='saved_HaMeR_prediction',independent_target=False,source_prediction_binding=pin(f['prediction.json']),image_binding=pin(f['image.png']),loader='numeric_npy_allow_pickle_false',legacy_item_loader_compatible=False)
    files={n:f[n] for n in ['native_hand.ply','hand_initial.ply','object.ply','object_native.ply','centered_state.json','image.png','scene.html','initialization.json','optimizer_input.json']}
    files.update({'hand_mask.pgm':f['hand_mask.pgm'],'object_mask.pgm':f['object_mask.pgm'],'overlap_mask.pgm':f['overlap_mask.pgm'],
        'hand_valid.pgm':pgm_bytes([a and v for a,v in zip(hand,valid)],size),'object_valid.pgm':pgm_bytes([a and v for a,v in zip(obj,valid)],size),
        'scene_observed.ply':visual.ply(sv,sf),'h2m.npy':numeric_npy([x for row in T for x in row],[4,4]),'hamer_keypoints.npy':numeric_npy([x for row in xy for x in row],[21,2]),'guidance.json':enc(guidance),'camera.json':enc(camera)})
    report=dict(schema=SCHEMA,case_id=case,runtime_inputs_complete=True,initialization_ready=True,contact_terms_used=False,model_calls=0,service_submissions=0,native_execution_verified=False,backend_execution_ready=False,rectified_flow_executed=False,placement_ready=False,full_parent_acceptance=False,mask_accuracy_verified=False,reference_status='awaiting_reference',source_receipt=pin((Path(folder)/'inputs.json').read_bytes()),camera=camera,object_transform=object_audit,support=counts,scene_surface=sa,max_map_projection_error_px=max(errors),max_map_depth_error=max(depth_errors),original_masks_modified=False,object_transform_changed=False,hand_pose_changed=False,
      next_action='verify_native_renderer_and_numeric_asset_adapter',runtime_pending=['renderer_pixel_center_and_normal_convention','numeric_HaMeR_loader_adapter','object_conditioning_image_and_latent_initialization_policy','native_tensor_model_and_asset_preflight','bounded_joint_rectified_flow_execution'],
      artifact_bindings={n:pin(b) for n,b in files.items()},notes=['Scene surface is a partial depth-observation proxy, not a closed physical mesh.','Shared hand/object boundary pixels remain excluded. Masks are preserved; validity-intersected copies are separately named.','HaMeR guidance is a model prediction, not independent ground truth.','No contact score adjusts or rejects the visual initial pose.','Fresh object transform is applied only to native Hunyuan object coordinates. Hand uses its separate saved centered state.'])
    files['runtime.json']=enc(report);files['index.html']=viewer(report,hand,obj,overlap,f['image.png'],xy,req['boxes'][0]);files['README.md']=b'Open index.html. Fresh CPU data only. Native execution remains pending. Preserve source receipts, original masks, human review and terminal logs. Numeric HaMeR guidance needs a loader adapter; never send it to the old .item() loader.\n'
    files['files.json']=enc(dict(schema='tracehoi.RuntimeInputFiles.v1',files={n:pin(b) for n,b in files.items()}));return report,files

def verify(folder,sha,source,source_sha,reader,visual,*,purpose):
    p=Path(folder);raw=reader.regular(p/'files.json',1024**2);require(pin(raw)['sha256']==sha,'output_receipt_hash');m=json.loads(raw)
    for n,b in m['files'].items():require(Path(n).name==n and pin(reader.regular(p/n,16*1024**2))==b,'output_changed:'+n)
    _,files=build(source,source_sha,reader,visual,purpose=purpose);require({n:reader.regular(p/n,16*1024**2) for n in files}==files,'output_recompute')
    return dict(verified=True,receipt_binding=pin(raw),runtime_inputs_complete=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)

def viewer(report,hand,obj,overlap,image,xy,box):
    data=dict(report=report,masks=[[i for i,x in enumerate(m) if x] for m in [hand,obj,overlap]],image='data:image/png;base64,'+base64.b64encode(image).decode(),xy=xy,box=box)
    page=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TraceHOI · Fresh runtime inputs</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101923;color:#edf4fa;font:15px system-ui}header,main{padding:24px 4vw}header{border-bottom:1px solid #3a4a5b}h1{font-size:32px;margin:10px 0}.tag{color:#70e4ce;letter-spacing:.12em;font-size:12px}p{color:#bacbdb;line-height:1.6;max-width:1050px}.cards,.views{display:grid;gap:16px;grid-template-columns:repeat(3,1fr)}.views{grid-template-columns:1fr 1fr;margin-top:20px}.card,.panel{background:#1a2939;border:1px solid #3a4a5b;border-radius:12px;padding:20px}.value{font-size:26px;color:#fff}small{color:#9bb4c8}canvas{width:100%;aspect-ratio:1;display:block;background:#0c141c}label{display:inline-block;margin:8px 12px 8px 0}input{vertical-align:middle}select,button{background:#253d53;color:#fff;border:1px solid #5b819d;padding:9px;border-radius:6px}a{color:#77e4df}pre{white-space:pre-wrap;font-size:13px;overflow-wrap:anywhere}iframe{width:100%;height:670px;border:0;margin-top:20px;border-radius:12px}.pending{color:#ffce85}.legend{font-size:13px}ul{line-height:1.8}@media(max-width:850px){.views,.cards{grid-template-columns:1fr}}</style>
<header><div class="tag">TRACEHOI / V6 / FRESH SCENE INPUTS</div><h1>One camera, one scene, explicit coordinates</h1><p>The visual initial hand pose stays fixed. These CPU-prepared inputs connect it to the fresh laptop scene. Contact belongs to the later joint rectified-flow stage. Native rendering and model execution are still pending.</p></header>
<main><div class="cards"><div class="card"><small>Object vertices checked</small><div class="value" id="verts"></div></div><div class="card"><small>Fresh point reprojection error</small><div class="value" id="err"></div></div><div class="card"><small>Contact terms in initialization</small><div class="value">0</div></div></div>
<div class="views"><section class="panel"><h2>Exact image and support</h2><canvas id="view" width="768" height="768" aria-label="Fresh hand and object support over the source image"></canvas><label><input id="hand" type="checkbox" checked>Hand</label><label><input id="obj" type="checkbox" checked>Laptop</label><label><input id="amb" type="checkbox" checked>Ambiguous boundary</label><label><input id="keypoints" type="checkbox" checked>HaMeR joints + box</label><label>Zoom <input id="zoom" type="range" min="1" max="3" step=".1" value="1"></label><p class="legend">Teal: hand-only. Blue: laptop-only. Amber: shared boundary, excluded from guidance. Pink: saved HaMeR keypoints and loose hand box. These are model predictions, not independent ground truth.</p></section>
<section class="panel"><h2>Inspect an input contract</h2><select id="topic" aria-label="Input contract"><option value="camera">Camera and pixel centers</option><option value="object_transform">Laptop transform</option><option value="scene_surface">Observed scene surface</option><option value="runtime_pending">Remaining native interfaces</option></select><pre id="detail"></pre><p class="pending">Data preparation complete · native execution pending</p><p>The scene mesh is a partial observation proxy. Triangles join neighboring valid pixels of the same class; depth discontinuities and the shared hand/object boundary are excluded. It is not a closed collision surface.</p><a href="runtime.json">All checks</a> · <a href="camera.json">Camera</a> · <a href="guidance.json">HaMeR guidance</a> · <a href="scene_observed.ply">Observed surface</a> · <a href="h2m.npy">Object transform</a></section></div>
<details class="panel" style="margin-top:20px"><summary>Preserved visual initial scene — open interactive view</summary><iframe src="scene.html" title="Preserved visual initial pose" loading="lazy"></iframe></details><p>Original masks and meshes are preserved. Numeric HaMeR data requires the next loader adapter; it cannot be passed to the legacy pickle-based loader. No native call, contact correction or placement acceptance occurs here.</p></main>
<script>const D=__DATA__,$=id=>document.getElementById(id);$('verts').textContent=D.report.object_transform.vertices.toLocaleString();$('err').textContent=D.report.max_map_projection_error_px.toExponential(2)+' px';const detail=()=>$('detail').textContent=JSON.stringify(D.report[$('topic').value],null,2);$('topic').onchange=detail;detail();const im=new Image();im.src=D.image;const overlays=D.masks.map((ids,k)=>{const c=document.createElement('canvas');c.width=c.height=512;const x=c.getContext('2d'),p=x.createImageData(512,512),color=[[55,229,192,130],[74,155,255,110],[255,185,60,230]][k];ids.forEach(i=>p.data.set(color,i*4));x.putImageData(p,0,0);return c});function draw(){const c=$('view'),x=c.getContext('2d'),z=+$('zoom').value;x.clearRect(0,0,768,768);x.save();x.scale(1.5*z,1.5*z);if(z>1)x.translate(-280*(z-1)/z,-205*(z-1)/z);x.drawImage(im,0,0,512,512);['hand','obj','amb'].forEach((n,i)=>{if($(n).checked)x.drawImage(overlays[i],0,0)});if($('keypoints').checked){x.strokeStyle='#ff8ac6';x.fillStyle='#ff8ac6';x.lineWidth=1/z;let b=D.box;x.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);D.xy.forEach(p=>{x.beginPath();x.arc(p[0],p[1],1.8/z,0,7);x.fill()})}x.restore()}im.onload=draw;['hand','obj','amb','keypoints','zoom'].forEach(n=>$(n).oninput=draw);</script></html>'''
    return page.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c')).encode()
