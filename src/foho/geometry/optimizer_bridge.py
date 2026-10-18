"""CPU bridge from a saved visual pose to explicit centered optimizer state.

No native backend is imported or executed. Contact belongs to the downstream
optimizer; neither contact nor collision chooses or changes this initial state.
"""
import ast,hashlib,html,json,math
from pathlib import Path
PURPOSE='optimizer_bridge'
SCHEMA='tracehoi.CenteredOptimizerState.v1'
FRAME='N7_PLY_x_right_y_up_z_backward'
def require(ok,msg):
    if not ok:raise ValueError(msg)
def encode(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def finite(v):return type(v) in (float,int) and math.isfinite(v)
def points(v):
    require(type(v) is list and 0<len(v)<=100000 and all(type(x) is list and len(x)==3 and all(finite(a) for a in x) for x in v),'points')
    return v
def mv(R,v):return [sum(a*b for a,b in zip(row,v)) for row in R]
def det(R):return sum(R[0][i]*(R[1][(i+1)%3]*R[2][(i+2)%3]-R[1][(i+2)%3]*R[2][(i+1)%3]) for i in range(3))
def rotation(R):
    require(type(R) is list and len(R)==3 and all(type(r) is list and len(r)==3 and all(finite(x) for x in r) for r in R),'rotation_shape')
    require(abs(det(R)-1)<1e-7 and max(abs(sum(R[k][i]*R[k][j] for k in range(3))-(i==j)) for i in range(3) for j in range(3))<1e-7,'proper_rotation')
    return R
def quat(R):
    rotation(R);t=sum(R[i][i] for i in range(3))
    if t>0:
        d=2*math.sqrt(t+1);q=[d/4,(R[2][1]-R[1][2])/d,(R[0][2]-R[2][0])/d,(R[1][0]-R[0][1])/d]
    else:
        i=max(range(3),key=lambda k:R[k][k]);j=(i+1)%3;k=(i+2)%3;d=2*math.sqrt(1+R[i][i]-R[j][j]-R[k][k]);q=[0.,0.,0.,0.];q[0]=(R[k][j]-R[j][k])/d;q[i+1]=d/4;q[j+1]=(R[i][j]+R[j][i])/d;q[k+1]=(R[i][k]+R[k][i])/d
    norm=math.sqrt(sum(x*x for x in q));q=[x/norm for x in q]
    if next((x for x in q if abs(x)>1e-15),1)<0:q=[-x for x in q]
    return q

def from_quat(q):
    require(type(q) is list and len(q)==4 and all(finite(x) for x in q) and abs(sum(x*x for x in q)-1)<1e-7,'unit_quaternion_wxyz')
    w,x,y,z=q;return [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
def decompose(M):
    require(type(M) is list and len(M)==4 and all(type(r) is list and len(r)==4 and all(finite(x) for x in r) for r in M),'matrix_shape')
    require(M[3]==[0,0,0,1],'affine_row');s=math.sqrt(sum(M[i][0]**2 for i in range(3)));require(s>1e-12,'positive_scale')
    R=[[M[i][j]/s for j in range(3)] for i in range(3)];rotation(R);return s,R,[M[i][3] for i in range(3)]
def center(v):
    points(v);return [(min(p[i] for p in v)+max(p[i] for p in v))/2 for i in range(3)]
def direct(v,M):
    points(v);decompose(M);return [[sum(M[i][j]*p[j] for j in range(3))+M[i][3] for i in range(3)] for p in v]
def make_state(v,M,geometry_binding):
    s,R,t=decompose(M);c=center(v);Rc=mv(R,c);d=[t[i]+s*Rc[i]-c[i] for i in range(3)]
    return dict(schema=SCHEMA,input_geometry='native_hamer',input_geometry_binding=geometry_binding,native_vertices_binding=pin(encode(v)),output_frame=FRAME,center_rule='axis_aligned_bbox_midpoint',center=c,scale=s,rotation_wxyz=quat(R),translation=d,formula='scale * R * (v - center) + center + translation',upstream_transform='bypass_hunyuan_to_moge_for_this_input',phase1_initialization='bypass_to_preserve_visual_initial_pose',contact_terms_used=False,backend_wired=False)
def apply_state(v,state,*,input_geometry,geometry_binding):
    points(v);require(state['schema']==SCHEMA and state['input_geometry']==input_geometry=='native_hamer','geometry_ownership')
    require(state['input_geometry_binding']==geometry_binding,'geometry_binding');require(state['output_frame']==FRAME and state['center_rule']=='axis_aligned_bbox_midpoint','state_frame')
    require(state['center']==center(v),'center_changed');require(state['native_vertices_binding']==pin(encode(v)),'native_vertices_changed');s=state['scale'];require(finite(s) and s>0,'positive_scale');R=from_quat(state['rotation_wxyz']);d=state['translation'];require(type(d) is list and len(d)==3 and all(finite(x) for x in d),'translation')
    c=state['center'];return [[s*a+c[i]+d[i] for i,a in enumerate(mv(R,[p[j]-c[j] for j in range(3)]))] for p in v]
def read_package(folder,sha,reader):
    folder=Path(folder);raw=reader.regular(folder/'files.json',1024**2);require(pin(raw)['sha256']==sha,'source_receipt_binding');receipt=json.loads(raw)
    # A pinned source receipt authenticates all source bytes; no fit is repeated.
    members=receipt['files'];require(set(members)=={'index.html','initialization.json','optimizer_input.json','hand_initial.ply','object.ply','image.png','README.md'},'source_inventory')
    files={n:reader.regular(folder/n,16*1024**2) for n in members};require({n:pin(b) for n,b in files.items()}==members,'source_member_binding');return files

def inspect_source(raw):
    """Static summaries only; ast.parse never executes a source file."""
    require(len(raw)<=2*1024**2,'source_cap');tree=ast.parse(raw);functions=[];calls=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            functions.append(dict(name=node.name,line=node.lineno,end_line=node.end_lineno,args=[a.arg for a in node.args.args],ast_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()))
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            if any(t in name for t in ('guidance','transform_mesh','transform_hunyuan','scheduler.step')):calls.append(dict(name=name,line=node.lineno,keywords=[k.arg for k in node.keywords]))
    return dict(binding=pin(raw),functions=functions,calls=calls,source_executed=False)

def build(folder,sha,prediction_raw,reader,visual,*,purpose):
    require(purpose==PURPOSE,'optimizer_bridge_purpose_required');files=read_package(folder,sha,reader);r=json.loads(files['initialization.json']);o=json.loads(files['optimizer_input.json']);h=json.loads(prediction_raw)
    require(r['initialization_ready'] is True and r['optimizer_handoff_ready'] is True and r['contact_terms_used'] is False and r['collision_terms_used'] is False,'initialization_scope')
    require(o['schema']=='tracehoi.InitialPoseOptimizerInput.v1' and o['geometry_state']=='already_in_scene_coordinates' and o['mesh_model_matrix']==[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],'exported_geometry_ownership')
    require(o['initialization_binding']==pin(files['initialization.json']) and o['native_prediction_binding']==pin(prediction_raw),'source_bindings')
    require(o['hand_binding']==pin(files['hand_initial.ply']) and o['object_binding']==pin(files['object.ply']),'mesh_bindings')
    require(o['native_geometry_frame']=='hamer_model_camera_axes_before_camera_translation' and o['camera']['scene_frame']==FRAME,'input_frame')
    require(o['native_mano_params']==h['mano_params'] and o['case_id']==r['case_id']==h['case_id'],'native_identity')
    require(o['source_to_scene_provenance_only']==r['source_to_scene'],'transform_binding')
    v=h['vertices'];require(len(v)==778 and len(h['faces'])==1538,'mano_topology');state=make_state(v,r['source_to_scene'],pin(prediction_raw));out=apply_state(v,state,input_geometry='native_hamer',geometry_binding=pin(prediction_raw));expected=direct(v,r['source_to_scene']);hand,faces=reader.mesh(files['hand_initial.ply']);require([list(f) for f in faces]==h['faces'],'face_order')
    e=max(abs(a-b) for p,q in zip(out,expected) for a,b in zip(p,q));e_mesh=max(abs(a-b) for p,q in zip(out,hand) for a,b in zip(p,q));require(e<1e-10 and e_mesh<1e-6,'vertex_roundtrip')
    q=from_quat(state['rotation_wxyz']);s,R,t=decompose(r['source_to_scene']);require(max(abs(q[i][j]-R[i][j]) for i in range(3) for j in range(3))<1e-10,'quaternion_roundtrip')
    # The baked scene mesh must be consumed with identity, never the native transform.
    baked=dict(schema='tracehoi.BakedSceneOptimizerState.v1',input_geometry='scene_mesh',input_geometry_binding=pin(files['hand_initial.ply']),output_frame=FRAME,scale=1.,rotation_wxyz=[1.,0.,0.,0.],translation=[0.,0.,0.],upstream_transform='bypass_hunyuan_to_moge_for_this_input',phase1_initialization='bypass_to_preserve_visual_initial_pose')
    report=dict(schema='tracehoi.OptimizerBridge.v1',case_id=r['case_id'],initialization_ready=True,bridge_complete=True,backend_wired=False,backend_execution_ready=False,rectified_flow_executed=False,contact_terms_used=False,contact_queries=0,source_geometry_modified=False,model_calls=0,placement_ready=False,full_parent_acceptance=False,mask_accuracy_verified=False,reference_status=r['reference_status'],native_state=state,baked_state=baked,roundtrip=dict(vertices=778,faces=1538,max_float64_error=e,max_export_float32_error=e_mesh),source_receipt_sha256=sha,native_prediction_binding=pin(prediction_raw),initialization_binding=pin(files['initialization.json']),next_action='inspect_current_backend_then_wire_opt_in_handoff',downstream_contract=dict(visual_initialization='consume unchanged S3 state',contact='resolved by later rectified-flow optimization, not initialization',native_route='use original native mesh and centered state together; bypass old h2m hand transform',baked_route='use exported scene mesh with identity; bypass old h2m hand transform',mano='native MANO parameters remain unchanged; external transform owns scene placement',object='preserve supplied laptop geometry until a separately implemented optimization stage'))
    payload={'bridge.json':encode(report),'centered_state.json':encode(state),'baked_state.json':encode(baked),'native_hand.ply':visual.ply(v,h['faces']),'hand_initial.ply':files['hand_initial.ply'],'object.ply':files['object.ply'],'scene.html':files['index.html'],'initialization.json':files['initialization.json'],'optimizer_input.json':files['optimizer_input.json'],'image.png':files['image.png']}
    payload['index.html']=viewer(report,v,expected).encode();payload['README.md']=b'# TraceHOI optimizer bridge\n\nOpen index.html. Both hand routes reproduce the same saved visual initializer. Native backend is not wired or executed. Contact remains a downstream optimization responsibility. Preserve all files together.\n'
    payload['files.json']=encode(dict(schema='tracehoi.OptimizerBridgeFiles.v1',members={n:pin(b) for n,b in payload.items()}));return report,payload

def verify(folder,receipt_sha,source,source_sha,prediction_raw,reader,visual,*,purpose):
    r,files=build(source,source_sha,prediction_raw,reader,visual,purpose=purpose);require(pin(files['files.json'])['sha256']==receipt_sha,'receipt_binding')
    folder=Path(folder);require(set(p.name for p in folder.iterdir())==set(files),'output_inventory')
    for n,b in files.items():require(reader.regular(folder/n,16*1024**2)==b,'output_changed:'+n)
    return dict(verified=True,receipt_binding=pin(files['files.json']),bridge_complete=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)

def viewer(r,native,scene):
    data=json.dumps(dict(report=r,native=native,scene=scene),allow_nan=False,separators=(',',':')).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TraceHOI · Optimizer bridge</title><style>body{margin:0;background:#0a1323;color:#e6eefb;font:16px system-ui}main{max-width:1120px;margin:auto;padding:32px}h1{font-size:36px;margin:12px 0}p{line-height:1.6;color:#b6c6dd}a{color:#7bd9d0}section{border:1px solid #30415b;background:#101e32;border-radius:16px;padding:22px;margin:18px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}canvas{width:100%;height:350px;background:#08101e;border-radius:12px}button,select{font:inherit;padding:9px;background:#20364e;color:white;border:1px solid #52718d;border-radius:8px}label{margin-right:14px}pre{white-space:pre-wrap;font:13px ui-monospace;line-height:1.5}.tag{color:#75e6b9}#err{font:20px ui-monospace;color:#75e6b9}@media(max-width:700px){.grid{display:block}}</style><main><span class="tag">TRACEHOI / INITIALIZER → OPTIMIZER</span><h1>Keep the pose. Transfer the state.</h1><p>The CPU visual initializer is complete. These two representations produce the same hand. Contact is deferred to later rectified-flow optimization. This packet verifies the coordinate bridge; the native optimizer has not been wired or run.</p><p><a href="scene.html">Open the initialized hand + laptop scene ↗</a> · <a href="centered_state.json">Native centered state</a> · <a href="baked_state.json">Baked scene state</a> · <a href="bridge.json">Verification record</a></p><section><div class="grid"><div><h2>778-vertex round-trip</h2><p>Blue: saved scene vertices. Green: native vertices transformed with centered optimizer parameters. Coincident points show that the bridge preserves the visual pose.</p><label>View <select id="axis"><option value="xy">X / Y</option><option value="xz">X / Z</option><option value="yz">Y / Z</option></select></label><label><input id="show" type="checkbox" checked>Show bridge</label><button id="reset">Reset</button><p id="err"></p><canvas id="c" width="900" height="600"></canvas></div><div><h2>Exactly one transform</h2><p><b>Native route:</b> original HaMeR mesh + centered scale, quaternion and translation. Bypass the old hand Hunyuan-to-MoGe transform.</p><p><b>Scene route:</b> S3's already placed mesh + identity parameters. Bypass the old hand transform here too.</p><pre id="state"></pre></div></div></section><section><h2>Stage boundary</h2><p>Initialization uses visual evidence and learned scene depth. It does not select poses by contact, clearance or collision. A later optimization stage may refine contact and geometry. Independent mask accuracy, metric scale and final placement remain unverified.</p><p>Next: inspect the current server backend sources, then wire an explicit opt-in input path that preserves this state and skips the older initialization stage.</p></section></main><script>const D=DATA;const S=D.report.native_state;document.getElementById('state').textContent=JSON.stringify({scale:S.scale,rotation_wxyz:S.rotation_wxyz,translation:S.translation,center:S.center},null,2);document.getElementById('err').textContent='Max bridge error: '+D.report.roundtrip.max_float64_error.toExponential(2);function draw(){let pair={xy:[0,1],xz:[0,2],yz:[1,2]}[document.getElementById('axis').value],a=pair[0],b=pair[1],cv=document.getElementById('c'),ctx=cv.getContext('2d');ctx.clearRect(0,0,900,600);let xs=D.scene.map(p=>p[a]),ys=D.scene.map(p=>p[b]),lo=[Math.min(...xs),Math.min(...ys)],hi=[Math.max(...xs),Math.max(...ys)],s=Math.min(820/(hi[0]-lo[0]),520/(hi[1]-lo[1])),[w,x,y,z]=S.rotation_wxyz,R=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]],pts=D.native.map(p=>R.map((row,i)=>S.scale*row.reduce((t,u,j)=>t+u*(p[j]-S.center[j]),0)+S.center[i]+S.translation[i]));function render(v,color,rad){ctx.fillStyle=color;for(let p of v){ctx.beginPath();ctx.arc(40+(p[a]-lo[0])*s,560-(p[b]-lo[1])*s,rad,0,Math.PI*2);ctx.fill()}}render(D.scene,'#63a5ff',3);if(document.getElementById('show').checked)render(pts,'#65edb1',1.3)}document.getElementById('axis').onchange=draw;document.getElementById('show').onchange=draw;document.getElementById('reset').onclick=()=>{document.getElementById('axis').value='xy';document.getElementById('show').checked=true;draw()};draw();</script></html>'''.replace('DATA',data)
