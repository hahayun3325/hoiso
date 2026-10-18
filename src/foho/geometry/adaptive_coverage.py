"""Bounded adaptive area intervals on unchanged hand triangles.

Midpoint subdivisions allocate one quarter of the parent's area to each child.
Only unresolved cells are queried. Inherited envelopes keep intervals nested.
These guarded floating-point bounds are diagnostic, not formal interval proofs.
"""
import base64,json,math,tempfile
from pathlib import Path
PURPOSE='adaptive_coverage'
SCHEMA='tracehoi.AdaptiveCoverage.v1'
RATIO=.02
DEPTH=3
QUERY_BUDGET=2048
def require(ok,msg):
 if not ok:raise ValueError(msg)
def split(t):
 require(len(t)==3 and all(len(p)==3 and all(math.isfinite(x) for x in p) for p in t),'triangle')
 a,b,c=t;mid=lambda p,q:tuple((x+y)/2 for x,y in zip(p,q));ab=mid(a,b);bc=mid(b,c);ca=mid(c,a)
 return [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]
def summarise(cells,threshold,coverage,depth,queries,budget):
 p=coverage.coverage(cells,threshold);p.update(depth=depth,queries_used=queries,query_budget=budget,leaf_cells=len(cells),unresolved_positive_cells=sum(c['area']>0 and coverage.classify(c['lower'],c['upper'],threshold)=='unresolved' for c in cells))
 return p
def refine(vertices,faces,rows,index,coverage,threshold,guard,max_depth=DEPTH,max_queries=QUERY_BUDGET):
 require(type(max_depth) is int and 0<=max_depth<=3 and type(max_queries) is int and 0<=max_queries<=2048,'refinement_limits')
 require(len(faces)==len(rows)>0 and math.isfinite(threshold) and threshold>=0 and math.isfinite(guard) and guard>0,'refinement_input')
 cells=[]
 for i,(f,r) in enumerate(zip(faces,rows)):
  require(r['face_index']==i and math.isfinite(r['area']) and r['area']>=0,'root_identity')
  coverage.classify(r['lower'],r['upper'],threshold)
  cells.append(dict(face_index=i,path='',triangle=tuple(tuple(vertices[j]) for j in f),area=r['area'],lower=r['lower'],upper=r['upper']))
 stages=[summarise(cells,threshold,coverage,0,0,max_queries)];queries=[];splits=0
 for depth in range(1,max_depth+1):
  refined=[]
  for cell in cells:
   if cell['area']==0 or coverage.classify(cell['lower'],cell['upper'],threshold)!='unresolved' or len(queries)+4>max_queries:
    refined.append(cell);continue
   children=split(cell['triangle']);splits+=1
   for digit,tri in enumerate(children):
    center=tuple(sum(p[k] for p in tri)/3 for k in range(3));w=index.nearest(center)
    lo,hi=coverage.envelope(tri,[(center,w['distance'],w['point'])],guard)
    lo=max(lo,cell['lower']);hi=min(hi,cell['upper']);require(lo<=hi,'inconsistent_child_bounds')
    path=cell['path']+str(digit);row=dict(face_index=cell['face_index'],path=path,centroid=list(center),distance=w['distance'],object_triangle=w['object_triangle'],point=w['point'],barycentric=w['barycentric'])
    queries.append(row);refined.append(dict(face_index=cell['face_index'],path=path,triangle=tri,area=cell['area']/4,lower=lo,upper=hi))
  cells=refined;st=summarise(cells,threshold,coverage,depth,len(queries),max_queries);prior=stages[-1]
  require(abs(st['total_area']-prior['total_area'])<=1e-13*max(1.,st['total_area']),'area_conservation')
  require(st['area_fraction_lower']+1e-13>=prior['area_fraction_lower'] and st['area_fraction_upper']<=prior['area_fraction_upper']+1e-13,'non_nested_coverage')
  stages.append(st)
 leaves=[dict(face_index=c['face_index'],path=c['path'],area=c['area'],lower=c['lower'],upper=c['upper'],state=coverage.classify(c['lower'],c['upper'],threshold)) for c in cells]
 stop='resolved' if stages[-1]['unresolved_positive_cells']==0 else 'query_budget' if len(queries)+4>max_queries else 'depth_limit'
 return dict(stages=stages,leaves=leaves,queries=queries,splits=splits,stop_reason=stop)

