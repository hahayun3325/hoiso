"""Portable, immutable workspace connecting scene and proximity diagnostics.

All source bytes remain hash-bound. Only recomputed per-face lower/upper
endpoints may differ by a narrow, recorded floating-point tolerance; all other
fields and every saved-profile classification must agree exactly.
"""
import base64,json,math,tempfile
from pathlib import Path
PURPOSE='proximity_pipeline'
SCHEMA='tracehoi.ProximityPipeline.v1'
FILES={'index.html','coverage.html','distances.html','scene.html','reference_annotation.html','TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html','proximity.json','README.md','files.json'}
def require(ok,msg):
    if not ok:raise ValueError(msg)
def ordered_like(values,template):
    """Preserve template insertion order while substituting verified values."""
    if isinstance(template,dict):return {k:ordered_like(values[k],v) for k,v in template.items()}
    if isinstance(template,list):return [ordered_like(a,b) for a,b in zip(values,template)]
    return values
def compare_bounds(saved,recomputed):
    diagonal=recomputed['object_bbox_diagonal'];guard=recomputed['numerical_guard']
    require(math.isfinite(diagonal) and diagonal>0 and math.isfinite(guard) and guard>0,'proximity_numeric_policy')
    tolerance=min(32*math.ulp(max(1.,diagonal)),guard/1024)
    audit=dict(endpoint_tolerance=tolerance,different_endpoints=0,maximum_endpoint_difference=0.,endpoint_values_checked=0)
    def walk(a,b,path=()):
        require(type(a) is type(b),'proximity_type:'+str(path))
        if isinstance(b,dict):
            require(a.keys()==b.keys(),'proximity_keys:'+str(path))
            for key in b:walk(a[key],b[key],path+(key,))
        elif isinstance(b,list):
            require(len(a)==len(b),'proximity_length:'+str(path))
            for i,(u,v) in enumerate(zip(a,b)):walk(u,v,path+(i,))
        elif len(path)==5 and path[0]=='candidates' and type(path[1]) is int and path[2]=='faces' and type(path[3]) is int and path[4] in ('lower','upper'):
            require(type(a) is float and math.isfinite(a) and a>=0,'proximity_endpoint')
            delta=abs(a-b);require(delta<=tolerance,'proximity_endpoint_difference:'+str(path));audit['endpoint_values_checked']+=1
            if delta:
                audit['different_endpoints']+=1;audit['maximum_endpoint_difference']=max(audit['maximum_endpoint_difference'],delta)
        else:require(a==b,'proximity_exact_field:'+str(path))
    walk(saved,recomputed)
    checked=0
    for a,b in zip(saved['candidates'],recomputed['candidates']):
        for x,y in zip(a['faces'],b['faces']):
            require(x['lower']<=x['upper'],'proximity_endpoint_order')
            for profile in b['profiles']:
                t=profile['threshold'];state=lambda f:0 if f['upper']<=t else 1 if f['lower']>t else 2
                require(state(x)==state(y),'proximity_classification_changed');checked+=1
    audit['profile_classifications_checked']=checked
    return audit

