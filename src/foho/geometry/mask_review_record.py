"""Bind human mask-review observations to immutable saved scene evidence.

A structurally complete record is a human assertion, not an accuracy certificate.
This module never edits masks, chooses scale, or admits pipeline placement.
"""
import base64,hashlib,json,re

IDS=['primary','minimum_scale','maximum_scale','minimum_scale_refined']
KINDS=['mask_missing','mask_excess','forearm_extent','occlusion_uncertain','mesh_disagreement','uncertain']
DECISIONS=['pending','needs_revision','uncertain','visually_consistent']
FALSE_FIELDS=['mask_modified','mask_accuracy_verified','scale_identified','physical_contact_verified','placement_ready','full_parent_acceptance']

def require(ok,message):
    if not ok:raise ValueError(message)
def encode(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def binding(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def parse(raw):
    require(isinstance(raw,bytes) and len(raw)<=128*1024,'record_size')
    def pairs(items):
        d={}
        for k,v in items:
            require(k not in d,'duplicate_key');d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))
def text(x,limit,label):
    require(type(x) is str and len(x)<=limit and not any(ord(c)<32 and c not in '\n\t' for c in x),label)
def context(review,review_raw):
    require(review['schema']=='tracehoi.HandDomainReview.v1','review_schema')
    require(review['placement_ready'] is review['full_parent_acceptance'] is review['mask_modified'] is False,'source_admission')
    require([c['id'] for c in review['audit']['candidates']]==IDS,'source_candidates')
    pins=review['audit']['source_bindings']
    return dict(case_id=review['case_id'],image_size=[512,512],review_binding=binding(review_raw),
        manifest_binding=review['manifest_binding'],audit_binding=review['audit_binding'],
        source_bindings=pins)
def blank(ctx):
    return dict(schema='tracehoi.MaskReviewRecord.v1',context=ctx,state='draft',reviewer='',reviewed_at='',
        original_image_inspected=False,provisional_mask_inspected=False,decision='pending',notes='',findings=[],
        selected_candidate=None,accepted_scale=None,**{k:False for k in FALSE_FIELDS})
def validate(record,ctx):
    require(type(record) is dict and set(record)==set(blank(ctx)),'record_fields')
    require(record['schema']=='tracehoi.MaskReviewRecord.v1','record_schema')
    # Canonical comparison distinguishes bool/int and rejects nonfinite values.
    require(encode(record['context'])==encode(ctx),'context_binding')
    for k in FALSE_FIELDS:require(record[k] is False,'forbidden_admission:'+k)
    require(record['selected_candidate'] is record['accepted_scale'] is None,'forbidden_selection')
    require(record['state'] in ['draft','reviewed'],'state')
    for k in ['original_image_inspected','provisional_mask_inspected']:require(type(record[k]) is bool,k)
    text(record['reviewer'],120,'reviewer');text(record['notes'],4000,'notes');text(record['reviewed_at'],32,'reviewed_at')
    require(record['decision'] in DECISIONS,'decision')
    require(type(record['findings']) is list and len(record['findings'])<=50,'findings')
    for f in record['findings']:
        require(type(f) is dict and set(f)=={'kind','candidate','bbox_xyxy_inclusive','note'},'finding_fields')
        require(f['kind'] in KINDS and f['candidate'] in IDS+['mask_only'],'finding_category')
        b=f['bbox_xyxy_inclusive'];require(type(b) is list and len(b)==4 and all(type(x) is int and 0<=x<512 for x in b),'finding_box')
        require(b[0]<=b[2] and b[1]<=b[3],'finding_box_order');text(f['note'],1000,'finding_note')
    if record['state']=='reviewed':
        require(record['reviewer'].strip() and record['notes'].strip(),'review_identity_and_summary')
        require(record['original_image_inspected'] and record['provisional_mask_inspected'],'inspection_required')
        require(record['decision']!='pending','decision_required')
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',record['reviewed_at']) is not None,'review_time')
        from datetime import datetime
        datetime.strptime(record['reviewed_at'],'%Y-%m-%dT%H:%M:%SZ')
        if record['decision']=='needs_revision':require(record['findings'],'revision_region_required')
    else:require(record['reviewed_at']=='','draft_time')
    return dict(schema='tracehoi.MaskReviewValidation.v1',record_binding=binding(encode(record)),
        human_review_record_complete=record['state']=='reviewed',decision=record['decision'],
        annotation_count=len(record['findings']),authorship_verified=False,mask_review_required=True,
        selected_candidate=None,accepted_scale=None,**{k:False for k in FALSE_FIELDS})