def build(workspace,wsha,distances,dsha,coverage_source,csha,case,*mods,purpose):
 require(purpose==PURPOSE,'adaptive_coverage_purpose_required')
 reader,export,pipeline,distance,coverage,proximity=mods[0],mods[5],mods[8],mods[9],mods[10],mods[11]
 originals=[pipeline.inventory(p,reader) for p in [workspace,distances,coverage_source]]
 with tempfile.TemporaryDirectory(prefix='tracehoi-adaptive-') as t:
  roots=[Path(t).resolve()/n for n in ['workspace','distances','coverage']]
  for root,files in zip(roots,originals):export.publish(root,files,reader)
  prior,_=proximity.verify_coverage(roots[0],wsha,roots[1],dsha,roots[2],csha,case,*mods[:11])
  package=reader.parse(originals[0]['scene/package.json']);manifest,data=reader.inspect_bundle(roots[0]/'scene/source/scene.json',package['source_manifest_binding']['sha256'],case)
 ov,of=reader.mesh(data['object']);index=distance.SurfaceIndex(ov,of);candidates=[]
 require(index.diagonal==prior['object_bbox_diagonal'],'object_extent')
 for c in prior['candidates']:
  scene=next(x for x in manifest['candidates'] if x['id']==c['id']);raw=data[scene['hand_asset']];v,f=reader.mesh(raw)
  require(reader.binding(raw)==c['hand_binding'],'hand_binding')
  result=refine(v,f,c['faces'],index,coverage,RATIO*index.diagonal,prior['numerical_guard'])
  result.update(id=c['id'],hand_binding=c['hand_binding'],collision_gate=c['collision_gate'],accepted=False)
  candidates.append(result)
 report=dict(schema=SCHEMA,purpose=PURPOSE,case_id=case,threshold_object_diagonal_ratio=RATIO,threshold=RATIO*index.diagonal,max_depth=DEPTH,query_budget_per_candidate=QUERY_BUDGET,
  source_workspace_binding=reader.binding(originals[0]['workspace.json']),source_distance_binding=reader.binding(originals[1]['files.json']),source_coverage_binding=reader.binding(originals[2]['files.json']),
  object_binding=prior['object_binding'],object_triangles=len(of),scene_frame=prior['scene_frame'],units=prior['units'],numerical_guard=prior['numerical_guard'],
  candidates=candidates,new_surface_queries=sum(len(c['queries']) for c in candidates),reference_status=prior['reference_status'],
  selected_candidate=None,accepted_scale=None,placement_ready=False,full_parent_acceptance=False,physical_contact_verified=False,scale_identified=False,geometric_accuracy_verified=False,mask_accuracy_verified=False,source_geometry_modified=False,model_calls=0,
  method='Midpoint subdivision of unresolved cells only; each cell inherits its parent envelope and adds a full-surface centroid query; child areas are one quarter of their parent.',
  limitations=['The 2% object-diagonal threshold is an exploratory display threshold, not a contact or acceptance criterion.',
   'Subdivision changes numerical integration cells, not source mesh vertices or faces.',
   'Unresolved area remains in the interval when the depth or query budget is reached.',
   'Guarded floating-point geometry is not formal interval arithmetic or physical contact verification.',
   'Collision gates, metric scale, mask accuracy and placement remain separate and unchanged.'])
 files={'adaptive.json':reader.encode(report),'index.html':html(report,data['original_rgb']),
  'reference_annotation.html':originals[0]['validation/reference_annotation.html'],
  'README.md':b'TraceHOI adaptive surface coverage\n\nOpen index.html offline. Display depth 0 is the authenticated K4 envelope; depths 1-3 subdivide only unresolved cells at 2% of object diagonal. Each candidate has at most 2048 new full-surface queries. Source meshes, masks and collision gates are unchanged. These numerical intervals do not establish contact, accuracy, metric scale or placement. Preserve original inputs and independent reference records.\n'}
 files['files.json']=reader.encode(dict(schema='tracehoi.AdaptiveCoverageFiles.v1',files={n:reader.binding(b) for n,b in files.items()},source_coverage_binding=report['source_coverage_binding'],placement_ready=False))
 require([pipeline.inventory(p,reader) for p in [workspace,distances,coverage_source]]==originals,'adaptive_sources_changed')
 return report,files

