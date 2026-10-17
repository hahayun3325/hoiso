"""Separate reference annotation and diagnostic mask scoring; standard library only.

Self-reported provenance is retained, not authenticated. No score is acceptance.
"""
import base64,datetime,hashlib,json
from pathlib import Path

N=512*512
PURPOSE='mask_validation'
POLICY='visible_selected_hand_to_wrist_uncertain_boundary_ignored_v1'

def require(ok,reason):
    if not ok:raise ValueError(reason)

def encode(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def binding(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def parse(raw):
    require(type(raw) is bytes and len(raw)<=1024**2,'reference_file_bound')
    def pairs(items):
        result={}
        for k,v in items:
            require(k not in result,'duplicate_key');result[k]=v
        return result
    def bad(v):raise ValueError('nonfinite_json')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)

def reference_context(protocol):
    return dict(protocol_binding=binding(encode(protocol)),case_id=protocol['case_id'],image_binding=protocol['image_binding'],
                selected_hand_id=protocol['selected_hand_id'],image_size=[512,512],policy=POLICY)

def validate_reference(raw,protocol):
    r=parse(raw);require(type(r) is dict,'reference_object')
    keys={'schema','context','state','annotator','annotated_at','method','candidate_mask_used','model_assistance_used','prior_candidate_exposure','whole_image_inspected','notes','labels_base64'}
    require(set(r)==keys,'reference_fields')
    require(r['schema']=='tracehoi.IndependentMaskReference.v1' and r['state']=='complete','completed_reference_required')
    require(r['context']==reference_context(protocol),'reference_context_mismatch')
    require(type(r['annotator']) is str and 1<=len(r['annotator'].strip())<=120,'annotator_required')
    require(type(r['notes']) is str and 1<=len(r['notes'].strip())<=4000,'reference_notes_required')
    require(type(r['annotated_at']) is str and len(r['annotated_at'])<=40,'annotation_time')
    try:when=datetime.datetime.fromisoformat(r['annotated_at'].replace('Z','+00:00'))
    except ValueError:raise ValueError('annotation_time')
    require(when.utcoffset() is not None,'annotation_timezone')
    require(r['method']=='manual_rgb_delineation' and r['candidate_mask_used'] is False and r['model_assistance_used'] is False,'separate_reference_required')
    require(r['prior_candidate_exposure'] in ['yes','no','unknown'] and type(r['prior_candidate_exposure']) is str,'prior_exposure_required')
    require(r['whole_image_inspected'] is True,'whole_image_inspection_required')
    require(type(r['labels_base64']) is str and len(r['labels_base64'])==349528,'label_encoding_size')
    try:labels=base64.b64decode(r['labels_base64'],validate=True)
    except Exception:raise ValueError('label_encoding')
    require(len(labels)==N and set(labels)<={0,128,255} and base64.b64encode(labels).decode()==r['labels_base64'],'labels_512_ternary')
    require(0 in labels and 255 in labels,'reference_needs_foreground_and_background')
    return r,labels

def score(pred,labels,excluded):
    require(type(pred) is bytes and type(labels) is bytes and type(excluded) is bytes and len(pred)==len(labels)==len(excluded)==N,'pixel_shape')
    require(set(pred)<={0,255} and set(excluded)<={0,255} and set(labels)<={0,128,255},'pixel_values')
    tp=fp=fn=tn=unknown=excluded_count=unknown_outside=0
    for p,r,x in zip(pred,labels,excluded):
        unknown+=r==128;excluded_count+=x!=0;unknown_outside+=r==128 and x==0
        if x or r==128:continue
        if p and r==255:tp+=1
        elif p:fp+=1
        elif r==255:fn+=1
        else:tn+=1
    denom=lambda a,b:a/b if b else None
    evaluated=tp+fp+fn+tn
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,evaluated_pixels=evaluated,total_pixels=N,
        fixed_overlap_excluded_pixels=excluded_count,reference_uncertain_pixels=unknown,reference_uncertain_outside_overlap=unknown_outside,
        evaluated_fraction=denom(evaluated,N),candidate_pixels_total=pred.count(255),candidate_pixels_evaluated=tp+fp,reference_positive_evaluated=tp+fn,
        iou=denom(tp,tp+fp+fn),dice=denom(2*tp,2*tp+fp+fn),precision=denom(tp,tp+fp),recall=denom(tp,tp+fn))

