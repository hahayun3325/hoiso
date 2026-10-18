"""Numeric HaMeR input and integer-pixel camera adapter for a saved initializer.

No native libraries are imported by this module. The camera factory receives
torch and PerspectiveCameras explicitly. Full joint-flow execution remains a
separate operation; this module does not provide an inference launcher.
"""
import ast
import copy
import hashlib
import json
import math
import struct
from pathlib import Path

PURPOSE = 'native_camera_adapter'

def require(ok, message):
    if not ok: raise ValueError(message)

def pin(raw): return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def encode(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def numeric_array(raw, shape):
    """Accept only the exact non-pickled float32 NPY form emitted by V6."""
    require(raw[:8] == b'\x93NUMPY\x01\x00' and len(raw)>=10,'numeric_npy_version')
    size=struct.unpack('<H',raw[8:10])[0]
    require(0<size<=256 and len(raw)>=10+size,'numeric_npy_header')
    header=ast.literal_eval(raw[10:10+size].decode('ascii').strip())
    require(header==dict(descr='<f4',fortran_order=False,shape=tuple(shape)),'numeric_npy_type_shape')
    count=math.prod(shape)
    require(len(raw)==10+size+4*count,'numeric_npy_size')
    values=struct.unpack('<'+'f'*count,raw[10+size:])
    require(all(math.isfinite(v) for v in values),'numeric_npy_nonfinite')
    return [list(values[i:i+shape[-1]]) for i in range(0,count,shape[-1])]

class NumericGuidance:
    """Read a bound 21x2 numeric file; never deserialize an object array."""
    def __init__(self,path,binding,reader):
        self.path=Path(path).absolute();self.binding=copy.deepcopy(binding);self.reader=reader
    def load(self,path):
        require(Path(path).absolute()==self.path,'guidance_path_changed')
        raw=self.reader.regular(self.path,4096)
        require(pin(raw)==self.binding,'guidance_binding_changed')
        return {'mano_2d_kps':numeric_array(raw,(21,2))}

def patch_source(raw,handoff):
    """Extend the U5 private overlay at exactly two numeric-input seams."""
    s=handoff.patch_source(raw).decode()
    edits=[('_tracehoi_handoff=None, **kwargs,','_tracehoi_handoff=None, _tracehoi_numeric=None, **kwargs,'),
           ('hamer4guid = np.load(hamer_for_guid_path, allow_pickle=True).item()',
            'hamer4guid = (_tracehoi_numeric.load(hamer_for_guid_path) if _tracehoi_numeric is not None else np.load(hamer_for_guid_path, allow_pickle=True).item())')]
    for before,after in edits:
        require(s.count(before)==1,'numeric_loader_seam_changed');s=s.replace(before,after,1)
    ast.parse(s);return s.encode()

def camera_contract(camera):
    size=camera['image_size_wh'];K=camera['K_integer_pixel_centers']
    require(isinstance(size,list) and len(size)==2 and all(type(v) is int and 1<=v<=8192 for v in size),'camera_size')
    require(isinstance(K,list) and len(K)==3 and all(isinstance(row,list) and len(row)==3 for row in K),'camera_K_shape')
    require(all(type(v) in (int,float) and math.isfinite(v) for row in K for v in row),'camera_K_finite')
    require(K[0][0]>0 and K[1][1]>0 and K[0][1]==K[1][0]==0 and K[2]==[0,0,1],'camera_K_form')
    require(camera['pixel_centers']=='integer_xy' and camera['scene_to_opencv']==[[1,0,0],[0,-1,0],[0,0,-1]],'camera_frame')
    return dict(image_size_hw=[size[1],size[0]],focal_length=[K[0][0],K[1][1]],
                principal_point_edge=[K[0][2]+.5,K[1][2]+.5],
                R_scene_to_pytorch3d=[[-1,0,0],[0,1,0],[0,0,-1]],T=[0,0,0],
                screen_result_offset_xy=[-.5,-.5],in_ndc=False,
                screen_api='integer_xy',raster_samples='pixel_cell_centers',znear=.01,zfar=100.,
                normal_frame='mesh_world_scene_axes',normal_shader='legacy_sum_of_vertex_normals_then_global_minmax',
                normal_is_metric_camera_normal=False)

def project(points,camera):
    camera_contract(camera);K=camera['K_integer_pixel_centers'];out=[]
    for p in points:
        require(len(p)==3 and all(math.isfinite(x) for x in p) and p[2]<0,'point_front_finite')
        out.append([K[0][0]*p[0]/-p[2]+K[0][2],K[1][1]*-p[1]/-p[2]+K[1][2]])
    return out

def make_camera(camera,torch,PerspectiveCameras,*,device='cpu'):
    """Raster in edge coordinates; expose integer centers to the keypoint loss.

    Rasterization calls transform_points / transform_points_ndc directly, so it
    retains the half-pixel principal-point shift. The native HaMeR loss calls
    transform_points_screen and receives the original integer-center pixels.
    """
    c=camera_contract(camera)
    class IntegerCenterCamera(PerspectiveCameras):
        def transform_points_screen(self,points,eps=None,with_xyflip=True,**kwargs):
            require(with_xyflip is True,'integer_camera_requires_xyflip')
            result=super().transform_points_screen(points,eps=eps,with_xyflip=True,**kwargs)
            return result-result.new_tensor([.5,.5,0.])
    result = IntegerCenterCamera(device=device,in_ndc=False,
        focal_length=torch.tensor([c['focal_length']],dtype=torch.float32,device=device),
        principal_point=torch.tensor([c['principal_point_edge']],dtype=torch.float32,device=device),
        image_size=torch.tensor([c['image_size_hw']],dtype=torch.float32,device=device),
        R=torch.tensor([c['R_scene_to_pytorch3d']],dtype=torch.float32,device=device),
        T=torch.tensor([c['T']],dtype=torch.float32,device=device))
    result.znear=c['znear'];result.zfar=c['zfar']
    return result

def load_runtime(folder,sha,reader):
    folder=Path(folder);raw=reader.regular(folder/'files.json',1024**2)
    require(pin(raw)['sha256']==sha,'runtime_receipt_binding')
    m=json.loads(raw);require(m['schema']=='tracehoi.RuntimeInputFiles.v1','runtime_receipt_schema')
    require(len(m['files'])==22,'runtime_inventory')
    files={}
    for n,b in m['files'].items():
        require(Path(n).name==n and '\\' not in n and n not in ('.','..'),'runtime_member_path')
        files[n]=reader.regular(folder/n,16*1024**2);require(pin(files[n])==b,'runtime_member_changed:'+n)
    files['files.json']=raw
    r=json.loads(files['runtime.json']);require(r['runtime_inputs_complete'] and r['initialization_ready'] and not r['contact_terms_used'],'runtime_not_ready')
    return files,r

def build(folder,sha,raw,handoff,reader,*,purpose):
    require(purpose==PURPOSE,'native_camera_adapter_purpose_required')
    files,previous=load_runtime(folder,sha,reader)
    kps=numeric_array(files['hamer_keypoints.npy'],(21,2));rt=numeric_array(files['h2m.npy'],(4,4))
    require(rt[3]==[0,0,0,1],'h2m_bottom_row')
    camera=json.loads(files['camera.json']);contract=camera_contract(camera);overlay=patch_source(raw,handoff)
    # Execute the actual patched assignment with a legacy loader that must not run.
    node=[n for n in ast.walk(ast.parse(overlay)) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='hamer4guid' for t in n.targets)]
    require(len(node)==1,'guidance_assignment_count')
    class NoPickle:
        def load(self,*args,**kw):raise ValueError('pickle_loader_called')
    loader=NumericGuidance(Path(folder)/'hamer_keypoints.npy',pin(files['hamer_keypoints.npy']),reader)
    env=dict(_tracehoi_numeric=loader,hamer_for_guid_path=loader.path,np=NoPickle())
    exec(compile(ast.Module(body=node,type_ignores=[]),'<numeric guidance seam>','exec'),env)
    require(env['hamer4guid']=={'mano_2d_kps':kps},'guidance_values_changed')
    report=dict(schema='tracehoi.NativeCameraAdapter.v1',case_id=previous['case_id'],
        adapter_complete=True,numeric_loader_seam_verified=True,camera_contract_complete=True,
        native_camera_execution_verified=False,backend_execution_ready=False,native_execution_verified=False,
        initialization_ready=True,contact_terms_used=False,rectified_flow_executed=False,model_calls=0,
        source_meshes_modified=False,original_masks_modified=False,placement_ready=False,full_parent_acceptance=False,
        source_receipt_sha256=sha,camera=contract,keypoints=kps,source_overlay=pin(overlay),
        fixture_preview=raster_diagnostics(raster_fixture()['expected_mask'],raster_fixture()),
        pending=['native_CPU_camera_preflight','object_conditioning_and_latent_initialization_policy',
                 'native_model_and_asset_preflight','bounded_joint_rectified_flow_execution'])
    out={n:files[n] for n in files if n!='index.html' and n!='files.json'}
    out.update({'adapter.json':encode(report),'camera_contract.json':encode(contract),'pipeline_overlay.py.txt':overlay,
                'index.html':viewer(report,files['image.png']).encode(),
                'README.md':b'# Native camera and numeric guidance adapter\n\nOpen index.html with all companion files. CPU initialization is preserved; contact belongs to subsequent joint rectified-flow optimization. Native preflight results, if present, are separate from full backend readiness. Keep original terminals and evidence archives.\n'})
    out['files.json']=encode(dict(schema='tracehoi.NativeCameraAdapterFiles.v1',files={n:pin(b) for n,b in out.items()}))
    return report,out

