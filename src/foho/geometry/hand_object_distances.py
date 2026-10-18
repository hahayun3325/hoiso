"""Unsigned hand-vertex to object-triangle diagnostics; no placement decision.

Pure standard library. Queries use every object triangle, not the display sample.
The nearest point on a triangle is its interior projection or a clamped edge.
Degenerate triangles are handled by their edges. AABB branch-and-bound finds
the numerical minimum, retaining the lowest face index for exact distance ties.
"""
import heapq,json,math,tempfile,base64
from pathlib import Path

PURPOSE='hand_object_distances'
SCHEMA='tracehoi.HandObjectDistances.v1'
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def point_ok(p):return len(p)==3 and all(type(x) in (int,float) and math.isfinite(x) and abs(x)<=1e6 for x in p)

def closest(p,triangle):
    """Return squared distance, nearest point and nonnegative barycentric weights."""
    require(point_ok(p) and len(triangle)==3 and all(point_ok(v) for v in triangle),'finite_triangle_query_required')
    a,b,c=triangle;ab=sub(b,a);ac=sub(c,a);n=cross(ab,ac);nn=dot(n,n);choices=[]
    if nn>0:
        k=dot(sub(p,a),n)/nn;q=tuple(p[i]-k*n[i] for i in range(3))
        v=dot(cross(sub(q,a),ac),n)/nn;w=dot(cross(ab,sub(q,a)),n)/nn
        if v>=0 and w>=0 and v+w<=1:
            weights=(1-v-w,v,w);q=tuple(sum(weights[j]*triangle[j][i] for j in range(3)) for i in range(3))
            choices.append((dot(sub(p,q),sub(p,q)),q,weights))
    for i,j in ((0,1),(1,2),(2,0)):
        v=sub(triangle[j],triangle[i]);den=dot(v,v)
        t=max(0.,min(1.,dot(sub(p,triangle[i]),v)/den)) if den else 0.
        weights=[0.,0.,0.];weights[i]=1-t;weights[j]+=t
        q=tuple(triangle[i][k]+t*v[k] for k in range(3));delta=sub(p,q)
        choices.append((dot(delta,delta),q,tuple(weights)))
    return min(choices,key=lambda x:x[0])

class SurfaceIndex:
    """Immutable triangle BVH with explicit limits; queries never mutate meshes."""
    def __init__(self,vertices,faces,leaf=16):
        require(0<len(vertices)<=80000 and all(point_ok(p) for p in vertices),'object_vertices')
        require(0<len(faces)<=160000 and all(len(f)==3 and all(type(i) is int and 0<=i<len(vertices) for i in f) for f in faces),'object_faces')
        require(type(leaf) is int and 1<=leaf<=64,'leaf_bound')
        self.tri=tuple(tuple(tuple(vertices[i]) for i in f) for f in faces)
        self.lo=[tuple(min(p[k] for p in t) for k in range(3)) for t in self.tri]
        self.hi=[tuple(max(p[k] for p in t) for k in range(3)) for t in self.tri]
        centers=[tuple((a+b)/2 for a,b in zip(lo,hi)) for lo,hi in zip(self.lo,self.hi)];self.nodes=[]
        def build(ids):
            lo=tuple(min(self.lo[i][k] for i in ids) for k in range(3));hi=tuple(max(self.hi[i][k] for i in ids) for k in range(3))
            pos=len(self.nodes);self.nodes.append(None)
            if len(ids)<=leaf:self.nodes[pos]=(lo,hi,tuple(ids),None)
            else:
                axis=max(range(3),key=lambda k:max(centers[i][k] for i in ids)-min(centers[i][k] for i in ids))
                ids.sort(key=lambda i:(centers[i][axis],i));m=len(ids)//2
                self.nodes[pos]=(lo,hi,None,(build(ids[:m]),build(ids[m:])))
            return pos
        build(list(range(len(faces))))
        self.diagonal=math.dist(self.nodes[0][0],self.nodes[0][1])
    def nearest(self,p,max_nodes=50000):
        require(point_ok(p),'finite_query_required');require(type(max_nodes) is int and 0<max_nodes<=320000,'node_budget')
        queue=[(0.,0)];best=None;visited=0;tested=0
        # Generous pruning slack only explores extra nodes; it never alters distances.
        slack=1e-12*max(self.diagonal**2,1.)
        while queue:
            lower,i=heapq.heappop(queue)
            if best is not None and lower>best[0]+slack:continue
            visited+=1;require(visited<=max_nodes,'distance_node_budget')
            lo,hi,ids,children=self.nodes[i]
            if ids is not None:
                for face in ids:
                    d,q,b=closest(p,self.tri[face]);tested+=1
                    if best is None or (d,face)<best[:2]:best=(d,face,q,b)
            else:
                for child in children:
                    lo,hi,_,_=self.nodes[child];bound=sum(max(lo[k]-p[k],p[k]-hi[k],0.)**2 for k in range(3))
                    if best is None or bound<=best[0]+slack:heapq.heappush(queue,(bound,child))
        require(best is not None,'missing_witness')
        return dict(distance=math.sqrt(best[0]),object_triangle=best[1],point=list(best[2]),barycentric=list(best[3]),nodes_visited=visited,triangles_tested=tested)