def build(package_dir,digest,case,reader,renderer,viewer,records,ready,export,*,reference_raw=None,purpose):
    require(purpose==PURPOSE,'mask_validation_purpose_required')
    root=Path(package_dir)
    verified=export.verify(root,digest,case,reader,renderer,viewer,records,ready,purpose='diagnostic')
    p=reader.parse(reader.regular(root/'package.json',1024**2))
    state=reader.parse(reader.regular(root/'readiness.json',1024**2))
    require(state['review']['record_complete'] is True and state['review']['decision']=='visually_consistent','reviewed_working_mask_required')
    m,data=reader.inspect_bundle(root/'source/scene.json',p['source_manifest_binding']['sha256'],case)
    pred=renderer.decode_pgm(data['hand_mask']);excluded=renderer.decode_pgm(data['overlap_mask'])
    require(not any(a and b for a,b in zip(pred,excluded)),'hand_only_support_overlaps_ambiguity')
    protocol=dict(schema='tracehoi.MaskValidationProtocol.v1',case_id=case,selected_hand_id=m['selected_hand_id'],image_size=[512,512],
        source_package_binding=verified['package_binding'],image_binding=binding(data['original_rgb']),working_mask_binding=binding(data['hand_mask']),
        excluded_overlap_binding=binding(data['overlap_mask']),human_review_binding=p['review_input_binding'],policy=POLICY,
        question='How closely does the reviewed hand-only support match a separately delineated visible-hand reference on this exact crop?',
        scope='Selected lower/right hand through the wrist crease; exclude the other hand, object and forearm. Mark uncertain wrist or occlusion boundaries as 128. Do not infer hidden anatomy.',
        labels={'0':'visible non-hand/background','128':'uncertain or unlabelled, excluded from scoring','255':'visible selected hand'},
        scoring='Exclude the fixed ambiguous hand/object overlap and reference label 128. Report TP, FP, FN, TN, IoU, Dice, precision, recall and coverage together. Undefined ratios are null.',
        independence='Draw from original RGB without tracing the working mask, HaMeR silhouette, SAM output or MoGe depth. Record prior exposure honestly; provenance remains self-reported.',
        acceptance_threshold=None,placement_ready=False,scope_status='validation_design_not_ground_truth',
        limitations=['One image and a self-reported reference do not establish dataset accuracy.','Wrist/forearm scope differs from a full arm mask; uncertain wrist pixels may be ignored explicitly.','Excluded pixels and coverage must accompany every score.','Scores do not accept geometry, scale, contact or placement.'])
    ctx=reference_context(protocol);record=labels=metrics=None
    if reference_raw is not None:
        record,labels=validate_reference(reference_raw,protocol);metrics=score(pred,labels,excluded)
        require(metrics['reference_positive_evaluated']>0,'no_reference_foreground_in_scoring_domain')
    report=dict(schema='tracehoi.MaskValidationRun.v1',case_id=case,protocol_binding=ctx['protocol_binding'],
        source_package_binding=verified['package_binding'],status='reference_scored' if record else 'awaiting_reference',
        human_review_record_complete=True,working_mask_visual_review='visually_consistent',reference_binding=binding(reference_raw) if record else None,
        reference_provenance=({k:record[k] for k in ['annotator','annotated_at','method','candidate_mask_used','model_assistance_used','prior_candidate_exposure','notes']} if record else None),
        metrics=metrics,provenance_verified=False,mask_accuracy_verified=False,scale_identified=False,physical_contact_verified=False,
        placement_ready=False,full_parent_acceptance=False,mask_modified=False,model_calls=0,reference_generated=False,
        next_action='inspect_reference_and_metrics' if record else 'collect_separate_reference_when_quantitative_validation_is_needed')
    files={'protocol.json':encode(protocol),'assessment.json':encode(report),'reference_annotation.html':annotation_html(ctx,data['original_rgb'],protocol),
           'index.html':report_html(report,data['original_rgb'],pred,excluded,labels)}
    if record:files['reference_original.json']=reference_raw
    receipt=dict(schema='tracehoi.MaskValidationFiles.v1',case_id=case,files={k:binding(v) for k,v in files.items()},placement_ready=False)
    files['files.json']=encode(receipt)
    require(export.verify(root,digest,case,reader,renderer,viewer,records,ready,purpose='diagnostic')==verified,'source_changed_during_validation')
    return report,files