def verify(folder,receipt_sha,source,source_sha,raw,handoff,reader,*,purpose):
    r,files=build(source,source_sha,raw,handoff,reader,purpose=purpose)
    require(pin(files['files.json'])['sha256']==receipt_sha,'adapter_receipt_binding')
    require(set(p.name for p in Path(folder).iterdir())==set(files),'adapter_inventory')
    for n,b in files.items():require(reader.regular(Path(folder)/n,16*1024**2)==b,'adapter_output_changed:'+n)
    return dict(verified=True,receipt_binding=pin(files['files.json']),adapter_complete=True,
                initialization_ready=True,backend_execution_ready=False,placement_ready=False)


def raster_fixture(*, legacy=False, shift_xy=(0.,0.)):
    """Analytic quads with an independent integer-center coverage oracle.

    Recovery offsets shared diagonals by 1/8 pixel; outer mask membership is
    unchanged. W7 put eight centers on shared edges, whose fill is not stable
    across floating point implementations of strict triangle interiors.
    """
    dy=0. if legacy else -.125
    regions=[(4.75,8.25,6.75+dy,10.25+dy,2.),
             (19.75,23.25,12.75+dy,16.25+dy,3.)]
    vertices=[];faces=[];mask=[[False]*48 for _ in range(32)];depth=[[0.]*48 for _ in range(32)]
    edges=[]
    for x0,x1,y0,y1,z in regions:
        x0+=shift_xy[0];x1+=shift_xy[0];y0+=shift_xy[1];y1+=shift_xy[1]
        corners=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)];k=len(vertices)
        vertices.extend([( (x-13.3)*z/35.,-(y-19.7)*z/42.,-z) for x,y in corners])
        faces.extend([[k,k+2,k+1],[k,k+3,k+2]])
        edges.extend([(corners[0],corners[1]),(corners[1],corners[2]),(corners[2],corners[3]),(corners[3],corners[0]),(corners[0],corners[2])])
        for y in range(32):
            for x in range(48):
                if x0<x<x1 and y0<y<y1:mask[y][x]=True;depth[y][x]=z
    def distance(x,y,a,b):
        dx=b[0]-a[0];dy=b[1]-a[1]
        t=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
        return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
    margins=[[min(distance(x,y,a,b) for a,b in edges) for x in range(48)] for y in range(32)]
    ties=[[x,y] for y in range(32) for x in range(48) if margins[y][x]<1e-9]
    return dict(vertices=vertices,faces=faces,expected_mask=mask,expected_depth=depth,
                image_size_hw=[32,48],minimum_edge_margin_px=min(map(min,margins)),
                edge_tie_pixels_xy=ties,legacy=legacy)

