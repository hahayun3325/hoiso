"""Prepare object pixels and verify native transforms without model execution."""
import ast
import base64
import copy
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path

PURPOSE = 'native_state_probe'

def require(ok, message):
    if not ok: raise ValueError(message)

def pin(b): return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
def encode(o): return (json.dumps(o, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()

def conditioning_pixels(rgb, mask, hand, overlap):
    require(len(rgb)==512*512*3 and all(len(x)==512*512 for x in (mask,hand,overlap)), 'conditioning_shape')
    require(all(set(x)<={0,255} for x in (mask,hand,overlap)), 'conditioning_binary_masks')
    require(0<sum(bool(x) for x in mask)<512*512, 'conditioning_empty_or_full')
    require(not any(a and (b or c) for a,b,c in zip(mask,hand,overlap)), 'conditioning_support_overlap')
    out=bytearray(512*512*4)
    for i,m in enumerate(mask):out[4*i:4*i+4]=rgb[3*i:3*i+3]+b'\xff' if m else b'\xff\xff\xff\0'
    return bytes(out)

def rgba_png(raw):
    require(len(raw)==512*512*4, 'rgba_shape')
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    rows=b''.join(b'\0'+raw[i:i+2048] for i in range(0,len(raw),2048))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',512,512,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')

def selected_functions(pipeline, helper, handoff):
    require(pin(pipeline)['sha256']==handoff.BACKEND_PINS[0] and pin(helper)['sha256']==handoff.BACKEND_PINS[1], 'native_source_changed')
    selected={}
    for raw,names in [(pipeline, ['transform_mesh_around_center_w_scale','transform_hunyuan2moge']), (helper,['get_guidance_params'])]:
        tree=ast.parse(raw)
        for name in names:
            nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
            require(len(nodes)==1,'native_function_count:'+name);selected[name]=nodes[0]
    return selected

def compile_functions(pipeline,helper,handoff,torch):
    # Only the three hash-bound functions execute, with torch as the sole native global.
    nodes=selected_functions(pipeline,helper,handoff)
    ns={'torch':torch}
    exec(compile(ast.fix_missing_locations(ast.Module(body=list(nodes.values()),type_ignores=[])), '<TraceHOI native state functions>', 'exec'), ns)
    return {name:ns[name] for name in nodes}

def load(folder,sha,pipeline,helper,camera,handoff,reader,review):
    files,runtime=camera.load_runtime(folder,sha,reader)
    selected_functions(pipeline,helper,handoff)
    c,rgb=review.decode_png(files['image.png']);require(c==3,'conditioning_RGB_required')
    masks=[review.decode_pgm(files[n]) for n in ['object_mask.pgm','hand_mask.pgm','overlap_mask.pgm']]
    rgba=conditioning_pixels(rgb,*masks)
    state=json.loads(files['centered_state.json'])
    require(state['schema']=='tracehoi.CenteredOptimizerState.v1' and state['input_geometry']=='native_hamer' and state['center_rule']=='axis_aligned_bbox_midpoint','hand_state_contract')
    require(state['contact_terms_used'] is False and math.isfinite(state['scale']) and state['scale']>0,'hand_state_scale')
    return files,runtime,state,rgba,masks

def build(folder,sha,pipeline,helper,prior_camera,camera,handoff,reader,review,*,purpose):
    require(purpose==PURPOSE,'native_state_probe_purpose_required')
    files,runtime,state,rgba,masks=load(folder,sha,pipeline,helper,camera,handoff,reader,review)
    pc=json.loads(prior_camera)
    require(pc['schema']=='tracehoi.NativeCameraCPUPreflight.v1' and pc['passed'] is True and pc.get('fixture_only') is not True and pc['runtime_receipt_sha256']==sha and pc['raster_mask_exact'] is True,'prior_camera_not_verified')
    cond=rgba_png(rgba)
    report=dict(schema='tracehoi.NativeStateProbe.v1',case_id=runtime['case_id'],prepared=True,
        initialization_ready=True,contact_terms_used=False,source_meshes_modified=False,original_masks_modified=False,
        native_state_execution_verified=False,backend_execution_ready=False,rectified_flow_executed=False,model_calls=0,
        placement_ready=False,full_parent_acceptance=False,mask_accuracy_verified=False,reference_status='awaiting_reference',
        source_receipt_sha256=sha,prior_camera_binding=pin(prior_camera),source_functions={k:pin(ast.unparse(v).encode()) for k,v in selected_functions(pipeline,helper,handoff).items()},
        conditioning=dict(binding=pin(cond),width=512,height=512,mode='RGBA',support='saved_object_only_mask',alpha_pixels=sum(bool(x) for x in masks[0]),
            excluded_hand_pixels=sum(bool(x) for x in masks[1]),excluded_ambiguous_pixels=sum(bool(x) for x in masks[2]),
            foreground_RGB='exact_original_pixels',background_RGBA=[255,255,255,0],image_binding=pin(files['image.png']),mask_binding=pin(files['object_mask.pgm']),
            source_crop_or_resize_applied=False,model_preprocessing_executed=False,conditioning_encoder_executed=False),
        state=state,
        latent_policy=dict(status='unresolved',saved_object_mesh_is_latent=False,latent_loaded=False,latent_sampled=False,
            reason='The saved object PLY has no bound diffusion latent. Fresh random noise would regenerate object shape; preserving the object requires a separately validated encoding or inversion path.'),
        probe_scope=['native hand mesh loader and centered transform','all native object vertices transformed to fresh scene','phase-2 parameter clones preserve initial values','finite autograd through hand and object transforms','Pillow RGBA and OpenCV mask decoding'],
        pending=['native_state_CPU_preflight','full_scene_renderer_and_regressor_assets','object_latent_initialization','bounded_joint_rectified_flow_execution'])
    out={n:b for n,b in files.items() if n not in ['files.json','index.html']}
    out.update({'object_conditioning.png':cond,'state_probe.json':encode(report),'camera_preflight_X8.json':prior_camera,
                'index.html':viewer(report,files['image.png'],cond).encode(),
                'README.md':b'# Native visual-state probe\n\nOpen index.html with companions intact. Native results are in native_state_preflight.json when produced. CPU initialization has no contact terms; downstream joint rectified-flow execution remains pending. Preserve original terminals, input records and evidence archives.\n'})
    out['files.json']=encode(dict(schema='tracehoi.NativeStateProbeFiles.v1',files={n:pin(b) for n,b in out.items()}))
    return report,out

def verify(output,receipt_sha,*args,purpose):
    r,files=build(*args,purpose=purpose)
    require(pin(files['files.json'])['sha256']==receipt_sha,'state_receipt_changed')
    reader=args[-2];root=Path(output)
    require(set(p.name for p in root.iterdir())==set(files),'state_output_inventory')
    for n,b in files.items():require(reader.regular(root/n,16*1024**2)==b,'state_output_changed:'+n)
    return dict(verified=True,receipt_binding=pin(files['files.json']),prepared=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)

def native_cpu_preflight(folder,sha,pipeline,helper,conditioning_path,camera,handoff,reader,review,*,progress=None):
    progress={} if progress is None else progress
    files,runtime,state,rgba,masks=load(folder,sha,pipeline,helper,camera,handoff,reader,review)
    require(reader.regular(conditioning_path,2*1024**2)==rgba_png(rgba),'conditioning_file_changed')
    progress.update(stage='native_imports')
    import torch
    import numpy as np
    import cv2
    import PIL
    from PIL import Image
    import pytorch3d
    from pytorch3d.io import load_ply
    from pytorch3d.structures import Meshes
    from pytorch3d.transforms import quaternion_to_matrix
    torch.set_num_threads(1)
    progress.update(torch_version=str(torch.__version__),numpy_version=str(np.__version__),pytorch3d_version=str(getattr(pytorch3d,'__version__','unknown')),pillow_version=str(PIL.__version__),opencv_version=str(cv2.__version__),stage='hand_transform')
    funcs=compile_functions(pipeline,helper,handoff,torch)
    def mesh(name):
        v,f=load_ply(str(Path(folder)/name));ev,ef=reader.mesh(files[name])
        require(v.device.type==f.device.type=='cpu' and v.tolist()==[list(p) for p in ev] and f.tolist()==[list(p) for p in ef],'native_mesh_loader_changed:'+name)
        return Meshes(verts=[v],faces=[f]),ev,ef
    hand,verts,faces=mesh('native_hand.ply');original_hand=hand.verts_packed().clone()
    binding=handoff._HandState(folder,state,[list(v) for v in verts],[list(f) for f in faces])
    scale,trans,rot=binding.tensors(hand,torch,'cpu')
    def matrix(t,q):
        # CopySlices retains gradients through both rotation and translation.
        T=torch.eye(4,dtype=torch.float32);T[:3,:3]=quaternion_to_matrix(q);T[:3,3]=t;return T
    got=funcs['transform_mesh_around_center_w_scale'](hand,matrix(trans,rot),scale)
    expected,expected_faces=reader.mesh(files['hand_initial.ply'])
    require(faces==expected_faces,'hand_faces_changed')
    error=float((got.verts_packed()-torch.tensor(expected)).abs().max())
    progress.update(hand_vertices=len(verts),hand_max_error=error)
    require(error<2e-6,'native_hand_placement_changed')
    progress['stage']='object_transform'
    obj,ov,of=mesh('object_native.ply');original_obj=obj.verts_packed().clone()
    h2m=torch.tensor(camera.numeric_array(files['h2m.npy'],(4,4)),dtype=torch.float32)
    placed=funcs['transform_hunyuan2moge'](obj,h2m)
    expected_obj,expected_of=reader.mesh(files['object.ply']);require(of==expected_of,'object_faces_changed')
    obj_error=float((placed.verts_packed()-torch.tensor(expected_obj)).abs().max())
    progress.update(object_vertices=len(ov),object_max_error=obj_error)
    require(obj_error<2e-6,'native_object_placement_changed')
    progress['stage']='joint_parameters'
    # Small synthetic velocity tensor tests cloning only, not model/latent shape.
    noise=torch.arange(8,dtype=torch.float32).reshape(1,2,4)/8
    inputs=[noise,scale,trans,rot,torch.ones(1),torch.zeros(3),torch.tensor([1.,0.,0.,0.])]
    before=[x.clone() for x in inputs]
    lr=dict(scale=.001,trans=.002,rot=.003)
    groups,*values=funcs['get_guidance_params'](2,*inputs[:4],'cpu',phase1_hand_lrs=lr,phase2_hand_lrs=lr,noise_obj_lr1=.001,noise_obj_lr2=.001,obj_lrs=lr,obj_2half_lrs=lr,scale_obj=inputs[4],trans_obj=inputs[5],rotation_obj=inputs[6])
    require(len(groups)==7 and len(values)==7,'joint_parameter_count')
    for a,b in zip(inputs,values):require(torch.equal(a,b) and a.data_ptr()!=b.data_ptr() and b.is_leaf and b.requires_grad,'joint_parameter_reset_or_alias')
    require(all(g['params'][0] is values[i] for g,i in zip(groups,[1,2,3,4,5,6,0])),'joint_parameter_routing')
    n,s,t,q,so,to,qo=values
    hv=funcs['transform_mesh_around_center_w_scale'](hand,matrix(t,q),s).verts_packed()
    ob=funcs['transform_mesh_around_center_w_scale'](placed,matrix(to,qo),so).verts_packed()
    zero_error=max(float((hv-got.verts_packed()).abs().max()),float((ob-placed.verts_packed()).abs().max()))
    require(zero_error<2e-6,'joint_zero_update_pose_changed');progress['joint_zero_update_max_error']=zero_error
    # A numerical graph exercise only; no contact loss or optimizer step.
    loss=hv.square().mean()+ob.square().mean()+n.square().mean()
    grads=torch.autograd.grad(loss,values)
    require(all(g is not None and torch.isfinite(g).all().item() for g in grads),'joint_gradient_nonfinite')
    require(all(torch.equal(a,b) for a,b in zip(inputs,before)) and torch.equal(hand.verts_packed(),original_hand) and torch.equal(obj.verts_packed(),original_obj),'source_tensor_mutated')
    progress.update(parameter_groups=7,zero_update_preserved=True,gradient_finite=True,gradient_norms=[float(g.norm()) for g in grads],optimizer_steps=0,stage='image_decoding')
    with Image.open(conditioning_path) as im:
        require(im.mode=='RGBA' and im.size==(512,512) and im.tobytes()==rgba,'Pillow_conditioning_changed')
    for name in ['hand_mask.pgm','object_mask.pgm','overlap_mask.pgm','hand_valid.pgm','object_valid.pgm']:
        decoded=cv2.imread(str(Path(folder)/name),cv2.IMREAD_GRAYSCALE)
        require(decoded is not None and decoded.dtype==np.uint8 and decoded.shape==(512,512) and decoded.tobytes()==review.decode_pgm(files[name]),'OpenCV_mask_changed:'+name)
    progress.update(Pillow_RGBA_exact=True,OpenCV_masks_exact=True,stage='complete')
    for name,b in files.items():require(reader.regular(Path(folder)/name,16*1024**2)==b,'runtime_changed_during_probe:'+name)
    return dict(schema='tracehoi.NativeStateCPUPreflight.v1',passed=True,device='cpu',runtime_receipt_sha256=sha,conditioning_binding=pin(rgba_png(rgba)),diagnostics=progress,
        native_state_execution_verified=True,native_execution_verified=False,backend_execution_ready=False,initialization_ready=True,contact_terms_used=False,
        rectified_flow_executed=False,model_calls=0,explicit_cuda_calls=0,optimizer_steps=0,latent_sampled=False,placement_ready=False)

def viewer(report,image,condition):
    data=dict(report=report,image='data:image/png;base64,'+base64.b64encode(image).decode(),condition='data:image/png;base64,'+base64.b64encode(condition).decode())
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TraceHOI · Native state</title><style>
    *{box-sizing:border-box}body{margin:0;background:#091421;color:#e9f2fb;font:16px system-ui}main{max-width:1120px;margin:auto;padding:32px}h1{font-size:40px;max-width:850px}p{line-height:1.6;color:#b7c9dd}.tag{color:#75e0c1}.warn{color:#f4ce87}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}section{border:1px solid #314b65;border-radius:16px;background:#112439;padding:22px;margin:20px 0}img{width:100%;display:block;border-radius:8px}.checker{background:repeating-conic-gradient(#364657 0% 25%,#243649 0% 50%) 0/20px 20px}button,select,input{font:inherit}button,select{background:#203c54;color:white;border:1px solid #688099;border-radius:8px;padding:10px;cursor:pointer}button[aria-pressed=true]{background:#246c5c}label{display:inline-block;margin:8px}a{color:#7ae1c8}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px ui-monospace;max-height:320px;overflow:auto}iframe{width:100%;height:620px;border:0}#metrics{display:flex;flex-wrap:wrap;gap:20px}#metrics div{flex:1;min-width:180px;padding:16px;background:#1b344b;border-radius:12px}#metrics b{display:block;font-size:26px}.steps{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:720px){.grid{grid-template-columns:1fr}main{padding:16px}h1{font-size:30px}}</style>
    <main><span class="tag">TRACEHOI / VISUAL INITIALIZATION → JOINT FLOW</span><h1>Carry the visual pose into native optimization.</h1><p>Keep the hand scale and placement from the image, HaMeR and the hand box. Contact is resolved during subsequent joint rectified-flow optimization.</p><div id="metrics"><div>Camera check<b>Verified in X8</b></div><div>Native state check<b id="native-status">Pending server</b></div><div>Joint-flow run<b>Not executed</b></div></div>
    <div class="grid"><section><h2>Original image</h2><img id="original" alt="Exact original hand and laptop image"><p>The original RGB, masks and geometry remain unchanged.</p></section><section><h2>Laptop conditioning</h2><img class="checker" id="condition" alt="Laptop-only RGBA conditioning image"><label><input id="background" type="checkbox"> White background</label><p id="support"></p><p>Full 512 × 512 image coordinates. Foreground RGB is copied exactly; hand and ambiguous pixels have zero alpha. Model preprocessing remains pending.</p></section></div>
    <section><h2>Follow the state transition</h2><div class="steps"><button data-stage="hand">Hand transform</button><button data-stage="object">Object transform</button><button data-stage="joint">Joint parameters</button><button data-stage="latent">Diffusion latent</button></div><h3 id="step-title"></h3><p id="step-text"></p><pre id="step-data"></pre></section>
    <section><h2>Native check results</h2><p id="native-message">Load native_state_preflight.json after the server run. No native-state success is claimed by this preview.</p><input id="result" type="file" accept=".json,application/json" aria-label="Load native state result JSON"><details><summary>Result details</summary><pre id="result-data"></pre></details></section>
    <section><h2>Inspect the initial hand and laptop</h2><p><a href="scene.html">Open interactive scene ↗</a> · <a href="state_probe.json">State contract</a> · <a href="object_conditioning.png">Conditioning PNG</a></p><button id="load-scene">Load initial scene</button><div id="scene"></div></section><p class="warn">The camera check and state check do not certify mask accuracy, metric scale, contact or final placement. Model assets, complete renderer behavior and object-latent initialization still need validation.</p></main>
    <script>const D=DATA,$=id=>document.getElementById(id);$('original').src=D.image;$('condition').src=D.condition;$('support').textContent=D.report.conditioning.alpha_pixels.toLocaleString()+' laptop pixels retained.';$('background').onchange=()=>{$('condition').className=$('background').checked?'':'checker';$('condition').style.backgroundColor=$('background').checked?'white':''};const steps={hand:['One saved hand transform','Apply scale and rotation around the native HaMeR bounding-box center, then translation. The object transform is never applied to the hand.',D.report.state],object:['One object transform','Apply the saved native-object-to-fresh-scene matrix. Joint object parameters start at identity.',['object_native.ply','h2m.npy','object.ply']],joint:['Preserve joint parameter values','Verify all seven parameter groups retain the starting values, use independent tensors and support finite gradients. No optimizer step is taken.',['hand scale / translation / rotation','object scale / translation / rotation','synthetic velocity for clone checking only']],latent:['Object latent remains unresolved','A saved mesh is not a saved diffusion latent. A new random-noise run could regenerate laptop shape; encoding or inversion needs separate validation.',D.report.latent_policy]};function show(k){const a=steps[k];$('step-title').textContent=a[0];$('step-text').textContent=a[1];$('step-data').textContent=JSON.stringify(a[2],null,2);document.querySelectorAll('[data-stage]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.stage===k))}document.querySelectorAll('[data-stage]').forEach(b=>b.onclick=()=>show(b.dataset.stage));show('hand');$('result').onchange=async e=>{try{const f=e.target.files[0];if(!f||f.size>1048576)throw Error('Choose a result JSON under 1 MiB.');const r=JSON.parse(await f.text());if(r.schema!=='tracehoi.NativeStateCPUPreflight.v1'||r.runtime_receipt_sha256!==D.report.source_receipt_sha256||r.conditioning_binding?.sha256!==D.report.conditioning.binding.sha256)throw Error('Result does not match these inputs.');$('native-status').textContent=r.fixture_only?'Synthetic test':r.passed===true?'Passed':'Failed';$('native-message').textContent=r.fixture_only?'Synthetic UI test only; no native execution.':r.passed===true?'Bound native CPU check passed. Joint rectified-flow execution is still pending.':'Native check failed; preserve this result and all partial outputs.';$('result-data').textContent=JSON.stringify(r,null,2)}catch(x){$('native-status').textContent='Not verified';$('native-message').textContent=x.message;$('result-data').textContent=''}};$('load-scene').onclick=function(){let f=document.createElement('iframe');f.title='Unchanged initial hand and laptop';f.src='scene.html';$('scene').replaceChildren(f);this.hidden=true};</script></html>'''
    return page.replace('DATA',json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c'))
