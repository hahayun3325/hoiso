"""Explicit continuation contract for authenticated diagnostic scenes.

Readiness describes evidence and stage prerequisites, never scientific accuracy.
No stage is executed here. Version 1 cannot authorize production placement.
"""
import json

STAGES=('diagnostic_export','mask_revision_planning','placement')

def evaluate(manifest_path,digest,case,review_dir,review_files_sha,reader,renderer,viewer,records,record_raw=None):
    """Return immutable-evidence readiness; reject any supplied invalid record."""
    source,_=records.build(manifest_path,digest,case,review_dir,review_files_sha,reader,renderer,viewer)
    m,data=reader.inspect_bundle(manifest_path,digest,case)
    return assess(m,source['context'],records,record_raw)

def assess(m,context,records,record_raw=None):
    """Internal assessment of a manifest already authenticated by evaluate()."""
    req=records.require
    req(m['schema']=='tracehoi.DiagnosticSceneBundle.v1' and m['case_id']==context['case_id'],'readiness_identity')
    req(m['placement_ready'] is m['full_parent_acceptance'] is m['scale_identified'] is m['physical_contact_verified'] is False and m['selected_candidate'] is m['accepted_scale'] is None,'readiness_scope')
    req(m['mask_review_required'] is True,'mask_review_flag')
    req([c['id'] for c in m['candidates']]==records.IDS,'readiness_candidates')
    rows=[]
    for c in m['candidates']:
        req(c['accepted'] is c['pipeline_admissible'] is False,'readiness_candidate_admission')
        req(c['collision_gate'] in ['blocked_transverse_crossing','clear_surface_separation_only'],'readiness_collision_gate')
        required=['selected_hand_mask_requires_review','scene_scale_unidentified','geometric_accuracy_unverified','physical_contact_unverified']
        crossing=c['collision_gate']=='blocked_transverse_crossing'
        req(c['blockers']==required+(['transverse_mesh_crossing'] if crossing else []),'readiness_blockers')
        rows.append(dict(id=c['id'],diagnostic_available=True,placement_available=False,conditional_scale=c['conditional_scale'],
            unsigned_surface_gap=c['unsigned_surface_gap'],collision_gate=c['collision_gate'],blockers=list(c['blockers'])))
    if record_raw is None:
        receipt=None;state='missing';decision='pending';findings=[];record_binding=None
    else:
        r=records.parse(record_raw);receipt=records.validate(r,context)
        state='reviewed' if receipt['human_review_record_complete'] else 'draft'
        decision=r['decision'];findings=r['findings'];record_binding=records.binding(record_raw)
    revision_ready=state=='reviewed' and decision=='needs_revision'
    next_action=('plan_mask_revision' if revision_ready else 'review_reported_uncertainty' if state=='reviewed' and decision=='uncertain'
        else 'design_independent_mask_validation' if state=='reviewed' else 'complete_mask_review')
    review=dict(state=state,decision=decision,input_binding=record_binding,validation=receipt,
        finding_count=len(findings),record_complete=state=='reviewed',authorship_verified=False)
    return dict(schema='tracehoi.SceneReadiness.v1',case_id=m['case_id'],context=context,review=review,
        facts=[dict(id='saved_scene',status='available',evidence='Authenticated saved meshes, camera, images and masks'),
            dict(id='human_mask_record',status=state,evidence='Self-reported visual observations; not an accuracy certificate'),
            dict(id='mask_accuracy',status='unverified',evidence='No independent accuracy evidence supplied'),
            dict(id='scene_scale',status='unidentified',evidence='MoGe scale and hand scale are conditional'),
            dict(id='geometric_accuracy',status='unverified',evidence='Image fitting does not establish 3D accuracy'),
            dict(id='physical_contact',status='unverified',evidence='Unsigned surface gap is not a contact certificate')],
        stages=[dict(id='diagnostic_export',available=True,blockers=[],effect='Returns verified diagnostic mesh bytes only'),
            dict(id='mask_revision_planning',available=revision_ready,blockers=[] if revision_ready else ['completed_review_requesting_revision_required'],effect='Returns region findings for planning; no pixel edits'),
            dict(id='placement',available=False,blockers=['selected_hand_mask_requires_review','scene_scale_unidentified','geometric_accuracy_unverified','physical_contact_unverified'],effect='Always refused by this diagnostic contract')],
        next_action=next_action,candidates=rows,mask_review_required=True,mask_accuracy_verified=False,
        scale_identified=False,physical_contact_verified=False,geometric_accuracy_verified=False,placement_ready=False,
        full_parent_acceptance=False,selected_candidate=None,accepted_scale=None,source_geometry_modified=False,mask_modified=False,
        models_executed=0,stages_executed=0)

