"""Exact native conditioning and synthetic scheduler checks; no model inference."""
import ast,base64,hashlib,json,math,sys,types
from pathlib import Path

PURPOSE='native_conditioning'
PINS={
 'preprocessors.py.txt':{'bytes':5131,'sha256':'2c73fa141d6f9a8da4285b380fbada3fc8a8955e6ec376de46469b81b2321e97'},
 'schedulers.py.txt':{'bytes':20116,'sha256':'e447d9551c403b337ad94e0176b819dd34a7470e8f511a74708e6e52c1897f25'},
 'models_vae.py.txt':{'bytes':21797,'sha256':'9c063d806a1ecb08820c4f82457a42ba3413dc3cc20436a5704b1f5a26757050'},
 'config.yaml.txt':{'bytes':1604,'sha256':'70bbfcdd18b9686ee56fe011c3a059b222eae1f5450f904577c50f0e107a8a53'}}
def require(ok,message):
 if not ok:raise ValueError(message)
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def encode(o):return (json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def read_sources(folder,reader):
 result={}
 for n,b in PINS.items():
  raw=reader.regular(Path(folder)/n,1024**2);require(pin(raw)==b,'conditioning_source_changed:'+n);result[n]=raw
 return result
def recenter_contract(mask,border=.15):
 require(len(mask)==512*512 and set(mask)<={0,255},'mask_shape_binary')
 require(type(border) in (int,float) and math.isfinite(border) and 0<=border<1,'border_ratio')
 points=[(i//512,i%512) for i,v in enumerate(mask) if v]
 require(points,'mask_empty');y0=min(p[0] for p in points);y1=max(p[0] for p in points);x0=min(p[1] for p in points);x1=max(p[1] for p in points)
 h=y1-y0;w=x1-x0;require(h>0 and w>0,'mask_line')
 size=int(512*(1-border));scale=size/max(h,w);h2=int(h*scale);w2=int(w*scale)
 require(h2>0 and w2>0,'recenter_empty')
 return dict(native_crop_xyxy_exclusive=[x0,y0,x1,y1],native_omits_maximum_row_column=True,resize_wh=[w2,h2],paste_xy=[(512-w2)//2,(512-h2)//2],border_ratio=border,
             original_mask_pixels=len(points),conditioning_coordinates='recentered_model_image_only',scene_camera_and_masks_unchanged=True)
def source_contract(pipeline,sources,handoff):
 require(pin(pipeline)['sha256']==handoff.BACKEND_PINS[0],'pipeline_changed')
 for n,p in PINS.items():require(pin(sources[n])==p,'conditioning_source_changed:'+n)
 tree=ast.parse(sources['models_vae.py.txt']);vae=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ShapeVAE')
 methods=[n.name for n in vae.body if isinstance(n,ast.FunctionDef)]
 require(methods==['__init__','forward','latents2mesh'],'vae_interface_changed')
 tree=ast.parse(pipeline);joint=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Hunyuan3DDiTFlowMatchingPipeline_main');call=next(n for n in joint.body if isinstance(n,ast.FunctionDef) and n.name=='__call__')
 starts=[n for n in ast.walk(call) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='prepare_latents']
 require(len(starts)==1 and len(starts[0].args)==4 and not starts[0].keywords,'joint_latent_entry_changed')
 return dict(schema='tracehoi.NativeConditioningSourceContract.v1',source_bindings={n:pin(b) for n,b in sources.items()},pipeline_binding=pin(pipeline),
  model_latent_shape=[1,3072,64],vae_public_methods=methods,mesh_encoder_exposed=False,joint_loop_supplies_saved_latent=False,
  model_latent_loaded=False,model_latent_sampled=False,object_mesh_latent_equivalence_verified=False,
  status='conditioning_and_scheduler_probe_only',next_model_decision='Validate a latent restart or inversion path before claiming preservation of the saved laptop shape.',
  conditioning_size=512,conditioning_border_ratio=.15,scheduler_endpoint='ascending_sigma_to_one',native_probe_modules=['preprocessors','schedulers'],vae_executed=False)
def build(folder,sha,pipeline,helper,prior_camera,prior_state,sources_folder,camera,handoff,reader,review,state_module,*,purpose):
 require(purpose==PURPOSE,'native_conditioning_purpose_required')
 previous,files=state_module.build(folder,sha,pipeline,helper,prior_camera,camera,handoff,reader,review,purpose=state_module.PURPOSE)
 native=json.loads(prior_state);require(native['schema']=='tracehoi.NativeStateCPUPreflight.v1' and native['passed'] is True and not native.get('fixture_only') and native['runtime_receipt_sha256']==sha and native['conditioning_binding']==previous['conditioning']['binding'],'prior_state_not_verified')
 sources=read_sources(sources_folder,reader);contract=source_contract(pipeline,sources,handoff)
 layout=recenter_contract(review.decode_pgm(files['object_mask.pgm']))
 report=dict(schema='tracehoi.NativeConditioning.v1',prepared=True,case_id=previous['case_id'],initialization_ready=True,native_state_execution_verified=True,
  native_conditioning_execution_verified=False,backend_execution_ready=False,native_execution_verified=False,contact_terms_used=False,rectified_flow_executed=False,model_calls=0,optimizer_steps=0,placement_ready=False,full_parent_acceptance=False,
  source_receipt_sha256=sha,conditioning_binding=previous['conditioning']['binding'],prior_state_binding=pin(prior_state),source_contract=contract,recenter=layout,
  pending=['native_conditioning_CPU_check','full_scene_renderer_and_joint_regressor','bound_diffusion_latent','bounded_joint_rectified_flow_execution'])
 out={n:b for n,b in files.items() if n not in ['files.json','index.html','state_probe.json']}
 out.update({'conditioning.json':encode(report),'state_preflight_Y9.json':prior_state,'index.html':viewer(report,files['image.png'],files['object_conditioning.png']).encode(),
  'README.md':b'# Native conditioning review\n\nOpen index.html with companion files. Load native_conditioning_preflight.json after the server run. Processed images and tensors use model coordinates only; the original scene is unchanged. No contact fit, model inference or latent generation occurs.\n'})
 out['files.json']=encode(dict(schema='tracehoi.NativeConditioningFiles.v1',files={n:pin(b) for n,b in out.items()}))
 return report,out
def verify(output,receipt,*args,purpose):
 r,files=build(*args,purpose=purpose);require(pin(files['files.json'])['sha256']==receipt,'conditioning_receipt_changed');reader=args[-3]
 require(set(p.name for p in Path(output).iterdir())==set(files),'conditioning_inventory')
 for n,b in files.items():require(reader.regular(Path(output)/n,16*1024**2)==b,'conditioning_output_changed:'+n)
 return dict(verified=True,receipt_binding=pin(files['files.json']),prepared=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)
def native_module(name,raw):
 # Only two exact reviewed dependency modules execute. ShapeVAE stays text-only.
 require(name in ['preprocessors','schedulers'] and pin(raw)==PINS[name+'.py.txt'],'native_module_not_admitted')
 module=types.ModuleType('_tracehoi_conditioning_'+name);sys.modules[module.__name__]=module
 try:exec(compile(raw,'<verified '+name+'>','exec'),module.__dict__)
 finally:sys.modules.pop(module.__name__,None)
 return module
def cpu_preflight(folder,sha,pipeline,helper,prior_camera,prior_state,sources_folder,conditioning,camera,handoff,reader,review,state_module,*,progress):
 report,_=build(folder,sha,pipeline,helper,prior_camera,prior_state,sources_folder,camera,handoff,reader,review,state_module,purpose=PURPOSE)
 raw=reader.regular(Path(conditioning)/'object_conditioning.png',2*1024**2);require(pin(raw)==report['conditioning_binding'],'conditioning_file_changed')
 sources=read_sources(sources_folder,reader);progress['stage']='native_imports'
 import torch,numpy as np,cv2,io
 from PIL import Image
 torch.set_num_threads(1);rng=torch.get_rng_state().clone()
 prep=native_module('preprocessors',sources['preprocessors.py.txt']);sched=native_module('schedulers',sources['schedulers.py.txt'])
 progress.update(stage='native_image_processor',torch_version=str(torch.__version__),numpy_version=str(np.__version__),opencv_version=str(cv2.__version__))
 processor=prep.ImageProcessorV2(size=512,border_ratio=.15)
 with Image.open(io.BytesIO(raw)) as image:
  rgba=np.asarray(image).copy();pil_image=image.copy()
 rgb,mask=processor(pil_image,to_tensor=False,return_mask=True)
 by_path,mask_path=processor(str(Path(conditioning)/'object_conditioning.png'),to_tensor=False,return_mask=True)
 require(np.array_equal(rgb,by_path) and np.array_equal(mask,mask_path),'PIL_path_preprocessing_disagrees')
 # Independently reconstruct the saved native half-open crop and alpha compositing.
 c=report['recenter'];x0,y0,x1,y1=c['native_crop_xyxy_exclusive'];w,h=c['resize_wh'];x,y=c['paste_xy']
 canvas=np.zeros((512,512,4),dtype=np.uint8);canvas[y:y+h,x:x+w]=cv2.resize(rgba[y0:y1,x0:x1],(w,h),interpolation=cv2.INTER_AREA)
 alpha=canvas[...,3:4].astype(np.float32)/255
 expected=(canvas[...,:3]*alpha+255*(1-alpha)).clip(0,255).astype(np.uint8)
 expected_mask=(alpha*255).clip(0,255).astype(np.uint8)
 require(rgb.dtype==mask.dtype==np.uint8 and rgb.shape==(512,512,3) and mask.shape==(512,512,1),'processed_image_shape')
 require(np.array_equal(rgb,expected) and np.array_equal(mask,expected_mask),'native_crop_composite_mismatch')
 image_tensor,mask_tensor=processor(pil_image,to_tensor=True,return_mask=True)
 expected_tensor=torch.from_numpy(rgb.copy()).float().permute(2,0,1).unsqueeze(0)/255*2-1
 expected_mask_tensor=torch.from_numpy(mask.copy()).float().permute(2,0,1).unsqueeze(0)/255*2-1
 require(torch.equal(image_tensor,expected_tensor) and torch.equal(mask_tensor,expected_mask_tensor),'native_tensor_values')
 require(tuple(image_tensor.shape)==(1,3,512,512) and tuple(mask_tensor.shape)==(1,1,512,512) and torch.isfinite(image_tensor).all() and torch.isfinite(mask_tensor).all(),'native_tensor_contract')
 artifacts={}
 for name,im in [('model_image.png',Image.fromarray(rgb)),('model_alpha.png',Image.fromarray(mask[...,0]))]:
  b=io.BytesIO();im.save(b,format='PNG');artifacts[name]=b.getvalue()
 for name,t in [('model_image.npy',image_tensor),('model_mask.npy',mask_tensor)]:
  b=io.BytesIO();np.save(b,t.numpy(),allow_pickle=False);artifacts[name]=b.getvalue()
 progress.update(PIL_path_equal=True,crop_composite_exact=True,tensor_values_exact=True,image_shape=list(image_tensor.shape),mask_shape=list(mask_tensor.shape),image_range=[float(image_tensor.min()),float(image_tensor.max())],mask_range=[float(mask_tensor.min()),float(mask_tensor.max())],model_alpha_nonzero=int(np.count_nonzero(mask)),stage='synthetic_scheduler')
 scheduler=sched.FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000);scheduler.set_timesteps(4,device='cpu')
 sigmas=scheduler.sigmas.tolist();require(len(sigmas)==5 and all(a<=b for a,b in zip(sigmas,sigmas[1:])) and sigmas[-1]==1,'scheduler_direction')
 sample=torch.arange(8,dtype=torch.float32).reshape(1,2,4)/8;velocity=torch.full_like(sample,.25,requires_grad=True);initial=sample.clone();records=[]
 for i,t in enumerate(scheduler.timesteps):
  final=scheduler.step_final(velocity,t,sample);idx=scheduler.step_index;expected_final=sample+(1-float(scheduler.sigmas[i]))*velocity
  require(torch.allclose(final,expected_final,atol=1e-7,rtol=0),'scheduler_final_equation')
  preview=scheduler.step_no_update(velocity,t,sample);require(scheduler.step_index==idx,'scheduler_preview_advanced')
  expected_next=sample+(float(scheduler.sigmas[i+1])-float(scheduler.sigmas[i]))*velocity
  result=scheduler.step(velocity,t,sample);require(scheduler.step_index==i+1 and torch.allclose(result.prev_sample,expected_next,atol=1e-7,rtol=0) and torch.equal(preview.prev_sample,result.prev_sample),'scheduler_step_equation')
  records.append(dict(index=i,sigma=sigmas[i],next_sigma=sigmas[i+1],sample_mean=float(result.prev_sample.detach().mean())));sample=result.prev_sample
 require(torch.allclose(sample,initial+(1-sigmas[0])*velocity,atol=2e-7,rtol=0),'scheduler_endpoint')
 gradient=torch.autograd.grad(sample.sum(),velocity)[0];require(torch.isfinite(gradient).all() and torch.allclose(gradient,torch.full_like(gradient,1-sigmas[0]),atol=2e-7,rtol=0),'scheduler_gradient')
 require(torch.equal(rng,torch.get_rng_state()),'unexpected_random_sampling')
 for n,b in sources.items():require(reader.regular(Path(sources_folder)/n,1024**2)==b,'source_mutated:'+n)
 require(reader.regular(Path(conditioning)/'object_conditioning.png',2*1024**2)==raw,'conditioning_mutated')
 progress.update(stage='complete',scheduler_records=records,scheduler_equations_verified=True,scheduler_gradient_finite=True,random_state_unchanged=True,synthetic_scheduler_steps=4)
 result=dict(schema='tracehoi.NativeConditioningCPUPreflight.v1',passed=True,device='cpu',runtime_receipt_sha256=sha,conditioning_binding=pin(raw),source_bindings=PINS,diagnostics=progress,
  output_bindings={n:pin(b) for n,b in artifacts.items()},native_conditioning_execution_verified=True,backend_execution_ready=False,native_execution_verified=False,rectified_flow_executed=False,
  model_calls=0,optimizer_steps=0,contact_terms_used=False,model_latent_sampled=False,placement_ready=False)
 return result,artifacts
def viewer(report,image,conditioning):
 data=dict(report=report,image='data:image/png;base64,'+base64.b64encode(image).decode(),conditioning='data:image/png;base64,'+base64.b64encode(conditioning).decode())
 page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TraceHOI · Native conditioning</title><style>*{box-sizing:border-box}body{margin:0;background:#091421;color:#e9f2fb;font:16px system-ui}main{max-width:1120px;margin:auto;padding:32px}h1{font-size:40px}p{line-height:1.6;color:#bccddd}.tag,a{color:#7ae1c8}section{background:#13273b;border:1px solid #3b526b;border-radius:16px;padding:24px;margin:24px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%;border-radius:8px;background:repeating-conic-gradient(#344659 0% 25%,#233548 0% 50%) 0/18px 18px}button{background:#25475e;color:white;border:1px solid #65849b;padding:10px;border-radius:8px;cursor:pointer;margin:3px}button[aria-pressed=true]{background:#226f61}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;overflow:auto}input{font:inherit}#badge{color:#f5cd86}iframe{width:100%;height:600px;border:0}@media(max-width:720px){main{padding:16px}h1{font-size:30px}.grid{grid-template-columns:1fr}}</style><main><span class="tag">TRACEHOI / IMAGE CONDITIONING → JOINT FLOW</span><h1>Keep the visual pose. Prepare the model input.</h1><p>Y9 verified the native hand and laptop transforms. This check follows the laptop pixels through native preprocessing and verifies the scheduler with a small synthetic tensor. No model or contact optimization runs.</p><section><b>Native conditioning: <span id="badge">Pending server</span></b><p>Scene initialization remains ready. Joint rectified-flow execution remains pending.</p></section><div class="grid"><section><h2>Saved image coordinates</h2><button id="original">Original RGB</button><button id="cutout">Laptop RGBA</button><img id="source" alt="Saved image or laptop-only conditioning"><p>The scene camera, hand box, geometry and masks stay in the original 512 × 512 coordinates.</p></section><section><h2>Model coordinates</h2><button id="color">Processed RGB</button><button id="alpha">Processed alpha</button><img id="processed" alt="Native recentered model input" hidden><p id="pending">The server will produce the recentered image and alpha mask.</p><p>Native preprocessing recenters the object and leaves a 15% border. This image is for conditioning; it does not replace scene masks or camera coordinates.</p></section></div><section><h2>Inspect the contract</h2><button data-tab="crop">Crop and resize</button><button data-tab="flow">Scheduler convention</button><button data-tab="latent">Saved mesh and latent</button><h3 id="title"></h3><p id="explanation"></p><pre id="details"></pre></section><section><h2>Load the native result</h2><p id="message">Load native_conditioning_preflight.json after the server run.</p><input type="file" id="result" aria-label="Load native conditioning result JSON" accept=".json"><details><summary>Result details</summary><pre id="result-data"></pre></details></section><section><h2>Initial scene</h2><a href="scene.html">Open interactive hand and laptop scene ↗</a><p>Contact remains a downstream joint-flow objective. Model weights, latent restart/inversion, the full renderer and the joint regressor still require validation.</p><a href="conditioning.json">Conditioning contract</a></section></main><script>const D=DATA,$=id=>document.getElementById(id);function source(k){$('source').src=D[k];$('original').setAttribute('aria-pressed',k==='image');$('cutout').setAttribute('aria-pressed',k==='conditioning')}source('conditioning');$('original').onclick=()=>source('image');$('cutout').onclick=()=>source('conditioning');function processed(alpha){$('processed').hidden=true;$('pending').hidden=false;$('processed').onload=()=>{$('processed').hidden=false;$('pending').hidden=true};$('processed').onerror=()=>{$('processed').hidden=true;$('pending').hidden=false};$('processed').src=alpha?'model_alpha.png':'model_image.png';$('color').setAttribute('aria-pressed',!alpha);$('alpha').setAttribute('aria-pressed',alpha)}$('color').onclick=()=>processed(false);$('alpha').onclick=()=>processed(true);const tabs={crop:['Native crop behavior','Preserve the installed preprocessor exactly, including its half-open crop bounds. No original input is edited.',D.report.recenter],flow:['Noise-to-data convention','The installed scheduler advances sigma toward one. Four deterministic synthetic steps will check endpoint prediction, index handling and gradients; they are not model inference.',['x_next = x + (sigma_next − sigma) × velocity','x_endpoint = x + (1 − sigma) × velocity']],latent:['A mesh is not a diffusion latent','The installed ShapeVAE exposes a decoder but no mesh encoder. The current joint loop does not pass a saved latent to prepare_latents. A validated latent restart or inversion path is still needed to preserve the saved shape.',D.report.source_contract]};function tab(k){let a=tabs[k];$('title').textContent=a[0];$('explanation').textContent=a[1];$('details').textContent=JSON.stringify(a[2],null,2);document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.tab===k))}document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));tab('crop');$('result').onchange=async e=>{try{let f=e.target.files[0];if(!f||f.size>1048576)throw Error('Choose a JSON under 1 MiB.');let r=JSON.parse(await f.text());if(r.schema!=='tracehoi.NativeConditioningCPUPreflight.v1'||r.runtime_receipt_sha256!==D.report.source_receipt_sha256||r.conditioning_binding?.sha256!==D.report.conditioning_binding.sha256)throw Error('Result does not match these inputs.');$('badge').textContent=r.fixture_only?'Synthetic test':r.passed===true?'Passed':'Failed';$('message').textContent=r.fixture_only?'Synthetic UI test only; no native execution.':r.passed===true?'Native preprocessing and synthetic scheduler checks passed. Joint-flow model execution is still pending.':'Check failed; keep partial outputs.';$('result-data').textContent=JSON.stringify(r,null,2);if(r.passed&&!r.fixture_only)processed(false)}catch(x){$('badge').textContent='Not verified';$('message').textContent=x.message;$('result-data').textContent=''}};</script></html>'''
 return page.replace('DATA',json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c'))
