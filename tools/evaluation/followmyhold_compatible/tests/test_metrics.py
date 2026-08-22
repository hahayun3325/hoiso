import numpy as np, trimesh
from metrics import object_metrics, similarity_icp, umeyama_similarity

def test_identical_object_is_perfect():
    mesh=trimesh.creation.box(extents=(0.2,0.1,0.05))
    m=object_metrics(mesh,mesh,count=30000,seed=7,unit_to_m=1.0)
    assert m['CD_cm2'] < 0.02
    assert m['F5'] > 0.99 and m['F10'] > 0.99

def test_umeyama_recovers_known_similarity():
    rng=np.random.default_rng(5); src=rng.normal(size=(4000,3))
    angle=0.25; r=np.array([[np.cos(angle),-np.sin(angle),0],
                           [np.sin(angle), np.cos(angle),0],[0,0,1]])
    dst=(1.3*(r@src.T)).T+np.array([0.1,-0.2,0.05])
    s,rr,t=umeyama_similarity(src,dst)
    aligned=(s*(rr@src.T)).T+t
    assert np.mean(np.linalg.norm(aligned-dst,axis=1)) < 1e-5

def test_icp_identity_is_stable():
    rng=np.random.default_rng(8); points=rng.normal(size=(4000,3))
    s,r,t=similarity_icp(points,points,max_iterations=20)
    aligned=(s*(r@points.T)).T+t
    assert np.mean(np.linalg.norm(aligned-points,axis=1)) < 1e-7

def test_icp_large_similarity_unordered_surface():
    rng=np.random.default_rng(20260821)
    src=rng.normal(size=(6000,3))*np.array([1.0,0.6,0.25])
    src[:1800]+=np.array([1.8,-0.4,0.3])
    angle=0.20
    r=np.array([[np.cos(angle),-np.sin(angle),0.0],
                [np.sin(angle), np.cos(angle),0.0],
                [0.0,0.0,1.0]])
    dst=(0.08*(r@src.T)).T+np.array([3.0,-2.0,1.0])
    rng.shuffle(dst)
    s,rr,t=similarity_icp(src,dst,max_iterations=75)
    aligned=(s*(rr@src.T)).T+t
    from scipy.spatial import cKDTree
    mean_distance=float(np.mean(cKDTree(dst).query(aligned,k=1)[0]))
    assert mean_distance < 1e-3
    assert abs(s-0.08) < 5e-3

