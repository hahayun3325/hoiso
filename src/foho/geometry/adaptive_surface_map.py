"""Locate authenticated adaptive coverage cells on unchanged diagnostic hands."""
import base64,json,math
from pathlib import Path
PURPOSE='adaptive_surface_map'
SCHEMA='tracehoi.AdaptiveSurfaceMap.v1'
def require(ok,msg):
 if not ok:raise ValueError(msg)
def triangle(vertices,faces,face,path,adaptive):
 require(type(face) is int and 0<=face<len(faces),'cell_face')
 require(type(path) is str and len(path)<=3 and all(d in '0123' for d in path),'cell_path')
 t=tuple(tuple(vertices[i]) for i in faces[face])
 for d in path:t=adaptive.split(t)[int(d)]
 return t
def partition(leaves,nfaces):
 require(type(nfaces) is int and nfaces>0 and len(leaves)<=nfaces*64,'partition_bound')
 groups={i:[] for i in range(nfaces)};seen=set()
 for c in leaves:
  f,p=c['face_index'],c['path'];require(type(f) is int and f in groups and type(p) is str and len(p)<=3 and all(d in '0123' for d in p),'partition_identity')
  require((f,p) not in seen,'duplicate_cell');seen.add((f,p));groups[f].append(p)
 for paths in groups.values():
  require(paths and sum(4**(3-len(p)) for p in paths)==64,'incomplete_partition')
  for p in paths:require(not any(p[:i] in paths for i in range(len(p))),'overlapping_cells')
 return groups

def locate(candidate,vertices,faces,ov,of,adaptive,coverage,threshold):
 partition(candidate['leaves'],len(faces));queries={}
 for q in candidate['queries']:
  key=q['face_index'],q['path'];require(key not in queries,'duplicate_query');queries[key]=q
 witnesses=[]
 for i,c in enumerate(candidate['leaves']):
  tri=triangle(vertices,faces,c['face_index'],c['path'],adaptive)
  require(coverage.classify(c['lower'],c['upper'],threshold)==c['state'],'cell_classification')
  require(math.isfinite(c['area']) and c['area']>=0,'cell_area')
  q=queries.get((c['face_index'],c['path']))
  # Every subdivided leaf has its own saved query. Root cells use inherited K4 bounds.
  require(bool(q)==bool(c['path']),'missing_leaf_query')
  if q:
   center=[sum(p[k] for p in tri)/3 for k in range(3)]
   require(all(abs(a-b)<=1e-13 for a,b in zip(center,q['centroid'])),'query_cell_centroid')
   j=q['object_triangle'];require(type(j) is int and 0<=j<len(of),'query_object_face')
   witnesses.append(dict(leaf_index=i,query=q,object_triangle_vertices=[list(ov[v]) for v in of[j]]))
 return dict(id=candidate['id'],hand_binding=candidate['hand_binding'],vertices=vertices,faces=faces,leaves=candidate['leaves'],witnesses=witnesses,
             stage=candidate['stages'][-1],stop_reason=candidate['stop_reason'],collision_gate=candidate['collision_gate'],accepted=False)