def verify_coverage(workspace,wsha,distances,dsha,source,csha,case,*mods):
    reader=mods[0];pipeline=mods[8];coverage=mods[10]
    raw=pipeline.inventory(source,reader);require(set(raw)=={'coverage.json','index.html','README.md','files.json'},'proximity_coverage_inventory')
    require(reader.binding(raw['files.json'])['sha256']==csha,'proximity_coverage_receipt')
    receipt=reader.parse(raw['files.json']);require(set(receipt)=={'schema','files','placement_ready','source_workspace_binding','source_distance_binding'},'proximity_receipt_keys')
    require(receipt['schema']=='tracehoi.SurfaceCoverageFiles.v1' and receipt['placement_ready'] is False,'proximity_receipt_contract')
    require(receipt['files']=={n:reader.binding(b) for n,b in raw.items() if n!='files.json'},'proximity_coverage_hashes')
    recomputed,expected=coverage.build(workspace,wsha,distances,dsha,case,*mods[:10],purpose=coverage.PURPOSE)
    saved=reader.parse(raw['coverage.json']);require(reader.encode(saved)==raw['coverage.json'],'proximity_canonical_report')
    require(receipt['source_workspace_binding']==recomputed['source_workspace_binding'] and receipt['source_distance_binding']==recomputed['source_distance_binding'],'proximity_source_receipts')
    audit=compare_bounds(saved,recomputed)
    # Rebuild the entire saved viewer from verified saved numbers and exact
    # recomputed geometry. Do not accept arbitrary HTML merely because JSON fits.
    marker='<script id="data" type="application/json">';page=expected['index.html'].decode()
    require(page.count(marker)==1,'proximity_viewer_template')
    display=json.loads(page.split(marker,1)[1].split('</script>',1)[0]);display['report']=ordered_like(saved,display['report'])
    require(raw['index.html']==coverage.html(display) and raw['README.md']==expected['README.md'],'proximity_viewer_changed')
    require(pipeline.inventory(source,reader)==raw,'proximity_coverage_changed')
    return saved,audit

def build(workspace,wsha,distances,dsha,coverage_source,csha,case,*mods,purpose):
    require(purpose==PURPOSE,'proximity_pipeline_purpose_required')
    reader=mods[0];export=mods[5];pipeline=mods[8]
    originals=[pipeline.inventory(p,reader) for p in [workspace,distances,coverage_source]]
    with tempfile.TemporaryDirectory(prefix='tracehoi-proximity-') as t:
        roots=[Path(t).resolve()/n for n in ['workspace','distances','coverage']]
        for root,files in zip(roots,originals):export.publish(root,files,reader)
        coverage,audit=verify_coverage(roots[0],wsha,roots[1],dsha,roots[2],csha,case,*mods)
    wf,df,cf=originals;distance=reader.parse(df['distances.json']);parent=reader.parse(wf['pipeline.json']);candidates=[]
    require(parent['human_review_record_complete'] is True and parent['reference_status']=='awaiting_reference','proximity_parent_scope')
    for c in coverage['candidates']:
        d=next(x for x in distance['candidates'] if x['id']==c['id'])
        require(c['hand_binding']==d['hand_binding'] and c['collision_gate']==d['collision_gate'],'proximity_candidate_binding')
        candidates.append(dict(id=c['id'],hand_binding=c['hand_binding'],conditional_scale=c['conditional_scale'],collision_gate=c['collision_gate'],
            unsigned_surface_gap=c['prior_triangle_surface_gap'],vertex_distances=d['summary'],total_hand_area=c['total_hand_area'],profiles=c['profiles'],accepted=False))
    report=dict(schema=SCHEMA,purpose=PURPOSE,case_id=case,status='diagnostic_proximity_workspace_complete',candidates=candidates,
        source_workspace_binding=reader.binding(wf['workspace.json']),source_distance_binding=reader.binding(df['files.json']),source_coverage_binding=reader.binding(cf['files.json']),
        object_binding=coverage['object_binding'],object_bbox_diagonal=coverage['object_bbox_diagonal'],scene_frame=coverage['scene_frame'],units=coverage['units'],
        reference_status=coverage['reference_status'],human_review_record_complete=parent['human_review_record_complete'],independent_reference_complete=False,
        mask_accuracy_verified=False,geometric_accuracy_verified=False,physical_contact_verified=False,scale_identified=False,
        selected_candidate=None,accepted_scale=None,placement_ready=False,full_parent_acceptance=False,source_geometry_modified=False,model_calls=0,
        verification_policy=dict(exact_source_file_hashes=True,exact_non_endpoint_fields=True,exact_saved_profile_classifications=True,
            allowed_numeric_fields='candidates/*/faces/*/{lower,upper}',endpoint_tolerance=audit['endpoint_tolerance'],
            tolerance_formula='min(32 * ulp(max(1, object_bbox_diagonal)), numerical_guard / 1024)',
            endpoint_values_checked=audit['endpoint_values_checked'],profile_classifications_checked=audit['profile_classifications_checked']),
        limitations=['Unsigned proximity and coverage do not establish physical contact or signed penetration depth.',
            'Collision gates remain independent. The minimum-scale branch is still blocked for transverse crossings.',
            'The completed visual observation review is not an independent mask reference. Scale and placement remain unresolved.',
            'Small platform differences are allowed only in distance-envelope endpoints; source hashes and all other values remain exact.'])
    files={'proximity.json':reader.encode(report),'index.html':html(report,wf['scene/source/assets/original_rgb.png']),
        'coverage.html':cf['index.html'],'distances.html':df['index.html'],'scene.html':wf['scene/index.html'],
        'reference_annotation.html':wf['validation/reference_annotation.html'],
        'TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html':wf['scene/TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html'],
        'README.md':b'TraceHOI portable proximity workspace\n\nExtract the complete ZIP into one folder and open index.html offline. Keep all companion HTML files together. The dashboard connects the unchanged scene, vertex distances and area-coverage intervals. Numerical verification is narrowly tolerant only for recomputed per-face lower/upper bounds; source bytes remain exactly hash-bound. No model, geometry edit, mask edit, scale, physical contact or placement acceptance. Preserve original human/reference records and all source packets to verify this workspace.\n'}
    files['files.json']=reader.encode(dict(schema='tracehoi.ProximityPipelineFiles.v1',files={n:reader.binding(b) for n,b in files.items()},source_workspace_binding=report['source_workspace_binding'],source_distance_binding=report['source_distance_binding'],source_coverage_binding=report['source_coverage_binding'],placement_ready=False))
    require([pipeline.inventory(p,reader) for p in [workspace,distances,coverage_source]]==originals,'proximity_inputs_changed')
    return report,files,audit