def prepare_stage(manifest_path,digest,case,review_dir,review_files_sha,reader,renderer,viewer,records,stage,candidate=None,record_raw=None):
    """Prepare immutable diagnostic data or a revision plan; never execute work."""
    reader.require(stage in STAGES,'unknown_stage')
    r=evaluate(manifest_path,digest,case,review_dir,review_files_sha,reader,renderer,viewer,records,record_raw)
    gate=next(s for s in r['stages'] if s['id']==stage)
    reader.require(gate['available'],'stage_blocked:'+stage+':'+','.join(gate['blockers']))
    if stage=='diagnostic_export':
        reader.require(candidate in records.IDS,'explicit_candidate_required')
        loaded=reader.load_candidate(manifest_path,expected_sha256=digest,expected_case_id=case,candidate_id=candidate,purpose='diagnostic')
        return dict(schema='tracehoi.PreparedDiagnosticScene.v1',readiness=r,scene=loaded)
    reader.require(candidate is None,'revision_has_no_selected_candidate')
    parsed=records.parse(record_raw)
    # Exact saved pixel regions are handed to a future planner; no mask is edited.
    return dict(schema='tracehoi.MaskRevisionPlanInput.v1',case_id=case,context=r['context'],review_input_binding=r['review']['input_binding'],
        notes=parsed['notes'],findings=parsed['findings'],planning_only=True,mask_modified=False,placement_ready=False,stages_executed=0)

