"""Offline interactive review of an authenticated hand-domain audit."""
import base64,json

IDS=['primary','minimum_scale','maximum_scale','minimum_scale_refined']

def validate_report(audit,manifest,data,reader):
    require=reader.require
    require(audit['schema']=='tracehoi.HandModelDomainAudit.v1','audit_schema')
    require(audit['case_id']==manifest['case_id'],'audit_case')
    require(audit['source_bindings']=={k:reader.binding(v) for k,v in data.items()},'audit_sources')
    require(audit['selected_candidate'] is audit['accepted_scale'] is None,'audit_selection')
    require(all(audit[k] is False for k in ['placement_ready','mask_modified','source_geometry_modified','full_parent_acceptance','scale_identified','geometric_accuracy_verified','physical_contact_verified']),'audit_admission')
    require([c['id'] for c in audit['candidates']]==[c['id'] for c in manifest['candidates']] and set(IDS)=={c['id'] for c in audit['candidates']},'audit_candidates')
    for c in audit['candidates']:
        require(c['accepted'] is c['placement_ready'] is c['mask_accuracy_verified'] is False,'candidate_admission')
        require(set(c['regions'])=={'hand_side','boundary_band','beyond_boundary'},'audit_regions')
        for key in ['mask_pixels','predicted_pixels','intersection']:
            require(sum(r[key] for r in c['regions'].values())==c['full_visible_hand_mask'][key],'region_conservation')
    return audit