def compare(saved,expected,coverage):
 tolerance=min(32*math.ulp(max(1.,expected['threshold'])),expected['numerical_guard']/1024);audit=dict(tolerance=tolerance,different_values=0,maximum_difference=0.)
 allowed={'lower','upper','area','total_area','area_fraction_lower','area_fraction_upper','unresolved_area_fraction','centroid','distance','point','barycentric'}
 def walk(a,b,path=()):
  require(type(a) is type(b),'adaptive_type')
  if isinstance(b,dict):
   require(a.keys()==b.keys(),'adaptive_keys')
   for k in b:walk(a[k],b[k],path+(k,))
  elif isinstance(b,list):
   require(len(a)==len(b),'adaptive_length')
   for i,(u,v) in enumerate(zip(a,b)):walk(u,v,path+(i,))
  elif type(b) is float and path[:1]==('candidates',) and any(k in allowed for k in path if isinstance(k,str)):
   delta=abs(a-b);require(math.isfinite(a) and delta<=tolerance,'adaptive_numeric_difference')
   if delta:audit['different_values']+=1;audit['maximum_difference']=max(audit['maximum_difference'],delta)
  else:require(a==b,'adaptive_exact_field')
 walk(saved,expected)
 for c in saved['candidates']:
  for leaf in c['leaves']:require(coverage.classify(leaf['lower'],leaf['upper'],saved['threshold'])==leaf['state'],'adaptive_classification')
 return audit
def verify(out,sha,workspace,wsha,distances,dsha,source,csha,case,*mods,purpose):
 require(purpose==PURPOSE,'adaptive_coverage_purpose_required');reader=mods[0];pipeline=mods[8];coverage=mods[10];actual=pipeline.inventory(out,reader)
 require(set(actual)=={'adaptive.json','index.html','reference_annotation.html','README.md','files.json'},'adaptive_inventory')
 require(reader.binding(actual['files.json'])['sha256']==sha,'adaptive_receipt')
 r=reader.parse(actual['files.json']);require(r['files']=={n:reader.binding(b) for n,b in actual.items() if n!='files.json'},'adaptive_output_hashes')
 expected,files=build(workspace,wsha,distances,dsha,source,csha,case,*mods,purpose=purpose);saved=reader.parse(actual['adaptive.json'])
 require(reader.encode(saved)==actual['adaptive.json'],'adaptive_canonical');audit=compare(saved,expected,coverage)
 ordered=mods[11].ordered_like(saved,expected);rgb=pipeline.inventory(workspace,reader)['scene/source/assets/original_rgb.png']
 require(actual['index.html']==html(ordered,rgb),'adaptive_viewer')
 require(actual['README.md']==files['README.md'] and actual['reference_annotation.html']==files['reference_annotation.html'],'adaptive_companions')
 require(r['schema']=='tracehoi.AdaptiveCoverageFiles.v1' and r['placement_ready'] is False and r['source_coverage_binding']==expected['source_coverage_binding'] and set(r)=={'schema','files','placement_ready','source_coverage_binding'},'adaptive_receipt_contract')
 return dict(verified=True,receipt_binding=reader.binding(actual['files.json']),numerical_audit=audit,placement_ready=False,selected_candidate=None)

