"""Import human observations into an immutable pipeline continuation packet.

Inputs remain untouched. A complete human record enables planning, never pixels,
scale selection, contact certification or production placement.
"""
import base64,json,os
from pathlib import Path

SCHEMA='tracehoi.ReviewIntake.v1'
FORM='TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html'

def build(package_dir,digest,case,reader,renderer,viewer,records,ready,export,*,record_raw=None,purpose):
    reader.require(purpose=='review_intake','review_intake_purpose_required')
    root=Path(package_dir)
    verified=export.verify(root,digest,case,reader,renderer,viewer,records,ready,purpose='diagnostic')
    package=reader.parse(reader.regular(root/'package.json',1024**2))
    # Preserve an already embedded record unless an explicit new record is supplied.
    inherited=record_raw is None and package['review_input_binding'] is not None
    if inherited:record_raw=reader.regular(root/'human_review.json',128*1024)
    manifest=root/'source/scene.json';source_digest=package['source_manifest_binding']['sha256']
    review_dir=root/'source_review';review_digest=package['source_review_binding']['sha256']
    state=ready.evaluate(manifest,source_digest,case,review_dir,review_digest,reader,renderer,viewer,records,record_raw)
    reader.require(record_raw is None or state['review']['record_complete'] is True,'completed_human_record_required')
    files={'readiness.json':reader.encode(state)};plan=None;original=None
    if record_raw is not None:
        original=records.parse(record_raw);files['review_original.json']=record_raw
        if original['decision']=='needs_revision':
            plan=ready.prepare_stage(manifest,source_digest,case,review_dir,review_digest,reader,renderer,viewer,records,stage='mask_revision_planning',record_raw=record_raw)
            reader.require(plan['planning_only'] is True and plan['mask_modified'] is False and plan['findings']==original['findings'] and plan['notes']==original['notes'],'planning_preservation')
            files['revision_plan.json']=reader.encode(plan)
    report=dict(schema=SCHEMA,case_id=case,purpose=purpose,source_package_binding=verified['package_binding'],
        source_manifest_binding=package['source_manifest_binding'],source_review_input_binding=package['review_input_binding'],
        record_input_binding=reader.binding(record_raw) if record_raw is not None else None,
        record_source='embedded_package' if inherited else 'explicit_record' if record_raw is not None else 'missing',
        status='recorded' if original else 'pending_human_review',human_review_record_complete=original is not None,
        review_state=state['review']['state'],decision=state['review']['decision'],next_action=state['next_action'],
        revision_plan_available=plan is not None,annotation_count=state['review']['finding_count'],
        authorship_verified=False,mask_accuracy_verified=False,scale_identified=False,physical_contact_verified=False,
        geometric_accuracy_verified=False,placement_ready=False,full_parent_acceptance=False,mask_modified=False,
        source_geometry_modified=False,selected_candidate=None,accepted_scale=None,models_executed=0,
        planning_only=True,revision_applied=False)
    files['intake.json']=reader.encode(report)
    _,data=reader.inspect_bundle(manifest,source_digest,case)
    files[FORM]=reader.regular(root/FORM,8*1024**2)
    files['index.html']=html(dict(report=report,readiness=state,record=original,
        original=base64.b64encode(data['original_rgb']).decode(),mask=base64.b64encode(bytes(renderer.decode_pgm(data['hand_mask']))).decode()))
    reader.require(export.verify(root,digest,case,reader,renderer,viewer,records,ready,purpose='diagnostic')==verified,'source_changed_during_intake')
    receipt=dict(schema='tracehoi.ReviewIntakeFiles.v1',source_package_binding=verified['package_binding'],case_id=case,
        files={n:reader.binding(b) for n,b in files.items()},record_input_binding=report['record_input_binding'],
        status=report['status'],placement_ready=False)
    files['files.json']=reader.encode(receipt)
    return report,files

