"""Compare authenticated diagnostic candidates; no winner or placement acceptance.

Saved fit metrics measure agreement with model observations, not ground truth.
Every candidate is retained, including branches blocked by recorded crossings.
"""
import base64,json,math
from decimal import Decimal,ROUND_HALF_EVEN
from pathlib import Path

PURPOSE='candidate_comparison'
IDS=['primary','minimum_scale','maximum_scale','minimum_scale_refined']
METRICS={'joint_median_px':('min',6),'visible_mask_iou':('max',9),'surface_gap':('min',9)}
PROFILES={'image_agreement':['joint_median_px','visible_mask_iou'],
          'image_and_proximity_hypothesis':['joint_median_px','visible_mask_iou','surface_gap']}

def require(ok,reason):
    if not ok:raise ValueError(reason)

def number(v,lo=0,hi=None):
    require(type(v) in (int,float) and math.isfinite(v) and v>=lo and (hi is None or v<=hi),'invalid_metric')
    return v

def key(v,metric):
    direction,places=METRICS[metric];number(v,0,1 if metric=='visible_mask_iou' else None)
    k=int((Decimal(str(v))*10**places).to_integral_value(rounding=ROUND_HALF_EVEN))
    return -k if direction=='max' else k

def compare(rows,profile):
    """Diagnostic Pareto relation at declared comparison precision; not selection."""
    require(profile in PROFILES,'unknown_comparison_profile')
    require(type(rows) is list and 0<len(rows)<=32,'candidate_count')
    ids=[r['id'] for r in rows];require(all(type(i) is str and i for i in ids) and len(set(ids))==len(ids),'unique_candidate_ids')
    for r in rows:
        require(r['collision_gate'] in ['clear_surface_separation_only','blocked_transverse_crossing'],'unknown_collision_gate')
        for m in METRICS:number(r[m],0,1 if m=='visible_mask_iou' else None)
    eligible=[r for r in rows if r['collision_gate']=='clear_surface_separation_only'];keys={r['id']:[key(r[m],m) for m in PROFILES[profile]] for r in eligible}
    relations=[]
    for a in eligible:
        for b in eligible:
            if a['id']==b['id']:continue
            ka,kb=keys[a['id']],keys[b['id']]
            if all(x<=y for x,y in zip(ka,kb)) and any(x<y for x,y in zip(ka,kb)):
                relations.append(dict(better_on_profile=a['id'],dominated_on_profile=b['id']))
    dominated={r['dominated_on_profile'] for r in relations}
    return dict(profile=profile,objectives=PROFILES[profile],comparison_precision={m:METRICS[m][1] for m in PROFILES[profile]},
        eligible_ids=[r['id'] for r in eligible],crossing_blocked_ids=[r['id'] for r in rows if r not in eligible],
        nondominated_ids=[r['id'] for r in eligible if r['id'] not in dominated],relations=relations,
        selected_candidate=None,placement_ready=False,candidates_removed=False)