def html(report):
    payload=json.dumps(report,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',payload).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Pipeline readiness</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#10141c;color:#edf1f7;font:16px/1.55 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:30px}h1{font-size:34px;margin:8px 0}h2{font-size:20px}p{color:#b5c2d5}.eyebrow{color:#7fc8ff;letter-spacing:2px;font-size:12px}.notice{border-left:3px solid #e7c26c;background:#242318;padding:14px 18px;margin:20px 0}.facts{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.fact,.panel{background:#181e29;border:1px solid #344055;border-radius:8px;padding:16px}.fact strong{display:block;color:#e7c26c;font-size:22px}.fact.available strong{color:#78d4ae}.fact p{font-size:13px;margin:8px 0 0}.panels{display:grid;grid-template-columns:1fr 1fr;gap:20px}.badge{font-size:14px;color:#e7c26c}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}button,select{background:#181e29;color:#edf1f7;border:1px solid #53647e;border-radius:5px;padding:9px 12px;font:inherit;cursor:pointer}button:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #7fc8ff;outline-offset:3px}a{color:#7fc8ff}li{margin:7px 0}code{overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer;color:#7fc8ff}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #344055}.scroll{overflow:auto}.small{font-size:13px}footer{color:#b5c2d5;font-size:13px;margin-top:30px}@media(max-width:760px){main{padding:18px}.facts,.panels{grid-template-columns:1fr}h1{font-size:28px}}
</style></head><body><main><div class="eyebrow">TRACEHOI / CONTINUATION CONTRACT</div><h1>What can the pipeline do next?</h1><p id="case"></p>
<div class="notice"><strong>Saved diagnostic scenes are available. Placement remains blocked.</strong><div id="next"></div></div>
<div class="row"><a href="TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html">Open the mask review form ↗</a><button id="download">Download readiness JSON</button></div>
<p class="small">Keep the review HTML beside this file. This dashboard shows the recorded inputs at generation time; downloading a review does not change this snapshot. Validate it with the repository CLI to generate an updated snapshot.</p>
<div id="facts" class="facts"></div><h2>Inspect a pipeline stage</h2><div class="panels"><section class="panel"><label for="stage">Stage</label><select id="stage"></select><h2 id="stageStatus"></h2><p id="effect"></p><ul id="stageBlockers"></ul></section><section class="panel"><label for="candidate">Diagnostic candidate</label><select id="candidate"></select><p id="collision" class="badge"></p><div id="metrics"></div><ul id="candidateBlockers"></ul></section></div>
<h2>All four candidates</h2><div class="scroll"><table><thead><tr><th>Candidate</th><th>Conditional scale</th><th>Unsigned gap*</th><th>Collision evidence</th></tr></thead><tbody id="rows"></tbody></table></div><p class="small">* Gaps use the unverified MoGe scene scale. Zero gap or surface separation does not certify physical contact or geometric accuracy.</p>
<details><summary>Review record and source bindings</summary><p id="review"></p><p>Completing a human review records observations. It does not clear the scientific acceptance conditions. A revision request enables planning from the exact recorded pixel regions; applying a revised mask remains a separate step.</p><pre id="bindings" style="white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px"></pre></details>
<footer>No model, optimization, mask edit or placement action occurs in this viewer. Changing a selector only changes the display.</footer>
<script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const R=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),label=s=>s.replaceAll('_',' '),actions={complete_mask_review:'Next: inspect the mask and return a completed review record.',plan_mask_revision:'Next: prepare a revision from the recorded regions; no pixel edits have been applied.',review_reported_uncertainty:'Next: resolve the uncertainty recorded by the reviewer.',design_independent_mask_validation:'Next: establish independent mask validation; a visual assessment alone does not certify accuracy.'};$('case').textContent='Case '+R.case_id+' · saved evidence, explicit stage prerequisites';$('next').textContent=actions[R.next_action];
for(const f of R.facts){const d=document.createElement('div');d.className='fact '+f.status;const t=document.createElement('div'),s=document.createElement('strong'),p=document.createElement('p');t.textContent=label(f.id);s.textContent=label(f.status);p.textContent=f.evidence;d.append(t,s,p);$('facts').append(d)}
for(const [id,rows]of [['stage',R.stages],['candidate',R.candidates]])for(const r of rows){const o=document.createElement('option');o.value=r.id;o.textContent=label(r.id);$(id).append(o)}
function list(id,values){$(id).replaceChildren();for(const v of values){const li=document.createElement('li');li.textContent=label(v);$(id).append(li)}}
function update(){const s=R.stages.find(s=>s.id===$('stage').value),c=R.candidates.find(c=>c.id===$('candidate').value);$('stageStatus').textContent=s.available?'Available for preparation':'Blocked';$('effect').textContent=s.effect;list('stageBlockers',s.blockers);$('collision').textContent=label(c.collision_gate);$('metrics').textContent='Conditional scale '+c.conditional_scale.toFixed(6)+' · unsigned gap '+c.unsigned_surface_gap.toPrecision(5);list('candidateBlockers',c.blockers)}
$('stage').onchange=$('candidate').onchange=update;for(const c of R.candidates){const tr=document.createElement('tr');for(const v of [label(c.id),c.conditional_scale.toFixed(6),c.unsigned_surface_gap.toPrecision(5),label(c.collision_gate)]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('rows').append(tr)}
$('review').textContent='Record: '+R.review.state+' · assessment: '+label(R.review.decision)+' · findings: '+R.review.finding_count+'. Reviewer identity is self-reported.';$('bindings').textContent=JSON.stringify({context:R.context,record_binding:R.review.input_binding},null,2);
$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='tracehoi_scene_readiness_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};window.addEventListener('pageshow',update);update();})();
</script></main></body></html>'''
