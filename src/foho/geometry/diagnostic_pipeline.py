"""Compose saved diagnostic stages in a portable, reproducible workspace.

No native model imports, inference, optimization, mask edits or placement.
A supplied reference is validated strictly; a missing reference stays pending.
"""
import json,os,tempfile
from pathlib import Path
PURPOSE='diagnostic_pipeline'
SCHEMA='tracehoi.DiagnosticPipelineWorkspace.v1'
MAX_FILES=48
MAX_BYTES=32*1024**2

def require(ok,reason):
    if not ok:raise ValueError(reason)

def summarize(scene,mask,comparison):
    """Internal stage join, for evidence already authenticated by build()."""
    require(scene['case_id']==mask['case_id']==comparison['case_id'],'pipeline_case_mismatch')
    require(scene['package_binding']==mask['source_package_binding']==comparison['source_package_binding'],'pipeline_source_mismatch')
    require(mask['status'] in ['awaiting_reference','reference_scored'] and comparison['reference_status']==mask['status'],'pipeline_reference_state')
    require(comparison['reference_metrics']==mask['metrics'],'pipeline_reference_metrics')
    pending=mask['status']=='awaiting_reference'
    require((mask['metrics'] is None)==pending and (mask['reference_binding'] is None)==pending,'pipeline_reference_presence')
    require(mask['human_review_record_complete'] is True and comparison['human_review_record_complete'] is True,'pipeline_human_review_required')
    require(mask['placement_ready'] is False and comparison['placement_ready'] is False and scene['placement_ready'] is False,'pipeline_placement_refused')
    require(comparison['selected_candidate'] is None and comparison['accepted_scale'] is None,'pipeline_selection_refused')
    return dict(schema='tracehoi.DiagnosticPipelineRun.v1',case_id=scene['case_id'],purpose=PURPOSE,
        stages=[dict(id='scene',status='verified',depends_on=[],receipt=scene['package_binding'],effect='Exact saved source package retained'),
            dict(id='validation',status=mask['status'],depends_on=['scene'],receipt=comparison['validation_receipt_binding'],effect='Separate-reference scoring or explicit pending state'),
            dict(id='comparison',status='complete',depends_on=['scene','validation'],effect='Saved diagnostic comparison; no winning candidate selected')],
        human_review_record_complete=True,reference_status=mask['status'],reference_binding=mask['reference_binding'],reference_metrics=mask['metrics'],
        next_actions=['supply_reference_when_quantitative_mask_validation_is_needed' if pending else 'inspect_reference_provenance_coverage_and_metrics',
            'establish_independent_scale_and_3d_evidence','validate_contact_before_placement'],
        profiles=comparison['profiles'],candidates=comparison['candidates'],
        candidate_loading_available=True,placement_ready=False,full_parent_acceptance=False,selected_candidate=None,accepted_scale=None,
        mask_accuracy_verified=False,scale_identified=False,geometric_accuracy_verified=False,physical_contact_verified=False,
        reference_provenance_verified=False,source_geometry_modified=False,mask_modified=False,model_calls=0,
        limitations=['Workspace completion is not full pipeline acceptance.',
            'A supplied manual reference retains self-reported provenance. Scores and coverage do not automatically verify accuracy.',
            'Candidate meshes already contain scene transforms. Parent code must not reapply provenance transforms.',
            'Diagnostic loading allows inspection of crossing candidates; it does not authorize their placement.'])

def inventory(root,reader):
    root=Path(root);files={}
    for base,dirs,names in os.walk(root,followlinks=False):
        for name in dirs+names:
            p=Path(base)/name;require(not p.is_symlink(),'pipeline_symlink')
            if name in names:
                require(len(files)<MAX_FILES,'pipeline_file_count');files[p.relative_to(root).as_posix()]=reader.regular(p,8*1024**2)
    require(sum(map(len,files.values()))<=MAX_BYTES,'pipeline_byte_bound');return files

