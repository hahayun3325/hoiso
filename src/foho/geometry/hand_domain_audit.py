"""Diagnose provisional-mask coverage relative to an open hand-mesh boundary.

The image-plane partition is a heuristic model-domain diagnostic. It neither
edits the mask nor establishes an anatomical boundary, scale or placement.
"""
import math
from collections import Counter,defaultdict,deque

def require(ok,reason):
    if not ok:raise ValueError(reason)

def project(vertices,K):
    require(len(K)==3 and all(len(row)==3 for row in K) and K[2]==[0,0,1] and all(math.isfinite(x) for row in K for x in row),'camera')
    out=[]
    for v in vertices:
        require(len(v)==3 and all(math.isfinite(x) for x in v) and v[2]<-1e-8,'camera_plane')
        x,y,z=v[0],-v[1],-v[2]
        out.append(((K[0][0]*x+K[0][1]*y)/z+K[0][2],(K[1][0]*x+K[1][1]*y)/z+K[1][2]))
    return out

def boundary_loop(vertices,faces):
    require(3<=len(vertices)<=80000 and 1<=len(faces)<=160000,'mesh_bound')
    edges=Counter();seen=set()
    for f in faces:
        require(len(f)==3 and all(type(i)is int and 0<=i<len(vertices) for i in f) and len(set(f))==3,'triangle')
        key=tuple(sorted(f));require(key not in seen,'duplicate_face');seen.add(key)
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1
    require(max(edges.values())<=2,'nonmanifold_edge')
    border=[e for e,count in edges.items() if count==1];require(3<=len(border)<=256,'open_boundary_required')
    adjacent=defaultdict(list)
    for a,b in border:adjacent[a].append(b);adjacent[b].append(a)
    require(all(len(v)==2 for v in adjacent.values()),'boundary_degree')
    start=min(adjacent);loop=[start];prev=None;cur=start
    for _ in range(len(border)):
        choices=sorted(v for v in adjacent[cur] if v!=prev);nxt=choices[0]
        if nxt==start:break
        require(nxt not in loop,'boundary_cycle');loop.append(nxt);prev,cur=cur,nxt
    require(len(loop)==len(border) and start in adjacent[loop[-1]],'multiple_boundary_loops')
    return loop

def partition_domain(vertices,faces,K,width=512,height=512,margin_px=2.):
    require(type(width)is int and type(height)is int and 0<width<=512 and 0<height<=512,'image_shape')
    require(math.isfinite(margin_px) and 0<=margin_px<=16,'margin')
    loop=boundary_loop(vertices,faces);uv=project(vertices,K);points=[uv[i] for i in loop]
    center=[sum(p[j] for p in points)/len(points) for j in (0,1)]
    xx=sum((p[0]-center[0])**2 for p in points);yy=sum((p[1]-center[1])**2 for p in points)
    xy=sum((p[0]-center[0])*(p[1]-center[1]) for p in points)
    anisotropy=math.hypot(xx-yy,2*xy)/max(xx+yy,1e-30)
    require(xx+yy>1e-10 and anisotropy>.1,'boundary_projection_ambiguous')
    angle=.5*math.atan2(2*xy,xx-yy);normal=[-math.sin(angle),math.cos(angle)]
    centroid=[sum(p[j] for p in uv)/len(uv) for j in (0,1)]
    orient=sum((centroid[j]-center[j])*normal[j] for j in (0,1))
    require(abs(orient)>1e-6,'boundary_orientation_ambiguous')
    if orient<0:normal=[-x for x in normal]
    vals=[sum((p[j]-center[j])*normal[j] for j in (0,1)) for p in points]
    lo=min(vals)-margin_px;hi=max(vals)+margin_px
    require(sum((centroid[j]-center[j])*normal[j] for j in (0,1))>hi,'mesh_centroid_not_hand_side')
    masks={k:bytearray(width*height) for k in ['hand_side','boundary_band','beyond_boundary']}
    for y in range(height):
        for x in range(width):
            distance=(x-center[0])*normal[0]+(y-center[1])*normal[1]
            role='hand_side' if distance>hi else 'beyond_boundary' if distance<lo else 'boundary_band'
            masks[role][y*width+x]=1
    return masks,dict(method='projected_single_open_boundary_principal_axis_band',boundary_vertex_ids=loop,
        boundary_uv=[list(p) for p in points],center_uv=center,hand_facing_unit_normal=normal,
        signed_band_limits_px=[lo,hi],margin_px=margin_px,anisotropy=anisotropy,
        interpretation='Heuristic image-plane model domain; not an anatomical or ground-truth segmentation.')

def components(mask,width,height):
    require(len(mask)==width*height and 0<width<=512 and 0<height<=512,'component_shape')
    work=bytearray(bool(x) for x in mask);rows=[]
    for start in range(len(work)):
        if not work[start]:continue
        queue=deque([start]);work[start]=0;pixels=0;left=right=start%width;top=bottom=start//width
        while queue:
            at=queue.popleft();x,y=at%width,at//width;pixels+=1;left=min(left,x);right=max(right,x);top=min(top,y);bottom=max(bottom,y)
            for yy in range(max(0,y-1),min(height,y+2)):
                for xx in range(max(0,x-1),min(width,x+2)):
                    index=yy*width+xx
                    if work[index]:work[index]=0;queue.append(index)
        rows.append(dict(pixels=pixels,bbox_xyxy_inclusive=[left,top,right,bottom],first_pixel=start,touches_image_edge=left==0 or top==0 or right==width-1 or bottom==height-1))
    return sorted(rows,key=lambda r:(-r['pixels'],r['first_pixel']))