def verify(out,receipt_sha,workspace,wsha,distances,dsha,coverage_source,csha,case,*mods,purpose):
    require(purpose==PURPOSE,'proximity_pipeline_purpose_required');reader=mods[0];pipeline=mods[8];actual=pipeline.inventory(out,reader)
    require(set(actual)==FILES,'proximity_inventory');require(reader.binding(actual['files.json'])['sha256']==receipt_sha,'proximity_receipt')
    receipt=reader.parse(actual['files.json']);require(receipt['files']=={n:reader.binding(b) for n,b in actual.items() if n!='files.json'},'proximity_output_hashes')
    report,expected,audit=build(workspace,wsha,distances,dsha,coverage_source,csha,case,*mods,purpose=purpose)
    require(actual==expected,'proximity_workspace_changed')
    return dict(verified=True,receipt_binding=reader.binding(actual['files.json']),source_workspace_binding=report['source_workspace_binding'],source_distance_binding=report['source_distance_binding'],source_coverage_binding=report['source_coverage_binding'],numerical_audit=audit,placement_ready=False,selected_candidate=None)

def html(report,rgb):
    payload=json.dumps(report,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',payload).replace('__RGB__',base64.b64encode(rgb).decode()).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Proximity workspace</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c1725;color:#eef5fc;font:15px/1.55 system-ui}main{max-width:1220px;margin:auto;padding:32px}.eyebrow{color:#85ddce;font-size:12px;letter-spacing:2px}h1{font-size:38px;line-height:1.2;margin:12px 0}h2{font-size:21px}p{color:#bdccdb}.top{display:grid;grid-template-columns:2fr 1fr;gap:26px}.panel{background:#14273b;border:1px solid #36546d;border-radius:12px;padding:22px;margin-top:22px}.badge{display:inline-block;background:#263c4d;color:#95e2d2;border-radius:20px;padding:5px 12px;font-size:12px;margin:3px}.warn{border-left:3px solid #e6b473;background:#302b24;padding:13px 18px;margin-top:20px}.links{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:22px}a{color:#a9e4ff;text-decoration:none}a.card{border:1px solid #3e617a;border-radius:10px;background:#1a3047;padding:18px;display:block}a.card strong{display:block;font-size:18px}a.card span{font-size:12px;color:#b6c9da}select,button{color:inherit;background:#223b53;border:1px solid #7496ac;border-radius:6px;padding:8px;font:inherit}label{display:inline-block;margin:0 20px 14px 0}svg{display:block;width:100%;height:auto}.small{font-size:12px}.large{font-size:30px;color:#98e1d4}.grid{display:grid;grid-template-columns:1.7fr 1fr;gap:22px}.photo{width:100%;max-height:245px;object-fit:contain;border-radius:10px;background:#07101b}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;border-bottom:1px solid #36546d;text-align:left}.scroll{overflow:auto}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}footer{color:#9db2c8;margin:24px 0;font-size:12px}@media(max-width:780px){.top,.grid{grid-template-columns:1fr}.links{grid-template-columns:1fr}main{padding:18px}h1{font-size:30px}}:focus-visible{outline:2px solid #8ee0ce;outline-offset:3px}
</style></head><body><main><div class="top"><div><div class="eyebrow">TRACEHOI / PORTABLE PROXIMITY WORKSPACE</div><h1>One scene. Four hypotheses.<br>Evidence kept separate.</h1><p id="case"></p><span class="badge">Human observation reviewed</span><span class="badge">Source hashes verified</span><div class="warn">Independent mask reference pending. No candidate, physical contact, metric scale or pipeline placement is accepted.</div></div><img class="photo" src="data:image/png;base64,__RGB__" alt="Original RGB crop used for this diagnostic case"></div>
<nav class="links" aria-label="Linked diagnostic stages"><a class="card" href="scene.html"><strong>1 · Scene geometry ↗</strong><span>Orbit all four unchanged hand–object candidates.</span></a><a class="card" href="distances.html"><strong>2 · Vertex witnesses ↗</strong><span>Inspect nearest object triangles and unsigned distances.</span></a><a class="card" href="coverage.html"><strong>3 · Surface coverage ↗</strong><span>Inspect whole-face bounds and unresolved surface area.</span></a></nav>
<section class="panel"><h2>Compare proximity without choosing a winner</h2><label>Display threshold <select id="threshold"></select></label><label>Inspect candidate <select id="candidate"></select></label><div class="grid"><div><svg id="chart" viewBox="0 0 670 310" role="img" aria-label="Area coverage intervals for all four diagnostic candidates"></svg><p class="small">Solid teal: area certainly within the numerical bound. Gold extension: unresolved area that may be within. Common 0–100% area axis; thresholds are percentages of object diagonal, not acceptance criteria.</p></div><aside><div id="name"></div><div class="large" id="interval"></div><p id="detail"></p><div class="warn" id="collision"></div><p id="distance" class="small"></p></aside></div><div class="scroll"><table><thead><tr><th>Candidate</th><th>Area interval</th><th>Unresolved area</th><th>Unsigned surface gap</th><th>Collision gate</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section class="panel"><h2>Verification across machines</h2><p>Original files and embedded viewers remain bound to exact checksums. Recomputed lower and upper distance bounds may differ only within the displayed numerical tolerance. All other fields and saved-profile classifications must match exactly.</p><pre id="policy"></pre><p class="small">This tolerance handles arithmetic differences between platforms. It grants no geometric or physical acceptance.</p><button id="download">Download workspace summary</button> <a href="reference_annotation.html">Open independent-reference annotator ↗</a><details><summary>Source receipts and limitations</summary><pre id="sources"></pre></details></section><footer>Keep the full extracted workspace together so the linked viewers remain available. Offline CPU diagnostics; no inference, optimization or source edits.</footer><script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const R=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),label=s=>s.replaceAll('_',' '),pct=v=>(100*v).toFixed(2)+'%',esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');$('case').textContent=R.case_id+' · '+R.candidates.length+' unchanged candidates · unverified scene units';for(let i=0;i<R.candidates[0].profiles.length;i++){const p=R.candidates[0].profiles[i],o=document.createElement('option');o.value=i;o.textContent=(100*p.threshold_object_diagonal_ratio).toFixed(1)+'% object diagonal';$('threshold').append(o)}$('threshold').value=4;for(const c of R.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=label(c.id);$('candidate').append(o)}$('policy').textContent='Endpoint tolerance: '+R.verification_policy.endpoint_tolerance.toPrecision(6)+' scene units\nEndpoint values checked: '+R.verification_policy.endpoint_values_checked.toLocaleString()+'\nSaved-profile classifications checked: '+R.verification_policy.profile_classifications_checked.toLocaleString();$('sources').textContent=JSON.stringify({workspace:R.source_workspace_binding,distances:R.source_distance_binding,coverage:R.source_coverage_binding,limitations:R.limitations},null,2);
function draw(){const ti=+$('threshold').value,id=$('candidate').value,c=R.candidates.find(x=>x.id===id),p=c.profiles[ti];$('name').textContent=label(c.id);$('interval').textContent=pct(p.area_fraction_lower)+' – '+pct(p.area_fraction_upper);$('detail').textContent=pct(p.unresolved_area_fraction)+' unresolved hand area at '+p.threshold.toPrecision(5)+' scene units.';$('collision').textContent=label(c.collision_gate);$('collision').style.borderLeftColor=c.collision_gate.startsWith('blocked')?'#f19182':'#80bfba';$('distance').textContent='Whole-surface gap: '+c.unsigned_surface_gap.toPrecision(6)+'\nMedian vertex distance: '+c.vertex_distances.median.toPrecision(6)+'. Neither is physical contact.';let g='<rect x="0" y="0" width="670" height="310" rx="10" fill="#0c1b2b"/>';for(let j=0;j<=4;j++){let x=180+j*110;g+='<line x1="'+x+'" y1="20" x2="'+x+'" y2="262" stroke="#365167"/><text x="'+x+'" y="292" text-anchor="middle" fill="#b5c6d7" font-size="12">'+j*25+'%</text>'}R.candidates.forEach((x,i)=>{let y=36+i*60,q=x.profiles[ti],lo=q.area_fraction_lower*440,hi=q.area_fraction_upper*440;g+='<text x="12" y="'+(y+12)+'" fill="'+(x.id===id?'#fff':'#aec1d2')+'" font-size="12">'+esc(label(x.id))+'</text><rect x="180" y="'+y+'" width="440" height="18" fill="#263c50" rx="3"/><rect x="180" y="'+y+'" width="'+hi+'" height="18" fill="#dfbd70"/><rect x="180" y="'+y+'" width="'+lo+'" height="18" fill="#7cd4bf"/><text x="180" y="'+(y+36)+'" fill="#d0dfec" font-size="11">'+pct(q.area_fraction_lower)+' – '+pct(q.area_fraction_upper)+'</text>'});$('chart').innerHTML=g;$('rows').replaceChildren();for(const x of R.candidates){const q=x.profiles[ti],tr=document.createElement('tr');if(x.id===id)tr.style.background='#233e53';for(const v of[label(x.id),pct(q.area_fraction_lower)+' – '+pct(q.area_fraction_upper),pct(q.unresolved_area_fraction),x.unsigned_surface_gap.toPrecision(6),label(x.collision_gate)]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('rows').append(tr)}}$('threshold').onchange=$('candidate').onchange=draw;$('download').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_proximity_workspace_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};window.addEventListener('pageshow',draw);draw();})();
</script></main></body></html>'''