def raster_diagnostics(observed, fixture):
    require(len(observed)==32 and all(len(row)==48 and all(type(x) is bool for x in row) for row in observed),'raster_diagnostic_shape')
    expected=fixture['expected_mask'];missing=[];extra=[]
    for y in range(32):
        for x in range(48):
            if expected[y][x] and not observed[y][x]:missing.append([x,y])
            if observed[y][x] and not expected[y][x]:extra.append([x,y])
    ties=fixture['edge_tie_pixels_xy']
    return dict(expected_mask=expected,observed_mask=observed,missing_pixels_xy=missing,extra_pixels_xy=extra,
        image_size_hw=[32,48],expected_pixels=sum(map(sum,expected)),observed_pixels=sum(map(sum,observed)),
        mask_exact=not missing and not extra,minimum_edge_margin_px=fixture['minimum_edge_margin_px'],
        edge_tie_pixels_xy=ties,all_mismatches_on_shared_edges=bool(missing or extra) and all(xy in ties for xy in missing+extra))

def native_cpu_preflight(folder,sha,reader,*,progress=None):
    """One CPU-only projection/raster test; no backend import or model weights."""
    progress={} if progress is None else progress
    progress.update(stage='native_imports')
    files,previous=load_runtime(folder,sha,reader)
    import torch
    import numpy as np
    import pytorch3d
    from pytorch3d.renderer.cameras import PerspectiveCameras
    from pytorch3d.renderer.mesh.rasterizer import MeshRasterizer,RasterizationSettings
    from pytorch3d.structures import Meshes
    progress.update(stage='projection',torch_version=str(torch.__version__),numpy_version=str(np.__version__),pytorch3d_version=str(getattr(pytorch3d,'__version__','unknown')))
    torch.set_num_threads(1)
    camera=json.loads(files['camera.json']);cam=make_camera(camera,torch,PerspectiveCameras)
    vertices,_=reader.mesh(files['scene_observed.ply']);hand,_=reader.mesh(files['hand_initial.ply'])
    points=list(vertices)+list(hand)
    p=torch.tensor(points,dtype=torch.float32,device='cpu',requires_grad=True)
    got=cam.transform_points_screen(p,image_size=tuple(reversed(camera['image_size_wh'])))[:,:2]
    expect=torch.tensor(project(points,camera),dtype=torch.float32)
    error=float((got-expect).abs().max().detach())
    progress.update(projected_points=len(points),max_projection_error_px=error)
    require(error<.001,'native_projection_mismatch')
    got.square().mean().backward();require(torch.isfinite(p.grad).all().item(),'native_projection_gradient')
    progress.update(stage='raster',projection_gradient_finite=True)
    small=dict(camera,image_size_wh=[48,32],K_integer_pixel_centers=[[35.,0.,13.3],[0.,42.,19.7],[0.,0.,1.]])
    c=make_camera(small,torch,PerspectiveCameras)
    raster=MeshRasterizer(cameras=c,raster_settings=RasterizationSettings(image_size=(32,48),blur_radius=0.,faces_per_pixel=1,bin_size=0,perspective_correct=True,cull_backfaces=False))
    # The legacy fixture is diagnostic only. New acceptance uses a separate
    # edge-separated fixture, an exact full-image mask and unchanged tolerance.
    for legacy in [True,False]:
        f=raster_fixture(legacy=legacy)
        mesh=Meshes(verts=[torch.tensor(f['vertices'],dtype=torch.float32)],faces=[torch.tensor(f['faces'],dtype=torch.int64)])
        frag=raster(mesh);hit=frag.pix_to_face[0,:,:,0]>=0
        detail=raster_diagnostics(hit.tolist(),f)
        progress['legacy_fixture' if legacy else 'raster_fixture']=detail
        if not legacy:
            require(f['minimum_edge_margin_px']>.08 and not f['edge_tie_pixels_xy'],'fixture_edge_margin')
            require(detail['mask_exact'],'native_pixel_center_raster_mismatch')
    depth=torch.tensor(f['expected_depth'])
    depth_error=float((frag.zbuf[0,:,:,0][hit]-depth[hit]).abs().max())
    progress.update(stage='depth_and_normals',max_depth_error=depth_error)
    require(depth_error<1e-5,'native_raster_depth_mismatch')
    normals=mesh.faces_normals_packed();normal_error=float((normals-torch.tensor([0.,0.,1.])).abs().max())
    progress.update(max_world_normal_error=normal_error,stage='numeric_loader')
    require(normal_error<1e-5,'native_world_normal_orientation')
    # Read both arrays with the real NumPy non-pickle path, and compare exact
    # float32 values to the stdlib loader consumed by the patched backend seam.
    import io,inspect
    for name,shape in [('hamer_keypoints.npy',(21,2)),('h2m.npy',(4,4))]:
        arr=np.load(io.BytesIO(files[name]),allow_pickle=False)
        require(arr.dtype==np.dtype('<f4') and arr.shape==shape and arr.tolist()==numeric_array(files[name],shape),'native_numeric_loader_mismatch')
    installed={}
    for obj in [PerspectiveCameras,MeshRasterizer]:
        path=Path(inspect.getfile(obj));installed[str(path)]=pin(reader.regular(path,2*1024**2))
    progress['stage']='complete'
    return dict(schema='tracehoi.NativeCameraCPUPreflight.v1',passed=True,device='cpu',
        diagnostics=progress,
        runtime_receipt_sha256=sha,torch_version=str(torch.__version__),pytorch3d_version=str(getattr(pytorch3d,'__version__','unknown')),
        numpy_version=str(np.__version__),installed_source_bindings=installed,
        projected_points=len(points),max_projection_error_px=error,projection_gradient_finite=True,
        raster_test_image_size_hw=[32,48],raster_triangles=4,raster_pixels=int(hit.sum()),
        raster_mask_exact=True,max_depth_error=depth_error,max_world_normal_error=normal_error,
        normal_shader_executed=False,normal_shader_convention='legacy world-space sum and global min-max; not metric camera normals',
        numeric_numpy_agrees=True,model_calls=0,explicit_cuda_calls=0,backend_execution_ready=False,
        native_execution_verified=False,rectified_flow_executed=False,contact_terms_used=False,placement_ready=False)