def quantile(xs,fraction):
    xs=sorted(xs);i=(len(xs)-1)*fraction;lo=int(i);hi=min(lo+1,len(xs)-1)
    return xs[lo]+(i-lo)*(xs[hi]-xs[lo])

def measure(index,vertices):
    require(0<len(vertices)<=2000,'hand_vertex_bound');require(index.diagonal>0,'zero_object_extent')
    rows=[]
    for i,p in enumerate(vertices):
        r=index.nearest(p);r.update(vertex_index=i,normalized_distance=r['distance']/index.diagonal);rows.append(r)
    ds=[r['distance'] for r in rows]
    summary=dict(vertex_count=len(rows),minimum=min(ds),median=quantile(ds,.5),p90=quantile(ds,.9),maximum=max(ds),
        fractions_at_object_diagonal_ratio={str(t):sum(r['normalized_distance']<=t for r in rows)/len(rows) for t in (.001,.005,.01,.02)},
        nodes_visited=sum(r['nodes_visited'] for r in rows),triangles_tested=sum(r['triangles_tested'] for r in rows))
    return rows,summary

def build(workspace,workspace_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,pipeline,*,purpose):
    require(purpose==PURPOSE,'hand_object_distances_purpose_required')
    original=pipeline.inventory(workspace,reader)
    # Freeze the entire input before semantic validation and geometry access.
    with tempfile.TemporaryDirectory(prefix='tracehoi-distances-') as t:
        snap=Path(t).resolve()/'workspace';export.publish(snap,original,reader)
        receipt=pipeline.verify(snap,workspace_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,purpose=pipeline.PURPOSE)
        package=reader.parse(original['scene/package.json'])
        manifest,data=reader.inspect_bundle(snap/'scene/source/scene.json',package['source_manifest_binding']['sha256'],case)
    ov,of=reader.mesh(data['object']);index=SurfaceIndex(ov,of);candidates=[];hands={}
    for c in manifest['candidates']:
        raw=data[c['hand_asset']];v,f=reader.mesh(raw);rows,summary=measure(index,v)
        candidates.append(dict(id=c['id'],hand_binding=reader.binding(raw),conditional_scale=c['conditional_scale'],
            collision_gate=c['collision_gate'],prior_triangle_surface_gap=c['unsigned_surface_gap'],accepted=False,summary=summary,vertices=rows))
        hands[c['id']]=dict(vertices=v,faces=f)
    require([c['id'] for c in candidates]==reader.IDS,'candidate_order')
    report=dict(schema=SCHEMA,case_id=case,purpose=PURPOSE,source_workspace_binding=receipt['workspace_binding'],
        source_manifest_binding=package['source_manifest_binding'],object_binding=reader.binding(data['object']),object_vertices=len(ov),object_triangles=len(of),
        object_bbox_diagonal=index.diagonal,scene_frame=manifest['scene_frame'],units=manifest['units'],mesh_model_matrix=reader.IDENTITY,
        method='AABB branch-and-bound: every hand vertex against the full object triangle surface',
        reference_status=receipt['reference_status'],candidates=candidates,selected_candidate=None,accepted_scale=None,
        placement_ready=False,full_parent_acceptance=False,physical_contact_verified=False,geometric_accuracy_verified=False,
        scale_identified=False,mask_accuracy_verified=False,source_geometry_modified=False,model_calls=0,
        limitations=['Unsigned vertex distances do not measure penetration depth or identify physical contact.',
            'Vertex samples are not area-weighted and do not bound distances across the complete hand surface.',
            'The prior triangle-surface minimum and collision gate are separate saved measurements; a low vertex distance never clears a crossing gate.',
            'Scene units have unverified MoGe scale. Display thresholds are exploratory, not acceptance thresholds.',
            'Object display uses a vertex subset; numerical queries use all object triangles.'])
    points=list(ov)+[p for h in hands.values() for p in h['vertices']]
    bounds=[(min(p[k] for p in points),max(p[k] for p in points)) for k in range(3)]
    center=[(a+b)/2 for a,b in bounds];radius=max(math.dist(p,center) for p in points)
    display=dict(report=report,hands=hands,object=export.sample_vertices(ov,3000)['points'],center=center,radius=radius,
        rgb=base64.b64encode(data['original_rgb']).decode())
    files={'distances.json':reader.encode(report),'index.html':html(display),
        'README.md':b'TraceHOI hand-object distance diagnostics\n\nOpen index.html offline. Numerical results use every object triangle and every hand vertex. The object preview is sampled, and hand distances are vertex samples, not a continuous or area-weighted field. Unsigned distance is not contact or penetration. All candidates remain unaccepted. Keep the source diagnostic workspace and its checksum. No masks or geometry were changed.\n'}
    files['files.json']=reader.encode(dict(schema='tracehoi.HandObjectDistancesFiles.v1',source_workspace_binding=receipt['workspace_binding'],files={n:reader.binding(b) for n,b in files.items()},placement_ready=False))
    require(pipeline.inventory(workspace,reader)==original,'workspace_changed_during_distance_build')
    return report,files