def verify(output,receipt_sha,package_dir,digest,case,reader,renderer,viewer,records,ready,export,*,purpose):
    require(purpose==PURPOSE,'mask_validation_purpose_required');out=Path(output)
    raw=reader.regular(out/'files.json',1024**2);require(binding(raw)['sha256']==receipt_sha,'validation_receipt_changed')
    rr=parse(raw);actual={}
    for q in out.iterdir():
        require(q.is_file() and not q.is_symlink() and len(actual)<6,'validation_inventory')
        actual[q.name]=reader.regular(q,2*1024**2)
    require(set(actual)==set(rr['files'])|{'files.json'},'validation_inventory')
    require({k:binding(v) for k,v in actual.items() if k!='files.json'}==rr['files'],'validation_files_changed')
    report,expected=build(package_dir,digest,case,reader,renderer,viewer,records,ready,export,reference_raw=actual.get('reference_original.json'),purpose=purpose)
    require(actual==expected,'validation_semantic_mismatch')
    return dict(verified=True,status=report['status'],receipt_binding=binding(raw),protocol_binding=report['protocol_binding'],reference_binding=report['reference_binding'],placement_ready=False)

def blob(data):return json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
def annotation_html(context,rgb,protocol):return ANNOTATION.replace('__DATA__',blob(dict(context=context,rgb=base64.b64encode(rgb).decode(),scope=protocol['scope']))).encode()
def report_html(report,rgb,pred,excluded,labels):
    return REPORT.replace('__DATA__',blob(dict(report=report,rgb=base64.b64encode(rgb).decode(),pred=base64.b64encode(pred).decode(),excluded=base64.b64encode(excluded).decode(),labels=base64.b64encode(labels).decode() if labels else None))).encode()

STYLE='''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1320;color:#e9eef7;font:15px/1.5 system-ui}main{max-width:1260px;margin:auto;padding:28px}.eyebrow{font-size:12px;letter-spacing:2px;color:#84d7c5}h1{font-size:34px;line-height:1.2;margin:12px 0}h2{font-size:18px;margin-top:0}.muted{color:#aebed0}.grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(280px,1fr);gap:20px}.panel{background:#142031;border:1px solid #34475e;border-radius:12px;padding:18px}.row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0}button,select,input[type=text],textarea{font:inherit;color:inherit;background:#203047;border:1px solid #59708b;border-radius:6px;padding:9px}button{cursor:pointer}button.primary{background:#235f56;border-color:#84d7c5}button:disabled{opacity:.4;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid #84d7c5;outline-offset:2px}textarea,input[type=text]{width:100%}textarea{min-height:80px}label{display:block}a{color:#8bdace}.notice{border-left:3px solid #e6c67b;background:#28271f;padding:12px 18px;margin:20px 0}.pill{border:1px solid #84d7c5;color:#84d7c5;display:inline-block;border-radius:18px;padding:3px 10px}.scroll{max-height:660px;overflow:auto;background:#060a10}canvas{display:block;width:100%;height:auto;touch-action:none;max-width:none}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}.stat{border:1px solid #34475e;border-radius:8px;padding:12px}.value{font-size:26px;color:#84d7c5}li{margin:8px 0}footer{margin-top:24px;font-size:13px;color:#aebed0}.small{font-size:12px}.legend span{padding-right:12px}@media(max-width:800px){main{padding:16px}.grid{grid-template-columns:1fr}h1{font-size:27px}.stats{grid-template-columns:1fr 1fr}}
</style>'''

