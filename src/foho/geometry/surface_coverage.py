"""Area-weighted unsigned proximity intervals for immutable diagnostic hands.

Distance to a fixed object surface is 1-Lipschitz. For each hand triangle and
each known sample (three vertices and its centroid), d(sample)-max_corner_radius
is a lower bound over the whole triangle. A known object-surface witness gives
an upper bound: max_corner_distance_to_witness. These bounds bracket the area
within a threshold without treating a centroid or vertex count as surface area.
This is floating-point geometry with a conservative guard, not formal interval
arithmetic or physical-contact verification.
"""
import math,json,tempfile,base64
from pathlib import Path
PURPOSE='surface_coverage'
SCHEMA='tracehoi.SurfaceCoverage.v1'
THRESHOLDS=(.001,.002,.005,.01,.02,.05,.1)
def require(ok,msg):
    if not ok:raise ValueError(msg)
def area(t):
    a=[t[1][i]-t[0][i] for i in range(3)];b=[t[2][i]-t[0][i] for i in range(3)]
    c=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]);return math.sqrt(sum(x*x for x in c))/2
def envelope(triangle,samples,guard):
    require(len(triangle)==3 and all(len(v)==3 and all(math.isfinite(x) for x in v) for v in triangle),'triangle_input')
    require(math.isfinite(guard) and guard>=0 and samples,'distance_guard')
    lower=0.;upper=math.inf
    for p,d,q in samples:
        require(len(p)==len(q)==3 and math.isfinite(d) and d>=0 and all(math.isfinite(x) for x in (*p,*q)),'sample_input')
        radius=max(math.dist(p,v) for v in triangle)
        lower=max(lower,d-radius)
        upper=min(upper,d+radius,max(math.dist(q,v) for v in triangle))
    lower=max(0.,lower-guard);upper+=guard
    require(lower<=upper,'inconsistent_distance_samples')
    return lower,upper
def classify(lower,upper,threshold):
    require(all(math.isfinite(x) for x in (lower,upper,threshold)) and 0<=lower<=upper and threshold>=0,'classification_input')
    return 'within_bound' if upper<=threshold else 'outside_bound' if lower>threshold else 'unresolved'
def coverage(rows,threshold):
    counts={n:0 for n in ['within_bound','outside_bound','unresolved']};areas=dict.fromkeys(counts,0.)
    for r in rows:
        a=r['area'];require(math.isfinite(a) and a>=0,'face_area');state=classify(r['lower'],r['upper'],threshold);counts[state]+=1;areas[state]+=a
    total=math.fsum(r['area'] for r in rows);require(total>0,'positive_hand_area_required')
    # All areas are nonnegative; fsum limits aggregate rounding drift.
    lower=math.fsum(r['area'] for r in rows if classify(r['lower'],r['upper'],threshold)=='within_bound')/total
    upper=1.-math.fsum(r['area'] for r in rows if classify(r['lower'],r['upper'],threshold)=='outside_bound')/total
    return dict(threshold=threshold,counts=counts,areas=areas,total_area=total,area_fraction_lower=max(0.,min(1.,lower)),area_fraction_upper=max(lower,min(1.,upper)),unresolved_area_fraction=areas['unresolved']/total)

