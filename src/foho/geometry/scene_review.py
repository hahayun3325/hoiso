"""Offline review of verified diagnostic scenes; Python standard library only."""
import json,math,struct,zlib
def require(ok,reason):
    if not ok:raise ValueError(reason)
SIZE=512*512
HEADER=b'P5\n512 512\n255\n'

def pgm(raw):
    require(type(raw) is bytes and len(raw)==SIZE and set(raw)<={0,255},'binary_mask_512')
    return HEADER+raw

def decode_pgm(raw):
    require(raw.startswith(HEADER),'pgm_header');pixels=raw[len(HEADER):];pgm(pixels);return pixels

def gray_png(raw):
    pgm(raw)
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    pixels=b''.join(b'\0'+raw[y*512:(y+1)*512] for y in range(512))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',512,512,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(pixels,9))+chunk(b'IEND',b'')

def decode_png(raw):
    require(raw[:8]==b'\x89PNG\r\n\x1a\n','PNG_signature');pos=8;compressed=b'';header=None;ended=False
    while pos<len(raw):
        require(pos+12<=len(raw),'PNG_chunk_header');size=int.from_bytes(raw[pos:pos+4],'big');kind=raw[pos+4:pos+8];data=raw[pos+8:pos+8+size]
        require(len(data)==size and pos+12+size<=len(raw) and zlib.crc32(kind+data)&0xffffffff==int.from_bytes(raw[pos+8+size:pos+12+size],'big'),'PNG_crc')
        if kind==b'IHDR':require(header is None,'PNG_duplicate_header');header=struct.unpack('>IIBBBBB',data)
        elif kind==b'IDAT':compressed+=data
        elif kind==b'IEND':require(size==0 and pos+12==len(raw),'PNG_end');ended=True
        else:require(kind[:1].islower(),'PNG_unknown_critical_chunk')
        pos+=12+size
    require(ended and header and header[:3]==(512,512,8) and header[3] in (0,2) and header[4:]==(0,0,0),'PNG_512_gray_or_RGB')
    channels=1 if header[3]==0 else 3;stride=512*channels;cap=(stride+1)*512
    d=zlib.decompressobj();decoded=d.decompress(compressed,cap+1)
    require(len(decoded)==cap and d.eof and not d.unused_data and not d.unconsumed_tail,'PNG_payload_bound')
    rows=[];previous=bytearray(stride)
    for y in range(512):
        f=decoded[y*(stride+1)];row=bytearray(decoded[y*(stride+1)+1:(y+1)*(stride+1)]);require(f<=4,'PNG_filter')
        for x in range(stride):
            a=row[x-channels] if x>=channels else 0;b=previous[x];c=previous[x-channels] if x>=channels else 0
            if f==1:v=a
            elif f==2:v=b
            elif f==3:v=(a+b)//2
            elif f==4:
                p=a+b-c;da,db,dc=abs(p-a),abs(p-b),abs(p-c);v=a if da<=db and da<=dc else b if db<=dc else c
            else:v=0
            row[x]=(row[x]+v)&255
        rows.append(bytes(row));previous=row
    return channels,b''.join(rows)

def rgb_png(raw):
    require(len(raw)==512*512*3,'RGB_size')
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',512,512,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+raw[i:i+1536] for i in range(0,len(raw),1536)),9))+chunk(b'IEND',b'')

def gray(raw):
    c,b=decode_png(raw);require(c==1 and set(b)<={0,255},'binary_gray_png');return b


# Standard-library rasterization. Mesh vertices already use scene coordinates.
import base64,html,math
from array import array