ANNOTATION='<!doctype html><html lang="en"><head>'+STYLE+r'''<title>TraceHOI · Separate reference annotation</title></head><body><main><div class="eyebrow">TRACEHOI / REFERENCE WORKSPACE</div><h1>Draw a separate visible-hand reference</h1><p class="muted" id="identity"></p><div class="notice">Your earlier visual review is already recorded. This optional annotation is for quantitative validation. Use the original RGB only; the working mask and model silhouettes are not included in this page.</div><div class="grid"><section class="panel"><div class="row"><label>Tool <select id="tool"><option value="polygon">Polygon</option><option value="brush">Brush</option></select></label><label>Label <select id="label"><option value="255">Visible hand</option><option value="0">Background</option><option value="128">Uncertain / unlabelled</option></select></label><label>Brush radius <input type="range" id="radius" min="1" max="24" value="5"></label><label>Zoom <select id="zoom"><option value="1">1×</option><option value="2">2×</option><option value="3">3×</option><option value="4">4×</option></select></label></div><div class="scroll"><canvas id="canvas" width="512" height="512" aria-label="Original RGB annotation canvas; click polygon vertices or drag brush"></canvas></div><div class="row"><button id="apply">Fill polygon</button><button id="cancel">Cancel polygon</button><button id="undo">Undo label edit</button><button id="background">Fill all uncertain pixels as background</button></div><div class="row"><label><input type="checkbox" id="show" checked> Show labels</label><label>Opacity <input type="range" id="opacity" min="0" max="90" value="40"></label></div><p class="legend small"><span style="color:#69e1bd">■ Visible hand</span><span style="color:#efc772">■ Uncertain / unlabelled</span>Background is transparent.</p><p id="counts" aria-live="polite"></p><p class="muted small">Click at least three polygon corners, then fill. The brush paints exact source pixels. Zoom uses a scrollable canvas. All pixels start uncertain; the background-fill button replaces every uncertain pixel, including any intentional uncertainty. Use it before marking uncertain boundaries, or undo it. Inspect the whole image before completion. Changes stay in memory until you download JSON. Keep a draft before closing.</p></section><aside class="panel"><h2>Annotation scope</h2><p id="scope"></p><p class="muted">Do not outline the upper hand or reconstruct fingers hidden by the object. Label ambiguous wrist and object boundaries uncertain.</p><h2>Reference provenance</h2><label>Annotator <input id="author" type="text" maxlength="120" autocomplete="off"></label><label>Have you previously seen the candidate mask? <select id="exposure"><option value="unknown">Unknown / not recorded</option><option value="yes">Yes</option><option value="no">No</option></select></label><label>Notes on boundaries and uncertainty <textarea id="notes" maxlength="4000"></textarea></label><p><label><input type="checkbox" id="separate"> I drew these labels from RGB without copying a candidate mask or using model-assisted segmentation.</label></p><p><label><input type="checkbox" id="inspected"> I inspected the whole image and the chosen wrist boundary.</label></p><button id="draft">Download draft</button> <button class="primary" id="complete" disabled>Download complete reference</button><p><label>Resume JSON draft/reference <input id="resume" type="file" accept="application/json,.json"></label></p><p id="message" role="status" class="muted"></p><p class="small">Identity and independence are self-reported. Prior exposure does not disappear when drawing again. Completion does not establish ground truth, mask accuracy or scene placement.</p></aside></div><footer>Offline. No network, model, automatic segmentation or mask acceptance. Transfer the saved JSON unchanged when you choose to evaluate it. Reference and source image bindings are checked again by the server.</footer><script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),C=$('canvas'),ctx=C.getContext('2d'),I=new Image(),N=512*512;let labels=new Uint8Array(N).fill(128),history=[],points=[],drag=false,last=null;const L=document.createElement('canvas');L.width=L.height=512;const lc=L.getContext('2d');$('identity').textContent=D.context.case_id+' · selected lower/right hand · 512 × 512 source pixels';$('scope').textContent=D.scope;const saveUndo=()=>{history.push(labels.slice());if(history.length>20)history.shift()};function draw(){ctx.clearRect(0,0,512,512);if(I.naturalWidth)ctx.drawImage(I,0,0);if($('show').checked){const a=lc.createImageData(512,512);for(let i=0;i<N;i++){if(labels[i]===255)a.data.set([70,220,166,255],i*4);else if(labels[i]===128)a.data.set([235,183,75,140],i*4)}lc.putImageData(a,0,0);ctx.globalAlpha=+$('opacity').value/100;ctx.drawImage(L,0,0);ctx.globalAlpha=1}if(points.length){ctx.strokeStyle='#ffffff';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(...points[0]);for(const p of points.slice(1))ctx.lineTo(...p);ctx.stroke();for(const p of points){ctx.fillStyle='#ffffff';ctx.fillRect(p[0]-2,p[1]-2,4,4)}}let fg=0,bg=0;for(const v of labels){fg+=v===255;bg+=v===0}$('counts').textContent=fg+' hand · '+bg+' background · '+(N-fg-bg)+' uncertain / unlabelled pixels';$('apply').disabled=points.length<3;$('undo').disabled=!history.length;$('complete').disabled=!(fg&&bg&&$('author').value.trim()&&$('notes').value.trim()&&$('separate').checked&&$('inspected').checked&&!points.length);}
function pos(e){const r=C.getBoundingClientRect();return[Math.max(0,Math.min(511.999,(e.clientX-r.left)*512/r.width)),Math.max(0,Math.min(511.999,(e.clientY-r.top)*512/r.height))]}
function brush(p){const rad=+$('radius').value,v=+$('label').value;for(let y=Math.max(0,Math.floor(p[1]-rad));y<Math.min(512,Math.ceil(p[1]+rad));y++)for(let x=Math.max(0,Math.floor(p[0]-rad));x<Math.min(512,Math.ceil(p[0]+rad));x++)if((x+.5-p[0])**2+(y+.5-p[1])**2<=rad*rad)labels[y*512+x]=v;}
C.onpointerdown=e=>{if($('tool').value==='polygon'){points.push(pos(e));draw();return}saveUndo();drag=true;last=pos(e);brush(last);C.setPointerCapture(e.pointerId);draw()};C.onpointermove=e=>{if(!drag)return;const p=pos(e),steps=Math.max(1,Math.ceil(Math.hypot(p[0]-last[0],p[1]-last[1])));for(let i=1;i<=steps;i++)brush([last[0]+(p[0]-last[0])*i/steps,last[1]+(p[1]-last[1])*i/steps]);last=p;draw()};C.onpointerup=C.onpointercancel=()=>{drag=false;last=null};$('apply').onclick=()=>{if(points.length<3)return;saveUndo();const path=new Path2D();path.moveTo(...points[0]);for(const p of points.slice(1))path.lineTo(...p);path.closePath();for(let y=0;y<512;y++)for(let x=0;x<512;x++)if(ctx.isPointInPath(path,x+.5,y+.5))labels[y*512+x]=+$('label').value;points=[];draw()};$('cancel').onclick=()=>{points=[];draw()};$('undo').onclick=()=>{if(history.length)labels=history.pop();points=[];draw()};$('background').onclick=()=>{saveUndo();for(let i=0;i<N;i++)if(labels[i]===128)labels[i]=0;draw()};$('zoom').onchange=()=>{C.style.width=+$('zoom').value===1?'100%':(512*+$('zoom').value)+'px';C.style.height='auto'};for(const id of ['show','opacity','author','notes','separate','inspected'])$(id).addEventListener('input',draw);
function b64(a){let s='';for(let i=0;i<a.length;i+=8192)s+=String.fromCharCode(...a.subarray(i,i+8192));return btoa(s)}function record(state){return{schema:'tracehoi.IndependentMaskReference.v1',context:D.context,state,annotator:$('author').value.trim(),annotated_at:new Date().toISOString(),method:'manual_rgb_delineation',candidate_mask_used:!$('separate').checked,model_assistance_used:!$('separate').checked,prior_candidate_exposure:$('exposure').value,whole_image_inspected:$('inspected').checked,notes:$('notes').value.trim(),labels_base64:b64(labels)}}function download(state){const url=URL.createObjectURL(new Blob([JSON.stringify(record(state),null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='tracehoi_reference_'+D.context.case_id+'_'+state+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('message').textContent='Downloaded '+state+' JSON. Keep it separate from your original mask-review JSON.'}$('draft').onclick=()=>download('draft');$('complete').onclick=()=>{if(!$('complete').disabled)download('complete')};const stable=x=>{if(Array.isArray(x))return x.map(stable);if(x&&typeof x==='object')return Object.fromEntries(Object.keys(x).sort().map(k=>[k,stable(x[k])]));return x};$('resume').onchange=async()=>{try{const f=$('resume').files[0];if(!f||f.size>1024*1024)throw Error('File is missing or too large.');const r=JSON.parse(await f.text());if(r.schema!=='tracehoi.IndependentMaskReference.v1'||JSON.stringify(stable(r.context))!==JSON.stringify(stable(D.context)))throw Error('Different image or protocol.');const b=Uint8Array.from(atob(r.labels_base64),c=>c.charCodeAt(0));if(b.length!==N||b.some(v=>![0,128,255].includes(v)))throw Error('Invalid pixel labels.');if(!['yes','no','unknown'].includes(r.prior_candidate_exposure)||typeof r.annotator!=='string'||typeof r.notes!=='string')throw Error('Invalid metadata.');saveUndo();labels=b;points=[];$('author').value=r.annotator;$('notes').value=r.notes;$('exposure').value=r.prior_candidate_exposure;$('separate').checked=r.candidate_mask_used===false&&r.model_assistance_used===false;$('inspected').checked=r.whole_image_inspected===true;$('message').textContent='Loaded labels locally. Server validation remains required.';draw()}catch(e){$('message').textContent='Could not load: '+e.message}};I.onload=draw;I.src='data:image/png;base64,'+D.rgb;draw();})();
</script></main></body></html>'''