def build(workspace,workspace_sha,distances,distance_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,pipeline,distance,*,purpose):
    require(purpose==PURPOSE,'surface_coverage_purpose_required')
    wfiles=pipeline.inventory(workspace,reader);dfiles=pipeline.inventory(distances,reader)
    with tempfile.TemporaryDirectory(prefix='tracehoi-coverage-') as t:
        root=Path(t).resolve();export.publish(root/'workspace',wfiles,reader);export.publish(root/'distances',dfiles,reader)
        receipt=distance.verify(root/'distances',distance_sha,root/'workspace',workspace_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,pipeline,purpose=distance.PURPOSE)
        package=reader.parse(wfiles['scene/package.json']);manifest,data=reader.inspect_bundle(root/'workspace/scene/source/scene.json',package['source_manifest_binding']['sha256'],case)
    prior=reader.parse(dfiles['distances.json']);ov,of=reader.mesh(data['object']);index=distance.SurfaceIndex(ov,of)
    require(index.diagonal==prior['object_bbox_diagonal'] and reader.binding(data['object'])==prior['object_binding'],'object_binding')
    guard=1e-9*max(1.,index.diagonal,max(abs(x) for p in ov for x in p));candidates=[];hands={}
    for c in manifest['candidates']:
        old=next(r for r in prior['candidates'] if r['id']==c['id']);raw=data[c['hand_asset']];v,f=reader.mesh(raw)
        require(reader.binding(raw)==old['hand_binding'],'hand_binding');rows=[]
        for face_id,face in enumerate(f):
            tri=[v[i] for i in face];center=tuple(sum(p[k] for p in tri)/3 for k in range(3));w=index.nearest(center)
            samples=[(v[i],old['vertices'][i]['distance'],old['vertices'][i]['point']) for i in face];samples.append((center,w['distance'],w['point']))
            lo,hi=envelope(tri,samples,guard)
            rows.append(dict(face_index=face_id,area=area(tri),lower=lo,upper=hi,centroid=list(center),centroid_distance=w['distance'],object_triangle=w['object_triangle'],point=w['point'],barycentric=w['barycentric']))
        profiles=[]
        for ratio in THRESHOLDS:
            s=coverage(rows,ratio*index.diagonal);s['threshold_object_diagonal_ratio']=ratio;profiles.append(s)
        candidates.append(dict(id=c['id'],hand_binding=old['hand_binding'],conditional_scale=c['conditional_scale'],collision_gate=c['collision_gate'],
            prior_triangle_surface_gap=c['unsigned_surface_gap'],faces=rows,total_hand_area=math.fsum(r['area'] for r in rows),zero_area_faces=sum(r['area']==0 for r in rows),profiles=profiles,accepted=False))
        hands[c['id']]=dict(vertices=v,faces=f)
    require([c['id'] for c in candidates]==reader.IDS,'candidate_order')
    report=dict(schema=SCHEMA,purpose=PURPOSE,case_id=case,source_workspace_binding=receipt['source_workspace_binding'],source_distance_binding=receipt['receipt_binding'],
        object_binding=prior['object_binding'],object_bbox_diagonal=index.diagonal,object_triangles=len(of),scene_frame=manifest['scene_frame'],units=manifest['units'],area_units='unverified_scene_units_squared',
        numerical_guard=guard,new_surface_queries=sum(len(c['faces']) for c in candidates),candidates=candidates,reference_status=prior['reference_status'],
        selected_candidate=None,accepted_scale=None,placement_ready=False,full_parent_acceptance=False,physical_contact_verified=False,scale_identified=False,
        geometric_accuracy_verified=False,mask_accuracy_verified=False,source_geometry_modified=False,model_calls=0,
        method='Per-face lower/upper envelopes from exact vertex and centroid queries; area fractions bracket threshold coverage',
        limitations=['Bounds describe unsigned proximity to the saved object surface, not physical contact or penetration depth.',
            'Unresolved triangle area is retained as an interval, not assigned by its centroid or vertex vote.',
            'Whole-mesh collision findings remain separate and unchanged; a small proximity distance cannot clear a crossing gate.',
            'Numerical guard is conservative engineering tolerance, not a formal floating-point proof.',
            'Display thresholds are exploratory fractions of object diagonal. Neither thresholds nor area fractions accept scale or placement.'])
    points=list(ov)+[p for h in hands.values() for p in h['vertices']];center=[(min(p[k] for p in points)+max(p[k] for p in points))/2 for k in range(3)];radius=max(math.dist(p,center) for p in points)
    display=dict(report=report,object=export.sample_vertices(ov,3000)['points'],hands=hands,center=center,radius=radius,rgb=base64.b64encode(data['original_rgb']).decode())
    files={'coverage.json':reader.encode(report),'index.html':html(display),'README.md':b'TraceHOI surface-coverage intervals\n\nOpen index.html offline. Orange faces are entirely within the display threshold according to numerical bounds; blue faces are outside; yellow faces are unresolved. Area fractions retain this uncertainty. Bounds use full-object nearest queries at vertices and centroids plus 1-Lipschitz/known-witness envelopes. No physical contact, scale or placement is accepted. Keep the source J3 distance packet and H2 workspace, original review/reference records and their checksums.\n'}
    files['files.json']=reader.encode(dict(schema='tracehoi.SurfaceCoverageFiles.v1',source_workspace_binding=report['source_workspace_binding'],source_distance_binding=report['source_distance_binding'],files={n:reader.binding(b) for n,b in files.items()},placement_ready=False))
    require(pipeline.inventory(workspace,reader)==wfiles and pipeline.inventory(distances,reader)==dfiles,'coverage_source_changed')
    return report,files