def build(manifest_path,digest,case,review_dir,files_sha,reader,renderer,viewer):
    from pathlib import Path
    root=Path(review_dir);m,data=reader.inspect_bundle(manifest_path,digest,case)
    raw_receipt=reader.regular(root/'files.json',1024**2)
    require(binding(raw_receipt)['sha256']==files_sha,'review_receipt_binding')
    receipt=reader.parse(raw_receipt);require(receipt['schema']=='tracehoi.HandDomainReviewFiles.v1' and set(receipt['files'])=={'review.json','index.html'},'review_receipt')
    files={n:reader.regular(root/n,8*1024**2) for n in receipt['files']}
    require(all(binding(files[n])==p for n,p in receipt['files'].items()),'review_file_binding')
    review=reader.parse(files['review.json']);viewer.validate_report(review['audit'],m,data,reader)
    require(review['manifest_binding']==receipt['manifest_binding']==binding(reader.regular(manifest_path,1024**2)),'review_manifest')
    require(review['audit_binding']==binding(reader.encode(review['audit'])),'review_audit_binding')
    ctx=context(review,files['review.json']);record=blank(ctx);valid=validate(record,ctx)
    # Direct source-mask view independent of any candidate silhouette or wrist partition.
    mask=renderer.decode_pgm(data['hand_mask'])
    # Use raw mask bytes in canvas to avoid interpreting black pixels as transparency.
    payload=dict(record=record,mask=base64.b64encode(bytes(mask)).decode(),original=base64.b64encode(data['original_rgb']).decode(),kinds=KINDS,candidates=IDS)
    blob=json.dumps(payload,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    html=files['index.html'].decode()
    require(html.count('</main>')==1,'review_html_shape')
    html=html.replace('<title>TraceHOI · Hand coverage review</title>','<title>TraceHOI · Record mask review</title>')
    html=html.replace('<h1>Where does hand coverage differ?</h1>','<h1>Inspect coverage and record findings</h1>')
    html=html.replace('<h1>Inspect coverage and record findings</h1>', '<h1>Inspect coverage and record findings</h1><p><a href="#recordPanel" style="color:#7fc8ff">Go to mask review form ↓</a></p>')
    html=html.replace('</main>',FORM.replace('__RECORD_DATA__',blob).replace('__HAND_PIXELS__',format(sum(bool(x) for x in mask),',' )).replace('__OVERLAP_PIXELS__',format(sum(bool(x) for x in renderer.decode_pgm(data['overlap_mask'])) if 'overlap_mask' in data else 0,','))+'</main>')
    require(len(html.encode())<=8*1024**2,'html_size')
    return dict(context=ctx,review_record_complete=False,mask_review_required=True,placement_ready=False),{
        'index.html':html.encode(),'review_template.json':encode(record),'validation.json':encode(valid),'context.json':encode(ctx)}

FORM=r'''
<style>#recordPanel input:not([type=checkbox]):not([type=range]):not([type=file]),#recordPanel textarea{font:inherit;color:#edf1f7;background:#181e29;border:1px solid #344055;border-radius:5px;padding:8px}#recordPanel label{margin:8px 0}#recordPanel select{max-width:100%}#findings li{margin:10px 0;overflow-wrap:anywhere}</style>
<section id="recordPanel" style="border-top:2px solid #344055;margin-top:32px;padding-top:24px">
<h2>Record your mask review</h2><p>Inspect the original crop and the provisional hand-only mask below. Drag a rectangle to locate a finding. These notes record your observations; they do not change the mask or accept a 3D candidate.</p>
<div class="panels"><div><div class="row"><label><input id="showMask" type="checkbox" checked> Provisional hand-only mask</label><label>Mask opacity <input id="maskOpacity" type="range" min="0" max="100" value="45"></label></div>
<canvas id="annotate" width="512" height="512" style="width:100%;height:auto;touch-action:none;border:1px solid #344055;cursor:crosshair" aria-label="Original crop with provisional mask; drag a rectangle to annotate"></canvas>
<p class="hint">Pink is the unchanged hand-only support (__HAND_PIXELS__ pixels). The __OVERLAP_PIXELS__ hand/object-overlap pixels stay excluded. Use the comparisons above for zoomed inspection. Rectangle coordinates use the original 512 × 512 crop.</p></div>
<div><label>Reviewer <input id="reviewer" maxlength="120" autocomplete="off" style="width:100%"></label>
<label for="decision">Assessment</label><select id="decision"><option value="pending">Not reviewed</option><option value="needs_revision">Mask needs revision</option><option value="uncertain">Uncertain from this image</option><option value="visually_consistent">Visually consistent in this image</option></select>
<label>Review summary <textarea id="reviewNotes" maxlength="4000" rows="3" style="width:100%"></textarea></label>
<label><input id="imageInspected" type="checkbox"> I inspected the original image</label>
<label><input id="maskInspected" type="checkbox"> I inspected the provisional mask</label>
<hr><label for="findingKind">Finding</label><select id="findingKind"></select><label for="findingCandidate">Reference</label><select id="findingCandidate"><option value="mask_only">Mask only</option></select>
<label>Region: x₁ y₁ x₂ y₂ (inclusive)</label><div class="row" id="boxFields"><input aria-label="Region x1" id="bx1" type="number" min="0" max="511" style="width:70px"><input aria-label="Region y1" id="by1" type="number" min="0" max="511" style="width:70px"><input aria-label="Region x2" id="bx2" type="number" min="0" max="511" style="width:70px"><input aria-label="Region y2" id="by2" type="number" min="0" max="511" style="width:70px"></div>
<label>Finding note <textarea id="findingNote" maxlength="1000" rows="2" style="width:100%"></textarea></label><button id="addFinding" type="button">Add finding</button>
</div></div><ol id="findings"></ol>
<div class="row"><button id="saveDraft" type="button">Download draft</button><button id="saveReview" type="button">Download completed review</button><label>Load saved record <input id="loadRecord" type="file" accept=".json,application/json"></label></div>
<p id="recordStatus" class="notice" role="status">Pending human review. Edits stay in this tab until you download a record. A completed record is an observation, not an accuracy certificate.</p>
<p class="hint">If you choose “needs revision,” add at least one region. Downloaded records carry the exact image, mask, scene and audit hashes. The repository validator checks these bindings and preserves every placement restriction. Reviewer identity is self-reported.</p>
</section>
<script id="recordData" type="application/json">__RECORD_DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('recordData').textContent),by=id=>document.getElementById(id),C=by('annotate'),ctx=C.getContext('2d'),original=new Image(),mask=Uint8Array.from(atob(D.mask),c=>c.charCodeAt(0)),base=structuredClone(D.record);let findings=[],drag=null,box=null;
const flags=['mask_modified','mask_accuracy_verified','scale_identified','physical_contact_verified','placement_ready','full_parent_acceptance'];
const labels={mask_missing:'Mask misses visible hand',mask_excess:'Mask includes non-hand pixels',forearm_extent:'Wrist / forearm extent',occlusion_uncertain:'Occlusion is uncertain',mesh_disagreement:'Projected mesh disagrees with image',uncertain:'Other uncertainty'};
for(const k of D.kinds){const o=document.createElement('option');o.value=k;o.textContent=labels[k];by('findingKind').append(o)}for(const id of D.candidates){const o=document.createElement('option');o.value=id;o.textContent=id.replaceAll('_',' ');by('findingCandidate').append(o)}
const maskCanvas=document.createElement('canvas');maskCanvas.width=maskCanvas.height=512;const mc=maskCanvas.getContext('2d'),im=mc.createImageData(512,512);for(let i=0;i<mask.length;i++){im.data.set([245,89,162,mask[i]?255:0],i*4)}mc.putImageData(im,0,0);
function status(s){by('recordStatus').textContent=s}function draw(){ctx.clearRect(0,0,512,512);if(original.complete)ctx.drawImage(original,0,0);if(by('showMask').checked){ctx.globalAlpha=Number(by('maskOpacity').value)/100;ctx.drawImage(maskCanvas,0,0);ctx.globalAlpha=1}for(const [i,f]of findings.entries()){ctx.strokeStyle='#65e6ff';ctx.lineWidth=1;const [x,y,x2,y2]=f.bbox_xyxy_inclusive;ctx.strokeRect(x,y,x2-x+1,y2-y+1);ctx.fillStyle='#fff';ctx.font='12px system-ui';ctx.fillText(String(i+1),x+2,Math.max(12,y-2))}if(box){ctx.strokeStyle='#ffdc70';ctx.lineWidth=2;const [x,y,x2,y2]=box;ctx.strokeRect(x,y,x2-x+1,y2-y+1)}}
original.onload=draw;original.src='data:image/png;base64,'+D.original;by('showMask').oninput=by('maskOpacity').oninput=draw;
function point(e){const r=C.getBoundingClientRect();return [Math.max(0,Math.min(511,Math.floor((e.clientX-r.left)/r.width*512))),Math.max(0,Math.min(511,Math.floor((e.clientY-r.top)/r.height*512)))]}
function setBox(a,b){box=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[0],b[0]),Math.max(a[1],b[1])];['bx1','by1','bx2','by2'].forEach((k,i)=>by(k).value=box[i]);draw()}
C.onpointerdown=e=>{drag=point(e);C.setPointerCapture(e.pointerId);setBox(drag,drag)};C.onpointermove=e=>{if(drag)setBox(drag,point(e))};C.onpointerup=e=>{if(drag)setBox(drag,point(e));drag=null};C.onpointercancel=()=>{drag=null};
function same(a,b){if(a===null||b===null||typeof a!=='object'||typeof b!=='object')return a===b;if(Array.isArray(a)!==Array.isArray(b))return false;const ak=Object.keys(a).sort(),bk=Object.keys(b).sort();return JSON.stringify(ak)===JSON.stringify(bk)&&ak.every(k=>same(a[k],b[k]))}
function checkText(x,n){if(typeof x!=='string'||x.length>n||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(x))throw Error('Invalid text field')}
function validate(r){if(!r||!same(Object.keys(r).sort(),Object.keys(base).sort())||r.schema!==base.schema||!same(r.context,base.context))throw Error('Record belongs to different evidence or has unexpected fields');if(flags.some(k=>r[k]!==false)||r.selected_candidate!==null||r.accepted_scale!==null)throw Error('Acceptance fields must remain unchanged');if(!['draft','reviewed'].includes(r.state)||!['pending','needs_revision','uncertain','visually_consistent'].includes(r.decision)||typeof r.original_image_inspected!=='boolean'||typeof r.provisional_mask_inspected!=='boolean')throw Error('Invalid review state');checkText(r.reviewer,120);checkText(r.notes,4000);checkText(r.reviewed_at,32);if(!Array.isArray(r.findings)||r.findings.length>50)throw Error('At most 50 findings');for(const f of r.findings){if(!f||!same(Object.keys(f).sort(),['bbox_xyxy_inclusive','candidate','kind','note'])||!D.kinds.includes(f.kind)||!['mask_only',...D.candidates].includes(f.candidate))throw Error('Invalid finding');const b=f.bbox_xyxy_inclusive;if(!Array.isArray(b)||b.length!==4||b.some(x=>!Number.isInteger(x)||x<0||x>511)||b[0]>b[2]||b[1]>b[3])throw Error('Region must be ordered integer pixels from 0 to 511');checkText(f.note,1000)}if(r.state==='reviewed'){if(!r.reviewer.trim()||!r.notes.trim()||!r.original_image_inspected||!r.provisional_mask_inspected||r.decision==='pending')throw Error('Enter reviewer, summary, assessment and both inspection checks');if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(r.reviewed_at)||!Number.isFinite(Date.parse(r.reviewed_at))||new Date(r.reviewed_at).toISOString().replace('.000','')!==r.reviewed_at)throw Error('Invalid review date');if(r.decision==='needs_revision'&&!r.findings.length)throw Error('Add a region for the needed revision')}else if(r.reviewed_at!=='')throw Error('Draft date must be empty');return r}
function collect(state){const r=structuredClone(base);Object.assign(r,{state,reviewer:by('reviewer').value,notes:by('reviewNotes').value,decision:by('decision').value,reviewed_at:state==='reviewed'?new Date().toISOString().replace(/\.\d{3}Z$/,'Z'):'',original_image_inspected:by('imageInspected').checked,provisional_mask_inspected:by('maskInspected').checked,findings:structuredClone(findings)});return validate(r)}
function list(){by('findings').replaceChildren();findings.forEach((f,i)=>{const li=document.createElement('li'),t=document.createElement('span'),b=document.createElement('button');t.textContent=`${labels[f.kind]} · ${f.candidate} · [${f.bbox_xyxy_inclusive.join(', ')}] — ${f.note} `;b.type='button';b.textContent='Remove';b.setAttribute('aria-label','Remove finding '+(i+1));b.onclick=()=>{findings.splice(i,1);list();status('Draft changed; download to keep it.')};li.append(t,b);by('findings').append(li)});draw()}
by('addFinding').onclick=()=>{try{const fields=['bx1','by1','bx2','by2'];if(fields.some(k=>by(k).value===''))throw Error('Drag a region or enter all four coordinates');const f={kind:by('findingKind').value,candidate:by('findingCandidate').value,bbox_xyxy_inclusive:fields.map(k=>Number(by(k).value)),note:by('findingNote').value};const r=structuredClone(base);r.findings=[...findings,f];validate(r);findings.push(f);box=null;by('findingNote').value='';fields.forEach(k=>by(k).value='');list();status('Finding added. Download to save your record.')}catch(e){status(e.message)}};
function download(state){try{const r=collect(state),url=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='tracehoi_mask_review_'+r.context.case_id+'_'+state+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status(state==='reviewed'?'Review record downloaded. Mask accuracy, scale and placement remain unaccepted.':'Draft downloaded.')}catch(e){status(e.message)}}by('saveDraft').onclick=()=>download('draft');by('saveReview').onclick=()=>download('reviewed');
by('loadRecord').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>131072)throw Error('Record exceeds 128 KiB');const r=validate(JSON.parse(await f.text()));by('reviewer').value=r.reviewer;by('reviewNotes').value=r.notes;by('decision').value=r.decision;by('imageInspected').checked=r.original_image_inspected;by('maskInspected').checked=r.provisional_mask_inspected;findings=structuredClone(r.findings);box=null;list();status('Loaded matching record. Changes export as a new draft or completed review. Server validation is required before downstream use.')}catch(err){status(err.message)}finally{e.target.value=''}};
for(const id of ['reviewer','reviewNotes','decision','imageInspected','maskInspected'])by(id).addEventListener('input',()=>status('Draft changed; download to keep it.'));
})();
</script>
'''
