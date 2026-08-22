from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree

def load_mesh(path: str | Path) -> trimesh.Trimesh:
    m=trimesh.load_mesh(path, process=False)
    if isinstance(m,trimesh.Scene):
        m=trimesh.util.concatenate(tuple(g for g in m.geometry.values()))
    if not isinstance(m,trimesh.Trimesh) or len(m.vertices)==0 or len(m.faces)==0:
        raise ValueError(f'invalid_mesh:{path}')
    return m

def sample_surface(mesh: trimesh.Trimesh, count: int, seed: int) -> np.ndarray:
    state=np.random.get_state(); np.random.seed(seed)
    try: pts,_=trimesh.sample.sample_surface(mesh,count)
    finally: np.random.set_state(state)
    return np.asarray(pts,dtype=np.float64)

def umeyama_similarity(src: np.ndarray, dst: np.ndarray):
    if src.shape!=dst.shape or src.ndim!=2 or src.shape[1]!=3:
        raise ValueError('similarity_shape')
    ms,md=src.mean(0),dst.mean(0); xs,xd=src-ms,dst-md
    cov=(xd.T@xs)/len(src)
    u,d,vt=np.linalg.svd(cov)
    sign=np.ones(3)
    if np.linalg.det(u@vt)<0: sign[-1]=-1
    r=u@np.diag(sign)@vt
    var=float((xs*xs).sum()/len(src))
    if var<=1e-18: raise ValueError('degenerate_similarity')
    scale=float((d*sign).sum()/var)
    t=md-scale*(r@ms)
    return scale,r,t

def similarity_icp(pred_hand: np.ndarray, gt_hand: np.ndarray,
                   max_iterations: int=75, tolerance: float=1e-9):
    src=np.asarray(pred_hand,dtype=np.float64)
    dst=np.asarray(gt_hand,dtype=np.float64)
    if src.ndim!=2 or dst.ndim!=2 or src.shape[1:]!=(3,) or dst.shape[1:]!=(3,):
        raise ValueError('ICP_shape')
    if len(src)<4 or len(dst)<4 or not np.isfinite(src).all() or not np.isfinite(dst).all():
        raise ValueError('ICP_invalid_points')
    src_center,dst_center=src.mean(0),dst.mean(0)
    src_centered,dst_centered=src-src_center,dst-dst_center
    src_rms=math.sqrt(float(np.mean(np.sum(src_centered**2,axis=1))))
    dst_rms=math.sqrt(float(np.mean(np.sum(dst_centered**2,axis=1))))
    if src_rms<=1e-12 or dst_rms<=1e-12:
        raise ValueError('degenerate_similarity_input')
    initial_scale=dst_rms/src_rms
    _,src_basis=np.linalg.eigh((src_centered.T@src_centered)/len(src))
    _,dst_basis=np.linalg.eigh((dst_centered.T@dst_centered)/len(dst))
    src_basis=src_basis[:,::-1]
    dst_basis=dst_basis[:,::-1]
    rotations=[np.eye(3)]
    for sx in (-1.0,1.0):
        for sy in (-1.0,1.0):
            for sz in (-1.0,1.0):
                rotation=dst_basis@np.diag([sx,sy,sz])@src_basis.T
                if np.linalg.det(rotation)>0.0:
                    rotations.append(rotation)
    tree=cKDTree(dst)
    solutions=[]
    for rotation0 in rotations:
        scale=initial_scale
        rot=rotation0.copy()
        trans=dst_center-scale*(rot@src_center)
        cur=(scale*(rot@src.T)).T+trans
        previous=math.inf
        try:
            for _ in range(max_iterations):
                _,index=tree.query(cur,k=1)
                if np.unique(index).size<4:
                    raise ValueError('degenerate_similarity_correspondence')
                ds,dr,dt=umeyama_similarity(cur,dst[index])
                if not np.isfinite(ds) or ds<=1e-12 or not np.isfinite(dr).all() or not np.isfinite(dt).all():
                    raise ValueError('invalid_similarity_increment')
                cur=(ds*(dr@cur.T)).T+dt
                trans=ds*(dr@trans)+dt
                rot=dr@rot
                scale=ds*scale
                error=float(np.mean(tree.query(cur,k=1)[0]))
                if abs(previous-error)<=tolerance:
                    break
                previous=error
            solutions.append((error,scale,rot,trans))
        except ValueError:
            continue
    if not solutions:
        raise ValueError('similarity_ICP_no_valid_initialization')
    _,scale,rot,trans=min(solutions,key=lambda item:item[0])
    return scale,rot,trans


def transform_mesh(mesh: trimesh.Trimesh, scale: float, rot: np.ndarray,
                   trans: np.ndarray) -> trimesh.Trimesh:
    out=mesh.copy(); matrix=np.eye(4)
    matrix[:3,:3]=scale*rot; matrix[:3,3]=trans
    out.apply_transform(matrix); return out

def object_metrics(pred: trimesh.Trimesh, gt: trimesh.Trimesh, *, count=30000,
                   seed=20260819, unit_to_m=1.0):
    p=sample_surface(pred,count,seed)*unit_to_m
    g=sample_surface(gt,count,seed+1)*unit_to_m
    pg=cKDTree(g).query(p,k=1)[0]; gp=cKDTree(p).query(g,k=1)[0]
    cd_cm2=float((np.mean(pg**2)+np.mean(gp**2))*1e4)
    def fscore(threshold_m):
        precision=float(np.mean(pg<threshold_m)); recall=float(np.mean(gp<threshold_m))
        return 0.0 if precision+recall==0 else 2*precision*recall/(precision+recall)
    return {'CD_cm2':cd_cm2,'F5':fscore(0.005),'F10':fscore(0.010)}

def intersection_volume_cm3(hand: trimesh.Trimesh, obj: trimesh.Trimesh,
                            *, pitch_in_mesh_units: float, unit_to_m: float):
    def keys(mesh):
        points=np.asarray(mesh.voxelized(pitch_in_mesh_units).fill().points)
        return {tuple(v) for v in np.rint(points/pitch_in_mesh_units).astype(np.int64)}
    voxels=len(keys(hand)&keys(obj))
    pitch_m=pitch_in_mesh_units*unit_to_m
    return float(voxels*(pitch_m**3)*1e6)

def evaluate_case(case: dict) -> dict:
    unit_to_m={'m':1.0,'cm':0.01,'mm':0.001}[case['mesh_unit']]
    ph=load_mesh(case['pred_hand']); gh=load_mesh(case['gt_hand'])
    po=load_mesh(case['pred_object']); go=load_mesh(case['gt_object'])
    ph_pts=sample_surface(ph,30000,int(case.get('seed',20260819)))
    gh_pts=sample_surface(gh,30000,int(case.get('seed',20260819))+1)
    s,r,t=similarity_icp(ph_pts,gh_pts)
    aph=transform_mesh(ph,s,r,t); apo=transform_mesh(po,s,r,t)
    result={'case_id':case['case_id'],'success':True,
            'alignment_scale':s,'alignment_rotation':r.tolist(),'alignment_translation':t.tolist()}
    result.update(object_metrics(apo,go,seed=int(case.get('seed',20260819)),unit_to_m=unit_to_m))
    result['IV_cm3']=intersection_volume_cm3(
        aph,apo,pitch_in_mesh_units=0.005/unit_to_m,unit_to_m=unit_to_m)
    return result