def build(workspace,wsha,distances,dsha,coverage,csha,adaptive_source,asha,case,*mods,purpose):
 require(purpose==PURPOSE,'adaptive_surface_map_purpose_required')
 reader,pipeline,adaptive=mods[0],mods[8],mods[12]
 roots=[workspace,distances,coverage,adaptive_source];before=[pipeline.inventory(p,reader) for p in roots]
 audit=adaptive.verify(adaptive_source,asha,workspace,wsha,distances,dsha,coverage,csha,case,*mods[:12],purpose=adaptive.PURPOSE)
 saved=reader.parse(before[3]['adaptive.json']);package=reader.parse(before[0]['scene/package.json'])
 manifest,data=reader.inspect_bundle(Path(workspace)/'scene/source/scene.json',package['source_manifest_binding']['sha256'],case)
 ov,of=reader.mesh(data['object']);candidates=[]
 for c in saved['candidates']:
  src=next(x for x in manifest['candidates'] if x['id']==c['id']);raw=data[src['hand_asset']];v,f=reader.mesh(raw)
  require(reader.binding(raw)==c['hand_binding'],'map_hand_binding');candidates.append(locate(c,v,f,ov,of,adaptive,mods[10],saved['threshold']))
 sample=mods[5].sample_vertices(ov)
 report=dict(schema=SCHEMA,purpose=PURPOSE,case_id=case,source_adaptive_binding=reader.binding(before[3]['files.json']),source_workspace_binding=saved['source_workspace_binding'],
  object_binding=saved['object_binding'],object_preview=sample,object_source_vertices=len(ov),object_source_faces=len(of),candidates=candidates,
  threshold=saved['threshold'],threshold_object_diagonal_ratio=saved['threshold_object_diagonal_ratio'],scene_frame=saved['scene_frame'],units=saved['units'],
  reference_status=saved['reference_status'],selected_candidate=None,accepted_scale=None,placement_ready=False,full_parent_acceptance=False,physical_contact_verified=False,
  mask_accuracy_verified=False,scale_identified=False,source_geometry_modified=False,new_surface_queries=0,source_queries_replayed=saved['new_surface_queries'],model_calls=0,
  limitations=['Colors show guarded bounds at the saved 2% object-diagonal threshold, not measured contact.',
   'All final calculation cells partition the original hand faces; midpoint cells do not alter source geometry.',
   'Object preview is a deterministic vertex subset. Orthographic painter rendering is not an occlusion or intersection test.',
   'Click inspection identifies a visible calculation cell. An orange connector is one saved centroid witness, not a global minimum gap.',
   'Root cells have inherited K4 bounds and no new adaptive centroid query.',
   'Independent reference, metric scale, physical contact and placement remain unverified.'])
 files={'surface_map.json':reader.encode(report),'index.html':html(report,data['original_rgb']),
        'adaptive.html':before[3]['index.html'],'reference_annotation.html':before[3]['reference_annotation.html'],
        'README.md':b'TraceHOI adaptive surface map\n\nOpen index.html offline. Rotate or zoom; click a hand cell to inspect its source face, subdivision path, bounds and saved centroid witness. All four candidates remain diagnostic. adaptive.html retains the exact prior interval dashboard. Keep all five companion files plus files.json together. No mesh, mask, scale or placement is changed.\n'}
 files['files.json']=reader.encode(dict(schema='tracehoi.AdaptiveSurfaceMapFiles.v1',files={n:reader.binding(b) for n,b in files.items()},source_adaptive_binding=report['source_adaptive_binding'],placement_ready=False))
 require([pipeline.inventory(p,reader) for p in roots]==before,'map_sources_changed')
 return report,files,audit

def verify(out,sha,*args,purpose):
 require(purpose==PURPOSE,'adaptive_surface_map_purpose_required')
 reader=args[9];pipeline=args[17];actual=pipeline.inventory(out,reader)
 require(set(actual)=={'surface_map.json','index.html','adaptive.html','reference_annotation.html','README.md','files.json'},'map_inventory')
 require(reader.binding(actual['files.json'])['sha256']==sha,'map_receipt')
 r=reader.parse(actual['files.json']);require(r['files']=={n:reader.binding(b) for n,b in actual.items() if n!='files.json'},'map_output_hashes')
 report,expected,audit=build(*args,purpose=purpose);require(actual==expected,'map_reconstruction_mismatch')
 return dict(verified=True,receipt_binding=reader.binding(actual['files.json']),source_numerical_audit=audit['numerical_audit'],placement_ready=False,selected_candidate=None)