def extract(package,audit,assembly,refinement):
    """Internal extraction from already authenticated evidence, with join checks."""
    require([r['id'] for r in package['candidates']]==IDS,'all_four_candidates_required')
    require([r['id'] for r in audit['candidates']]==IDS,'audit_candidate_identity')
    require([r['id'] for r in assembly['candidates']]==IDS[:3],'assembly_candidate_identity')
    require(refinement['branch']['id']==IDS[3] and refinement['branch']['source_id']==IDS[1],'refinement_identity')
    require(refinement['artifact_bindings']['refinement/hand_candidate.ply']==package['candidates'][3]['hand_binding'],'refined_mesh_binding')
    rows=[]
    for c,a in zip(package['candidates'],audit['candidates']):
        require(a['collision_gate']==c['collision_gate'],'audit_collision_disagreement')
        mask=a['full_visible_hand_mask'];intersection=mask['intersection'];total=mask['mask_pixels']+mask['predicted_pixels']-intersection
        require(all(type(mask[k]) is int and mask[k]>=0 for k in ['intersection','mask_pixels','predicted_pixels']) and intersection<=min(mask['mask_pixels'],mask['predicted_pixels']) and total>0,'invalid_mask_counts')
        require(abs(mask['iou']-intersection/total)<1e-12 and mask['accuracy_verified'] is False,'mask_iou_consistency')
        if c['id']==IDS[3]:metrics=refinement['hand_reprojection'];origin='source/evidence/refinement.json';scale=refinement['refined_scale']
        else:
            evidence=next(r for r in assembly['candidates'] if r['id']==c['id']);require(evidence['hand_mesh_binding']==c['hand_binding'],'assembly_mesh_binding')
            metrics=evidence['hand_reprojection'];origin='source/evidence/assembly.json';scale=evidence['source_hypothesis']['conditional_scale']
        require(scale==c['conditional_scale'],'scale_binding');number(scale,1e-12)
        row=dict(id=c['id'],conditional_scale=scale,collision_gate=c['collision_gate'],joint_median_px=number(metrics['median_px']),
            joint_rmse_px=number(metrics['rmse_px']),visible_mask_iou=number(mask['iou'],0,1),surface_gap=number(c['unsigned_surface_gap']),
            mask_intersection=intersection,mask_pixels=mask['mask_pixels'],visible_hand_pixels=mask['predicted_pixels'],
            hand_binding=c['hand_binding'],evidence=dict(joint_metrics=origin,mask_metrics='source_review/review.json#/audit/candidates/'+str(IDS.index(c['id']))+'/full_visible_hand_mask',surface_metrics='package.json#/candidates/'+str(IDS.index(c['id']))),
            accepted=False,placement_ready=False)
        rows.append(row)
    return rows

def build(package_dir,digest,validation_dir,validation_sha,case,reader,renderer,viewer,records,ready,export,validation,*,purpose):
    require(purpose==PURPOSE,'candidate_comparison_purpose_required');root=Path(package_dir)
    args=(root,digest,case,reader,renderer,viewer,records,ready,export)
    vr=validation.verify(validation_dir,validation_sha,*args,purpose='mask_validation')
    package=reader.parse(reader.regular(root/'package.json',1024**2));assessment=reader.parse(reader.regular(Path(validation_dir)/'assessment.json',1024**2))
    read_json=lambda n:reader.parse(reader.regular(root/n,1024**2))
    audit=read_json('source_review/review.json')['audit'];assembly=read_json('source/evidence/assembly.json');refinement=read_json('source/evidence/refinement.json')
    require(package['case_id']==audit['case_id']==assembly['case_id']==refinement['case_id']==case,'evidence_case')
    require(assessment['source_package_binding']==reader.binding(reader.regular(root/'package.json',1024**2)),'validation_source_binding')
    rows=extract(package,audit,assembly,refinement)
    report=dict(schema='tracehoi.CandidateComparison.v1',case_id=case,source_package_binding=assessment['source_package_binding'],
        validation_receipt_binding=vr['receipt_binding'],reference_status=assessment['status'],reference_metrics=assessment['metrics'],
        human_review_record_complete=assessment['human_review_record_complete'],reference_provenance_verified=False,
        candidates=rows,profiles={p:compare(rows,p) for p in PROFILES},
        policy=dict(collision_filter='Recorded transverse crossing excludes a branch from comparison frontiers; retain it in the evidence table.',
            quantization='Round half to even at 6 decimal places for pixels and 9 for IoU and scene gap, only for pairwise comparisons. This precision is not a confidence interval.',
            image_agreement='Minimize median reprojection residual and maximize full visible-silhouette IoU against the working mask.',
            image_and_proximity_hypothesis='Additionally minimize unsigned surface gap as an explicit proximity hypothesis. No contact target is established.',
            depth_comparison='Omitted: candidate depth fits use different support subsets and must not be presented as a common validation score.'),
        limitations=['These are saved fitting diagnostics on one case, not held-out accuracy measurements.',
            'Working-mask silhouette agreement is distinct from separate-reference mask validation.',
            'A nondominated candidate is only a tradeoff under the stated objectives, not a recommended placement.',
            'Recorded surface separation does not classify solid containment, penetration depth or physical contact.',
            'All four candidates and exact mesh bytes remain available. No metric scale is identified.'],
        selected_candidate=None,accepted_scale=None,mask_accuracy_verified=False,scale_identified=False,geometric_accuracy_verified=False,
        physical_contact_verified=False,placement_ready=False,full_parent_acceptance=False,candidates_removed=False,
        source_geometry_modified=False,mask_modified=False,new_optimization_executed=False,model_calls=0)
    files={'comparison.json':reader.encode(report),'index.html':html(report,reader.regular(root/'source/assets/original_rgb.png',1024**2))}
    receipt=dict(schema='tracehoi.CandidateComparisonFiles.v1',case_id=case,files={n:reader.binding(b) for n,b in files.items()},placement_ready=False)
    files['files.json']=reader.encode(receipt)
    require(validation.verify(validation_dir,validation_sha,*args,purpose='mask_validation')==vr,'comparison_inputs_changed')
    return report,files

