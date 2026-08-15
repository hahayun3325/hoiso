from __future__ import annotations
import numpy as np

def rasterize_signed_pinhole(vertices, faces, camera, height, width):
    vertices=np.asarray(vertices,dtype=np.float64); faces=np.asarray(faces,dtype=np.int64)
    fx,fy,cx,cy=(float(camera[k]) for k in ("fx","fy","cx","cy"))
    depth=-vertices[:,2]
    projected=np.empty((len(vertices),2),dtype=np.float64)
    projected[:,0]=fx*vertices[:,0]/depth+cx
    projected[:,1]=fy*vertices[:,1]/depth+cy
    zbuf=np.full((height,width),np.inf,dtype=np.float64)
    face_id=np.full((height,width),-1,dtype=np.int64)
    for face_index,ids in enumerate(faces):
        d=depth[ids]
        if not np.isfinite(d).all() or np.any(d<=0): continue
        p=projected[ids]
        if not np.isfinite(p).all(): continue
        x0=max(0,int(np.floor(p[:,0].min()))); x1=min(width-1,int(np.ceil(p[:,0].max())))
        y0=max(0,int(np.floor(p[:,1].min()))); y1=min(height-1,int(np.ceil(p[:,1].max())))
        if x1<x0 or y1<y0: continue
        ax,ay=p[0]; bx,by=p[1]; cxp,cyp=p[2]
        den=(by-cyp)*(ax-cxp)+(cxp-bx)*(ay-cyp)
        if not np.isfinite(den) or abs(den)<1e-12: continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1]; px=xx+0.5; py=yy+0.5
        w0=((by-cyp)*(px-cxp)+(cxp-bx)*(py-cyp))/den
        w1=((cyp-ay)*(px-cxp)+(ax-cxp)*(py-cyp))/den; w2=1.0-w0-w1
        inside=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)
        inv_depth=w0/d[0]+w1/d[1]+w2/d[2]
        candidate=np.where(inside&(inv_depth>0),1.0/inv_depth,np.inf)
        local=zbuf[y0:y1+1,x0:x1+1]; update=candidate<local
        local[update]=candidate[update]; face_id[y0:y1+1,x0:x1+1][update]=face_index
    valid=np.isfinite(zbuf)&(face_id>=0)
    zbuf[~valid]=np.nan
    return {"depth":zbuf.astype(np.float32),"face_id":face_id.astype(np.int64),"valid":valid}