def verify(out,receipt_sha,workspace,workspace_sha,distances,distance_sha,case,*mods,purpose):
    require(purpose==PURPOSE,'surface_coverage_purpose_required');reader=mods[0];pipeline=mods[-2];actual=pipeline.inventory(out,reader)
    require(set(actual)=={'coverage.json','index.html','README.md','files.json'},'coverage_inventory');require(reader.binding(actual['files.json'])['sha256']==receipt_sha,'coverage_receipt_binding')
    m=reader.parse(actual['files.json']);require(m['files']=={n:reader.binding(b) for n,b in actual.items() if n!='files.json'},'coverage_files_changed')
    report,expected=build(workspace,workspace_sha,distances,distance_sha,case,*mods,purpose=purpose);require(actual==expected,'coverage_semantic_mismatch')
    return dict(verified=True,receipt_binding=reader.binding(actual['files.json']),source_workspace_binding=report['source_workspace_binding'],source_distance_binding=report['source_distance_binding'],placement_ready=False,selected_candidate=None)
def html(display):
    payload=json.dumps(display,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',payload).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Surface coverage</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c1521;color:#edf3fa;font:15px/1.55 system-ui}main{max-width:1280px;margin:auto;padding:28px}h1{font-size:36px;margin:8px 0}h2{font-size:19px}.eyebrow{color:#81ddca;letter-spacing:2px;font-size:12px}.muted{color:#acbed2}.notice{padding:14px 18px;background:#2b261c;border-left:3px solid #e5bd76;margin:20px 0}.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(285px,1fr);gap:20px}.panel{padding:18px;background:#142335;border:1px solid #3b5068;border-radius:12px}.controls{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:12px}button,select{font:inherit;background:#243b52;color:inherit;border:1px solid #6786a2;border-radius:6px;padding:8px}button,select,input{cursor:pointer}canvas{width:100%;aspect-ratio:1;display:block;touch-action:none;background:#0a131d;border-radius:8px}img{width:100%;border-radius:8px}input[type=range]{max-width:140px}.big{font-size:29px;color:#8fe0d1}.small{font-size:12px}.near{color:#ffac69}.far{color:#6195bd}.unknown{color:#e9d568}.bar{display:flex;height:16px;border-radius:6px;overflow:hidden;margin:12px 0}.bar span{display:block}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid #364d65}.scroll{overflow:auto;margin-top:20px}@media(max-width:800px){.grid{grid-template-columns:1fr}main{padding:15px}h1{font-size:28px}}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #8fe0d1;outline-offset:3px}
</style></head><body><main><div class="eyebrow">TRACEHOI / SURFACE COVERAGE INTERVALS</div><h1>How much hand surface is near the object?</h1><p id="identity" class="muted"></p><div class="notice"><strong>Proximity remains a diagnostic.</strong> The colored regions bracket surface coverage at your display threshold. They do not establish physical contact, penetration depth, metric scale or placement.</div><div class="grid"><section class="panel"><div class="controls"><label>Candidate <select id="candidate"></select></label><button id="reset">Reset view</button><label><input type="checkbox" id="focus" checked> Focus on hand</label><label><input type="checkbox" id="object" checked> Object preview</label></div><canvas id="scene" width="800" height="800" role="img" aria-label="Rotate the hand with proximity-bound face colors; click a face center to inspect its interval"></canvas><div class="controls"><label>Yaw <input id="yaw" type="range" min="-180" max="180" value="0"></label><label>Pitch <input id="pitch" type="range" min="-85" max="85" value="0"></label><label>Zoom <input id="zoom" type="range" min="0.5" max="3" step="0.1" value="1"></label></div><div class="controls small"><span class="near">● Within bound</span><span class="unknown">● Unresolved</span><span class="far">● Outside bound</span></div><p class="small muted">Drag to rotate. Click a projected face center for its numerical interval. Transparent orthographic preview; occlusion is not certified. Object display samples vertices, while calculations use every object triangle.</p></section><aside class="panel"><h2 id="name"></h2><p id="gate"></p><label>Threshold (% object diagonal)<br><input id="threshold" type="range" min="0.1" max="10" step="0.1" value="2"> <span id="thresholdValue"></span></label><h2>Area within threshold</h2><div class="big" id="interval"></div><div class="bar"><span id="barNear" style="background:#ffac69"></span><span id="barUnknown" style="background:#e9d568"></span><span id="barFar" style="background:#6195bd"></span></div><p id="summary" class="small muted"></p><h2>Face interval</h2><pre id="witness"></pre><img id="rgb" alt="Original RGB crop"><p class="small muted">Unsigned geometry in unverified scene units. All four candidates remain unaccepted.</p></aside></div><section class="panel scroll"><h2>Area-weighted comparison at the same threshold</h2><table><thead><tr><th>Candidate</th><th>Area lower bound</th><th>Area upper bound</th><th>Unresolved area</th><th>Collision gate</th></tr></thead><tbody id="rows"></tbody></table><p class="small muted">Fractions weight each triangle by its area. Unresolved area is retained in the interval; it is not assigned by a centroid or vertex vote. Thresholds are exploratory, not acceptance criteria.</p></section><div class="controls" style="margin-top:20px"><button id="download">Download all face intervals</button></div><details><summary>Method, tolerance and limitations</summary><pre id="limits"></pre></details><footer class="small muted">Offline inspection. No inference, optimization, geometry edit, mask edit or placement acceptance.</footer><script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),R=D.report,$=id=>document.getElementById(id),C=$('scene'),ctx=C.getContext('2d'),label=s=>s.replaceAll('_',' ');let selected=0,centers=[];const colors=['#ffac69','#6195bd','#e9d568'];function state(f,t){return f.upper<=t?0:f.lower>t?1:2}function stats(c,t){const a=[0,0,0];for(const f of c.faces)a[state(f,t)]+=f.area;const total=a.reduce((x,y)=>x+y,0);return{a,total,lo:a[0]/total,hi:(a[0]+a[2])/total,unknown:a[2]/total}}const current=()=>R.candidates.find(c=>c.id===$('candidate').value);for(const c of R.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=label(c.id);$('candidate').append(o)}$('rgb').src='data:image/png;base64,'+D.rgb;$('identity').textContent=R.case_id+' · '+R.new_surface_queries.toLocaleString()+' triangle-centroid queries · four unchanged hands';$('limits').textContent=R.method+'\nNumerical guard: '+R.numerical_guard+'\n\n'+R.limitations.join('\n');function pickNearest(){const c=current();selected=c.faces.reduce((best,f)=>f.lower<c.faces[best].lower?f.face_index:best,0)}
function draw(){const c=current(),h=D.hands[c.id],vs=h.vertices;let center=D.center,radius=D.radius;if($('focus').checked){center=[0,1,2].map(k=>(Math.min(...vs.map(v=>v[k]))+Math.max(...vs.map(v=>v[k])))/2);radius=Math.max(...vs.map(v=>Math.hypot(...v.map((x,i)=>x-center[i]))))*1.25}const yaw=+$('yaw').value*Math.PI/180,pitch=+$('pitch').value*Math.PI/180,scale=340*+$('zoom').value/radius;function project(p){const[x,y,z]=p.map((v,i)=>v-center[i]),xx=Math.cos(yaw)*x+Math.sin(yaw)*z,zz=-Math.sin(yaw)*x+Math.cos(yaw)*z;return[400+xx*scale,400-(Math.cos(pitch)*y-Math.sin(pitch)*zz)*scale,Math.sin(pitch)*y+Math.cos(pitch)*zz]}ctx.clearRect(0,0,800,800);if($('object').checked){ctx.fillStyle='#7694ac';ctx.globalAlpha=.4;for(const p of D.object){const q=project(p);ctx.fillRect(q[0],q[1],2,2)}}ctx.globalAlpha=1;const pv=vs.map(project),t=+$('threshold').value/100*R.object_bbox_diagonal;centers=c.faces.map(f=>project(f.centroid));const order=c.faces.map(f=>f.face_index).sort((a,b)=>centers[a][2]-centers[b][2]);for(const i of order){const f=h.faces[i];ctx.beginPath();ctx.moveTo(pv[f[0]][0],pv[f[0]][1]);ctx.lineTo(pv[f[1]][0],pv[f[1]][1]);ctx.lineTo(pv[f[2]][0],pv[f[2]][1]);ctx.closePath();ctx.fillStyle=colors[state(c.faces[i],t)];ctx.globalAlpha=.75;ctx.fill();ctx.globalAlpha=.25;ctx.strokeStyle='#0b1420';ctx.stroke()}ctx.globalAlpha=1;const f=c.faces[selected],p=centers[selected],q=project(f.point);ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.stroke();ctx.beginPath();ctx.arc(p[0],p[1],6,0,Math.PI*2);ctx.stroke();ctx.lineWidth=1;$('name').textContent=label(c.id);$('gate').textContent=label(c.collision_gate);$('gate').style.color=c.collision_gate.startsWith('blocked')?'#ffac69':'#acbed2';$('thresholdValue').textContent=(+$('threshold').value).toFixed(1)+'%';const s=stats(c,t);$('interval').textContent=(s.lo*100).toFixed(2)+'–'+(s.hi*100).toFixed(2)+'%';$('barNear').style.width=s.lo*100+'%';$('barUnknown').style.width=s.unknown*100+'%';$('barFar').style.width=s.a[1]/s.total*100+'%';$('summary').textContent=(100*s.unknown).toFixed(2)+'% of hand area remains unresolved at '+t.toPrecision(5)+' scene units. Total hand area '+s.total.toPrecision(5)+' unverified scene units².';$('witness').textContent='Face '+selected+' · '+['within bound','outside bound','unresolved'][state(f,t)]+'\nDistance interval ['+f.lower.toPrecision(6)+', '+f.upper.toPrecision(6)+']\nCentroid distance '+f.centroid_distance.toPrecision(6)+'\nNearest object triangle '+f.object_triangle+'\nFace area '+f.area.toPrecision(6);$('rows').replaceChildren();for(const r of R.candidates){const x=stats(r,t),tr=document.createElement('tr');if(r.id===c.id)tr.style.background='#233a4e';for(const v of[label(r.id),(100*x.lo).toFixed(2)+'%',(100*x.hi).toFixed(2)+'%',(100*x.unknown).toFixed(2)+'%',label(r.collision_gate)]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('rows').append(tr)}}
for(const id of['yaw','pitch','zoom','threshold','focus','object'])$(id).oninput=draw;$('candidate').onchange=()=>{pickNearest();draw()};$('reset').onclick=()=>{$('yaw').value=$('pitch').value=0;$('zoom').value=1;draw()};let drag=null;C.onpointerdown=e=>{drag=[e.clientX,e.clientY,+$('yaw').value,+$('pitch').value];C.setPointerCapture(e.pointerId)};C.onpointermove=e=>{if(!drag)return;if(Math.hypot(e.clientX-drag[0],e.clientY-drag[1])>3){$('yaw').value=Math.max(-180,Math.min(180,drag[2]+(e.clientX-drag[0])*.5));$('pitch').value=Math.max(-85,Math.min(85,drag[3]+(e.clientY-drag[1])*.5));draw()}};C.onpointerup=e=>{if(drag&&Math.hypot(e.clientX-drag[0],e.clientY-drag[1])<=3){const b=C.getBoundingClientRect(),p=[(e.clientX-b.left)*800/b.width,(e.clientY-b.top)*800/b.height];let best=100;for(let i=0;i<centers.length;i++){const d=(p[0]-centers[i][0])**2+(p[1]-centers[i][1])**2;if(d<best){best=d;selected=i}}draw()}drag=null};C.onpointercancel=()=>{drag=null};$('download').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_surface_coverage_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};window.addEventListener('pageshow',()=>{pickNearest();draw()});pickNearest();draw();})();
</script></main></body></html>'''