def verify(output,receipt_sha,package_dir,package_sha,case,reader,renderer,viewer,records,ready,export,*,purpose):
    reader.require(purpose=='review_intake','review_intake_purpose_required')
    out=Path(output);raw=reader.regular(out/'files.json',1024**2)
    reader.require(reader.binding(raw)['sha256']==receipt_sha,'intake_receipt_binding')
    receipt=reader.parse(raw);actual={}
    for p in out.iterdir():
        reader.require(len(actual)<8 and not p.is_symlink() and p.is_file(),'intake_inventory')
        actual[p.name]=reader.regular(p,8*1024**2)
    reader.require(set(actual)==set(receipt['files'])|{'files.json'} and sum(map(len,actual.values()))<=8*1024**2,'intake_inventory')
    reader.require({n:reader.binding(b) for n,b in actual.items() if n!='files.json'}==receipt['files'],'intake_file_binding')
    recorded=reader.parse(actual['intake.json'])
    # Preserve the original intake mode when replaying an inherited record.
    supplied=None if recorded['record_source']=='embedded_package' else actual.get('review_original.json')
    report,expected=build(package_dir,package_sha,case,reader,renderer,viewer,records,ready,export,record_raw=supplied,purpose=purpose)
    reader.require(actual==expected,'intake_semantic_mismatch')
    return dict(schema='tracehoi.ReviewIntakeReceipt.v1',receipt_binding=reader.binding(raw),source_package_binding=receipt['source_package_binding'],
        case_id=case,verified=True,status=report['status'],review_state=report['review_state'],
        human_review_record_complete=report['human_review_record_complete'],revision_plan_available=report['revision_plan_available'],
        next_action=report['next_action'],record_input_binding=report['record_input_binding'],placement_ready=False,revision_applied=False)