def build(package_dir,package_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,*,reference_raw=None,purpose):
    require(purpose==PURPOSE,'diagnostic_pipeline_purpose_required')
    root=Path(package_dir)
    scene=export.verify(root,package_sha,case,reader,renderer,viewer,records,ready,purpose='diagnostic')
    source=inventory(root,reader)
    require(reader.binding(source['package.json'])==scene['package_binding'],'pipeline_source_changed')
    # Snapshot to a private temporary directory; no runtime dependency on old run folders.
    with tempfile.TemporaryDirectory(prefix='tracehoi-pipeline-') as t:
        work=Path(t).resolve();export.publish(work/'scene',source,reader)
        args=(work/'scene',package_sha,case,reader,renderer,viewer,records,ready,export)
        mask,mfiles=validation.build(*args,reference_raw=reference_raw,purpose='mask_validation')
        export.publish(work/'validation',mfiles,reader)
        vsha=reader.binding(mfiles['files.json'])['sha256']
        comp,cfiles=comparison.build(work/'scene',package_sha,work/'validation',vsha,case,reader,renderer,viewer,records,ready,export,validation,purpose='candidate_comparison')
    report=summarize(scene,mask,comp)
    files={'scene/'+n:b for n,b in source.items()}
    files.update({'validation/'+n:b for n,b in mfiles.items()});files.update({'comparison/'+n:b for n,b in cfiles.items()})
    files['pipeline.json']=reader.encode(report);files['index.html']=html(report)
    files['README.md']=('TraceHOI diagnostic workspace for '+case+'\n\nOpen index.html after extracting the complete ZIP. Source geometry, human review and all four candidates remain in scene/. Validation files and the RGB-only reference annotator are in validation/. comparison/ retains the exact comparison artifacts. Use the top-level dashboard for portable navigation; legacy links inside comparison/index.html refer to earlier standalone filenames.\n\nVerify workspace.json with its separately recorded SHA-256. Parent code may call diagnostic_pipeline.load_candidate with an explicit candidate ID and purpose="diagnostic_pipeline". Mesh bytes are already transformed and the returned model matrices are identity. No stage accepts a candidate or authorizes placement.\n\nTo evaluate a later reference, build a NEW workspace from scene/package.json with its recorded SHA and the original reference JSON; preserve this workspace and the exact reference bytes. Missing reference stays pending. Drafts, wrong image bindings and invalid provenance are refused. No thresholds or human findings are generated.\n').encode()
    manifest=dict(schema=SCHEMA,case_id=case,purpose=PURPOSE,source_package_binding=scene['package_binding'],
        validation_receipt_binding=reader.binding(mfiles['files.json']),comparison_receipt_binding=reader.binding(cfiles['files.json']),
        reference_binding=mask['reference_binding'],files={n:reader.binding(b) for n,b in files.items()},placement_ready=False,selected_candidate=None)
    files['workspace.json']=reader.encode(manifest)
    require(len(files)<=MAX_FILES and sum(map(len,files.values()))<=MAX_BYTES,'pipeline_output_bound')
    require(inventory(root,reader)==source,'pipeline_source_changed_during_build')
    return report,files

def verify(out,workspace_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,*,purpose):
    require(purpose==PURPOSE,'diagnostic_pipeline_purpose_required');root=Path(out)
    raw=reader.regular(root/'workspace.json',1024**2);require(reader.binding(raw)['sha256']==workspace_sha,'pipeline_receipt_changed')
    m=reader.parse(raw);require(m['schema']==SCHEMA and m['case_id']==case and m['purpose']==PURPOSE,'pipeline_identity')
    actual=inventory(root,reader);require(set(actual)==set(m['files'])|{'workspace.json'},'pipeline_inventory')
    require({n:reader.binding(b) for n,b in actual.items() if n!='workspace.json'}==m['files'],'pipeline_files_changed')
    report,expected=build(root/'scene',m['source_package_binding']['sha256'],case,reader,renderer,viewer,records,ready,export,validation,comparison,reference_raw=actual.get('validation/reference_original.json'),purpose=purpose)
    require(actual==expected,'pipeline_semantic_mismatch')
    return dict(schema='tracehoi.DiagnosticPipelineReceipt.v1',workspace_binding=reader.binding(raw),case_id=case,verified=True,
        source_package_binding=m['source_package_binding'],reference_status=report['reference_status'],reference_binding=report['reference_binding'],
        files=len(actual),candidate_ids=[c['id'] for c in report['candidates']],placement_ready=False,selected_candidate=None)