REPORT='<!doctype html><html lang="en"><head>'+STYLE+r'''<title>TraceHOI · Mask validation</title></head><body><main><div class="eyebrow">TRACEHOI / VISUAL REVIEW → MEASUREMENT</div><h1>A reviewed mask, a separate validation question</h1><p class="muted" id="identity"></p><span class="pill">Visual review recorded</span><div class="notice" id="status"></div><div class="stats"><div class="stat">Intersection over union<div class="value" id="iou">Pending</div></div><div class="stat">Dice overlap<div class="value" id="dice">Pending</div></div><div class="stat">Evaluated image coverage<div class="value" id="coverage">Pending</div></div></div><div class="grid"><section class="panel"><h2>Inspect the scoring domain</h2><div class="row"><label>Overlay <select id="layer"><option value="working">Reviewed hand-only support</option><option value="excluded">Fixed overlap exclusions</option><option value="reference">Separate reference</option><option value="errors">Disagreement</option><option value="rgb">Original RGB</option></select></label><label>Opacity <input type="range" id="opacity" min="0" max="90" value="50"></label><label>Zoom <select id="zoom"><option value="1">1×</option><option value="2">2×</option><option value="3">3×</option></select></label></div><div class="scroll"><canvas id="canvas" width="512" height="512" aria-label="Original RGB with diagnostic mask overlay"></canvas></div><p id="legend" class="muted small"></p></section><aside class="panel"><h2>What is ready</h2><p>Your original visual approval stays recorded. This step adds a frozen evaluation protocol, a separate RGB annotation page and a repeatable scorer.</p><h2>What remains open</h2><p id="referenceState"></p><p>Reference scope: visible selected lower/right hand through the wrist crease. Forearm and the upper hand are outside this scope; uncertain boundaries can be ignored explicitly.</p><p>Coverage is reported with every score. The fixed hand/object overlap is excluded. No threshold or accuracy claim is chosen automatically.</p><p><a href="reference_annotation.html">Open RGB-only reference workspace ↗</a></p><p class="muted small">No need to redo your visual review. A separate reference can be supplied later when quantitative validation is needed. The annotation page contains no working-mask pixels.</p><h2>Next pipeline boundary</h2><p>Keep all four scene candidates. Mask scores do not resolve metric scale, geometry, collision or physical contact, and do not commit placement.</p></aside></div><details><summary>Counts, reference provenance and bindings</summary><pre id="details"></pre></details><footer>Offline diagnostic inspection. Provenance is self-reported; no independent reference is fabricated. No model execution or mask edits.</footer><script id="data" type="application/json">__DATA__</script><script>
(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent),R=D.report,$=id=>document.getElementById(id),C=$('canvas'),ctx=C.getContext('2d'),I=new Image(),bytes=b=>b?Uint8Array.from(atob(b),c=>c.charCodeAt(0)):null,P=bytes(D.pred),X=bytes(D.excluded),T=bytes(D.labels),L=document.createElement('canvas');L.width=L.height=512;const lc=L.getContext('2d');$('identity').textContent=R.case_id+' · fixed image and mask bindings · diagnostic evaluation';$('status').textContent=T?'Reference scored. Inspect disagreements, excluded pixels and provenance before interpreting any metric.':'Awaiting a separately drawn reference. No accuracy score has been calculated.';$('referenceState').textContent=T?'A reference is present. Its annotator and independence declarations are retained, but not independently authenticated.':'No separate reference was supplied. The working mask remains visually approved; quantitative accuracy is unresolved.';$('details').textContent=JSON.stringify(R,null,2);if(R.metrics){for(const k of ['iou','dice'])$(k).textContent=R.metrics[k]===null?'Undefined':R.metrics[k].toFixed(3);$('coverage').textContent=(100*R.metrics.evaluated_fraction).toFixed(1)+'%'}for(const o of $('layer').options)if(['reference','errors'].includes(o.value))o.disabled=!T;function draw(){ctx.clearRect(0,0,512,512);if(I.naturalWidth)ctx.drawImage(I,0,0);const layer=$('layer').value,a=lc.createImageData(512,512);for(let i=0;i<P.length;i++){let c=null;if(layer==='working'&&P[i])c=[70,220,166,255];if(layer==='excluded'&&X[i])c=[240,190,60,255];if(layer==='reference'&&T)c=T[i]===255?[90,180,255,255]:T[i]===128?[240,190,60,255]:null;if(layer==='errors'&&T){if(X[i]||T[i]===128)c=[240,190,60,255];else if(P[i]&&T[i]===0)c=[255,105,160,255];else if(!P[i]&&T[i]===255)c=[90,180,255,255]}if(c)a.data.set(c,i*4)}lc.putImageData(a,0,0);ctx.globalAlpha=+$('opacity').value/100;ctx.drawImage(L,0,0);ctx.globalAlpha=1;$('legend').textContent={working:'Green: unchanged reviewed hand-only support.',excluded:'Amber: fixed ambiguous hand/object overlap, excluded from scoring.',reference:'Blue: reference hand. Amber: reference uncertainty.',errors:'Pink: working-mask-only. Blue: reference-only. Amber: excluded or uncertain.',rgb:'Original RGB without mask overlays.'}[layer]}$('layer').onchange=$('opacity').oninput=draw;$('zoom').onchange=()=>{C.style.width=+$('zoom').value===1?'100%':(512*+$('zoom').value)+'px';C.style.height='auto'};I.onload=draw;I.src='data:image/png;base64,'+D.rgb;draw();})();
</script></main></body></html>'''