def html(report,rgb):
 payload=json.dumps(report,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
 return TEMPLATE.replace('__DATA__',payload).replace('__RGB__',base64.b64encode(rgb).decode()).encode()
TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Adaptive surface map</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c1725;color:#eef5fb;font:15px/1.55 system-ui}main{max-width:1320px;padding:28px;margin:auto}h1{font-size:38px;line-height:1.1;margin:10px 0 16px}h2{font-size:20px;margin:0 0 12px}.eyebrow{color:#87decf;font-size:12px;letter-spacing:2px}.top{display:grid;grid-template-columns:3fr 1fr;gap:30px}.photo{width:100%;height:160px;object-fit:contain;background:#07111b;border-radius:10px}.notice{background:#332c22;border-left:3px solid #e4b96b;padding:12px 16px;margin:18px 0}.layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:20px}.panel{background:#15283b;border:1px solid #37536a;border-radius:12px;padding:20px}.controls{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:12px 0}button,select,input[type=number]{font:inherit;color:inherit;background:#203d55;border:1px solid #7794ad;border-radius:5px;padding:7px}input[type=number]{width:95px}label{font-size:13px}input[type=range]{width:100px;vertical-align:middle}canvas{width:100%;aspect-ratio:1.2;display:block;background:#081523;border-radius:8px;touch-action:none}.small{font-size:12px;color:#b8cadb}.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px}.within{color:#73dbc5}.uncertain{color:#ffcc6d}.outside{color:#90a7c0}.big{font-size:26px;color:#83decd}a{color:#a7dfff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 ui-monospace,monospace}dl{display:grid;grid-template-columns:1fr 1.3fr;gap:7px;font-size:13px}dt{color:#b8cadb}dd{margin:0;overflow-wrap:anywhere}footer{margin-top:20px;color:#b8cadb;font-size:12px}:focus-visible{outline:2px solid #8de0ca;outline-offset:3px}@media(max-width:850px){.top,.layout{grid-template-columns:1fr}main{padding:16px}h1{font-size:30px}.photo{height:130px}}
</style></head><body><main><header class="top"><div><div class="eyebrow">TRACEHOI / SAVED SURFACE EVIDENCE</div><h1>See where proximity remains uncertain.</h1><p id="case"></p><p>Inspect the final adaptive cells on each unchanged hand mesh. Their colors show distance bounds at one fixed display threshold.</p></div><img class="photo" src="data:image/png;base64,__RGB__" alt="Original case RGB crop"></header><div class="notice">Diagnostic geometry. No physical contact, mask accuracy, metric scale or pipeline placement is accepted.</div>
<div class="layout"><section class="panel"><h2>Surface map</h2><div class="controls"><label>Candidate <select id="candidate"></select></label><label>Cells <select id="filter"><option value="all">All cells</option><option value="near">Within + unresolved</option><option value="unresolved">Unresolved only</option><option value="within_bound">Within bound only</option></select></label><label>Focus <select id="focus"><option value="hand">Hand</option><option value="scene">Scene</option></select></label><button id="reset">Reset view</button></div><canvas id="scene" width="960" height="800" role="img" aria-label="Adaptive hand cells; drag to orbit and click to inspect"></canvas><div class="controls"><label>Yaw <input id="yaw" type="range" min="-180" max="180" value="0"></label><label>Pitch <input id="pitch" type="range" min="-90" max="90" value="0"></label><label>Zoom <input id="zoom" type="range" min="0.5" max="5" step="0.1" value="1"></label><label><input id="object" type="checkbox" checked> Object points</label><label><input id="edges" type="checkbox"> Cell edges</label><label><input id="witness" type="checkbox" checked> Selected witness</label></div><div class="legend"><span class="within">● Within bound</span><span class="uncertain">● Unresolved</span><span class="outside">● Outside bound</span></div><p class="small">Drag to rotate; click a visible cell. Object points are sampled for display. Orthographic painter rendering does not certify occlusion. Filtering hides cells without changing any metric.</p></section>
<aside class="panel"><h2 id="candidateName"></h2><div class="big" id="interval"></div><p class="small" id="summary"></p><div class="notice" id="gate"></div><h2>Inspect a calculation cell</h2><div class="controls"><label>Cell index <input id="cell" type="number" min="0" value="0"></label><button id="previous" aria-label="Previous cell">←</button><button id="next" aria-label="Next cell">→</button></div><p id="selectionStatus" class="small" aria-live="polite"></p><dl id="details"></dl><p id="witnessNote" class="small"></p><button id="download">Download selected cell evidence</button><p class="small">The orange segment joins a saved cell centroid to its nearest point on the full object surface. The outlined object triangle is the corresponding witness face. This segment is not the global mesh gap.</p></aside></div>
<section class="panel" style="margin-top:20px"><h2>Keep the evidence connected</h2><p><a href="adaptive.html">Open the authenticated interval dashboard ↗</a> · <a href="reference_annotation.html">Open independent-reference annotation ↗</a></p><details><summary>Source bindings and display limits</summary><pre id="sources"></pre></details></section><footer>Offline · saved CPU diagnostics · no additional refinement · all source meshes, masks and review records preserved. This viewer does not record an acceptance decision.</footer>
<script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const R=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),cv=$('scene'),ctx=cv.getContext('2d'),label=s=>s.replaceAll('_',' '),pct=x=>(100*x).toFixed(3)+'%',colors={within_bound:'#73dbc5',unresolved:'#ffcc6d',outside_bound:'#506e8b'};let c,triangles,queryMap,pick=[],selected=0,drag=null,moved=false;
for(const a of R.candidates){const o=document.createElement('option');o.value=a.id;o.textContent=label(a.id);$('candidate').append(o)}$('case').textContent=R.case_id+' · '+R.object_source_faces.toLocaleString()+' object triangles · final subdivision level';$('sources').textContent=R.limitations.join('\n\n')+'\n\n'+JSON.stringify({adaptive:R.source_adaptive_binding,workspace:R.source_workspace_binding,object:R.object_binding,frame:R.scene_frame,units:R.units},null,2);
const midpoint=(a,b)=>a.map((v,i)=>(v+b[i])/2);function split(t){let[a,b,c]=t,ab=midpoint(a,b),bc=midpoint(b,c),ca=midpoint(c,a);return[[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]}function cellTriangle(l){let t=c.faces[l.face_index].map(i=>c.vertices[i]);for(const d of l.path)t=split(t)[+d];return t}function shown(l){const f=$('filter').value;return f==='all'||f==='near'&&l.state!=='outside_bound'||f===l.state}
function change(){c=R.candidates.find(x=>x.id===$('candidate').value);triangles=c.leaves.map(cellTriangle);queryMap=new Map(c.witnesses.map(w=>[w.leaf_index,w]));selected=Math.max(0,c.leaves.findIndex(l=>l.state==='unresolved'));$('cell').max=c.leaves.length-1;$('candidateName').textContent=label(c.id);$('interval').textContent=pct(c.stage.area_fraction_lower)+' – '+pct(c.stage.area_fraction_upper);$('summary').textContent='Hand area within 2% of object diagonal: '+R.threshold.toPrecision(5)+' scene units. '+c.leaves.length.toLocaleString()+' cells; '+pct(c.stage.unresolved_area_fraction)+' unresolved.';$('gate').textContent=label(c.collision_gate);$('gate').style.borderLeftColor=c.collision_gate.startsWith('blocked')?'#f18e84':'#83decd';update()}
function bounds(){const pts=$('focus').value==='hand'?c.vertices:c.vertices.concat(R.object_preview.points);let lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(const p of pts)for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],p[k]);hi[k]=Math.max(hi[k],p[k])}return{center:lo.map((x,k)=>(x+hi[k])/2),radius:Math.max(1e-8,Math.hypot(...hi.map((x,k)=>x-lo[k]))/2)}}
function draw(){ctx.clearRect(0,0,cv.width,cv.height);const b=bounds(),yaw=+$('yaw').value*Math.PI/180,pitch=+$('pitch').value*Math.PI/180,scale=330*+$('zoom').value/b.radius;function project(p){let[x,y,z]=p.map((v,k)=>v-b.center[k]),xx=x*Math.cos(yaw)+z*Math.sin(yaw),zz=-x*Math.sin(yaw)+z*Math.cos(yaw),yy=y*Math.cos(pitch)-zz*Math.sin(pitch);zz=y*Math.sin(pitch)+zz*Math.cos(pitch);return[480+scale*xx,400-scale*yy,zz]}
const items=[];if($('object').checked)for(const p of R.object_preview.points){const q=project(p);items.push({z:q[2],point:q})}pick=[];for(let i=0;i<c.leaves.length;i++){if(!shown(c.leaves[i]))continue;const t=triangles[i].map(project);items.push({z:t.reduce((s,p)=>s+p[2],0)/3,t,i})}items.sort((a,b)=>a.z-b.z);for(const item of items){if(item.point){ctx.fillStyle='#6d9da380';ctx.fillRect(item.point[0]-1,item.point[1]-1,2,2);continue}const {t,i}=item;ctx.beginPath();ctx.moveTo(t[0][0],t[0][1]);ctx.lineTo(t[1][0],t[1][1]);ctx.lineTo(t[2][0],t[2][1]);ctx.closePath();ctx.fillStyle=colors[c.leaves[i].state];ctx.fill();if($('edges').checked){ctx.strokeStyle='#0b172555';ctx.lineWidth=.55;ctx.stroke()}pick.push({t,i})}
if(shown(c.leaves[selected])){const t=triangles[selected].map(project);ctx.beginPath();t.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.stroke()}
const w=queryMap.get(selected);if(w&&$('witness').checked){let a=project(w.query.centroid),b=project(w.query.point);ctx.strokeStyle='#ff8f61';ctx.lineWidth=2;ctx.setLineDash([5,3]);ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.setLineDash([]);for(const p of[a,b]){ctx.beginPath();ctx.arc(p[0],p[1],4,0,2*Math.PI);ctx.fillStyle='#ff8f61';ctx.fill()}const t=w.object_triangle_vertices.map(project);ctx.beginPath();t.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.stroke()}
ctx.fillStyle='#c9d8e8';ctx.font='14px system-ui';ctx.fillText('x right · y up · z backward / orthographic preview',18,28);$('selectionStatus').textContent=shown(c.leaves[selected])?'Selected cell outlined in white.':'Selected cell is hidden by the display filter.';$('selectionStatus').textContent+=' Displayed cells: '+pick.length+'.';cv.dataset.visibleCells=pick.length;cv.dataset.selectedCell=selected}
function update(){const l=c.leaves[selected],w=queryMap.get(selected);$('cell').value=selected;$('details').replaceChildren();const rows=[['Classification',label(l.state)],['Source face',l.face_index],['Subdivision path',l.path||'root'],['Distance lower',l.lower.toPrecision(8)],['Distance upper',l.upper.toPrecision(8)],['Area',l.area.toPrecision(8)],['Object witness face',w?w.query.object_triangle:'No adaptive query'],['Centroid distance',w?w.query.distance.toPrecision(8):'Inherited K4 bounds']];for(const[k,v]of rows){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=v;$('details').append(dt,dd)}$('witnessNote').textContent=w?'This leaf has a saved centroid query; its object face and point are preserved exactly.':'This unsplit root cell has inherited bounds. No new adaptive centroid witness was recorded.';draw()}
$('candidate').onchange=change;for(const id of['filter','focus','yaw','pitch','zoom','object','edges','witness'])$(id).oninput=draw;$('reset').onclick=()=>{$('yaw').value=0;$('pitch').value=0;$('zoom').value=1;draw()};$('cell').onchange=()=>{selected=Math.max(0,Math.min(c.leaves.length-1,Math.trunc(Number($('cell').value)||0)));update()};$('previous').onclick=()=>{selected=(selected+c.leaves.length-1)%c.leaves.length;update()};$('next').onclick=()=>{selected=(selected+1)%c.leaves.length;update()};cv.onpointerdown=e=>{drag=[e.clientX,e.clientY,+$('yaw').value,+$('pitch').value];moved=false;cv.setPointerCapture(e.pointerId)};cv.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(Math.hypot(dx,dy)>3)moved=true;if(moved){$('yaw').value=Math.max(-180,Math.min(180,drag[2]+dx*.5));$('pitch').value=Math.max(-90,Math.min(90,drag[3]+dy*.5));draw()}};cv.onpointercancel=()=>{drag=null};cv.onpointerup=e=>{if(!drag)return;drag=null;if(moved)return;const r=cv.getBoundingClientRect(),x=(e.clientX-r.left)*cv.width/r.width,y=(e.clientY-r.top)*cv.height/r.height;function inside(t){const s=t.map((p,i)=>{const q=t[(i+1)%3];return(q[0]-p[0])*(y-p[1])-(q[1]-p[1])*(x-p[0])});const a=Math.abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[2][0]-t[0][0])*(t[1][1]-t[0][1]));return a>1e-10&&(s.every(v=>v>=-1e-8)||s.every(v=>v<=1e-8))}for(let i=pick.length-1;i>=0;i--)if(inside(pick[i].t)){selected=pick[i].i;update();break}};
$('download').onclick=()=>{const record={schema:'tracehoi.SurfaceMapSelection.v1',case_id:R.case_id,candidate:c.id,cell_index:selected,cell:c.leaves[selected],triangle:triangles[selected],witness:queryMap.get(selected)||null,source_adaptive_binding:R.source_adaptive_binding,hand_binding:c.hand_binding,object_binding:R.object_binding,accepted:false,placement_ready:false};const u=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_surface_cell_'+c.id+'_'+selected+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};change();})();
</script></main></body></html>
'''