def load_candidate(out,workspace_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,*,candidate_id,purpose):
    require(purpose==PURPOSE,'diagnostic_pipeline_purpose_required')
    require(candidate_id in reader.IDS,'explicit_candidate_required')
    receipt=verify(out,workspace_sha,case,reader,renderer,viewer,records,ready,export,validation,comparison,purpose=purpose)
    root=Path(out);p=reader.parse(reader.regular(root/'scene/package.json',1024**2))
    payload=reader.load_candidate(root/'scene/source/scene.json',expected_sha256=p['source_manifest_binding']['sha256'],expected_case_id=case,candidate_id=candidate_id,purpose='diagnostic')
    require(payload['hand_model_matrix']==payload['object_model_matrix']==reader.IDENTITY,'pipeline_double_transform_refused')
    return dict(schema='tracehoi.ParentDiagnosticScene.v1',workspace_receipt=receipt,requested_candidate=candidate_id,
        scene=payload,placement_ready=False,selected_candidate=None,accepted_scale=None)

def html(report):
    data=json.dumps(report,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',data).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Diagnostic pipeline workspace</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#0c1420;color:#edf2f9;font:15px/1.6 system-ui;margin:0}main{max-width:1220px;margin:auto;padding:32px}h1{font-size:38px;line-height:1.2;margin:8px 0}h2{font-size:20px}.eyebrow{font-size:12px;color:#7edcc8;letter-spacing:2px}.muted{color:#a9bbcf}.notice{padding:15px 20px;background:#29261a;border-left:3px solid #e5bc6b;margin:22px 0}.stages{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.stage,.panel{padding:20px;border:1px solid #3b4c65;border-radius:10px;background:#152132}.stage{text-align:left;color:inherit;font:inherit;cursor:pointer}.stage strong{display:block;font-size:20px}.stage.active{border-color:#7edcc8;background:#1b3440}.status{color:#e8bf73}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}.row{display:flex;gap:16px;flex-wrap:wrap;align-items:center}a{color:#9fd8ff}select,button.action{font:inherit;background:#22334a;color:inherit;border:1px solid #5b718d;border-radius:5px;padding:8px 12px;cursor:pointer}button:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #7edcc8;outline-offset:3px}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:12px;text-align:left;border-bottom:1px solid #35475e}th{color:#a9bbcf}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.value{font-size:24px;color:#7edcc8}.small{font-size:12px}code{overflow-wrap:anywhere}footer{color:#a9bbcf;margin-top:24px}@media(max-width:750px){main{padding:18px}.grid,.stages{grid-template-columns:1fr}h1{font-size:29px}}
</style></head><body><main><div class="eyebrow">TRACEHOI / CONNECTED DIAGNOSTIC PIPELINE</div><h1>One workspace, connected evidence.</h1><p id="identity" class="muted"></p><div class="notice"><strong>Diagnostic data is ready for parent code. Placement remains unaccepted.</strong><br>Your visual review is preserved. A separate reference is optional for continued diagnostic work and required to calculate its mask-validation metrics.</div>
<div id="stages" class="stages"></div><div class="grid"><section class="panel"><h2 id="stageTitle"></h2><div id="stageStatus" class="value"></div><p id="stageDetail"></p><a id="stageLink" href="scene/index.html">Inspect stage output ↗</a><p class="small muted">Select a stage to inspect its state and source dependency. These controls only change the display.</p></section><section class="panel"><h2>Reference state</h2><p id="reference"></p><p id="referenceMetrics"></p><a href="validation/reference_annotation.html">Open the RGB-only reference workspace ↗</a><p class="small muted">Keep your original review JSON. A separate reference JSON uses its own frozen protocol and is never synthesized by this pipeline.</p></section></div>
<section class="panel"><div class="row"><h2>Inspect the saved candidate interface</h2><label>Candidate <select id="candidate"></select></label><label>Comparison <select id="profile"><option value="image_agreement">Image agreement</option><option value="image_and_proximity_hypothesis">Image + proximity hypothesis</option></select></label></div><p id="candidateDetail"></p><p id="frontier" class="status"></p><p class="small muted">Named diagnostic loading returns exact mesh bytes and identity model matrices. Loading or inspecting a candidate never selects it for placement. The proximity profile minimizes unsigned gap as a hypothesis, not as contact evidence.</p><div class="scroll"><table><thead><tr><th>Candidate</th><th>Median residual (px)</th><th>Visible-mask IoU*</th><th>Unsigned gap†</th><th>Recorded collision gate</th></tr></thead><tbody id="rows"></tbody></table></div><p class="small muted">* Working-mask overlap, distinct from separate-reference validation. † Unverified scene units; surface separation does not certify physical contact or containment. All four candidates remain retained.</p><a href="scene/index.html">Explore the saved geometry ↗</a></section>
<div class="grid"><section class="panel"><h2>Use the workspace from the parent pipeline</h2><p>Verify the separately recorded <code>workspace.json</code> checksum, then request an explicit candidate through <code>diagnostic_pipeline.load_candidate</code>. The API verifies all stages and refuses placement purpose.</p><p>When a reference is available, run the build command with <code>--reference</code> and a new output directory. The same source scene is preserved; validation and comparison are rebuilt together.</p></section><section class="panel"><h2>Still unresolved</h2><ul><li>Independent mask accuracy and reference provenance</li><li>Metric scale and 3D geometric accuracy</li><li>Physical contact and production placement</li></ul><p>Workspace completion certifies the software/evidence contract. It does not resolve these scientific questions.</p></section></div>
<details><summary>Stage receipts and exact pipeline state</summary><pre id="state"></pre></details><button class="action" id="download">Download pipeline state JSON</button><footer>Offline inspection. No inference, optimization, mask edit or placement action occurs here. Extract the complete workspace ZIP before opening its index.html so stage links resolve.</footer>
<script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const R=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),label=s=>s.replaceAll('_',' '),names={scene:'1 · Saved scene',validation:'2 · Mask validation',comparison:'3 · Candidate comparison'},links={scene:'scene/index.html',validation:'validation/index.html',comparison:'#candidate'};let stage='scene';$('identity').textContent=R.case_id+' · portable source snapshots · reproducible stage outputs';$('state').textContent=JSON.stringify(R,null,2);$('reference').textContent=R.reference_status==='awaiting_reference'?'Separate reference pending. The completed visual review remains recorded.':'Separate reference scored. Its provenance is self-reported and must be inspected.';$('referenceMetrics').textContent=R.reference_metrics?'IoU '+(R.reference_metrics.iou===null?'undefined':R.reference_metrics.iou.toFixed(4))+' · Dice '+(R.reference_metrics.dice===null?'undefined':R.reference_metrics.dice.toFixed(4))+' · evaluated pixels '+R.reference_metrics.evaluated_pixels:'No quantitative reference metrics have been calculated.';
for(const s of R.stages){const b=document.createElement('button');b.className='stage';b.dataset.stage=s.id;const h=document.createElement('strong'),v=document.createElement('span');h.textContent=names[s.id];v.textContent=label(s.status);v.className='status';b.append(h,v);b.onclick=()=>{stage=s.id;showStage()};$('stages').append(b)}function showStage(){for(const b of $('stages').children){b.classList.toggle('active',b.dataset.stage===stage);b.setAttribute('aria-pressed',String(b.dataset.stage===stage))}const s=R.stages.find(s=>s.id===stage);$('stageTitle').textContent=names[stage];$('stageStatus').textContent=label(s.status);$('stageDetail').textContent=s.effect+'. Dependencies: '+(s.depends_on.map(label).join(', ')||'authenticated portable source')+'.';$('stageLink').href=links[stage];$('stageLink').textContent=stage==='comparison'?'Inspect candidates below ↓':'Inspect stage output ↗'}
for(const c of R.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=label(c.id);$('candidate').append(o)}function showCandidate(){const c=R.candidates.find(c=>c.id===$('candidate').value),p=R.profiles[$('profile').value];$('candidateDetail').textContent=label(c.id)+' · conditional scale '+c.conditional_scale.toFixed(6)+' · '+label(c.collision_gate)+'. Placement remains false.';$('frontier').textContent='Diagnostic frontier under this profile: '+p.nondominated_ids.map(label).join(' · ');$('rows').replaceChildren();for(const r of R.candidates){const tr=document.createElement('tr');if(r.id===c.id)tr.style.background='#22394a';for(const v of[label(r.id),r.joint_median_px.toFixed(3),r.visible_mask_iou.toFixed(4),r.surface_gap.toPrecision(5),label(r.collision_gate)]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('rows').append(tr)}}$('candidate').onchange=$('profile').onchange=showCandidate;$('download').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='tracehoi_pipeline_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};window.addEventListener('pageshow',()=>{showStage();showCandidate()});showStage();showCandidate();})();
</script></main></body></html>'''