def html(data):
    blob=json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return TEMPLATE.replace('__DATA__',blob).encode()

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><title>TraceHOI · Review intake</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c1320;color:#e8eef6;font:16px/1.5 system-ui}main{max-width:1180px;margin:auto;padding:28px}h1{font-size:34px;margin:8px 0}h2{font-size:20px}.eyebrow{color:#80d4c7;letter-spacing:2px;font-size:12px}.muted{color:#b4c2d4}.notice{padding:14px 18px;background:#29251c;border-left:3px solid #edc56b;margin:20px 0}.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:20px}.panel{padding:18px;border:1px solid #34445c;border-radius:10px;background:#141e2d}canvas{width:100%;height:auto;background:#10141c}.row{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:12px 0}button,select{font:inherit;color:inherit;background:#1e2c40;border:1px solid #526781;border-radius:5px;padding:8px;cursor:pointer}button:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #80d4c7}a{color:#9dd7ff}code,pre{overflow-wrap:anywhere;white-space:pre-wrap;font-size:12px}li{margin:8px 0}.pill{display:inline-block;border:1px solid #edc56b;padding:3px 10px;border-radius:20px;color:#edc56b}.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.steps button[aria-pressed=true]{border-color:#80d4c7;color:#80d4c7}footer{font-size:13px;color:#b4c2d4;margin:24px 0}@media(max-width:760px){main{padding:16px}.grid{grid-template-columns:1fr}.steps{grid-template-columns:1fr 1fr}h1{font-size:27px}}
</style></head><body><main><div class="eyebrow">TRACEHOI / REVIEW → PIPELINE</div><h1>Bring human findings into the pipeline</h1><p id="identity" class="muted"></p><div class="notice"><span id="status" class="pill"></span><p id="next"></p><strong>Recording observations does not accept a mask, scale, contact or scene placement.</strong></div>
<div class="steps" aria-label="Review workflow"><button data-step="0" aria-pressed="true">1 · Inspect</button><button data-step="1" aria-pressed="false">2 · Save & transfer</button><button data-step="2" aria-pressed="false">3 · Validate</button><button data-step="3" aria-pressed="false">4 · Plan</button></div><p id="stepHelp" class="muted"></p>
<div class="grid"><section class="panel"><h2>Original image and provisional support</h2><canvas id="image" width="512" height="512" role="img" aria-label="Original image with unchanged provisional hand mask and recorded finding"></canvas><div class="row"><label><input type="checkbox" id="showMask" checked> Show provisional mask</label><label>Opacity <input id="opacity" type="range" min="0" max="100" value="45"></label></div><p class="muted">Pink marks the saved hand-only support. Hand/object overlap stays excluded. The image and mask are unchanged.</p></section><section class="panel"><h2>Recorded findings</h2><p id="summary"></p><label for="finding">Finding to inspect</label><select id="finding"></select><p id="findingText"></p><p id="author" class="muted"></p><a href="TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html">Open the original review form ↗</a><h2>Continuation</h2><p id="plan"></p><ul><li>Original record bytes are preserved.</li><li>Revision plans contain the recorded regions and notes.</li><li>No mask pixels, geometry or placement are changed.</li></ul><button id="download">Download intake summary</button></section></div>
<details><summary>Source bindings and server validation</summary><pre id="bindings"></pre><p>This snapshot changes only when a new intake is validated. To import a completed record, use the repository command <code>tools/tracehoi/intake_mask_review.py import</code> with the package hash, record and a new output folder. A draft or mismatched record is refused. A missing record remains pending.</p></details><footer>Offline inspection. Reviewer identity is self-reported. The server CLI validates the complete source package and exact JSON record before preparing a continuation packet.</footer>
<script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),R=D.report,$=id=>document.getElementById(id),C=$('image'),ctx=C.getContext('2d'),rgb=new Image(),mask=Uint8Array.from(atob(D.mask),c=>c.charCodeAt(0)),mc=document.createElement('canvas');mc.width=mc.height=512;const mctx=mc.getContext('2d'),im=mctx.createImageData(512,512);for(let i=0;i<mask.length;i++)im.data.set([245,89,162,mask[i]?255:0],i*4);mctx.putImageData(im,0,0);const label=s=>s.replaceAll('_',' '),findings=D.record?D.record.findings:[];
$('identity').textContent=R.case_id+' · verified diagnostic package · immutable review intake';$('status').textContent=label(R.status);$('next').textContent='Next action: '+label(R.next_action)+'.';$('summary').textContent=D.record?D.record.notes:'No completed human review was supplied. The pipeline has no human findings to apply.';$('author').textContent=D.record?'Reviewer: '+D.record.reviewer+' · '+D.record.reviewed_at+' · identity self-reported':'Human review is required; this tool does not author observations.';$('plan').textContent=R.revision_plan_available?'A planning packet is available with the exact recorded regions. No revision has been applied.':'No revision plan has been created. Follow the recorded next action.';$('bindings').textContent=JSON.stringify({package:R.source_package_binding,record:R.record_input_binding,source:R.record_source},null,2);
const none=document.createElement('option');none.value='';none.textContent='No region highlighted';$('finding').append(none);findings.forEach((f,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=(i+1)+' · '+label(f.kind);$('finding').append(o)});$('finding').disabled=!findings.length;
function draw(){ctx.clearRect(0,0,512,512);if(rgb.complete&&rgb.naturalWidth)ctx.drawImage(rgb,0,0);if($('showMask').checked){ctx.globalAlpha=+$('opacity').value/100;ctx.drawImage(mc,0,0);ctx.globalAlpha=1}const f=$('finding').value===''?null:findings[+$('finding').value];$('findingText').textContent=f?f.candidate+' · ['+f.bbox_xyxy_inclusive.join(', ')+'] · '+f.note:'Select a recorded region when available.';if(f){const [x,y,x2,y2]=f.bbox_xyxy_inclusive;ctx.strokeStyle='#65e6ff';ctx.lineWidth=2;ctx.strokeRect(x,y,x2-x+1,y2-y+1)}}rgb.onload=draw;rgb.src='data:image/png;base64,'+D.original;for(const id of ['showMask','opacity','finding'])$(id).addEventListener('input',draw);
const help=['Inspect the original RGB and provisional mask in the review form. Record what you observe; no assessment is preselected.','Download a completed review from the form. Keep that JSON unchanged and manually copy it to the server Downloads folder.','The CLI validates the source package, image/mask bindings, review fields and completion. Existing outputs are never overwritten.','A completed revision request produces planning inputs. Uncertainty or a visually consistent assessment follows its own next action; placement stays blocked.'];function step(i){document.querySelectorAll('[data-step]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.step===i)));$('stepHelp').textContent=help[i]}document.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>step(+b.dataset.step));$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='tracehoi_review_intake_'+R.case_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};window.addEventListener('pageshow',draw);step(0);draw();})();
</script></main></body></html>'''
