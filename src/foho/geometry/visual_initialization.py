"""CPU visual initial pose. Contact belongs to a later optimizer, not this objective."""
import ast,base64,hashlib,io,json,math,statistics,struct,zipfile
from pathlib import Path
PURPOSE='visual_initialization'
SCHEMA='tracehoi.VisualInitialization.v1'

def require(v,msg):
 if not v:raise ValueError(msg)
def encode(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def vector(x,n):return isinstance(x,list) and len(x)==n and all(finite(v) for v in x)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def mv(a,x):return [dot(r,x) for r in a]
def add(a,b):return [x+y for x,y in zip(a,b)]
def norm(a):return math.sqrt(dot(a,a))
def median(a):require(len(a)>0,'empty_support');return statistics.median(a)
def quantile(a,q):
 a=sorted(a);i=(len(a)-1)*q;l=int(i);return a[l]+(a[min(l+1,len(a)-1)]-a[l])*(i-l)
def solve(A,b):
 a=[list(r)+[v] for r,v in zip(A,b)];n=len(b)
 for i in range(n):
  k=max(range(i,n),key=lambda k:abs(a[k][i]));require(abs(a[k][i])>1e-14,'singular_system');a[i],a[k]=a[k],a[i];d=a[i][i];a[i]=[x/d for x in a[i]]
  for k in range(n):
   if k!=i:
    d=a[k][i];a[k]=[x-d*y for x,y in zip(a[k],a[i])]
 return [r[-1] for r in a]
def rodrigues(v):
 t=norm(v)
 if t<1e-14:return [[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
 x,y,z=[a/t for a in v];K=[[0,-z,y],[z,0,-x],[-y,x,0]];s=math.sin(t);c=1-math.cos(t)
 return [[float(i==j)+s*K[i][j]+c*sum(K[i][k]*K[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def project(points,K):
 require(all(vector(p,3) and p[2]>1e-5 for p in points),'nonpositive_camera_depth')
 return [[K[0][0]*p[0]/p[2]+K[0][2],K[1][1]*p[1]/p[2]+K[1][2]] for p in points]
def weight_targets(xy,conf):
 return [c/sum(q==p for q in xy) for p,c in zip(xy,conf)]
def objective(p,xyz,xy,weights,K,box):
 R=rodrigues(p[:3]);pts=[add(mv(R,x),p[3:]) for x in xyz];uv=project(pts,K);r=[];w=[];cost=0.
 for a,b,wt in zip(uv,xy,weights):
  e=[a[j]-b[j] for j in range(2)];d=norm(e);cost+=wt*(d*d if d<=4 else 8*d-16);r.extend(e);w.extend([wt*min(1.,4/max(d,1e-12))]*2)
 # The selected box is a loose hand ROI, not a silhouette to stretch the hand into.
 for u,v in uv:
  for d in [min(0,u-box[0]),max(0,u-box[2]),min(0,v-box[1]),max(0,v-box[3])]:r.append(d);w.append(.25);cost+=.25*d*d
 # HaMeR articulation and native orientation are the initialization prior.
 for v in p[:3]:r.append(v);w.append(4.);cost+=4*v*v
 return cost,r,w,uv,pts

def fit_camera(joints,xy,conf,K,box):
 require(len(joints)==len(xy)==len(conf)==21,'joint_count')
 require(all(vector(p,3) for p in joints) and all(vector(p,2) for p in xy),'joint_values')
 require(all(finite(v) and 0<v<=1 for v in conf),'confidence')
 require(vector(box,4) and box[0]<box[2] and box[1]<box[3],'box')
 ctr=[sum(p[j] for p in joints)/len(joints) for j in range(3)];xyz=[[p[j]-ctr[j] for j in range(3)] for p in joints];weights=weight_targets(xy,conf)
 starts=[[0.,0.,0.]]+[[s*.35 if j==axis else 0. for j in range(3)] for axis in range(3) for s in [-1,1]];best=None
 for rv in starts:
  rotated=[mv(rodrigues(rv),x) for x in xyz];A=[];b=[]
  for (u,v),x in zip(xy,rotated):
   a=(u-K[0][2])/K[0][0];c=(v-K[1][2])/K[1][1];A.extend([[1,0,-a],[0,1,-c]]);b.extend([a*x[2]-x[0],c*x[2]-x[1]])
  t=solve([[sum(r[i]*r[j] for r in A) for j in range(3)] for i in range(3)],[sum(r[i]*v for r,v in zip(A,b)) for i in range(3)])
  p=rv+t;damping=.001;steps=0
  try:cur=objective(p,xyz,xy,weights,K,box)
  except ValueError:continue
  for iteration in range(80):
   J=[]
   for j in range(6):
    eps=1e-6*max(1.,abs(p[j]));pp=p[:];pp[j]+=eps;r2=objective(pp,xyz,xy,weights,K,box)[1];J.append([(a-b)/eps for a,b in zip(r2,cur[1])])
   H=[[sum(w*a*b for w,a,b in zip(cur[2],J[i],J[j])) for j in range(6)] for i in range(6)];g=[sum(w*a*b for w,a,b in zip(cur[2],J[i],cur[1])) for i in range(6)]
   for i in range(6):H[i][i]+=damping*max(H[i][i],1e-8)
   delta=solve(H,[-v for v in g]);trial=[a+b for a,b in zip(p,delta)]
   try:new=objective(trial,xyz,xy,weights,K,box)
   except ValueError:new=None
   if new and new[0]<cur[0]:
    improvement=cur[0]-new[0];p=trial;cur=new;steps+=1;damping=max(1e-9,damping/3)
    if improvement<1e-9 or norm(delta)<1e-9:break
   else:damping=min(1e12,damping*5)
  if best is None or cur[0]<best[0]:best=(cur[0],p,cur,steps)
 require(best is not None,'camera_fit_failed');cost,p,cur,steps=best;R=rodrigues(p[:3]);t=[p[3+j]-mv(R,ctr)[j] for j in range(3)]
 errors=[norm([a-b for a,b in zip(u,v)]) for u,v in zip(cur[3],xy)]
 return dict(rotation=R,translation=t,rotation_vector=p[:3],projected_joints=cur[3],cost=cost,accepted_steps=steps,starts=len(starts),joint_median_px=median(errors),joint_rmse_px=math.sqrt(sum(x*x for x in errors)/21),joint_max_px=max(errors),duplicate_groups=[list(i for i,q in enumerate(xy) if q==v) for k,v in enumerate(xy) if xy.index(v)==k and xy.count(v)>1],weights=weights)

def npy(raw,descr,shape):
 require(raw[:8]==b'\x93NUMPY\x01\x00','npy_version');n=struct.unpack('<H',raw[8:10])[0];require(n<4096,'npy_header')
 h=ast.literal_eval(raw[10:10+n].decode('ascii'));require(h==dict(descr=descr,fortran_order=False,shape=tuple(shape)),'npy_layout')
 fmt={'<f4':'f','<i8':'q','|u1':'B','|b1':'?'}[descr];count=math.prod(shape);require(len(raw)==10+n+count*struct.calcsize('<'+fmt),'npy_length')
 return list(struct.unpack('<'+str(count)+fmt,raw[10+n:]))
def arrays(raw,names):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  require(len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(names),'npz_members');require(sum(i.file_size for i in z.infolist())<10*1024**2,'npz_bound');require(z.testzip() is None,'npz_crc')
  return {n:npy(z.read(n),*spec) for n,spec in names.items()}
def depth_observations(maps,membership,size):
 w,h=size;d=arrays(maps,{'points_camera.npy':('<f4',[h,w,3]),'depth.npy':('<f4',[h,w]),'normal_camera.npy':('<f4',[h,w,3]),'valid.npy':('|b1',[h,w]),'intrinsics_normalized.npy':('<f4',[3,3])})
 with zipfile.ZipFile(io.BytesIO(membership)) as z:
  require(set(z.namelist())=={'pixel_indices.npy','support_labels.npy'} and len(z.namelist())==2 and sum(i.file_size for i in z.infolist())<2*1024**2,'membership_inventory')
  raw=z.read('pixel_indices.npy');n=struct.unpack('<H',raw[8:10])[0];shape=ast.literal_eval(raw[10:10+n].decode())['shape'];require(len(shape)==1 and 0<shape[0]<=w*h,'membership_shape');idx=npy(raw,'<i8',shape);lab=npy(z.read('support_labels.npy'),'|u1',shape)
 require(len(set(idx))==len(idx) and all(0<=i<w*h for i in idx) and set(lab)<={1,2,3},'membership_indices')
 hand={i:d['depth.npy'][i] for i,l in zip(idx,lab) if l==1 and d['valid.npy'][i] and finite(d['depth.npy'][i]) and d['depth.npy'][i]>0}
 require(len(hand)>=100,'insufficient_hand_depth');return hand,d['intrinsics_normalized.npy']

def raster_depth(vertices,faces,K,size):
 w,h=size;uv=project(vertices,K);out={}
 for face in faces:
  a,b,c=[uv[i] for i in face];z=[vertices[i][2] for i in face];den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-12:continue
  x0=max(0,math.ceil(min(a[0],b[0],c[0])));x1=min(w-1,math.floor(max(a[0],b[0],c[0])));y0=max(0,math.ceil(min(a[1],b[1],c[1])));y1=min(h-1,math.floor(max(a[1],b[1],c[1])))
  for y in range(y0,y1+1):
   for x in range(x0,x1+1):
    p=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;q=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;r=1-p-q
    if min(p,q,r)<-1e-10:continue
    depth=1/(p/z[0]+q/z[1]+r/z[2]);i=y*w+x
    if i not in out or depth<out[i]:out[i]=depth
 return out

def scale_from_depth(rendered,observed,width):
 shared=sorted(set(rendered)&set(observed));require(len(shared)>=100,'insufficient_shared_depth');tiles={}
 for i in shared:
  ratio=observed[i]/rendered[i];require(finite(ratio) and ratio>0,'depth_ratio');tiles.setdefault((i%width//8,i//width//8),[]).append(ratio)
 tile_values=[median(v) for v in tiles.values() if len(v)>=3];require(len(tile_values)>=8,'insufficient_depth_tiles');s=median(tile_values)
 return dict(scale=s,shared_pixels=len(shared),tiles=len(tile_values),method='median_of_8px_tile_median_depth_ratios',tile_ratio_q10_q90=[quantile(tile_values,.1),quantile(tile_values,.9)],metric_scale_verified=False,confidence_interval=False)

def ply(vertices,faces):
 head=('ply\nformat binary_little_endian 1.0\nelement vertex '+str(len(vertices))+'\nproperty float x\nproperty float y\nproperty float z\nelement face '+str(len(faces))+'\nproperty list uchar int vertex_indices\nend_header\n').encode()
 return head+b''.join(struct.pack('<fff',*v) for v in vertices)+b''.join(struct.pack('<Biii',3,*f) for f in faces)
def read_inputs(folder,expected_sha):
 p=Path(folder);m=(p/'inputs.json').read_bytes();require(hashlib.sha256(m).hexdigest()==expected_sha,'input_receipt_hash');spec=json.loads(m);require(spec['schema']=='tracehoi.VisualInitializationInputs.v1','input_schema');files={}
 for n,b in spec['files'].items():
  require(Path(n).name==n and not (p/n).is_symlink(),'input_path');raw=(p/n).read_bytes();require(pin(raw)==b and len(raw)<=4*1024**2,'input_binding:'+n);files[n]=raw
 require(set(files)=={'prediction.json','target.json','request.json','maps.npz','membership.npz','camera.json','object.ply','image.png','human_review.json'},'visual_inventory')
 return spec,files

def build(folder,expected_sha,reader,*,purpose):
 require(purpose==PURPOSE,'visual_initialization_purpose_required');spec,f=read_inputs(folder,expected_sha)
 h=json.loads(f['prediction.json']);target=json.loads(f['target.json']);req=json.loads(f['request.json']);camera=json.loads(f['camera.json']);K=camera['K'];size=camera['image_size'];box=req['boxes'][0]
 require(camera['camera_frame']=='x_right_y_down_z_forward' and camera['scene_frame']=='N7_PLY_x_right_y_up_z_backward','camera_frame');require(size==[512,512] and len(K)==3 and all(vector(r,3) for r in K) and K[0][0]>0 and K[1][1]>0 and K[2]==[0,0,1] and K[0][1]==K[1][0]==0,'camera')
 require(h['schema']=='tracehoi.SelectedHandPrediction.v1' and target['schema']=='tracehoi.IndependentHandTarget.v1','prediction_schema')
 require(h['case_id']==target['case_id']==req['case_id']==spec['case_id'] and h['selected_hand_id']==target['selected_hand_id']==req['selected_hand_id'],'hand_identity')
 require(h['geometry_frame']=='hamer_model_camera_axes_before_camera_translation' and h['canonical_is_right'] is True and h['pixels_mirrored'] is False and target['handedness']=='right','hand_frame')
 require(h['request_binding']==pin(f['request.json']),'request_binding')
 require(h['joint_order']=='OpenPose21' and h['joint_map_21']==list(range(21)) and h['scene_placement_transform'] is None and not h['object_transform_applied'],'native_joint_contract')
 require(target['pixels_mirrored'] is False and req['pixels_mirrored'] is False and req['right']==[1] and req['batch_size']==1 and req['image_size']==size and req['image_kind']=='original_unmasked_crop','request_frame')
 require(target['image_binding']==req['image_binding']==pin(f['image.png']) and target['image_size_wh']==size and target['frame']=='original_unmasked_crop_pixels_xy','image_binding')
 require(target['visible']==[True]*21 and target['joint_order']=='openpose_hand_21_wrist_thumb_index_middle_ring_little','target_order')
 vertices=h['vertices'];faces=h['faces'];joints=h['joints'];require(len(vertices)==778 and len(faces)==1538 and all(vector(v,3) for v in vertices) and all(len(f)==3 and all(type(i)==int and 0<=i<778 for i in f) for f in faces),'native_geometry')
 fit=fit_camera(joints,target['xy'],target['confidence'],K,box);R=fit['rotation'];t=fit['translation'];unit=[add(mv(R,v),t) for v in vertices]
 observed,kn=depth_observations(f['maps.npz'],f['membership.npz'],size);require(abs(K[0][0]-kn[0]*size[0])<.001 and abs(K[1][1]-kn[4]*size[1])<.001,'depth_camera')
 gauge=scale_from_depth(raster_depth(unit,faces,K,size),observed,size[0]);scale=gauge['scale'];camera_vertices=[[scale*x for x in v] for v in unit];scene_vertices=[[v[0],-v[1],-v[2]] for v in camera_vertices];cj=[[scale*x for x in add(mv(R,v),t)] for v in joints];sj=[[v[0],-v[1],-v[2]] for v in cj]
 matrix=[[scale*(1 if i==0 else -1)*R[i][j] for j in range(3)]+[scale*(1 if i==0 else -1)*t[i]] for i in range(3)]+[[0,0,0,1]]
 ov,of=reader.mesh(f['object.ply']);ob=[[(min(v[j] for v in ov)+max(v[j] for v in ov))/2 for j in range(3)]][0];wrist=sj[0]
 out=dict(schema=SCHEMA,case_id=spec['case_id'],selected_hand_id=h['selected_hand_id'],initialization_ready=True,optimizer_handoff_ready=True,placement_ready=False,full_parent_acceptance=False,physical_contact_verified=False,scale_identified=False,mask_accuracy_verified=False,independent_reference_complete=False,model_calls=0,contact_terms_used=False,collision_terms_used=False,contact_queries=0,source_geometry_modified=False,object_transform_changed=False,articulation_changed=False,rectified_flow_executed=False,reference_status='awaiting_reference',source_inputs=pin((Path(folder)/'inputs.json').read_bytes()),fit=fit,depth_gauge=gauge,camera=camera,box_xyxy=box,box_semantics='loose selected-hand ROI; containment, not a tight silhouette target',source_to_scene=matrix,joints_scene=sj,relative_to_laptop=dict(object_bbox_center=ob,wrist_minus_object_bbox_center=[a-b for a,b in zip(wrist,ob)]),stage_policy=dict(initialization='visual cues, saved HaMeR geometry, selected hand box and learned scene depth',downstream='rectified-flow optimization may resolve contact, interpenetration and joint consistency',final_acceptance='requires later geometric and task validation'),limitations=['Single-image depth/scale remains ambiguous; scale is tied to learned MoGe depth, not metric calibration.','Independent 2D model targets are not human ground-truth masks.','No contact or collision score selects, adjusts or rejects this initial pose.','The original hand box includes slack; padded HaMeR crop size is not anatomical hand size.','This packet supplies optimizer inputs; no rectified-flow model or optimizer is executed.'])
 hand=ply(scene_vertices,faces);handoff=dict(schema='tracehoi.InitialPoseOptimizerInput.v1',purpose='optimizer_initialization_only',case_id=spec['case_id'],hand_mesh='hand_initial.ply',hand_binding=pin(hand),object_mesh='object.ply',object_binding=pin(f['object.ply']),geometry_state='already_in_scene_coordinates',mesh_model_matrix=[[int(i==j) for j in range(4)] for i in range(4)],camera=camera,source_to_scene_provenance_only=matrix,joints_scene=sj,native_mano_params=h['mano_params'],native_geometry_frame=h['geometry_frame'],native_model_transform_rule='Evaluate original native MANO parameters unchanged, then apply source_to_scene to native vertices. Do not apply it again to the exported scene mesh or substitute a new MANO root rotation without handling its root pivot.',native_prediction_binding=pin(f['prediction.json']),contact_resolved=False,contact_required_for_initialization=False,optimizer_backend='rectified_flow_not_implemented_here',optimizer_executed=False,final_placement_accepted=False,initialization_binding=pin(encode(out)))
 files={'initialization.json':encode(out),'optimizer_input.json':encode(handoff),'hand_initial.ply':hand,'object.ply':f['object.ply'],'image.png':f['image.png'],'README.md':b'CPU visual initializer. Open index.html. Meshes already contain their transforms. optimizer_input.json is an initial state, not final placement. Contact and collision are deferred to later rectified-flow optimization. Retain inputs, human records and evidence.\n'}
 files['index.html']=viewer(out,vertices,faces,ov,of,f['image.png'],target['xy']);files['files.json']=encode(dict(schema='tracehoi.VisualInitializationFiles.v1',files={n:pin(b) for n,b in files.items()}));return out,files

def verify(folder,sha,inputs,input_sha,reader,*,purpose):
 p=Path(folder);raw=(p/'files.json').read_bytes();require(pin(raw)['sha256']==sha,'output_receipt_hash');m=json.loads(raw)
 for n,b in m['files'].items():require(Path(n).name==n and not (p/n).is_symlink() and pin((p/n).read_bytes())==b,'output_changed:'+n)
 _,files=build(inputs,input_sha,reader,purpose=purpose);require({n:(p/n).read_bytes() for n in files}==files,'output_recompute');return dict(verified=True,receipt_binding=pin(raw),initialization_ready=True,optimizer_handoff_ready=True,placement_ready=False)

# VIEWER appended below.
def viewer(report,native,faces,ov,of,rgb,target):
 R=report['fit']['rotation'];t=report['fit']['translation'];s=report['depth_gauge']['scale'];hand=[[s*x for x in add(mv(R,v),t)] for v in native];obj=[[v[0],-v[1],-v[2]] for v in ov]
 data=dict(report=report,hand=hand,faces=faces,object=obj,object_faces=of,target=target,image='data:image/png;base64,'+base64.b64encode(rgb).decode())
 page=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TraceHOI · Visual initial pose</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101822;color:#e6edf5;font:15px system-ui}header{padding:25px 4vw;border-bottom:1px solid #364151}h1{font-size:30px;margin:8px 0}p{line-height:1.55;color:#b9c8d8;max-width:1050px}.pill{color:#67e5cb;font-size:12px;letter-spacing:.08em}main{padding:24px 4vw}.cards,.views{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.cards{grid-template-columns:repeat(4,1fr);margin-bottom:20px}.card,.panel{padding:18px;background:#1b2635;border:1px solid #364151;border-radius:12px}.num{font-size:26px;color:#fff}.muted{font-size:12px;color:#a3b7ca}canvas{width:100%;aspect-ratio:1;background:#101822;border-radius:8px;touch-action:none}button,select{background:#26394d;color:#eef4fa;border:1px solid #5f7993;border-radius:6px;padding:8px;margin:6px}label{display:inline-block;margin:7px}input[type=range]{width:145px;vertical-align:middle}details{margin-top:20px}a{color:#74dce9}footer{padding:25px 4vw;color:#9cb4c7}@media(max-width:900px){.views{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,1fr)}}</style>
<header><div class="pill">TRACEHOI / VISUAL INITIALIZATION / S3</div><h1>Place the hand before solving contact</h1><p>Saved HaMeR shape and articulation + independent image joints + selected hand box. Fresh MoGe depth sets the relative scene scale. The laptop is unchanged. This initial state is ready to be passed to an optimizer; final placement is still unvalidated.</p></header>
<main><div class="cards"><div class="card"><div class="muted">2D joint median</div><div class="num" id="err"></div></div><div class="card"><div class="muted">Learned-depth scale</div><div class="num" id="scale"></div></div><div class="card"><div class="muted">Shared depth pixels</div><div class="num" id="support"></div></div><div class="card"><div class="muted">Contact / collision terms</div><div class="num">0</div></div></div>
<div class="views"><section class="panel"><h2>Image evidence</h2><canvas id="image" width="700" height="700" aria-label="Hand projection over the original image"></canvas><label><input type="checkbox" id="mesh" checked>Hand mesh</label><label><input type="checkbox" id="joints" checked>Joints and residuals</label><label><input type="checkbox" id="box" checked>Hand box</label><label>Zoom <input type="range" id="zoom" min="1" max="4" step=".1" value="1"></label><p class="muted">Cyan: fitted joints. Amber: independent ViTPose targets. Pink: loose recorded hand box. No masks are edited. Repeated little-finger targets share one observation weight.</p></section>
<section class="panel"><h2>Initial hand relative to laptop</h2><canvas id="orbit" width="700" height="700" aria-label="Orbit view of initial hand and laptop"></canvas><button id="reset">Reset orbit</button><label>Display scale <input type="range" id="display" min=".8" max="1.2" step=".01" value="1"></label><span id="factor">1.00×</span><p class="muted">Drag to orbit. The slider explores the unresolved scale/depth ambiguity along camera rays; it does not edit or export a new pose. Both displayed meshes retain every face. Exported coordinates remain unchanged.</p></section></div>
<div class="panel" style="margin-top:18px"><h2>Optimizer handoff</h2><p><strong>Initialization ready.</strong> Contact, collision and physical consistency are deferred to the following rectified-flow optimization stage. That optimizer has not been executed here. Independent mask validation and metric calibration remain separate validation tasks.</p><a href="optimizer_input.json">Optimizer input JSON</a> · <a href="initialization.json">Fit and provenance</a> · <a href="hand_initial.ply">Initial hand mesh</a> · <a href="object.ply">Unchanged laptop mesh</a><details><summary>Scope and limitations</summary><pre id="limits" style="white-space:pre-wrap"></pre></details></div></main><footer>alapuse02v3n60 · CPU only · original inputs retained · no contact-driven candidate selection</footer>
<script>const D=__DATA__;const R=D.report,K=R.camera.K;const $=id=>document.getElementById(id);$('err').textContent=R.fit.joint_median_px.toFixed(2)+' px';$('scale').textContent=R.depth_gauge.scale.toFixed(4);$('support').textContent=R.depth_gauge.shared_pixels;$('limits').textContent=R.limitations.join('\n\n');let img=new Image();img.src=D.image;function p(v){return [K[0][0]*v[0]/v[2]+K[0][2],K[1][1]*v[1]/v[2]+K[1][2]]}const uv=D.hand.map(p);function drawImage(){const c=$('image'),x=c.getContext('2d'),z=+$('zoom').value;x.clearRect(0,0,700,700);x.save();x.scale(700/512*z,700/512*z);if(z>1)x.translate(-R.box_xyxy[0]+18,-R.box_xyxy[1]+15);x.drawImage(img,0,0,512,512);if($('mesh').checked){x.strokeStyle='#44ecd266';x.lineWidth=.4/z;for(const f of D.faces){x.beginPath();f.forEach((i,k)=>k?x.lineTo(...uv[i]):x.moveTo(...uv[i]));x.closePath();x.stroke()}}if($('box').checked){x.strokeStyle='#ff81bd';x.lineWidth=1.4/z;const b=R.box_xyxy;x.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1])}if($('joints').checked){R.fit.projected_joints.forEach((v,i)=>{x.strokeStyle='#ffe2aa';x.lineWidth=.6/z;x.beginPath();x.moveTo(...v);x.lineTo(...D.target[i]);x.stroke();[[v,'#44ecd2'],[D.target[i],'#ffd07b']].forEach(([a,color])=>{x.fillStyle=color;x.beginPath();x.arc(...a,1.6/z,0,7);x.fill()})})}x.restore()}img.onload=drawImage;['mesh','joints','box','zoom'].forEach(id=>$(id).addEventListener('input',drawImage));
let yaw=.35,pitch=-.4,drag=null;const all=D.object.concat(D.hand),lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];all.forEach(v=>v.forEach((x,i)=>{lo[i]=Math.min(lo[i],x);hi[i]=Math.max(hi[i],x)}));const center=lo.map((x,i)=>(x+hi[i])/2);let extent=Math.max(...hi.map((x,i)=>(x-lo[i])/2))*1.15;function drawOrbit(){const c=$('orbit'),x=c.getContext('2d'),f=+$('display').value;x.clearRect(0,0,700,700);const proj=v=>{const a=v.map((k,i)=>k-center[i]),cx=Math.cos(yaw),sx=Math.sin(yaw),cy=Math.cos(pitch),sy=Math.sin(pitch),b=[cx*a[0]+sx*a[2],a[1],-sx*a[0]+cx*a[2]],v2=[b[0],cy*b[1]-sy*b[2],sy*b[1]+cy*b[2]];return [350+v2[0]*240/extent,350+v2[1]*240/extent,v2[2]]};const o=D.object.map(proj),h=D.hand.map(v=>proj(v.map(x=>x*f)));let triangles=[];[[o,D.object_faces,'#648baa'],[h,D.faces,'#48cdb6']].forEach(([v,faces,color])=>faces.forEach(face=>triangles.push({p:face.map(i=>v[i]),color,z:face.reduce((s,i)=>s+v[i][2],0)/3})));triangles.sort((a,b)=>b.z-a.z);for(const t of triangles){x.fillStyle=t.color;x.strokeStyle=t.color;x.lineWidth=.35;x.beginPath();t.p.forEach((v,i)=>i?x.lineTo(v[0],v[1]):x.moveTo(v[0],v[1]));x.closePath();x.fill();x.stroke()}$('factor').textContent=f.toFixed(2)+'×'}$('orbit').addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];e.target.setPointerCapture(e.pointerId)});$('orbit').addEventListener('pointermove',e=>{if(drag){yaw+=(e.clientX-drag[0])*.008;pitch+=(e.clientY-drag[1])*.008;drag=[e.clientX,e.clientY];drawOrbit()}});$('orbit').addEventListener('pointerup',()=>drag=null);$('reset').onclick=()=>{yaw=.35;pitch=-.4;$('display').value=1;drawOrbit()};$('display').oninput=drawOrbit;drawOrbit();</script></html>'''
 return page.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c')).encode()