def surface_depth(vertices,faces,K,shape=(512,512),work_limit=32000000):
    """Nearest two-sided surface at integer pixel centers; reciprocal-depth interpolation.

    Geometry crossing/behind the camera is rejected, not silently clipped. The
    actual saved contract contains only vertices in front of the camera.
    """
    h,w=shape
    require(type(h) is int and type(w) is int and 0<h<=512 and 0<w<=512,'raster_shape')
    require(0<len(vertices)<=80000 and 0<len(faces)<=160000,'raster_mesh_bound')
    require(len(K)==3 and all(len(row)==3 for row in K) and all(math.isfinite(x) for row in K for x in row) and K[2]==[0,0,1],'raster_K')
    uv=[];depth=[]
    for p in vertices:
        require(len(p)==3 and all(math.isfinite(x) for x in p) and p[2]<-1e-8,'raster_camera_plane')
        x,y,z=p[0],-p[1],-p[2]
        uv.append(((K[0][0]*x+K[0][1]*y)/z+K[0][2],(K[1][0]*x+K[1][1]*y)/z+K[1][2]));depth.append(z)
    buf=array('d',[math.inf])*(h*w);work=0;degenerate=0
    for face in faces:
        require(len(face)==3 and all(type(i) is int and 0<=i<len(vertices) for i in face),'raster_face')
        i,j,k=face;a,b,c=uv[i],uv[j],uv[k]
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:degenerate+=1;continue
        left=max(0,math.ceil(min(a[0],b[0],c[0])));right=min(w-1,math.floor(max(a[0],b[0],c[0])))
        top=max(0,math.ceil(min(a[1],b[1],c[1])));bottom=min(h-1,math.floor(max(a[1],b[1],c[1])))
        if left>right or top>bottom:continue
        work+=(right-left+1)*(bottom-top+1);require(work<=work_limit,'raster_work_bound')
        az,bz,cz=1/depth[i],1/depth[j],1/depth[k]
        for y in range(top,bottom+1):
            for x in range(left,right+1):
                aa=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
                bb=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;cc=1-aa-bb
                if min(aa,bb,cc)<-1e-9:continue
                inv=aa*az+bb*bz+cc*cz
                if inv>0:
                    z=1/inv;at=y*w+x
                    if z<buf[at]:buf[at]=z
    return buf,dict(faces=len(faces),projected_degenerate=degenerate,bounding_box_pixel_tests=work)

def partition(hand,object_depth,tolerance):
    require(len(hand)==len(object_depth) and 0<len(hand)<=512*512 and math.isfinite(tolerance) and tolerance>0,'depth_partition_input')
    out={k:bytearray(len(hand)) for k in ['hand','object','overlap','hand_front','object_front','near','visible_hand']}
    for i,(h,o) in enumerate(zip(hand,object_depth)):
        require((math.isfinite(h) and h>0 or h==math.inf) and (math.isfinite(o) and o>0 or o==math.inf),'depth_values')
        H=h!=math.inf;O=o!=math.inf;out['hand'][i]=H;out['object'][i]=O
        if H and O:
            out['overlap'][i]=1
            key='near' if abs(h-o)<=tolerance else 'hand_front' if h<o else 'object_front';out[key][i]=1
        out['visible_hand'][i]=H and not out['object_front'][i]
    return out

def scores(pred,mask):
    require(len(pred)==len(mask),'mask_shape')
    intersection=sum(bool(p) and bool(m) for p,m in zip(pred,mask));union=sum(bool(p) or bool(m) for p,m in zip(pred,mask))
    count=sum(bool(m) for m in mask)
    return dict(intersection=intersection,predicted_pixels=sum(bool(p) for p in pred),mask_pixels=count,
                iou=intersection/union if union else 0.,mask_coverage=intersection/count if count else 0.,accuracy_verified=False)

def paint(rgb,layers):
    require(len(rgb)==512*512*3,'RGB_size');out=bytearray(rgb)
    for mask,color,alpha in layers:
        require(len(mask)==512*512 and 0<=alpha<=1,'paint_layer')
        for i,on in enumerate(mask):
            if on:
                for k in range(3):out[3*i+k]=int(out[3*i+k]*(1-alpha)+color[k]*alpha)
    return rgb_png(bytes(out))

