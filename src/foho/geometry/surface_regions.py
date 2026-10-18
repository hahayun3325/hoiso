"""Connected regions of authenticated adaptive cells; no contact inference."""
import base64, hashlib, json, math
from collections import defaultdict
from pathlib import Path

PURPOSE = 'surface_regions'
SCHEMA = 'tracehoi.SurfaceRegions.v1'
FILES = {'regions.json','index.html','surface_map.html','adaptive.html','reference_annotation.html','README.md','files.json'}

def require(ok, message):
    if not ok: raise ValueError(message)

def bary_triangle(path):
    require(type(path) is str and len(path) <= 3 and all(x in '0123' for x in path), 'cell_path')
    t = ((8,0,0),(0,8,0),(0,0,8))
    for digit in path:
        a,b,c = t
        ab,bc,ca = [tuple((x+y)//2 for x,y in zip(p,q)) for p,q in [(a,b),(b,c),(c,a)]]
        t = [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)][int(digit)]
    return t

def edge_interval(face_index, face, a, b):
    weights = [{v:w for v,w in zip(face,p) if w} for p in (a,b)]
    support = sorted(set(weights[0]) | set(weights[1]))
    if len(support) == 2:
        key = ('mesh_edge', *support)
        ends = [w.get(support[1],0) for w in weights]
    else:
        x,y = a[1:]; u,v = b[1:]
        A,B = v-y,x-u; C = A*x+B*y
        g = math.gcd(math.gcd(abs(A),abs(B)),abs(C))
        require(g > 0, 'zero_edge')
        A,B,C = A//g,B//g,C//g
        if A < 0 or (A == 0 and B < 0): A,B,C = -A,-B,-C
        key = ('face',face_index,A,B,C)
        ends = [x,u] if x != u else [y,v]
    return key,min(ends),max(ends)

def adjacency(faces, leaves, nvertices, partition):
    require(type(nvertices) is int and 0 < nvertices <= 100000, 'vertex_bound')
    require(0 < len(faces) <= 10000 and len(leaves) <= 100000, 'topology_bound')
    mesh_edges = defaultdict(int); seen = set()
    for face in faces:
        require(len(face)==3 and all(type(v) is int and 0<=v<nvertices for v in face) and len(set(face))==3,'face_indices')
        key=tuple(sorted(face));require(key not in seen,'duplicate_face');seen.add(key)
        for a,b in zip(face,face[1:]+face[:1]): mesh_edges[tuple(sorted((a,b)))] += 1
    require(all(n<=2 for n in mesh_edges.values()), 'nonmanifold_edge')
    partition(leaves,len(faces)); lines=defaultdict(list)
    for i,leaf in enumerate(leaves):
        f=leaf['face_index'];t=bary_triangle(leaf['path'])
        for a,b in zip(t,t[1:]+t[:1]):
            key,lo,hi=edge_interval(f,faces[f],a,b);require(lo<hi,'zero_edge')
            lines[key].append((lo,hi,i))
    edges=set()
    for segments in lines.values():
        segments.sort()
        for j,(lo,hi,i) in enumerate(segments):
            for lo2,hi2,k in segments[j+1:]:
                if lo2>=hi: break
                if i!=k and min(hi,hi2)>max(lo,lo2):edges.add(tuple(sorted((i,k))))
    return sorted(edges),dict(source_edges=len(mesh_edges),boundary_edges=sum(v==1 for v in mesh_edges.values()),nonmanifold_edges=0)

def components(nodes, edges):
    nodes=set(nodes); links={i:set() for i in nodes}
    for a,b in edges:
        if a in nodes and b in nodes:links[a].add(b);links[b].add(a)
    groups=[]
    while nodes:
        start=min(nodes);nodes.remove(start);todo=[start];group=[]
        while todo:
            i=todo.pop();group.append(i)
            for j in sorted(links[i] & nodes):nodes.remove(j);todo.append(j)
        groups.append(sorted(group))
    return groups

def regions(leaves,edges):
    states={'within_bound','unresolved','outside_bound'}
    for leaf in leaves:
        require(leaf['state'] in states and type(leaf['area']) in (int,float) and math.isfinite(leaf['area']) and leaf['area']>=0,'leaf_state_area')
    total=math.fsum(l['area'] for l in leaves);require(total>0,'zero_total_area')
    inside={i for i,l in enumerate(leaves) if l['area']>0 and l['state']=='within_bound'}
    possible={i for i,l in enumerate(leaves) if l['area']>0 and l['state']!='outside_bound'}
    core_groups=components(inside,edges); groups=components(possible,edges)
    core_index=[-1]*len(leaves);region_index=[-1]*len(leaves);cores=[];result=[]
    for k,g in enumerate(core_groups):
        for i in g:core_index[i]=k
        area=math.fsum(leaves[i]['area'] for i in g)
        cores.append(dict(id=k,leaf_indices=g,area=area,area_fraction=area/total))
    for k,g in enumerate(groups):
        for i in g:region_index[i]=k
        lower=math.fsum(leaves[i]['area'] for i in g if i in inside)
        unresolved=math.fsum(leaves[i]['area'] for i in g if i not in inside)
        result.append(dict(id=k,leaf_indices=g,core_ids=sorted({core_index[i] for i in g if core_index[i]>=0}),
            area_lower=lower,unresolved_area=unresolved,area_upper=lower+unresolved,
            fraction_lower=lower/total,fraction_upper=(lower+unresolved)/total,
            source_faces=sorted({leaves[i]['face_index'] for i in g}),accepted=False))
    lower=math.fsum(leaves[i]['area'] for i in inside);upper=math.fsum(leaves[i]['area'] for i in possible)
    require(math.isclose(math.fsum(c['area_lower'] for c in result),lower,rel_tol=1e-12,abs_tol=1e-15) and
            math.isclose(math.fsum(c['area_upper'] for c in result),upper,rel_tol=1e-12,abs_tol=1e-15),'region_area_conservation')
    return dict(total_area=total,area_lower=lower,area_upper=upper,core_components=cores,possible_regions=result,
        core_index=core_index,region_index=region_index,zero_area_cells=sum(l['area']==0 for l in leaves),
        positive_outside_cells=sum(l['area']>0 and l['state']=='outside_bound' for l in leaves))

def summarize(mapped,mapmod):
    require(mapped['placement_ready'] is False and mapped['selected_candidate'] is None and mapped['accepted_scale'] is None,'source_acceptance')
    candidates=[]
    for c in mapped['candidates']:
        require(c['accepted'] is False,'candidate_accepted')
        edges,topology=adjacency(c['faces'],c['leaves'],len(c['vertices']),mapmod.partition)
        group=regions(c['leaves'],edges)
        require(math.isclose(group['total_area'],c['stage']['total_area'],rel_tol=1e-12,abs_tol=1e-15),'source_area')
        for field,key in [('area_lower','area_fraction_lower'),('area_upper','area_fraction_upper')]:
            require(math.isclose(group[field]/group['total_area'],c['stage'][key],rel_tol=1e-12,abs_tol=1e-15),'source_coverage')
        digest=hashlib.sha256(json.dumps(edges,separators=(',',':')).encode()).hexdigest()
        candidates.append(dict(id=c['id'],hand_binding=c['hand_binding'],collision_gate=c['collision_gate'],
            adjacency_edges=len(edges),adjacency_sha256=digest,topology=topology,accepted=False,**group))
    return candidates

def build(workspace,wsha,distances,dsha,coverage,csha,adaptive,asha,surface_map,msha,case,*mods,purpose):
    require(purpose==PURPOSE,'surface_regions_purpose_required')
    reader,pipeline,mapmod=mods[0],mods[8],mods[13]
    roots=[workspace,distances,coverage,adaptive,surface_map];before=[pipeline.inventory(p,reader) for p in roots]
    audit=mapmod.verify(surface_map,msha,workspace,wsha,distances,dsha,coverage,csha,adaptive,asha,case,*mods[:13],purpose=mapmod.PURPOSE)
    mapped=reader.parse(before[4]['surface_map.json'])
    report=dict(schema=SCHEMA,purpose=PURPOSE,case_id=case,candidates=summarize(mapped,mapmod),
        source_map_binding=reader.binding(before[4]['files.json']),source_workspace_binding=mapped['source_workspace_binding'],object_binding=mapped['object_binding'],
        scene_frame=mapped['scene_frame'],units=mapped['units'],threshold=mapped['threshold'],threshold_object_diagonal_ratio=mapped['threshold_object_diagonal_ratio'],
        reference_status=mapped['reference_status'],selected_candidate=None,accepted_scale=None,placement_ready=False,full_parent_acceptance=False,
        mask_accuracy_verified=False,physical_contact_verified=False,scale_identified=False,source_geometry_modified=False,new_surface_queries=0,model_calls=0,
        source_queries_replayed=mapped['source_queries_replayed'],connectivity='positive_length_shared_topological_edge',
        limitations=['Regions use existing guarded bounds at the fixed 2% object-diagonal threshold; this is not a contact threshold.',
         'Core components contain positive-area within-bound cells. Possible regions include unresolved cells that may connect distinct cores.',
         'Possible-region area intervals bound the total within-threshold area inside that region. They do not bound the size or number of actual connected proximity components.',
         'Corner-only touches, zero-area cells and outside-bound cells do not connect regions. Mesh indices define adjacency; coincident unshared vertices are not welded.',
         'The mesh is an open hand surface. These topological patches do not certify volume containment, penetration or physical contact.',
         'The independent mask reference is still missing. Metric scale, geometric accuracy and placement remain unverified.'])
    display=dict(mapped,region_report=report)
    package=reader.parse(before[0]['scene/package.json'])
    _,data=reader.inspect_bundle(Path(workspace)/'scene/source/scene.json',package['source_manifest_binding']['sha256'],case)
    files={'regions.json':reader.encode(report),'index.html':html(display,data['original_rgb']),
        'surface_map.html':before[4]['index.html'],'adaptive.html':before[4]['adaptive.html'],'reference_annotation.html':before[4]['reference_annotation.html'],
        'README.md':b'TraceHOI connected surface regions\n\nOpen index.html offline; choose a candidate and possible region. Core cells are within the saved distance bound; unresolved cells may connect cores. Region totals are conditional geometry diagnostics, not accepted contact. All seven files belong together. Source meshes, masks, review records and collision gates are unchanged.\n'}
    files['files.json']=reader.encode(dict(schema='tracehoi.SurfaceRegionFiles.v1',files={n:reader.binding(b) for n,b in files.items()},source_map_binding=report['source_map_binding'],placement_ready=False))
    require([pipeline.inventory(p,reader) for p in roots]==before,'region_sources_changed')
    return report,files,audit

def verify(out,sha,*args,purpose):
    require(purpose==PURPOSE,'surface_regions_purpose_required')
    reader,pipeline=args[11],args[19];actual=pipeline.inventory(out,reader)
    require(set(actual)==FILES,'surface_regions_inventory')
    require(reader.binding(actual['files.json'])['sha256']==sha,'surface_regions_receipt')
    require(reader.parse(actual['files.json'])['files']=={n:reader.binding(b) for n,b in actual.items() if n!='files.json'},'surface_regions_hashes')
    report,expected,audit=build(*args,purpose=purpose);require(actual==expected,'surface_regions_reconstruction')
    return dict(verified=True,receipt_binding=reader.binding(actual['files.json']),source_numerical_audit=audit['source_numerical_audit'],placement_ready=False,selected_candidate=None)

def html(report,rgb):
    payload=json.dumps(report,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',payload).replace('__RGB__',base64.b64encode(rgb).decode()).encode()

TEMPLATE = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; connect-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>TraceHOI · Connected surface regions</title><style>\n:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c1725;color:#eef5fb;font:15px/1.55 system-ui}main{max-width:1320px;padding:28px;margin:auto}h1{font-size:38px;line-height:1.1;margin:10px 0 16px}h2{font-size:20px;margin:0 0 12px}.eyebrow{color:#87decf;font-size:12px;letter-spacing:2px}.top{display:grid;grid-template-columns:3fr 1fr;gap:30px}.photo{width:100%;height:160px;object-fit:contain;background:#07111b;border-radius:10px}.notice{background:#332c22;border-left:3px solid #e4b96b;padding:12px 16px;margin:18px 0}.layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:20px}.panel{background:#15283b;border:1px solid #37536a;border-radius:12px;padding:20px}.controls{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:12px 0}button,select,input[type=number]{font:inherit;color:inherit;background:#203d55;border:1px solid #7794ad;border-radius:5px;padding:7px}input[type=number]{width:95px}label{font-size:13px}input[type=range]{width:100px;vertical-align:middle}canvas{width:100%;aspect-ratio:1.2;display:block;background:#081523;border-radius:8px;touch-action:none}.small{font-size:12px;color:#b8cadb}.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px}.within{color:#73dbc5}.uncertain{color:#ffcc6d}.outside{color:#90a7c0}.big{font-size:26px;color:#83decd}a{color:#a7dfff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 ui-monospace,monospace}dl{display:grid;grid-template-columns:1fr 1.3fr;gap:7px;font-size:13px}dt{color:#b8cadb}dd{margin:0;overflow-wrap:anywhere}footer{margin-top:20px;color:#b8cadb;font-size:12px}:focus-visible{outline:2px solid #8de0ca;outline-offset:3px}@media(max-width:850px){.top,.layout{grid-template-columns:1fr}main{padding:16px}h1{font-size:30px}.photo{height:130px}}\n</style></head><body><main><header class="top"><div><div class="eyebrow">TRACEHOI / SAVED SURFACE EVIDENCE</div><h1>Find connected regions of possible proximity.</h1><p id="case"></p><p>Explore connected regions on each unchanged hand mesh. Green cells are within the saved distance bound; amber cells may connect otherwise separate green cores.</p></div><img class="photo" src="data:image/png;base64,__RGB__" alt="Original case RGB crop"></header><div class="notice">Diagnostic geometry. No physical contact, mask accuracy, metric scale or pipeline placement is accepted.</div>\n<div class="layout"><section class="panel"><h2>Region explorer</h2><div class="controls"><label>Candidate <select id="candidate"></select></label><label>Possible region <select id="region"></select></label><label>Cells <select id="filter"><option value="all">All cells</option><option value="near" selected>Within + unresolved</option><option value="unresolved">Unresolved only</option><option value="within_bound">Within bound only</option></select></label><label>Focus <select id="focus"><option value="hand">Hand</option><option value="scene">Scene</option></select></label><button id="reset">Reset view</button></div><canvas id="scene" width="960" height="800" role="img" aria-label="Adaptive hand cells; drag to orbit and click to inspect"></canvas><div class="controls"><label>Yaw <input id="yaw" type="range" min="-180" max="180" value="0"></label><label>Pitch <input id="pitch" type="range" min="-90" max="90" value="0"></label><label>Zoom <input id="zoom" type="range" min="0.5" max="5" step="0.1" value="1"></label><label><input id="object" type="checkbox" checked> Object points</label><label><input id="edges" type="checkbox"> Cell edges</label><label><input id="witness" type="checkbox" checked> Selected witness</label></div><div class="legend"><span class="within">● Within bound</span><span class="uncertain">● Unresolved</span><span class="outside">● Outside bound</span></div><p class="small">Drag to rotate; click a visible cell. Object points are sampled for display. Orthographic painter rendering does not certify occlusion. Filtering hides cells without changing any metric.</p></section>\n<aside class="panel"><h2 id="candidateName"></h2><div class="big" id="interval"></div><p class="small" id="summary"></p><div class="notice" id="gate"></div><h2>Region evidence</h2><p id="regionStats"></p><p class="small">A possible region can contain several separated cores joined through unresolved cells. Its area interval describes total area within the bound, not one confirmed connected patch.</p><button id="downloadRegion">Download region evidence</button><h2 style="margin-top:24px">Inspect a calculation cell</h2><div class="controls"><label>Cell index <input id="cell" type="number" min="0" value="0"></label><button id="previous" aria-label="Previous cell">←</button><button id="next" aria-label="Next cell">→</button></div><p id="selectionStatus" class="small" aria-live="polite"></p><dl id="details"></dl><p id="witnessNote" class="small"></p><button id="download">Download selected cell evidence</button><p class="small">The orange segment joins a saved cell centroid to its nearest point on the full object surface. The outlined object triangle is the corresponding witness face. This segment is not the global mesh gap.</p></aside></div>\n<section class="panel" style="margin-top:20px"><h2>Keep the evidence connected</h2><p><a href="surface_map.html">Open the original surface map ↗</a> · <a href="adaptive.html">Open the authenticated interval dashboard ↗</a> · <a href="reference_annotation.html">Open independent-reference annotation ↗</a></p><details><summary>Source bindings and display limits</summary><pre id="sources"></pre></details></section><footer>Offline · saved CPU diagnostics · no additional refinement · all source meshes, masks and review records preserved. This viewer does not record an acceptance decision.</footer>\n<script id="data" type="application/json">__DATA__</script><script>\n(()=>{\'use strict\';const R=JSON.parse(document.getElementById(\'data\').textContent),$=id=>document.getElementById(id),cv=$(\'scene\'),ctx=cv.getContext(\'2d\'),label=s=>s.replaceAll(\'_\',\' \'),pct=x=>(100*x).toFixed(3)+\'%\',colors={within_bound:\'#73dbc5\',unresolved:\'#ffcc6d\',outside_bound:\'#506e8b\'};let cr,c,triangles,queryMap,pick=[],selected=0,drag=null,moved=false;\nfor(const a of R.candidates){const o=document.createElement(\'option\');o.value=a.id;o.textContent=label(a.id);$(\'candidate\').append(o)}$(\'case\').textContent=R.case_id+\' · \'+R.object_source_faces.toLocaleString()+\' object triangles · final subdivision level\';$(\'sources\').textContent=R.region_report.limitations.concat(R.limitations).join(\'\\n\\n\')+\'\\n\\n\'+JSON.stringify({adaptive:R.source_adaptive_binding,workspace:R.source_workspace_binding,object:R.object_binding,frame:R.scene_frame,units:R.units},null,2);\nconst midpoint=(a,b)=>a.map((v,i)=>(v+b[i])/2);function split(t){let[a,b,c]=t,ab=midpoint(a,b),bc=midpoint(b,c),ca=midpoint(c,a);return[[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]}function cellTriangle(l){let t=c.faces[l.face_index].map(i=>c.vertices[i]);for(const d of l.path)t=split(t)[+d];return t}function shown(l){const i=c.leaves.indexOf(l),r=$(\'region\').value,f=$(\'filter\').value;return (r===\'all\'||cr.region_index[i]===Number(r))&&(f===\'all\'||f===\'near\'&&l.state!==\'outside_bound\'||f===l.state)}\nfunction change(){c=R.candidates.find(x=>x.id===$(\'candidate\').value);cr=R.region_report.candidates.find(x=>x.id===c.id);$(\'region\').replaceChildren();for(const r of [{id:\'all\',name:\'All possible regions\'},...cr.possible_regions.map(r=>({id:r.id,name:\'Region \'+(r.id+1)+\' · \'+r.leaf_indices.length+\' cells\'}))]){const o=document.createElement(\'option\');o.value=r.id;o.textContent=r.name;$(\'region\').append(o)}regionStats();triangles=c.leaves.map(cellTriangle);queryMap=new Map(c.witnesses.map(w=>[w.leaf_index,w]));selected=Math.max(0,c.leaves.findIndex(l=>l.state===\'unresolved\'));$(\'cell\').max=c.leaves.length-1;$(\'candidateName\').textContent=label(c.id);$(\'interval\').textContent=pct(c.stage.area_fraction_lower)+\' – \'+pct(c.stage.area_fraction_upper);$(\'summary\').textContent=\'Hand area within 2% of object diagonal: \'+R.threshold.toPrecision(5)+\' scene units. \'+c.leaves.length.toLocaleString()+\' cells; \'+pct(c.stage.unresolved_area_fraction)+\' unresolved.\';$(\'gate\').textContent=label(c.collision_gate);$(\'gate\').style.borderLeftColor=c.collision_gate.startsWith(\'blocked\')?\'#f18e84\':\'#83decd\';update()}\nfunction bounds(){const pts=$(\'focus\').value===\'hand\'?c.vertices:c.vertices.concat(R.object_preview.points);let lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(const p of pts)for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],p[k]);hi[k]=Math.max(hi[k],p[k])}return{center:lo.map((x,k)=>(x+hi[k])/2),radius:Math.max(1e-8,Math.hypot(...hi.map((x,k)=>x-lo[k]))/2)}}\nfunction draw(){ctx.clearRect(0,0,cv.width,cv.height);const b=bounds(),yaw=+$(\'yaw\').value*Math.PI/180,pitch=+$(\'pitch\').value*Math.PI/180,scale=330*+$(\'zoom\').value/b.radius;function project(p){let[x,y,z]=p.map((v,k)=>v-b.center[k]),xx=x*Math.cos(yaw)+z*Math.sin(yaw),zz=-x*Math.sin(yaw)+z*Math.cos(yaw),yy=y*Math.cos(pitch)-zz*Math.sin(pitch);zz=y*Math.sin(pitch)+zz*Math.cos(pitch);return[480+scale*xx,400-scale*yy,zz]}\nconst items=[];if($(\'object\').checked)for(const p of R.object_preview.points){const q=project(p);items.push({z:q[2],point:q})}pick=[];for(let i=0;i<c.leaves.length;i++){if(!shown(c.leaves[i]))continue;const t=triangles[i].map(project);items.push({z:t.reduce((s,p)=>s+p[2],0)/3,t,i})}items.sort((a,b)=>a.z-b.z);for(const item of items){if(item.point){ctx.fillStyle=\'#6d9da380\';ctx.fillRect(item.point[0]-1,item.point[1]-1,2,2);continue}const {t,i}=item;ctx.beginPath();ctx.moveTo(t[0][0],t[0][1]);ctx.lineTo(t[1][0],t[1][1]);ctx.lineTo(t[2][0],t[2][1]);ctx.closePath();ctx.fillStyle=colors[c.leaves[i].state];ctx.fill();if($(\'edges\').checked){ctx.strokeStyle=\'#0b172555\';ctx.lineWidth=.55;ctx.stroke()}pick.push({t,i})}\nif(shown(c.leaves[selected])){const t=triangles[selected].map(project);ctx.beginPath();t.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.strokeStyle=\'#ffffff\';ctx.lineWidth=2;ctx.stroke()}\nconst w=queryMap.get(selected);if(w&&shown(c.leaves[selected])&&$(\'witness\').checked){let a=project(w.query.centroid),b=project(w.query.point);ctx.strokeStyle=\'#ff8f61\';ctx.lineWidth=2;ctx.setLineDash([5,3]);ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.setLineDash([]);for(const p of[a,b]){ctx.beginPath();ctx.arc(p[0],p[1],4,0,2*Math.PI);ctx.fillStyle=\'#ff8f61\';ctx.fill()}const t=w.object_triangle_vertices.map(project);ctx.beginPath();t.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.stroke()}\nctx.fillStyle=\'#c9d8e8\';ctx.font=\'14px system-ui\';ctx.fillText(\'x right · y up · z backward / orthographic preview\',18,28);$(\'selectionStatus\').textContent=shown(c.leaves[selected])?\'Selected cell outlined in white.\':\'Selected cell is hidden by the display filter.\';$(\'selectionStatus\').textContent+=\' Displayed cells: \'+pick.length+\'.\';cv.dataset.visibleCells=pick.length;cv.dataset.selectedCell=selected}\nfunction update(){const l=c.leaves[selected],w=queryMap.get(selected);$(\'cell\').value=selected;$(\'details\').replaceChildren();const rows=[[\'Possible region\',cr.region_index[selected]<0?\'None\':cr.region_index[selected]+1],[\'Core component\',cr.core_index[selected]<0?\'None\':cr.core_index[selected]+1],[\'Classification\',label(l.state)],[\'Source face\',l.face_index],[\'Subdivision path\',l.path||\'root\'],[\'Distance lower\',l.lower.toPrecision(8)],[\'Distance upper\',l.upper.toPrecision(8)],[\'Area\',l.area.toPrecision(8)],[\'Object witness face\',w?w.query.object_triangle:\'No adaptive query\'],[\'Centroid distance\',w?w.query.distance.toPrecision(8):\'Inherited K4 bounds\']];for(const[k,v]of rows){const dt=document.createElement(\'dt\'),dd=document.createElement(\'dd\');dt.textContent=k;dd.textContent=v;$(\'details\').append(dt,dd)}$(\'witnessNote\').textContent=w?\'This leaf has a saved centroid query; its object face and point are preserved exactly.\':\'This unsplit root cell has inherited bounds. No new adaptive centroid witness was recorded.\';draw()}\nfunction regionStats(){const id=$(\'region\').value,r=cr.possible_regions.find(r=>String(r.id)===id);$(\'regionStats\').textContent=r?\'Region \'+(r.id+1)+\': \'+r.core_ids.length+\' resolved cores · \'+r.leaf_indices.length+\' cells · \'+pct(r.fraction_lower)+\' – \'+pct(r.fraction_upper)+\' of hand area.\':cr.possible_regions.length+\' possible regions · \'+cr.core_components.length+\' resolved cores. \'+(cr.possible_regions.length?\'Select a region to inspect its cells.\':\'No positive-area cell can lie within this saved distance bound.\');}\n$(\'region\').onchange=()=>{regionStats();const i=c.leaves.findIndex(shown);if(i>=0)selected=i;update()};\n$(\'downloadRegion\').onclick=()=>{const id=$(\'region\').value,r=cr.possible_regions.find(r=>String(r.id)===id)||null;const record={schema:\'tracehoi.SurfaceRegionSelection.v1\',case_id:R.case_id,candidate:c.id,region:r,all_regions:r?null:cr.possible_regions,core_components:r?cr.core_components.filter(x=>r.core_ids.includes(x.id)):cr.core_components,source_map_binding:R.region_report.source_map_binding,hand_binding:c.hand_binding,object_binding:R.object_binding,collision_gate:c.collision_gate,connectivity:R.region_report.connectivity,physical_contact_verified:false,accepted:false,placement_ready:false};const u=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+\'\\n\'],{type:\'application/json\'})),a=document.createElement(\'a\');a.href=u;a.download=\'tracehoi_surface_region_\'+c.id+\'_\'+id+\'.json\';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};\n$(\'candidate\').onchange=change;for(const id of[\'filter\',\'focus\',\'yaw\',\'pitch\',\'zoom\',\'object\',\'edges\',\'witness\'])$(id).oninput=draw;$(\'reset\').onclick=()=>{$(\'yaw\').value=0;$(\'pitch\').value=0;$(\'zoom\').value=1;draw()};$(\'cell\').onchange=()=>{selected=Math.max(0,Math.min(c.leaves.length-1,Math.trunc(Number($(\'cell\').value)||0)));update()};$(\'previous\').onclick=()=>{selected=(selected+c.leaves.length-1)%c.leaves.length;update()};$(\'next\').onclick=()=>{selected=(selected+1)%c.leaves.length;update()};cv.onpointerdown=e=>{drag=[e.clientX,e.clientY,+$(\'yaw\').value,+$(\'pitch\').value];moved=false;cv.setPointerCapture(e.pointerId)};cv.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(Math.hypot(dx,dy)>3)moved=true;if(moved){$(\'yaw\').value=Math.max(-180,Math.min(180,drag[2]+dx*.5));$(\'pitch\').value=Math.max(-90,Math.min(90,drag[3]+dy*.5));draw()}};cv.onpointercancel=()=>{drag=null};cv.onpointerup=e=>{if(!drag)return;drag=null;if(moved)return;const r=cv.getBoundingClientRect(),x=(e.clientX-r.left)*cv.width/r.width,y=(e.clientY-r.top)*cv.height/r.height;function inside(t){const s=t.map((p,i)=>{const q=t[(i+1)%3];return(q[0]-p[0])*(y-p[1])-(q[1]-p[1])*(x-p[0])});const a=Math.abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[2][0]-t[0][0])*(t[1][1]-t[0][1]));return a>1e-10&&(s.every(v=>v>=-1e-8)||s.every(v=>v<=1e-8))}for(let i=pick.length-1;i>=0;i--)if(inside(pick[i].t)){selected=pick[i].i;update();break}};\n$(\'download\').onclick=()=>{const record={schema:\'tracehoi.SurfaceMapSelection.v1\',case_id:R.case_id,candidate:c.id,cell_index:selected,cell:c.leaves[selected],triangle:triangles[selected],witness:queryMap.get(selected)||null,source_adaptive_binding:R.source_adaptive_binding,hand_binding:c.hand_binding,object_binding:R.object_binding,accepted:false,placement_ready:false};const u=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+\'\\n\'],{type:\'application/json\'})),a=document.createElement(\'a\');a.href=u;a.download=\'tracehoi_surface_cell_\'+c.id+\'_\'+selected+\'.json\';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};change();})();\n</script></main></body></html>\n'