def build_review(manifest_path,digest,case,audit_dir,audit_sha,files_sha,reader,renderer):
    from pathlib import Path
    manifest,data=reader.inspect_bundle(manifest_path,digest,case);root=Path(audit_dir)
    receipt_raw=reader.regular(root/'files.json',1024**2);reader.require(reader.binding(receipt_raw)['sha256']==files_sha,'audit_receipt_binding')
    receipt=reader.parse(receipt_raw);reader.require(receipt['schema']=='tracehoi.HandDomainAuditFiles.v1','audit_receipt_schema')
    expected={'audit.json','audit.md'}|{c+'_domain.png' for c in IDS}
    reader.require(set(receipt['files'])==expected,'audit_file_set');saved={}
    for name,pin in receipt['files'].items():
        raw=reader.regular(root/name,8*1024**2);reader.require(reader.binding(raw)==pin,'audit_file_binding:'+name);saved[name]=raw
    audit_raw=saved['audit.json'];reader.require(reader.binding(audit_raw)['sha256']==audit_sha,'audit_binding')
    audit=validate_report(reader.parse(audit_raw),manifest,data,reader)
    manifest_binding=reader.binding(reader.regular(manifest_path,1024**2))
    reader.require(audit['manifest_binding']==receipt['manifest_binding']==manifest_binding,'audit_manifest')
    images={'original':data['original_rgb']}
    for c in IDS:
        raw=saved[c+'_domain.png'];channels,_=renderer.decode_png(raw);reader.require(channels==3,'audit_image');images[c]=raw
    report=dict(schema='tracehoi.HandDomainReview.v1',case_id=case,manifest_binding=manifest_binding,audit_binding=reader.binding(audit_raw),
        audit_receipt_binding=reader.binding(receipt_raw),audit=audit,mask_modified=False,source_geometry_modified=False,
        selected_candidate=None,accepted_scale=None,placement_ready=False,full_parent_acceptance=False,model_calls=0)
    files={'review.json':reader.encode(report)}
    payload=dict(report=report,images={k:base64.b64encode(v).decode() for k,v in images.items()})
    text=json.dumps(payload,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    files['index.html']=TEMPLATE.replace('__DATA__',text).encode()
    reader.require(len(files['index.html'])<=8*1024**2,'html_size');return report,files

TEMPLATE=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>TraceHOI · Hand coverage review</title>
<style>
:root{color-scheme:dark;--bg:#10141c;--panel:#181e29;--text:#edf1f7;--muted:#acb8cb;--line:#344055;--accent:#7fc8ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}main{max-width:1260px;margin:auto;padding:28px}h1{font-size:30px;line-height:1.15;margin:6px 0 12px}h2{font-size:18px;margin:0 0 10px}p{margin:8px 0}.eyebrow{color:var(--accent);font-size:12px;letter-spacing:2px}.muted{color:var(--muted)}.notice{padding:12px 16px;background:#242318;border-left:3px solid #e6c774;margin:20px 0}.toolbar{display:flex;gap:18px;flex-wrap:wrap;align-items:end;margin:20px 0}label{display:block}select,button{font:inherit;color:var(--text);background:var(--panel);border:1px solid var(--line);padding:9px 12px;border-radius:5px}button{cursor:pointer}button:hover{border-color:var(--accent)}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:3px}input[type=range]{width:150px;accent-color:var(--accent)}.panels{display:grid;grid-template-columns:1fr 1fr;gap:22px}.panel{min-width:0}.viewport{position:relative;aspect-ratio:1;background:#090b10;overflow:hidden;border-radius:6px;touch-action:manipulation}.viewport img,.viewport svg{position:absolute;width:100%;height:100%;left:0;top:0;transform-origin:76% 55%;pointer-events:none}.viewport{cursor:crosshair}.viewport svg{overflow:visible}.metrics{display:flex;flex-wrap:wrap;gap:12px 24px;padding:12px 0}.metric{font-variant-numeric:tabular-nums}.metric strong{display:block;font-size:24px}.metric span{color:var(--muted);font-size:12px}.legend{display:flex;flex-wrap:wrap;gap:9px 18px;margin:16px 0;font-size:13px}.legend span:before{content:'';display:inline-block;width:12px;height:12px;background:var(--swatch);margin-right:6px}.hint{font-size:13px;color:var(--muted)}.readout{min-height:50px;margin-top:8px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}td button{padding:5px 8px}.residuals{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 22px}.residuals button{font-size:13px}details{margin:22px 0}summary{cursor:pointer;color:var(--accent)}code{overflow-wrap:anywhere}footer{margin-top:28px;color:var(--muted);font-size:13px}.status{font-size:13px;color:#e6c774}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.selected{border-color:var(--accent)}@media(max-width:760px){main{padding:16px}.panels{grid-template-columns:1fr}h1{font-size:25px}.toolbar{gap:12px}select{max-width:100%}.metrics{gap:10px 18px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style></head><body><main>
<div class="eyebrow">TRACEHOI / SAVED SCENE DIAGNOSTICS</div><h1>Where does hand coverage differ?</h1>
<p class="muted">Compare the projected hand with the provisional mask, including its extension beyond the open wrist boundary.</p>
<div class="notice"><strong>Diagnostic candidates only.</strong> Region overlap is not an accuracy score. Masks, metric scale, physical contact and pipeline placement remain unaccepted.</div>
<div class="toolbar">
<label for="mode">View<br><select id="mode"><option value="domain">Coverage overlay</option><option value="boundary">Boundary on original image</option><option value="original">Original image</option></select></label>
<label for="zoom">Zoom <output id="zoomValue">1×</output><br><input id="zoom" type="range" min="1" max="4" step="0.25" value="1"></label>
<label for="opacity">Overlay opacity <output id="opacityValue">100%</output><br><input id="opacity" type="range" min="0" max="100" step="5" value="100"></label>
<label><input id="boxes" type="checkbox"> Show residual bounding boxes</label>
<button id="download" type="button">Download review JSON</button>
</div>
<div class="panels">
<section class="panel"><label for="left">Compare A</label><select id="left"></select><p id="leftStatus" class="status"></p><div id="leftView" class="viewport" role="img" aria-label="Candidate A coverage overlay; click to inspect a pixel"><img id="leftBase" alt="Original RGB crop"><img id="leftLayer" alt="Candidate A coverage diagnostic"><svg id="leftSvg" viewBox="0 0 512 512" aria-hidden="true"></svg></div><div id="leftMetrics" class="metrics"></div><div id="leftReadout" class="hint readout" aria-live="polite">Click the image to inspect the fixed boundary partition.</div><h2>Hand-side residuals</h2><div id="leftResiduals" class="residuals"></div></section>
<section class="panel"><label for="right">Compare B</label><select id="right"></select><p id="rightStatus" class="status"></p><div id="rightView" class="viewport" role="img" aria-label="Candidate B coverage overlay; click to inspect a pixel"><img id="rightBase" alt="Original RGB crop"><img id="rightLayer" alt="Candidate B coverage diagnostic"><svg id="rightSvg" viewBox="0 0 512 512" aria-hidden="true"></svg></div><div id="rightMetrics" class="metrics"></div><div id="rightReadout" class="hint readout" aria-live="polite">Click the image to inspect the fixed boundary partition.</div><h2>Hand-side residuals</h2><div id="rightResiduals" class="residuals"></div></section>
</div>
<div class="legend"><span style="--swatch:#42d28e">Mask + projected hand</span><span style="--swatch:#3884ff">Uncovered mask, hand-facing side</span><span style="--swatch:#b66ce7">Mask beyond boundary</span><span style="--swatch:#ffde50">Boundary band</span><span style="--swatch:#ff9630">Projected hand outside mask</span><span style="--swatch:#ffffff">Mesh boundary vertices</span></div>
<p class="hint">Residual buttons highlight the largest connected mask-only regions on the hand-facing side. Boxes show extents, not exact component shapes. Boundary inspection is also available numerically:</p>
<div class="row"><label>Pixel x <input id="pixelX" type="number" min="0" max="511" value="430" style="width:70px"></label><label>Pixel y <input id="pixelY" type="number" min="0" max="511" value="280" style="width:70px"></label><button id="inspect" type="button">Inspect in both views</button></div>
<h2 style="margin-top:28px">All four preserved candidates</h2><div class="table-wrap"><table><thead><tr><th>Candidate</th><th>Full-mask IoU</th><th>Hand-side IoU</th><th>Beyond-boundary mask pixels</th><th>Hand-side uncovered pixels</th></tr></thead><tbody id="rows"></tbody></table></div>
<details><summary>Method, provenance and limits</summary><p>The 16-vertex open mesh boundary is projected using the recorded camera. Its principal axis defines a band containing all boundary vertices plus a fixed two-pixel margin. The band faces the projected mesh centroid. This is a heuristic model-domain partition, not anatomical ground truth.</p><p>Each full-mask score is preserved from X8. Restricting the score to the hand-facing side changes its domain; it does not prove a better reconstruction. No mask, geometry, camera or transform is changed here. Display selections are never pipeline acceptance.</p><p id="identity"></p><p>Scene units are MoGe-predicted metric scale without independent verification. The minimum-scale candidate retains its saved crossing rejection; similar image masks can conceal different 3D relationships.</p></details>
<footer>Offline review · No network, model inference, optimization or acceptance action.</footer>
<script id="data" type="application/json">__DATA__</script><script>
'use strict';const D=JSON.parse(document.getElementById('data').textContent),R=D.report,A=R.audit;
const $=id=>document.getElementById(id),labels={primary:'Primary',minimum_scale:'Minimum scale',maximum_scale:'Maximum scale',minimum_scale_refined:'Minimum scale · refined'};
const active={left:null,right:null},points={left:null,right:null};const svgNS='http://www.w3.org/2000/svg';
function image(name){return 'data:image/png;base64,'+D.images[name]}
for(const side of ['left','right']){for(const c of A.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=labels[c.id];$(side).append(o)}$(side+'Base').src=image('original');$(side).addEventListener('change',()=>{active[side]=null;points[side]=null;update()})}
$('right').value='maximum_scale';
for(const c of A.candidates){const tr=document.createElement('tr');const td=document.createElement('td'),b=document.createElement('button');b.type='button';b.textContent=labels[c.id];b.addEventListener('click',()=>{$('left').value=c.id;active.left=null;points.left=null;update()});td.append(b);tr.append(td);for(const x of [c.full_visible_hand_mask.iou.toFixed(4),c.regions.hand_side.iou.toFixed(4),c.regions.beyond_boundary.mask_pixels,c.regions.hand_side.mask_only]){const t=document.createElement('td');t.textContent=x;tr.append(t)}$('rows').append(tr)}
function element(svg,name,attrs){const e=document.createElementNS(svgNS,name);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);svg.append(e);return e}
function metric(root,label,value){const d=document.createElement('div');d.className='metric';const v=document.createElement('strong'),l=document.createElement('span');v.textContent=value;l.textContent=label;d.append(v,l);root.append(d)}
function inspect(side,x,y){const c=A.candidates.find(c=>c.id===$(side).value),b=c.boundary;const s=(x-b.center_uv[0])*b.hand_facing_unit_normal[0]+(y-b.center_uv[1])*b.hand_facing_unit_normal[1];const part=s>b.signed_band_limits_px[1]?'hand-facing side':s<b.signed_band_limits_px[0]?'beyond boundary':'boundary band';points[side]=[x,y];$(side+'Readout').textContent=`Pixel (${x}, ${y}) · ${part} · signed distance ${s.toFixed(2)} px. This classifies the boundary partition only; it does not identify anatomy or mask membership.`}
function update(){const z=+$('zoom').value,mode=$('mode').value;$('zoomValue').value=z+'×';$('opacityValue').value=$('opacity').value+'%';
for(const side of ['left','right']){const c=A.candidates.find(c=>c.id===$(side).value),b=c.boundary,svg=$(side+'Svg');$(side+'Status').textContent='Unaccepted · '+c.collision_gate.replaceAll('_',' ');
$(side+'Layer').src=image(c.id);$(side+'Layer').hidden=mode!=='domain';$(side+'Layer').style.opacity=$('opacity').value/100;
for(const suffix of ['Base','Layer','Svg'])$(side+suffix).style.transform=`scale(${z})`;
svg.replaceChildren();svg.hidden=mode==='original';
if(mode==='boundary'){for(const limit of b.signed_band_limits_px){const n=b.hand_facing_unit_normal,t=[-n[1],n[0]],q=[b.center_uv[0]+limit*n[0],b.center_uv[1]+limit*n[1]];element(svg,'line',{x1:q[0]-800*t[0],y1:q[1]-800*t[1],x2:q[0]+800*t[0],y2:q[1]+800*t[1],stroke:'#ffde50','stroke-width':1,'stroke-dasharray':'3 3'})}for(const p of b.boundary_uv)element(svg,'circle',{cx:p[0],cy:p[1],r:1.4,fill:'#fff'})}
const list=$(side+'Residuals');list.replaceChildren();c.hand_side_mask_only_components.slice(0,5).forEach((r,i)=>{const btn=document.createElement('button');btn.type='button';btn.textContent=`#${i+1} · ${r.pixels} px`;btn.setAttribute('aria-pressed',active[side]===i);if(active[side]===i)btn.className='selected';btn.addEventListener('click',()=>{active[side]=active[side]===i?null:i;update()});list.append(btn);if($('boxes').checked||active[side]===i){const [x,y,x2,y2]=r.bbox_xyxy_inclusive;element(svg,'rect',{x,y,width:x2-x+1,height:y2-y+1,fill:'none',stroke:active[side]===i?'#fff':'#3884ff','stroke-width':1,'stroke-dasharray':'3 2'});const t=element(svg,'text',{x:x+2,y:Math.max(8,y-2),fill:'#fff','font-size':8});t.textContent='#'+(i+1)}});
if(points[side]){inspect(side,...points[side]);element(svg,'circle',{cx:points[side][0],cy:points[side][1],r:3,fill:'none',stroke:'#fff','stroke-width':1})}
if(!points[side])$(side+'Readout').textContent='Click the image to inspect the fixed boundary partition.';
const metrics=$(side+'Metrics');metrics.replaceChildren();metric(metrics,'Full-mask IoU',c.full_visible_hand_mask.iou.toFixed(3));metric(metrics,'Beyond-boundary pixels',c.regions.beyond_boundary.mask_pixels);metric(metrics,'Uncovered hand-side pixels',c.regions.hand_side.mask_only);
}}
for(const id of ['mode','zoom','opacity','boxes'])$(id).addEventListener('input',update);
for(const side of ['left','right'])$(side+'View').addEventListener('click',e=>{const rect=e.currentTarget.getBoundingClientRect(),z=+$('zoom').value,x=Math.round(((e.clientX-rect.left)/rect.width*512-389.12)/z+389.12),y=Math.round(((e.clientY-rect.top)/rect.height*512-281.6)/z+281.6);if(x>=0&&x<512&&y>=0&&y<512){$('pixelX').value=x;$('pixelY').value=y;inspect(side,x,y);update()}});
$('inspect').addEventListener('click',()=>{const x=Number($('pixelX').value),y=Number($('pixelY').value);if(!Number.isInteger(x)||!Number.isInteger(y)||x<0||x>511||y<0||y>511){for(const side of ['left','right'])$(side+'Readout').textContent='Enter integer pixel coordinates from 0 to 511.';return}for(const side of ['left','right'])inspect(side,x,y);update()});
$('download').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(R,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='tracehoi_hand_domain_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
$('identity').textContent=`Case ${R.case_id}. Scene SHA-256: ${R.manifest_binding.sha256}. Audit SHA-256: ${R.audit_binding.sha256}.`;
update();
</script></main></body></html>'''