def comparison_layers(pred,mask):
    both=bytes(bool(p) and bool(m) for p,m in zip(pred,mask))
    missing=bytes(bool(m) and not p for p,m in zip(pred,mask))
    extra=bytes(bool(p) and not m for p,m in zip(pred,mask))
    return [(both,(66,210,142),.65),(missing,(56,132,255),.65),(extra,(255,150,48),.65)]

def review_html(report,images):
    encoded={k:base64.b64encode(v).decode() for k,v in images.items()}
    data=json.dumps(dict(report=report,images=encoded),allow_nan=False).replace('<','\\u003c')
    return ('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'">
<title>TraceHOI · Diagnostic scene review</title><style>
*{box-sizing:border-box}body{margin:0;background:#f1f4f7;color:#172531;font:16px system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:28px}h1{font-size:32px;margin:8px 0}p{line-height:1.55}small{color:#455565}.badge{color:#7b4a00;background:#ffedc4;padding:7px 12px;border-radius:6px;display:inline-block;font-weight:650}.controls,.metrics{display:flex;flex-wrap:wrap;gap:18px;margin:22px 0}.controls label{display:flex;flex-direction:column;gap:7px}select,button{font:inherit;padding:9px;border:1px solid #a1adba;border-radius:6px;background:white}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0;background:white;border:1px solid #ccd5df;border-radius:10px;overflow:hidden}figcaption{padding:13px 16px;font-weight:650;min-height:68px;display:flex;align-items:center}.stack{position:relative;aspect-ratio:1}.stack img{position:absolute;width:100%;height:100%;image-rendering:auto}img{display:block;width:100%}.metric{flex:1;min-width:155px;padding:16px;background:white;border:1px solid #ccd5df;border-radius:8px}.metric b{display:block;font-size:23px;margin-top:8px}.legend{padding:14px 18px;background:#e3ebf2;border-radius:8px;min-height:58px}table{width:100%;border-collapse:collapse;background:white;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #d4dce4}th{background:#e5ebf1}code{font-size:13px;overflow-wrap:anywhere}details{margin:20px 0}footer{margin-top:24px;border-top:1px solid #c5d0da;padding-top:18px}button{cursor:pointer}@media(max-width:720px){main{padding:16px}.grid{grid-template-columns:1fr}h1{font-size:26px}.table{overflow-x:auto}}
</style><main><span class="badge">Diagnostic only · no accepted placement</span><h1>TraceHOI scene review</h1>
<p>Compare four saved hand/object candidates under the same recorded camera. Changing the view does not select or accept a pipeline candidate.</p>
<div class="controls"><label>Viewing candidate<select id="candidate"></select></label><label>Review layer<select id="mode"><option value="overlay">Joint scene overlay</option><option value="hand_compare">Hand / provisional mask</option><option value="occlusion">Projected depth ordering</option><option value="object_compare">Object / provisional mask</option><option value="masks">Input support masks</option><option value="scene_rgb">Revised scene input</option></select></label><label>Layer opacity<input id="opacity" type="range" min="0" max="100" value="100"></label><label>Zoom<input id="zoom" type="range" min="1" max="3" step=".25" value="1"></label></div>
<div class="grid"><figure><figcaption>Original RGB crop</figcaption><div class="stack" style="overflow:hidden"><img id="original" alt="Original 512 by 512 RGB crop"></div></figure><figure><figcaption id="caption">Candidate overlay</figcaption><div class="stack" style="overflow:hidden"><img id="base" alt="Original crop under review layer"><img id="layer" alt="Diagnostic review layer"></div></figure></div>
<p class="legend" id="legend"></p><div class="metrics"><div class="metric">Conditional scale<b id="scale"></b><small>Unverified scene units</small></div><div class="metric">Visible hand / mask IoU<b id="iou"></b><small>Provisional mask, not ground truth</small></div><div class="metric">Unsigned surface gap<b id="gap"></b><small>Saved triangle audit; not contact proof</small></div></div>
<div class="table"><table><thead><tr><th>Candidate</th><th>Scale</th><th>Visible hand IoU</th><th>Collision evidence</th></tr></thead><tbody id="rows"></tbody></table></div>
<p id="blockers"></p><details><summary>Camera, provenance and limits</summary><p>Scene coordinates are x-right, y-up, z-backward. Camera coordinates are x-right, y-down, z-forward. Meshes already contain their transforms; the reader supplies identity model matrices. Rasterization uses integer pixel centers, two-sided triangles and perspective-correct depth. Surfaces behind the camera are rejected. The original masks, geometry and candidates are unchanged.</p><p>Colors show projected ordering, not signed penetration depth. Scale sensitivity is not a confidence interval. Mask accuracy, scene scale, geometric accuracy and physical contact remain unresolved. The minimum-scale branch has recorded transverse crossings; the refined branch remains unaccepted despite numerical separation.</p><code id="binding"></code></details>
<button id="download">Download diagnostic JSON</button><footer><small>Self-contained offline report. No network access, model execution, or acceptance action.</small></footer></main>
<script>const D=DATA;const byId=id=>document.getElementById(id);const image=name=>'data:image/png;base64,'+D.images[name];
const labels={primary:'Primary',minimum_scale:'Minimum scale',maximum_scale:'Maximum scale',minimum_scale_refined:'Minimum scale · refined'};
const legends={overlay:'Teal: projected object. Orange: visible hand. Red: hand surface behind the object. All geometry is diagnostic.',hand_compare:'Green: visible hand and provisional hand-only mask agree. Blue: mask only. Orange: rendered hand only. Ambiguous hand/object pixels are excluded from the reference mask.',occlusion:'Red: object is in front at overlapping pixels. Yellow: hand is in front. Gray: depths are within the numerical tolerance. Tinted silhouettes show context; this is not a collision test.',object_compare:'Green: object and provisional object-only mask agree. Blue: mask only. Orange: rendered object only.',masks:'Orange: hand-only support. Teal: object-only support. Magenta: ambiguous overlap, excluded from both fitting supports.',scene_rgb:'Exact revised RGB image used by the fresh MoGe scene observation. This is separate from the original image.'};
for(const c of D.report.candidates){let o=document.createElement('option');o.value=c.id;o.textContent=labels[c.id];byId('candidate').append(o);let tr=document.createElement('tr');for(const value of [labels[c.id],c.conditional_scale.toFixed(6),c.visible_hand_mask.iou.toFixed(3),c.collision_gate.replaceAll('_',' ')]){let td=document.createElement('td');td.textContent=value;tr.append(td)}byId('rows').append(tr)}
byId('original').src=byId('base').src=image('original_rgb.png');byId('binding').textContent='Case '+D.report.case_id+' | manifest SHA-256 '+D.report.manifest_binding.sha256;
function update(){let id=byId('candidate').value,mode=byId('mode').value,c=D.report.candidates.find(c=>c.id===id);let name=['masks','object_compare','scene_rgb'].includes(mode)?mode+'.png':id+'_'+mode+'.png';byId('layer').src=image(name);byId('layer').style.opacity=byId('opacity').value/100;byId('caption').textContent=labels[id]+' · '+byId('mode').selectedOptions[0].textContent;byId('legend').textContent=legends[mode];byId('scale').textContent=c.conditional_scale.toFixed(6);byId('iou').textContent=c.visible_hand_mask.iou.toFixed(3);byId('gap').textContent=c.unsigned_surface_gap.toPrecision(5);byId('blockers').textContent='Unresolved: '+c.blockers.map(x=>x.replaceAll('_',' ')).join('; ')+'.';for(const name of ['original','base','layer']){byId(name).style.transform='scale('+byId('zoom').value+')';byId(name).style.transformOrigin='76% 55%'}}
for(const id of ['candidate','mode','opacity','zoom'])byId(id).addEventListener('input',update);update();
byId('download').onclick=()=>{let a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(D.report,null,2)],{type:'application/json'}));a.href=url;a.download='scene_visual_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
</script></html>'''.replace('DATA',data)).encode()

def build_review(manifest_path,expected_sha256,case_id,reader):
    manifest,data=reader.inspect_bundle(manifest_path,expected_sha256,case_id)
    channels,rgb=decode_png(data['original_rgb']);require(channels==3,'RGB_required')
    hand_mask=decode_pgm(data['hand_mask']);object_mask=decode_pgm(data['object_mask']);overlap=decode_pgm(data['overlap_mask'])
    ov,of=reader.mesh(data['object']);object_depth,object_raster=surface_depth(ov,of,manifest['camera_K'])
    assembly=reader.parse(data['assembly']);tolerance=assembly['depth_order_tolerance']
    images={'original_rgb.png':data['original_rgb'],'scene_rgb.png':data['scene_rgb'],
            'masks.png':paint(rgb,[(object_mask,(42,170,196),.55),(hand_mask,(255,150,48),.55),(overlap,(224,60,215),.8)])}
    object_silhouette=bytes(z!=math.inf for z in object_depth)
    images['object_compare.png']=paint(rgb,comparison_layers(object_silhouette,object_mask))
    rows=[]
    for c in manifest['candidates']:
        hand_v,hand_f=reader.mesh(data[c['hand_asset']]);hand_depth,raster=surface_depth(hand_v,hand_f,manifest['camera_K'])
        p=partition(hand_depth,object_depth,tolerance)
        images[c['id']+'_overlay.png']=paint(rgb,[(p['object'],(42,170,196),.35),(p['visible_hand'],(255,150,48),.6),(p['object_front'],(244,55,70),.9)])
        images[c['id']+'_hand_compare.png']=paint(rgb,comparison_layers(p['visible_hand'],hand_mask))
        images[c['id']+'_occlusion.png']=paint(rgb,[(p['object'],(42,170,196),.15),(p['hand'],(255,150,48),.2),(p['object_front'],(244,55,70),1.),(p['hand_front'],(255,220,40),1.),(p['near'],(170,170,170),1.)])
        rows.append(dict(id=c['id'],conditional_scale=c['conditional_scale'],accepted=False,pipeline_admissible=False,
            collision_gate=c['collision_gate'],unsigned_surface_gap=c['unsigned_surface_gap'],blockers=c['blockers'],
            hand_mask=scores(p['hand'],hand_mask),visible_hand_mask=scores(p['visible_hand'],hand_mask),
            occlusion_counts={k:sum(v) for k,v in p.items()},raster=raster,hand_binding=reader.binding(data[c['hand_asset']])))
    report=dict(schema='tracehoi.SceneVisualReview.v1',case_id=case_id,manifest_binding=reader.binding(reader.regular(manifest_path,1024**2)),
        frame=manifest['scene_frame'],units=manifest['units'],camera_K=manifest['camera_K'],image_size=[512,512],
        source_bindings={k:reader.binding(v) for k,v in data.items()},object_raster=object_raster,
        object_mask=scores(object_silhouette,object_mask),ambiguous_overlap_pixels=sum(bool(v) for v in overlap),
        depth_order_tolerance=tolerance,candidates=rows,selected_candidate=None,accepted_scale=None,
        placement_ready=False,full_parent_acceptance=False,physical_contact_verified=False,scale_identified=False,mask_review_required=True,
        model_calls=0,source_geometry_modified=False,mask_modified=False,
        limitations=['Provisional masks are not independent ground truth.','Raster overlap and depth ordering do not certify physical contact or penetration.',
                    'No candidate or conditional scale is accepted.','Geometry is already transformed; provenance matrices are never applied here.'])
    files=dict(images);files['review.json']=reader.encode(report);files['index.html']=review_html(report,images)
    return report,files