def viewer(r,image):
    import base64
    data=json.dumps(r).replace('<','\\u003c');url='data:image/png;base64,'+base64.b64encode(image).decode()
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TraceHOI · Camera & guidance</title><style>body{margin:0;background:#0b1420;color:#ecf3fa;font:16px system-ui}main{max-width:1120px;margin:auto;padding:36px}h1{font-size:38px;margin:12px 0}p{color:#b4c7d7;line-height:1.6}section{background:#142437;padding:24px;border-radius:16px;margin:20px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}canvas{width:100%;max-width:512px;background:#fff;border-radius:8px}button,select{padding:10px 14px;border:1px solid #69849a;border-radius:7px;color:inherit;background:#243c54;margin:4px}button[aria-pressed=true]{background:#216f79}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}a{color:#6edcdb}.tag{color:#78ddd3}iframe{width:100%;height:700px;border:0}@media(max-width:800px){.grid{grid-template-columns:1fr}h1{font-size:30px}}</style><main><span class="tag">TraceHOI / native input adapter</span><h1>One camera, two pixel conventions</h1><p>The saved hand pose stays fixed. Numeric HaMeR guidance and the fresh scene camera are prepared for the later joint rectified-flow stage.</p><section class="grid"><div><canvas id="image" width="512" height="512"></canvas><button id="points" aria-pressed="true">HaMeR keypoints</button><p>These are HaMeR predictions used for guidance, not independently measured targets.</p></div><div><h2>Inspect the coordinate contract</h2><select id="mode"><option value="screen">Keypoint projection</option><option value="raster">Raster pixel sampling</option><option value="normal">Normal convention</option><option value="loader">Numeric loader</option></select><p id="description"></p><pre id="contract"></pre></div></section><section><h2>Native CPU preflight</h2><p id="probe-status">Load native_preflight.json from the collected server workspace to inspect the actual CPU projection and raster checks. This preview has not executed that preflight.</p><input id="probe-file" type="file" accept=".json"><details><summary>Native result details</summary><pre id="probe" style="max-height:360px;overflow:auto"></pre></details><p><a href="native_preflight.json">Open server preflight results</a> · <a href="adapter.json">Adapter record</a></p></section><section><h2>Raster test inspection</h2><p id="raster-label">Analytic expected coverage only. Load the server JSON above for observed pixels and differences.</p><select id="fixture"><option value="raster_fixture">Recovery fixture</option><option value="legacy_fixture">W7 edge-tie fixture</option></select><select id="layer"><option value="expected">Expected</option><option value="observed">Observed</option><option value="difference">Differences</option></select><canvas id="raster-grid" width="576" height="384"></canvas><pre id="raster-info"></pre></section><section><h2>Preserved visual initialization</h2><p>Contact and penetration objectives belong to downstream joint optimization. No model, contact fitting, or pose change is performed here.</p><button id="scene-button">Load initial scene</button><div id="scene"></div></section><section><h2>Remaining runtime work</h2><p>The CPU camera preflight does not certify full backend execution. Object conditioning and latent initialization policy, model assets and a bounded joint-flow run remain to be checked.</p><details><summary>Inspect private loader overlay</summary><a href="pipeline_overlay.py.txt">Open source overlay</a></details></section></main><script>const R=DATA;let img=new Image(),show=true;const cv=document.getElementById('image'),ctx=cv.getContext('2d');function draw(){ctx.drawImage(img,0,0,512,512);if(show)for(const [x,y] of R.keypoints){ctx.beginPath();ctx.arc(x,y,3,0,7);ctx.fillStyle='#00d9ed';ctx.fill();ctx.strokeStyle='#102334';ctx.stroke()}}img.onload=draw;img.src='IMAGE';document.getElementById('points').onclick=function(){show=!show;this.setAttribute('aria-pressed',show);draw()};const modes={screen:['The native keypoint loss receives integer pixel centers: the original HaMeR convention.',{screen_offset:R.camera.screen_result_offset_xy,scene_to_view:R.camera.R_scene_to_pytorch3d}],raster:['The rasterizer samples pixel cells. Its principal point includes a half-pixel shift; rasterization keeps that shift.',{principal_point:R.camera.principal_point_edge,image_size_hw:R.camera.image_size_hw,focal:R.camera.focal_length}],normal:['The recorded native shader uses mesh/world normals and global normalization. It does not produce metric camera-space normals.',{frame:R.camera.normal_frame,shader:R.camera.normal_shader}],loader:['The private adapter reads only a bound 21×2 float32 array. No pickle deserialization occurs on the opt-in path.',{points:R.keypoints.length,shape:[21,2],pickle:false}]};function mode(){const s=modes[document.getElementById('mode').value];document.getElementById('description').textContent=s[0];document.getElementById('contract').textContent=JSON.stringify(s[1],null,2)}document.getElementById('mode').onchange=mode;mode();document.getElementById('scene-button').onclick=function(){let f=document.createElement('iframe');f.src='scene.html';f.title='Saved visual initial scene';document.getElementById('scene').replaceChildren(f);this.hidden=true};let nativeDiagnostics=null,nativeFixtureOnly=false;function rasterView(){const choice=document.getElementById('fixture').value,layer=document.getElementById('layer').value,d=nativeDiagnostics&&nativeDiagnostics[choice],v=d||R.fixture_preview,c=document.getElementById('raster-grid'),g=c.getContext('2d');g.fillStyle='#09111b';g.fillRect(0,0,c.width,c.height);if(!d&&(choice!=='raster_fixture'||layer!=='expected')){document.getElementById('raster-label').textContent='Server observation unavailable; no observed pixels are shown.';document.getElementById('raster-info').textContent='';return}for(let y=0;y<32;y++)for(let x=0;x<48;x++){const e=v.expected_mask[y][x],o=d?d.observed_mask[y][x]:false;g.fillStyle=layer==='expected'?(e?'#62ded4':'#122234'):layer==='observed'?(o?'#8ab7ff':'#122234'):e===o?'#122234':e?'#ffbf69':'#ff687c';g.fillRect(x*12+1,y*12+1,10,10)}document.getElementById('raster-label').textContent=d?(nativeFixtureOnly?'Synthetic UI test only; no native execution.':'Loaded server observation: cyan expected, blue observed; differences use amber missing and pink extra.'):'Analytic expected coverage only; native execution pending.';document.getElementById('raster-info').textContent=JSON.stringify({expected_pixels:v.expected_pixels,observed_pixels:d?d.observed_pixels:null,minimum_edge_margin_px:v.minimum_edge_margin_px,edge_ties:v.edge_tie_pixels_xy,missing:d?d.missing_pixels_xy:null,extra:d?d.extra_pixels_xy:null},null,2)}document.getElementById('fixture').onchange=rasterView;document.getElementById('layer').onchange=rasterView;rasterView();document.getElementById('probe-file').onchange=async function(){try{const p=JSON.parse(await this.files[0].text());if(p.schema!=='tracehoi.NativeCameraCPUPreflight.v1')throw Error('Unexpected preflight format');if(p.fixture_only!==true&&p.runtime_receipt_sha256!==R.source_receipt_sha256)throw Error('This record belongs to different runtime inputs');document.getElementById('probe-status').textContent=p.fixture_only?'Synthetic UI test only; no native execution.':p.passed?'CPU preflight passed. Full backend execution remains pending.':'CPU preflight did not pass.';document.getElementById('probe').textContent=JSON.stringify(p,(key,value)=>['expected_mask','observed_mask'].includes(key)?'[see raster inspection]':value,2);nativeDiagnostics=p.diagnostics||null;nativeFixtureOnly=p.fixture_only===true;rasterView()}catch(e){nativeDiagnostics=null;document.getElementById('probe-status').textContent=e.message;rasterView()}};</script></html>'''.replace('DATA',data).replace('IMAGE',url)