def verify(out,receipt_sha,*args,purpose):
    require(purpose==PURPOSE,'candidate_comparison_purpose_required');reader=args[5];root=Path(out)
    actual={}
    for p in root.iterdir():
        require(p.is_file() and not p.is_symlink() and len(actual)<3,'comparison_inventory');actual[p.name]=reader.regular(p,1024**2)
    require(set(actual)=={'comparison.json','index.html','files.json'},'comparison_inventory')
    require(reader.binding(actual['files.json'])['sha256']==receipt_sha,'comparison_receipt_changed')
    report,expected=build(*args,purpose=purpose);require(actual==expected,'comparison_semantic_mismatch')
    return dict(verified=True,case_id=report['case_id'],profiles=report['profiles'],receipt_binding=reader.binding(actual['files.json']),
        reference_status=report['reference_status'],placement_ready=False,selected_candidate=None)

def html(report,rgb):
    data=json.dumps(dict(report=report,rgb=base64.b64encode(rgb).decode()),separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',data).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Candidate tradeoffs</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#0c1420;color:#e8edf5;margin:0;font:15px/1.6 system-ui}main{max-width:1260px;margin:auto;padding:32px}h1{font-size:38px;margin:4px 0 12px;line-height:1.15}h2{font-size:19px}.eyebrow{color:#81dccc;font-size:12px;letter-spacing:2px}.muted{color:#acbbcd}.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:18px}.panel{border:1px solid #344259;border-radius:10px;background:#141f2d;padding:20px}.notice{border-left:3px solid #e5bb6c;background:#292518;padding:14px 18px;margin:20px 0}.row{display:flex;gap:14px;align-items:center;flex-wrap:wrap}select,button{background:#1c2b3d;color:inherit;border:1px solid #57718e;border-radius:5px;padding:9px;font:inherit;cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid #81dccc;outline-offset:3px}svg{width:100%;height:auto;display:block;overflow:visible}svg text{fill:#b4c5d8;font:13px system-ui}.cardValue{font-size:22px;color:#81dccc}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:11px;text-align:left;border-bottom:1px solid #344259}th{color:#aebed1}td:first-child{white-space:nowrap}.scroll{overflow:auto}img{width:100%;border-radius:6px;background:white}.small{font-size:12px}a{color:#a3d7ff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.pill{padding:3px 8px;border:1px solid #526681;border-radius:5px;font-size:12px}footer{margin:24px 0;color:#aebed1}@media(max-width:800px){main{padding:18px}.grid{grid-template-columns:1fr}h1{font-size:29px}}
</style></head><body><main><div class="eyebrow">TRACEHOI / EVIDENCE COMPARISON</div><h1>Four candidates. Different tradeoffs.</h1><p class="muted" id="identity"></p><div class="notice"><strong>No placement is selected.</strong> The comparison preserves every candidate. Your visual review is recorded; the separate reference annotation remains a distinct validation task.</div>
<div class="grid"><section class="panel"><div class="row"><label>Objectives <select id="profile"><option value="image_agreement">Image agreement</option><option value="image_and_proximity_hypothesis">Image + proximity hypothesis</option></select></label><label>Inspect <select id="candidate"></select></label></div><p id="policy" class="muted"></p><svg id="plot" viewBox="0 0 720 390" role="img" aria-label="Saved reprojection residual versus working-mask overlap"></svg><p class="small muted">Left is lower reprojection residual; up is higher working-mask overlap. Circles show recorded surface separation; × marks a recorded crossing. A ring marks the current profile’s nondominated set. The proximity profile also uses the surface gap shown in the table.</p><div class="row"><span class="pill">Diagnostic frontier</span><span id="frontier"></span></div><p class="small muted">“Nondominated” means another eligible candidate is not at least as good on all stated objectives and better on one at the declared comparison precision. It does not mean correct or accepted.</p></section>
<aside class="panel"><h2 id="name"></h2><div id="gate" class="cardValue"></div><p id="detail"></p><img id="rgb" alt="Original RGB crop showing the selected lower right hand supporting the object"><p class="small muted">Original image for context. This comparison performs no new fitting or rendering.</p></aside></div>
<h2>Keep the complete evidence table</h2><div class="scroll panel"><table><thead><tr><th>Candidate</th><th>Conditional scale</th><th>Median / RMSE (px)</th><th>Visible-mask IoU*</th><th>Unsigned gap†</th><th>Comparison status</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="small muted">* Against the provisional hand-only working mask; independent mask accuracy is not measured here. † Scene units follow unverified MoGe scale. A smaller gap is only a proximity hypothesis, never contact certification.</p>
<div class="grid"><section class="panel"><h2>Separate mask validation</h2><p id="reference"></p><p>Your completed visual observation is preserved. You can continue annotation separately when a quantitative mask score is needed.</p><a href="TRACEHOI_REFERENCE_ANNOTATOR_F8d5Vm2F.html">Open the existing RGB-only reference workspace ↗</a></section><section class="panel"><h2>What would change the decision?</h2><p>Resolve visible-hand boundaries with a separate reference; assess depth and scale with independent evidence; test contact and 3D accuracy. A frontier alone cannot identify scene scale.</p><p>Depth residuals are omitted from cross-candidate ranking because their support subsets differ. All branches, including the crossing branch, remain available for later analysis.</p></section></div>
<details><summary>Exact metrics, sources and comparison policy</summary><pre id="json"></pre></details><div class="row"><button id="download">Download comparison JSON</button><a href="TRACEHOI_REVIEWED_SCENE_E7c4Ul9E.html">Open the saved orbit viewer ↗</a></div><footer>Offline display only. Changing objectives or the inspected candidate never edits meshes, masks or pipeline placement.</footer>
<script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),R=D.report,$=id=>document.getElementById(id),label=s=>s.replaceAll('_',' '),colors=['#81dccc','#ff9494','#b6a0ff','#f0bf72'];$('identity').textContent=R.case_id+' · saved source evidence · all four candidates retained';$('rgb').src='data:image/png;base64,'+D.rgb;$('json').textContent=JSON.stringify(R,null,2);$('reference').textContent=R.reference_status==='awaiting_reference'?'Awaiting a separately drawn reference. No quantitative mask-validation score is available.':'A separate reference has been scored; inspect its coverage and self-reported provenance in the validation packet. No accuracy threshold is accepted.';
for(const c of R.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=label(c.id);$('candidate').append(o)}
const ns='http://www.w3.org/2000/svg';function el(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n}function draw(){const p=R.profiles[$('profile').value],selected=$('candidate').value;$('policy').textContent=R.policy[$('profile').value];$('frontier').textContent=p.nondominated_ids.map(label).join(' · ');$('rows').replaceChildren();for(const c of R.candidates){const blocked=c.collision_gate==='blocked_transverse_crossing',status=blocked?'Crossing: excluded from frontier':p.nondominated_ids.includes(c.id)?'Nondominated under this profile':'Dominated under this profile',tr=document.createElement('tr');tr.style.background=c.id===selected?'#213044':'';for(const v of[label(c.id),c.conditional_scale.toFixed(6),c.joint_median_px.toFixed(3)+' / '+c.joint_rmse_px.toFixed(3),c.visible_mask_iou.toFixed(4),c.surface_gap.toPrecision(5),status]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('rows').append(tr)}
const c=R.candidates.find(c=>c.id===selected);$('name').textContent=label(c.id);$('gate').textContent=c.collision_gate==='blocked_transverse_crossing'?'Recorded crossing':'Surface separation recorded';$('detail').textContent='Conditional scale '+c.conditional_scale.toFixed(6)+'. Unsigned gap '+c.surface_gap.toPrecision(6)+'. Geometry and physical contact remain unverified.';
const S=$('plot');S.replaceChildren();const xmin=Math.min(...R.candidates.map(c=>c.joint_median_px))-.15,xmax=Math.max(...R.candidates.map(c=>c.joint_median_px))+.15,ymin=Math.min(...R.candidates.map(c=>c.visible_mask_iou))-.015,ymax=Math.max(...R.candidates.map(c=>c.visible_mask_iou))+.015,X=v=>75+(v-xmin)/(xmax-xmin)*590,Y=v=>320-(v-ymin)/(ymax-ymin)*270;
for(let i=0;i<=4;i++){let x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;S.append(el('line',{x1:X(x),y1:50,x2:X(x),y2:320,stroke:'#293b50'}),el('text',{x:X(x),y:344,'text-anchor':'middle'},x.toFixed(2)),el('line',{x1:75,y1:Y(y),x2:665,y2:Y(y),stroke:'#293b50'}),el('text',{x:64,y:Y(y)+4,'text-anchor':'end'},y.toFixed(3)))}S.append(el('text',{x:370,y:376,'text-anchor':'middle'},'Median reprojection residual (px) →'),el('text',{x:75,y:25},'Working-mask visible silhouette IoU ↑'));
R.candidates.forEach((c,i)=>{const x=X(c.joint_median_px),y=Y(c.visible_mask_iou),g=el('g',{});g.append(el('title',{},label(c.id)+': '+c.joint_median_px+' px; IoU '+c.visible_mask_iou));if(p.nondominated_ids.includes(c.id))g.append(el('circle',{cx:x,cy:y,r:15,fill:'none',stroke:colors[i],'stroke-width':2}));if(c.collision_gate==='blocked_transverse_crossing')g.append(el('path',{d:`M${x-8} ${y-8}l16 16m0 -16l-16 16`,stroke:colors[i],'stroke-width':3}));else g.append(el('circle',{cx:x,cy:y,r:7,fill:colors[i]}));if(c.id===selected)g.append(el('circle',{cx:x,cy:y,r:20,fill:'none',stroke:'#fff','stroke-dasharray':'3 3'}));const dy=i===1?28:i===3?-20:-18;g.append(el('text',{x:x-8,y:y+dy,'text-anchor':i===0?'start':'end',style:'fill:'+colors[i]},label(c.id)));S.append(g)});}
$('profile').onchange=$('candidate').onchange=draw;$('download').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_candidate_comparison_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};draw();})();
</script></main></body></html>'''