def html(report,rgb):
 payload=json.dumps(report,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
 return TEMPLATE.replace('__DATA__',payload).replace('__RGB__',base64.b64encode(rgb).decode()).encode()
TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Adaptive surface coverage</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1624;color:#edf5fb;font:15px/1.55 system-ui}main{max-width:1200px;margin:auto;padding:30px}h1{font-size:38px;line-height:1.15}h2{font-size:21px}.eyebrow{font-size:12px;letter-spacing:2px;color:#8fe2ce}.top{display:grid;grid-template-columns:2fr 1fr;gap:28px}.photo{width:100%;height:235px;object-fit:contain;background:#07111b;border-radius:12px}.panel{background:#15293d;border:1px solid #38546c;border-radius:12px;margin-top:22px;padding:22px}.notice{background:#302b24;border-left:3px solid #e0b976;padding:14px;margin:20px 0}.small{font-size:12px;color:#b4c6d8}.grid{display:grid;grid-template-columns:1.7fr 1fr;gap:22px}.big{font-size:32px;color:#8de0ca}select,button{background:#254159;color:inherit;border:1px solid #7d9cb2;border-radius:6px;padding:9px;font:inherit}label{display:inline-block;margin:0 20px 15px 0}svg{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid #38546c;padding:10px;text-align:left}.scroll{overflow:auto}a{color:#a8e5ff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}footer{font-size:12px;color:#b4c6d8;margin-top:24px}:focus-visible{outline:2px solid #8de0ca;outline-offset:3px}@media(max-width:780px){.top,.grid{grid-template-columns:1fr}main{padding:16px}h1{font-size:30px}}
</style></head><body><main><div class="top"><div><div class="eyebrow">TRACEHOI / ADAPTIVE SURFACE COVERAGE</div><h1>Smaller patches.<br>Tighter proximity intervals.</h1><p id="case"></p><p>Subdivide unresolved triangles while preserving the original hand and object meshes.</p><div class="notice">Numerical proximity only. No physical contact, metric scale, mask accuracy or placement is accepted.</div></div><img class="photo" src="data:image/png;base64,__RGB__" alt="Original RGB crop"></div>
<section class="panel"><h2>Follow the remaining uncertainty</h2><label>Candidate <select id="candidate"></select></label><label>Refinement level <select id="depth"><option value="0">0 · original faces</option><option value="1">1 · first subdivision</option><option value="2">2 · second subdivision</option><option value="3" selected>3 · final bounded pass</option></select></label><p class="small">Fixed display threshold: 2% of the object diagonal. Refinement levels subdivide only unresolved cells; they do not optimize geometry.</p><div class="grid"><div><svg id="chart" viewBox="0 0 620 330" role="img" aria-label="Area interval convergence across refinement levels"></svg><p class="small">Shaded band: possible area fraction within the threshold. Vertical scale is labelled in percent and adapts to this candidate. The dotted line marks the displayed level.</p></div><aside><div id="name"></div><div class="big" id="interval"></div><p id="uncertainty"></p><pre id="budget"></pre><div class="notice" id="gate"></div></aside></div><div class="scroll"><table><thead><tr><th>Candidate</th><th>Area interval</th><th>Unresolved area</th><th>Queries used</th><th>Collision gate</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section class="panel"><h2>What refinement changes</h2><p>Each midpoint split creates four equal-area calculation cells. A new centroid query uses the complete saved object surface. Child bounds also retain their parent bounds, so resolved area stays resolved.</p><p>Maximum depth: 3. Budget: 2,048 new queries per candidate. Unresolved cells remain unresolved when a limit is reached. The minimum-scale branch keeps its transverse-crossing block.</p><button id="download">Download refinement witnesses</button> <a href="reference_annotation.html">Open independent-reference annotator ↗</a><details><summary>Method and source receipts</summary><pre id="method"></pre></details></section><footer>Your visual observation review remains preserved in the source workspace. The independent mask reference is pending. Offline CPU diagnostics; source meshes and masks are unchanged.</footer><script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const R=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),label=s=>s.replaceAll('_',' '),pct=x=>(100*x).toFixed(3)+'%';for(const c of R.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=label(c.id);$('candidate').append(o)}$('case').textContent=R.case_id+' · '+R.object_triangles.toLocaleString()+' object triangles · four unchanged hypotheses';$('method').textContent=R.method+'\n\n'+R.limitations.join('\n')+'\n\n'+JSON.stringify({workspace:R.source_workspace_binding,distances:R.source_distance_binding,coverage:R.source_coverage_binding},null,2);
function draw(){const c=R.candidates.find(x=>x.id===$('candidate').value),d=+$('depth').value,s=c.stages[d],initial=c.stages[0];$('name').textContent=label(c.id);$('interval').textContent=pct(s.area_fraction_lower)+' – '+pct(s.area_fraction_upper);$('uncertainty').textContent=pct(s.unresolved_area_fraction)+' unresolved (originally '+pct(initial.unresolved_area_fraction)+').';$('budget').textContent=s.queries_used+' / '+s.query_budget+' queries used\n'+s.leaf_cells+' calculation cells\n'+s.unresolved_positive_cells+' unresolved positive-area cells\nFinal stop: '+label(c.stop_reason);$('gate').textContent=label(c.collision_gate);$('gate').style.borderLeftColor=c.collision_gate.startsWith('blocked')?'#f29181':'#86cfc5';const ymax=Math.max(.001,initial.area_fraction_upper*1.15),x=i=>70+i*155,y=v=>270-v/ymax*235;let g='<rect width="620" height="330" rx="10" fill="#0a1b2b"/>';for(let j=0;j<=4;j++){let v=ymax*j/4,yy=y(v);g+='<line x1="70" y1="'+yy+'" x2="535" y2="'+yy+'" stroke="#345069"/><text x="60" y="'+(yy+4)+'" text-anchor="end" fill="#c5d6e4" font-size="12">'+(100*v).toFixed(2)+'%</text>'}const lo=c.stages.map((z,i)=>x(i)+','+y(z.area_fraction_lower)),hi=c.stages.map((z,i)=>x(i)+','+y(z.area_fraction_upper));g+='<polygon points="'+lo.concat([...hi].reverse()).join(' ')+'" fill="#d8b56d" opacity=".3"/><polyline points="'+lo.join(' ')+'" fill="none" stroke="#8de0ca" stroke-width="3"/><polyline points="'+hi.join(' ')+'" fill="none" stroke="#e3bd74" stroke-width="3"/><line x1="'+x(d)+'" y1="20" x2="'+x(d)+'" y2="280" stroke="#fff" stroke-dasharray="5 5"/>';c.stages.forEach((z,i)=>{g+='<circle cx="'+x(i)+'" cy="'+y(z.area_fraction_lower)+'" r="4" fill="#8de0ca"/><circle cx="'+x(i)+'" cy="'+y(z.area_fraction_upper)+'" r="4" fill="#e3bd74"/><text x="'+x(i)+'" y="302" text-anchor="middle" fill="#d9e5ef" font-size="12">Level '+i+'</text>'});$('chart').innerHTML=g;$('rows').replaceChildren();for(const a of R.candidates){const z=a.stages[d],tr=document.createElement('tr');if(a.id===c.id)tr.style.background='#27465e';for(const v of[label(a.id),pct(z.area_fraction_lower)+' – '+pct(z.area_fraction_upper),pct(z.unresolved_area_fraction),z.queries_used,label(a.collision_gate)]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('rows').append(tr)}}$('candidate').onchange=$('depth').onchange=draw;$('download').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_adaptive_coverage_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};window.addEventListener('pageshow',draw);draw();})();
</script></main></body></html>'''