def html(display):
    raw=json.dumps(display,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',raw).encode()

def verify(out,receipt_sha,workspace,workspace_sha,case,*modules,purpose):
    require(purpose==PURPOSE,'hand_object_distances_purpose_required');reader=modules[0];pipeline=modules[-1]
    actual=pipeline.inventory(out,reader)
    require(set(actual)=={'distances.json','index.html','README.md','files.json'},'distance_output_inventory')
    require(reader.binding(actual['files.json'])['sha256']==receipt_sha,'distance_receipt_binding')
    m=reader.parse(actual['files.json'])
    require(m['files']=={n:reader.binding(b) for n,b in actual.items() if n!='files.json'},'distance_files_changed')
    report,expected=build(workspace,workspace_sha,case,*modules,purpose=purpose)
    require(actual==expected,'distance_semantic_mismatch')
    return dict(verified=True,receipt_binding=reader.binding(actual['files.json']),source_workspace_binding=report['source_workspace_binding'],placement_ready=False,selected_candidate=None)

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Hand–object distances</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1421;color:#ebf2fa;font:15px/1.55 system-ui}main{max-width:1280px;margin:auto;padding:28px}h1{font-size:36px;margin:8px 0}h2{font-size:19px}.eyebrow{color:#80dbc9;letter-spacing:2px;font-size:12px}.muted{color:#acbed3}.notice{background:#2a251c;border-left:3px solid #e9be75;padding:14px 18px;margin:20px 0}.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:20px}.panel{background:#142234;border:1px solid #344b65;border-radius:12px;padding:18px}.controls{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:12px}button,select{font:inherit;background:#22384e;color:inherit;border:1px solid #66849d;border-radius:6px;padding:8px}button,select,input{cursor:pointer}canvas{width:100%;aspect-ratio:1;display:block;touch-action:none;background:#09131e;border-radius:8px}img{width:100%;border-radius:8px}input[type=range]{max-width:140px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.legend{height:9px;background:linear-gradient(90deg,#ffbc64,#33bad5);border-radius:5px;margin:14px 0 6px}.ends{display:flex;justify-content:space-between;font-size:12px}.metric{font-size:22px;color:#88dece}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid #344b65}.scroll{overflow:auto;margin-top:20px}.small{font-size:12px}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #88dece;outline-offset:3px}@media(max-width:800px){main{padding:15px}.grid{grid-template-columns:1fr}h1{font-size:28px}}
</style></head><body><main><div class="eyebrow">TRACEHOI / SPATIAL DIAGNOSTICS</div><h1>Where is the hand close to the object?</h1><p id="identity" class="muted"></p><div class="notice"><strong>All four candidates remain unaccepted.</strong> Colors show unsigned vertex distances. They do not certify contact, penetration depth, scale or placement. Recorded collision gates remain in force.</div><div class="grid"><section class="panel"><div class="controls"><label>Candidate <select id="candidate"></select></label><button id="reset">Reset view</button><label><input id="focus" type="checkbox" checked> Focus on hand</label><label><input id="object" type="checkbox" checked> Object preview</label></div><canvas id="scene" width="800" height="800" role="img" aria-label="Rotate the distance-colored hand and click a vertex to inspect its closest surface witness"></canvas><div class="controls"><label>Yaw <input id="yaw" type="range" min="-180" max="180" value="0"></label><label>Pitch <input id="pitch" type="range" min="-85" max="85" value="0"></label><label>Zoom <input id="zoom" type="range" min="0.5" max="3" step="0.1" value="1"></label></div><div class="legend"></div><div class="ends"><span>0 · closest</span><span id="colorMax"></span></div><p class="small muted">Drag to orbit. Click a hand vertex to inspect its nearest object-triangle witness. This orthographic display is transparent and does not resolve occlusion. Object preview: 3,000 sampled vertices; distance calculations: every triangle.</p></section><aside class="panel"><h2 id="name"></h2><p id="gate" class="metric"></p><label>Display threshold (% object diagonal)<br><input id="threshold" type="range" min="0.1" max="10" step="0.1" value="2"> <span id="thresholdValue"></span></label><p id="fraction"></p><p id="summary" class="muted"></p><h2>Nearest-surface witness</h2><p class="small muted">The initial vertex is the nearest sampled hand vertex. Changing the candidate only changes the displayed branch.</p><pre id="witness"></pre><img id="rgb" alt="Original RGB crop"><p class="small muted">Reference state: <span id="reference"></span>. Your completed visual review is preserved in the source workspace.</p></aside></div><section class="panel scroll"><h2>Compare the unchanged candidates</h2><table><thead><tr><th>Candidate</th><th>Vertex min</th><th>Vertex median</th><th>Vertex p90</th><th>Prior triangle gap</th><th>Collision gate</th></tr></thead><tbody id="rows"></tbody></table><p class="small muted">All distances use the unverified scene units. Vertex statistics are not area-weighted. The triangle gap can be smaller than every vertex distance, especially when faces intersect.</p></section><div class="controls" style="margin-top:20px"><button id="download">Download all distance witnesses</button></div><details><summary>Method and limitations</summary><pre id="limits"></pre></details><footer class="small muted">Offline inspection. No fitting, inference, mask change, geometry change or candidate acceptance occurs here.</footer><script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),R=D.report,$=id=>document.getElementById(id),C=$('scene'),ctx=C.getContext('2d'),label=s=>s.replaceAll('_',' ');let vertex=0,screenPoints=[];for(const r of R.candidates){const o=document.createElement('option');o.value=r.id;o.textContent=label(r.id);$('candidate').append(o);const tr=document.createElement('tr');for(const x of[label(r.id),r.summary.minimum.toPrecision(5),r.summary.median.toPrecision(5),r.summary.p90.toPrecision(5),r.prior_triangle_surface_gap.toPrecision(5),label(r.collision_gate)]){const td=document.createElement('td');td.textContent=x;tr.append(td)}$('rows').append(tr)}$('identity').textContent=R.case_id+' · '+R.object_triangles.toLocaleString()+' object triangles · exact saved meshes';$('rgb').src='data:image/png;base64,'+D.rgb;$('reference').textContent=label(R.reference_status);$('limits').textContent=R.method+'\n\n'+R.limitations.join('\n');
const current=()=>R.candidates.find(c=>c.id===$('candidate').value);function nearest(){const r=current();vertex=r.vertices.reduce((best,x)=>x.distance<r.vertices[best].distance?x.vertex_index:best,0)}function color(d,cap){const t=Math.min(1,d/cap);return 'rgb('+Math.round(255*(1-t)+51*t)+','+Math.round(188*(1-t)+186*t)+','+Math.round(100*(1-t)+213*t)+')'}
function draw(){const r=current(),h=D.hands[r.id],vs=h.vertices;let center=D.center,radius=D.radius;if($('focus').checked){center=[0,1,2].map(k=>(Math.min(...vs.map(p=>p[k]))+Math.max(...vs.map(p=>p[k])))/2);radius=Math.max(...vs.map(p=>Math.hypot(...p.map((x,i)=>x-center[i]))))*1.25}const yaw=+$('yaw').value*Math.PI/180,pitch=+$('pitch').value*Math.PI/180,scale=340*+$('zoom').value/radius;function project(p){const [x,y,z]=p.map((v,i)=>v-center[i]),xx=Math.cos(yaw)*x+Math.sin(yaw)*z,zz=-Math.sin(yaw)*x+Math.cos(yaw)*z;return[400+xx*scale,400-(Math.cos(pitch)*y-Math.sin(pitch)*zz)*scale]}ctx.clearRect(0,0,800,800);if($('object').checked){ctx.fillStyle='#7394ad';ctx.globalAlpha=.4;for(const p of D.object){const q=project(p);ctx.fillRect(q[0],q[1],2,2)}}ctx.globalAlpha=1;screenPoints=vs.map(project);ctx.strokeStyle='#46637b';ctx.lineWidth=.5;ctx.beginPath();for(const f of h.faces){ctx.moveTo(...screenPoints[f[0]]);ctx.lineTo(...screenPoints[f[1]]);ctx.lineTo(...screenPoints[f[2]]);ctx.closePath()}ctx.stroke();const threshold=+$('threshold').value/100,cap=threshold*R.object_bbox_diagonal;for(let i=0;i<vs.length;i++){const q=screenPoints[i];ctx.fillStyle=color(r.vertices[i].distance,cap);ctx.beginPath();ctx.arc(q[0],q[1],2.8,0,2*Math.PI);ctx.fill()}const w=r.vertices[vertex],p=screenPoints[vertex],q=project(w.point);ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();ctx.beginPath();ctx.arc(p[0],p[1],7,0,2*Math.PI);ctx.stroke();ctx.strokeRect(q[0]-4,q[1]-4,8,8);$('name').textContent=label(r.id);$('gate').textContent=label(r.collision_gate);$('thresholdValue').textContent=(threshold*100).toFixed(1)+'%';$('colorMax').textContent='≥ '+cap.toPrecision(4)+' scene units';const count=r.vertices.filter(v=>v.normalized_distance<=threshold).length;$('fraction').textContent=count+' / '+vs.length+' hand vertices within this display threshold ('+(100*count/vs.length).toFixed(1)+'%). This is not an acceptance test.';$('summary').textContent='Conditional scale '+r.conditional_scale.toFixed(6)+' · full object diagonal '+R.object_bbox_diagonal.toPrecision(5)+'.';$('witness').textContent='Hand vertex '+vertex+' → object triangle '+w.object_triangle+'\nDistance '+w.distance.toPrecision(8)+'\nObject-diagonal ratio '+w.normalized_distance.toPrecision(6)+'\nBarycentric '+w.barycentric.map(x=>x.toFixed(6)).join(', ')+'\nNearest point '+w.point.map(x=>x.toFixed(6)).join(', ')}
for(const id of['yaw','pitch','zoom','focus','object','threshold'])$(id).oninput=draw;$('candidate').onchange=()=>{nearest();draw()};$('reset').onclick=()=>{$('yaw').value=$('pitch').value=0;$('zoom').value=1;draw()};let drag=null;C.onpointerdown=e=>{drag=[e.clientX,e.clientY,+$('yaw').value,+$('pitch').value];C.setPointerCapture(e.pointerId)};C.onpointermove=e=>{if(!drag)return;if(Math.hypot(e.clientX-drag[0],e.clientY-drag[1])>3){$('yaw').value=Math.max(-180,Math.min(180,drag[2]+(e.clientX-drag[0])*.5));$('pitch').value=Math.max(-85,Math.min(85,drag[3]+(e.clientY-drag[1])*.5));draw()}};C.onpointerup=e=>{if(drag&&Math.hypot(e.clientX-drag[0],e.clientY-drag[1])<=3){const b=C.getBoundingClientRect(),p=[(e.clientX-b.left)*800/b.width,(e.clientY-b.top)*800/b.height];let best=100;for(let i=0;i<screenPoints.length;i++){const d=(p[0]-screenPoints[i][0])**2+(p[1]-screenPoints[i][1])**2;if(d<best){best=d;vertex=i}}draw()}drag=null};C.onpointercancel=()=>{drag=null};$('download').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_hand_object_distances_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};window.addEventListener('pageshow',()=>{nearest();draw()});nearest();draw();})();
</script></main></body></html>'''