def count_regions(pred,mask,regions):
    require(len(pred)==len(mask) and set(regions)=={'hand_side','boundary_band','beyond_boundary'} and all(len(r)==len(mask) for r in regions.values()),'region_shape')
    require(all(sum(bool(r[i]) for r in regions.values())==1 for i in range(len(mask))),'region_partition')
    out={}
    for name,region in regions.items():
        overlap=sum(bool(p) and bool(m) and bool(r) for p,m,r in zip(pred,mask,region))
        pp=sum(bool(p) and bool(r) for p,r in zip(pred,region));mp=sum(bool(m) and bool(r) for m,r in zip(mask,region));union=pp+mp-overlap
        out[name]=dict(mask_pixels=mp,predicted_pixels=pp,intersection=overlap,mask_only=mp-overlap,prediction_only=pp-overlap,iou=overlap/union if union else None)
    return out

def build_audit(manifest_path,digest,case,reader,renderer):
    m,data=reader.inspect_bundle(manifest_path,digest,case)
    mask=renderer.decode_pgm(data['hand_mask']);_,rgb=renderer.decode_png(data['original_rgb'])
    ov,of=reader.mesh(data['object']);od,_=renderer.surface_depth(ov,of,m['camera_K'])
    tolerance=reader.parse(data['assembly'])['depth_order_tolerance'];rows=[];files={}
    for candidate in m['candidates']:
        v,f=reader.mesh(data[candidate['hand_asset']]);hd,_=renderer.surface_depth(v,f,m['camera_K'])
        visible=renderer.partition(hd,od,tolerance)['visible_hand']
        regions,boundary=partition_domain(v,f,m['camera_K'])
        metrics=count_regions(visible,mask,regions)
        missing=bytes(bool(a) and not b for a,b in zip(mask,visible));extra=bytes(bool(a) and not b for a,b in zip(visible,mask))
        only_hand=bytes(a and b for a,b in zip(missing,regions['hand_side']))
        near_mask=bytes(a and b for a,b in zip(mask,regions['boundary_band']))
        beyond_mask=bytes(a and b for a,b in zip(mask,regions['beyond_boundary']))
        matched=bytes(bool(a) and bool(b) for a,b in zip(mask,visible))
        image=renderer.paint(rgb,[(matched,(66,210,142),.65),(only_hand,(56,132,255),.75),
            (beyond_mask,(182,108,231),.7),(near_mask,(255,222,80),.7),(extra,(255,150,48),.75)])
        raw=bytearray(renderer.decode_png(image)[1])
        for px,py in boundary['boundary_uv']:
            x,y=round(px),round(py)
            for yy in range(max(0,y-1),min(512,y+2)):
                for xx in range(max(0,x-1),min(512,x+2)):raw[(yy*512+xx)*3:(yy*512+xx)*3+3]=b'\xff\xff\xff'
        files[candidate['id']+'_domain.png']=renderer.rgb_png(bytes(raw))
        comps=components(only_hand,512,512)
        rows.append(dict(id=candidate['id'],boundary=boundary,regions=metrics,full_visible_hand_mask=renderer.scores(visible,mask),
            mask_only_components=components(missing,512,512)[:16],hand_side_mask_only_components=comps[:16],hand_side_component_count=len(comps),
            accepted=False,placement_ready=False,mask_accuracy_verified=False,collision_gate=candidate['collision_gate']))
    report=dict(schema='tracehoi.HandModelDomainAudit.v1',case_id=case,manifest_binding=reader.binding(reader.regular(manifest_path,1024**2)),
        source_bindings={k:reader.binding(v) for k,v in data.items()},candidates=rows,model_calls=0,mask_modified=False,
        source_geometry_modified=False,scale_identified=False,selected_candidate=None,accepted_scale=None,placement_ready=False,
        full_parent_acceptance=False,physical_contact_verified=False,geometric_accuracy_verified=False,mask_review_required=True,
        limitations=['The sole open boundary is interpreted as the wrist for this saved HaMeR hand mesh.',
        'A projected boundary band is a heuristic model-domain partition, not ground truth or anatomical labeling.',
        'Region-restricted IoU must not replace the full-mask score or drive automatic candidate selection.',
        'The provisional mask and its ambiguous overlap exclusion are unchanged. No scene fitting or scale acceptance occurs.'])
    lines=['# Hand model-domain audit','', 'All candidates remain unaccepted. This report separates mask coverage beyond the open mesh boundary from residual mismatch on the hand-facing side. It does not edit or validate the mask.','',
        '| Candidate | Full visible-hand IoU | Hand-side IoU | Mask pixels beyond boundary | Hand-side mask-only pixels |', '|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append('| %s | %.4f | %.4f | %d | %d |'%(row['id'],row['full_visible_hand_mask']['iou'],row['regions']['hand_side']['iou'],row['regions']['beyond_boundary']['mask_pixels'],row['regions']['hand_side']['mask_only']))
    lines+=['','Green: projected hand and mask overlap. Blue: mask-only pixels on the hand-facing side. Purple: mask beyond the projected open-boundary band. Yellow: mask inside that band. Orange: projected hand outside the mask. White marks: actual projected boundary vertices.','',
        'The band contains all projected open-boundary vertices plus a fixed two-pixel margin. Its orientation comes from boundary principal axes and the projected mesh centroid. This is a diagnostic partition; it cannot certify forearm anatomy, mask accuracy, metric scale or contact.']
    for row in rows:lines+=['','## '+row['id'],'','!['+row['id']+']('+row['id']+'_domain.png)']
    files['audit.json']=reader.encode(report);files['audit.md']=('\n'.join(lines)+'\n').encode()
    return report,files
