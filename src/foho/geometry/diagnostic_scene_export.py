"""Portable, immutable diagnostic export. Never authorizes pipeline placement."""
import base64,json,math,os
from pathlib import Path

SCHEMA='tracehoi.DiagnosticSceneExport.v1'

def sample_vertices(vertices,limit=6000):
    if type(limit) is not int or not 1<=limit<=6000:raise ValueError('preview_limit')
    if not vertices:raise ValueError('empty_preview')
    # Deterministic vertex subset for display only; full meshes are retained.
    n=len(vertices);indices=list(range(n)) if n<=limit else [i*(n-1)//(limit-1) for i in range(limit)] if limit>1 else [0]
    return dict(source_count=n,indices=indices,points=[list(vertices[i]) for i in indices])

def build(manifest,digest,case,review_dir,review_sha,reader,renderer,viewer,records,ready,*,candidate_ids,purpose,record_raw=None):
    reader.require(purpose=='diagnostic','diagnostic_purpose_required')
    reader.require(type(candidate_ids) is list and candidate_ids and len(candidate_ids)==len(set(candidate_ids)) and all(c in reader.IDS for c in candidate_ids),'explicit_unique_candidates_required')
    readiness=ready.evaluate(manifest,digest,case,review_dir,review_sha,reader,renderer,viewer,records,record_raw)
    reader.require(readiness['placement_ready'] is False and any(s['id']=='diagnostic_export' and s['available'] is True for s in readiness['stages']),'diagnostic_stage_unavailable')
    m,data=reader.inspect_bundle(manifest,digest,case)
    raw=reader.regular(manifest,1024**2);reader.require(reader.binding(raw)['sha256']==digest,'source_changed')
    files={'source/scene.json':raw}
    for role,item in m['resources'].items():files['source/'+item['path']]=data[role]
    for name in ['files.json','index.html','review.json']:files['source_review/'+name]=reader.regular(Path(review_dir)/name,8*1024**2)
    reader.require(reader.binding(files['source_review/files.json'])['sha256']==review_sha,'review_changed')
    rr=reader.parse(files['source_review/files.json'])
    reader.require(all(reader.binding(files['source_review/'+name])==pin for name,pin in rr['files'].items()),'review_files_changed')
    if record_raw is not None:files['human_review.json']=record_raw
    files['readiness.json']=reader.encode(readiness)
    _,form=records.build(manifest,digest,case,review_dir,review_sha,reader,renderer,viewer)
    files['TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html']=form['index.html']
    rows=[];hands={};downloads={}
    for cid in candidate_ids:
        payload=ready.prepare_stage(manifest,digest,case,review_dir,review_sha,reader,renderer,viewer,records,stage='diagnostic_export',candidate=cid,record_raw=record_raw)
        reader.require(payload['readiness']==readiness,'readiness_changed')
        scene=payload['scene'];c=next(c for c in m['candidates'] if c['id']==cid)
        reader.require(scene['hand_mesh_bytes']==data[c['hand_asset']] and scene['object_mesh_bytes']==data['object'],'stage_mesh_changed')
        reader.require(scene['hand_model_matrix']==scene['object_model_matrix']==reader.IDENTITY,'double_transform_refused')
        v,f=reader.mesh(scene['hand_mesh_bytes']);hands[cid]=dict(vertices=v,faces=f)
        downloads[cid]=base64.b64encode(scene['hand_mesh_bytes']).decode()
        rows.append(dict(id=cid,hand_path='source/'+m['resources'][c['hand_asset']]['path'],hand_binding=reader.binding(scene['hand_mesh_bytes']),conditional_scale=c['conditional_scale'],unsigned_surface_gap=c['unsigned_surface_gap'],collision_gate=c['collision_gate'],blockers=c['blockers'],accepted=False))
    ov,of=reader.mesh(data['object']);sample=sample_vertices(ov)
    allpoints=list(ov)+[p for h in hands.values() for p in h['vertices']]
    bounds=[[min(p[k] for p in allpoints),max(p[k] for p in allpoints)] for k in range(3)]
    center=[sum(b)/2 for b in bounds];radius=max(math.dist(p,center) for p in allpoints);reader.require(math.isfinite(radius) and radius>0,'preview_extent')
    package=dict(schema=SCHEMA,case_id=case,purpose='diagnostic',export_candidate_ids=list(candidate_ids),selected_candidate=None,accepted_scale=None,
        placement_ready=False,pipeline_placement_committed=False,full_parent_acceptance=False,scale_identified=False,physical_contact_verified=False,
        geometric_accuracy_verified=False,mask_modified=False,source_geometry_modified=False,models_executed=0,
        source_manifest_binding=reader.binding(raw),source_review_binding=reader.binding(files['source_review/files.json']),review_input_binding=readiness['review']['input_binding'],
        scene_frame=m['scene_frame'],units=m['units'],camera_K=m['camera_K'],scene_to_camera=m['scene_to_camera'],mesh_model_matrix=reader.IDENTITY,
        object_path='source/'+m['resources']['object']['path'],object_binding=reader.binding(data['object']),candidates=rows,
        preview=dict(method='deterministic_vertex_subset_and_full_hand_wireframe',object_source_vertices=len(ov),object_source_faces=len(of),object_displayed_vertices=len(sample['points']),geometry_is_unchanged=True,orthographic=True,occlusion_certified=False),
        limits=['Diagnostic selection is not acceptance.','Meshes already contain scene transforms; apply no provenance transform.','Preview samples object vertices; use full PLY assets for geometry.','MoGe scale, masks, geometric accuracy and physical contact remain unverified.'])
    display=dict(package=package,object=sample['points'],hands=hands,center=center,radius=radius,original=base64.b64encode(data['original_rgb']).decode(),hand_downloads=downloads,object_download=base64.b64encode(data['object']).decode(),review_state=readiness['review']['state'])
    files['index.html']=html(display)
    files['README.md']=('Diagnostic export for '+case+'\n\nUse index.html offline. Full PLY meshes are stored under source/assets/. All source candidates and evidence remain in source/, even when the displayed/exported candidate list is a subset. Source meshes are ALREADY in scene coordinates. Never reapply provenance transforms.\n\nValidate package.json with the separately supplied SHA-256 and tools/tracehoi/export_diagnostic_scene.py verify. This checks evidence, exact file inventory, readiness, preview and mesh bytes. Hashes establish integrity against that supplied binding, not scientific accuracy. No placement is accepted. Human review remains '+readiness['review']['state']+'.\n').encode()
    package['files']={n:reader.binding(b) for n,b in files.items()};files['package.json']=reader.encode(package)
    return package,files

def publish(out,files,reader):
    out=Path(out).absolute();reader.require('..' not in out.parts and not os.path.lexists(out),'new_output_required')
    for p in [*reversed(out.parent.parents),out.parent]:reader.require(p.is_dir() and not p.is_symlink(),'output_parent_route')
    for name,b in files.items():
        p=Path(name);reader.require(not p.is_absolute() and '..' not in p.parts and p.as_posix()==name and '\\' not in name,'output_path')
        reader.require(type(b) is bytes and len(b)<=8*1024**2,'output_file_bound')
    reader.require(len(files)<=40 and sum(map(len,files.values()))<=24*1024**2,'output_bound')
    out.mkdir(mode=0o700)
    for name,b in sorted(files.items()):
        p=out/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        reader.require(reader.regular(p,8*1024**2)==b,'export_readback')
    for d in sorted([out]+[p for p in out.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):
        fd=os.open(str(d),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)

def verify(out,expected_sha,case,reader,renderer,viewer,records,ready,*,purpose):
    reader.require(purpose=='diagnostic','diagnostic_purpose_required');out=Path(out).absolute()
    raw=reader.regular(out/'package.json',1024**2);reader.require(reader.binding(raw)['sha256']==expected_sha,'export_manifest_binding');p=reader.parse(raw)
    reader.require(p['schema']==SCHEMA and p['case_id']==case and p['purpose']=='diagnostic','export_identity')
    actual={}
    for base,dirs,files in os.walk(out,followlinks=False):
        for name in dirs+files:
            path=Path(base)/name;reader.require(not path.is_symlink(),'export_symlink')
            if name in files:
                reader.require(len(actual)<40,'export_inventory_bound');actual[path.relative_to(out).as_posix()]=reader.regular(path,8*1024**2)
    reader.require(sum(map(len,actual.values()))<=24*1024**2,'export_total_bound')
    reader.require(set(actual)==set(p['files'])|{'package.json'},'export_inventory')
    reader.require({n:reader.binding(b) for n,b in actual.items() if n!='package.json'}==p['files'],'export_file_binding')
    rebuilt,expected=build(out/'source/scene.json',p['source_manifest_binding']['sha256'],case,out/'source_review',p['source_review_binding']['sha256'],reader,renderer,viewer,records,ready,candidate_ids=p['export_candidate_ids'],purpose=purpose,record_raw=actual.get('human_review.json'))
    reader.require(actual==expected and rebuilt==p,'export_semantic_mismatch')
    return dict(schema='tracehoi.DiagnosticExportReceipt.v1',package_binding=reader.binding(raw),case_id=case,candidates=p['export_candidate_ids'],files=len(actual),verified=True,purpose='diagnostic',placement_ready=False,full_parent_acceptance=False,source_geometry_modified=False)

def html(display):
    payload=json.dumps(display,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',payload).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Explore saved geometry</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c1320;color:#e8eef6;font:15px/1.5 system-ui}main{max-width:1240px;margin:auto;padding:26px}.eyebrow{color:#83d8cf;letter-spacing:2px;font-size:12px}h1{font-size:34px;margin:8px 0}h2{font-size:18px}.muted{color:#a4b5cc}.notice{padding:12px 16px;background:#2a251a;border-left:3px solid #edc56b;margin:18px 0}.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:18px}.panel{border:1px solid #34445c;background:#141e2d;border-radius:10px;padding:16px}.controls{display:flex;gap:15px;flex-wrap:wrap;align-items:center;margin:12px 0}button,select{font:inherit;color:inherit;background:#1e2c40;border:1px solid #526781;border-radius:5px;padding:8px}button,select,label{cursor:pointer}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid #83d8cf}canvas{width:100%;aspect-ratio:1;display:block;background:#0b111b;touch-action:none;border-radius:6px}img{width:100%;background:white;border-radius:6px}.metric{font-size:18px;color:#edc56b}a{color:#9dd7ff}input[type=range]{max-width:130px;vertical-align:middle}.small{font-size:12px}.legend span{display:inline-block;margin-right:18px}.hand{color:#ffa88c}.object{color:#8ad8d0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}li{margin:7px 0}@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:16px}h1{font-size:27px}}
</style></head><body><main><div class="eyebrow">TRACEHOI / PORTABLE DIAGNOSTIC EXPORT</div><h1>Explore the saved hand–object scene</h1><p id="identity" class="muted"></p><div class="notice"><strong>All candidates remain unaccepted.</strong> This viewer changes only the viewing angle. Scale, mask quality, geometric accuracy and physical contact are unresolved.</div>
<div class="grid"><section class="panel"><div class="controls"><label>Candidate <select id="candidate"></select></label><label>View <select id="preset"><option value="front">Front</option><option value="side">Side</option><option value="top">Top</option><option value="orbit">Orbit</option></select></label><button id="reset">Reset view</button></div><canvas id="scene" width="800" height="800" aria-label="Interactive diagnostic scene; drag to rotate" role="img"></canvas><div class="controls"><label>Yaw <input id="yaw" type="range" min="-180" max="180" value="0"></label><label>Pitch <input id="pitch" type="range" min="-85" max="90" value="0"></label><label>Zoom <input id="zoom" type="range" min="0.6" max="4" step="0.1" value="1"></label></div><div class="controls legend"><label class="object"><input id="object" type="checkbox" checked> Object points</label><label class="hand"><input id="hand" type="checkbox" checked> Hand wireframe</label></div><p class="muted small">Drag to orbit, or use the angle controls. Orthographic preview uses a deterministic subset of object vertices and all hand faces. It does not perform visibility, collision or contact validation. Full, unchanged meshes are available below.</p></section>
<aside class="panel"><h2>Original RGB crop</h2><img id="rgb" alt="Original 512 by 512 RGB crop"><h2 id="name"></h2><p id="collision" class="metric"></p><p id="measure"></p><ul id="blockers"></ul><p id="review" class="muted"></p><a href="TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html">Open adjacent mask review form ↗</a></aside></div>
<div class="controls"><button id="handDownload">Download diagnostic hand PLY</button><button id="objectDownload">Download diagnostic object PLY</button><button id="metaDownload">Download diagnostic metadata</button></div><p class="muted small">Meshes are already in scene coordinates (x right, y up, z backward). Do not apply source transforms again. Units follow unverified MoGe scale. Downloading a candidate does not select it for pipeline placement.</p><details><summary>Package provenance and preview limits</summary><pre id="meta"></pre></details><footer class="muted small">Offline, no network or models. Keep this HTML beside the review form. Server-side package verification checks full meshes and evidence; the sampled display is for inspection only.</footer>
<script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),P=D.package,$=id=>document.getElementById(id),C=$('scene'),ctx=C.getContext('2d'),label=s=>s.replaceAll('_',' ');for(const r of P.candidates){const o=document.createElement('option');o.value=r.id;o.textContent=label(r.id);$('candidate').append(o)}$('identity').textContent=P.case_id+' · '+P.candidates.length+' diagnostic candidates · '+D.object.length+' / '+P.preview.object_source_vertices+' object vertices displayed';$('rgb').src='data:image/png;base64,'+D.original;$('review').textContent='Human mask review: '+D.review_state+'.';$('meta').textContent=JSON.stringify(P,null,2);
function rotate(p){const yaw=+$('yaw').value*Math.PI/180,pitch=+$('pitch').value*Math.PI/180,x=p[0]-D.center[0],y=p[1]-D.center[1],z=p[2]-D.center[2],xx=Math.cos(yaw)*x+Math.sin(yaw)*z,zz=-Math.sin(yaw)*x+Math.cos(yaw)*z;return[xx,Math.cos(pitch)*y-Math.sin(pitch)*zz,Math.sin(pitch)*y+Math.cos(pitch)*zz]}
function screen(p){const r=rotate(p),k=340*+$('zoom').value/D.radius;return[400+r[0]*k,400-r[1]*k,r[2]]}
function draw(){ctx.clearRect(0,0,800,800);const cid=$('candidate').value,h=D.hands[cid];if(!h)return;const dots=$('object').checked?D.object.map(screen).sort((a,b)=>a[2]-b[2]):[];ctx.fillStyle='#8ad8d0';for(const p of dots){ctx.globalAlpha=.3+.55*(p[2]+D.radius)/(2*D.radius);ctx.fillRect(p[0]-1,p[1]-1,2,2)}ctx.globalAlpha=1;if($('hand').checked){const v=h.vertices.map(screen);ctx.strokeStyle='#ffa88c';ctx.lineWidth=.65;ctx.beginPath();for(const f of h.faces){ctx.moveTo(v[f[0]][0],v[f[0]][1]);ctx.lineTo(v[f[1]][0],v[f[1]][1]);ctx.lineTo(v[f[2]][0],v[f[2]][1]);ctx.closePath()}ctx.stroke()}const origin=[72,728],colors=['#ff8b8b','#8fdda0','#8ebdff'];for(let k=0;k<3;k++){const p=D.center.slice();p[k]+=D.radius*.14;const v=rotate(p);ctx.strokeStyle=colors[k];ctx.beginPath();ctx.moveTo(...origin);ctx.lineTo(origin[0]+v[0]*320/D.radius,origin[1]-v[1]*320/D.radius);ctx.stroke();ctx.fillStyle=colors[k];ctx.font='16px system-ui';ctx.fillText('XYZ'[k],origin[0]+v[0]*380/D.radius,origin[1]-v[1]*380/D.radius)}ctx.fillStyle='#a4b5cc';ctx.font='15px system-ui';ctx.fillText('Orthographic diagnostic preview',18,27);const c=P.candidates.find(c=>c.id===cid);$('name').textContent=label(cid);$('collision').textContent=label(c.collision_gate);$('measure').textContent='Conditional scale '+c.conditional_scale.toFixed(6)+' · unsigned gap '+c.unsigned_surface_gap.toPrecision(5);$('blockers').replaceChildren();for(const b of c.blockers){const li=document.createElement('li');li.textContent=label(b);$('blockers').append(li)}}
for(const id of ['candidate','zoom','hand','object'])$(id).addEventListener('input',draw);for(const id of ['yaw','pitch'])$(id).addEventListener('input',()=>{$('preset').value='orbit';draw()});$('preset').onchange=()=>{const v={front:[0,0],side:[90,0],top:[0,90],orbit:[35,20]}[$('preset').value];$('yaw').value=v[0];$('pitch').value=v[1];draw()};$('reset').onclick=()=>{$('preset').value='front';$('yaw').value=$('pitch').value=0;$('zoom').value=1;draw()};let drag=null;C.onpointerdown=e=>{drag=[e.clientX,e.clientY,+$('yaw').value,+$('pitch').value];C.setPointerCapture(e.pointerId)};C.onpointermove=e=>{if(!drag)return;$('yaw').value=Math.max(-180,Math.min(180,drag[2]+(e.clientX-drag[0])*.5));$('pitch').value=Math.max(-85,Math.min(90,drag[3]+(e.clientY-drag[1])*.5));$('preset').value='orbit';draw()};C.onpointerup=C.onpointercancel=()=>{drag=null};function save(raw,name,type){const url=URL.createObjectURL(new Blob([raw],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}const bytes=b=>Uint8Array.from(atob(b),c=>c.charCodeAt(0));$('handDownload').onclick=()=>save(bytes(D.hand_downloads[$('candidate').value]),'diagnostic_hand_'+$('candidate').value+'.ply','application/octet-stream');$('objectDownload').onclick=()=>save(bytes(D.object_download),'diagnostic_object.ply','application/octet-stream');$('metaDownload').onclick=()=>save(JSON.stringify(P,null,2)+'\n','tracehoi_diagnostic_metadata_'+P.case_id+'.json','application/json');window.addEventListener('pageshow',draw);draw();})();
</script></main></body></html>'''
