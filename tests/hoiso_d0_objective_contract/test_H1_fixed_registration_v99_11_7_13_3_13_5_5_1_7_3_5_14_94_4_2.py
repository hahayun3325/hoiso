import hashlib,json,os
from pathlib import Path
import numpy as np
import torch
import trimesh
from foho.guidance.h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import register_hshape_vertices

def mesh(path):
    item=trimesh.load(path,process=False)
    if isinstance(item,trimesh.Scene):
        item=trimesh.util.concatenate(tuple(item.geometry.values()))
    return np.asarray(item.vertices,dtype=np.float64),np.asarray(item.faces,dtype=np.int64)

out=Path(os.environ['CPU_TEST19442']); errors=[]
hshape_path=Path(os.environ['RECOVERED_HSHAPE'])
accepted_path=Path(os.environ['ACCEPTED_CPU_HAND'])
transform_path=Path(os.environ['ACCEPTED_T_H2M'])
missing=[str(p) for p in (hshape_path,accepted_path,transform_path) if not p.is_file()]
try:
    hshape,hfaces=mesh(hshape_path); accepted,afaces=mesh(accepted_path)
    T_np=np.load(transform_path).astype(np.float64)
    value=torch.tensor(hshape,dtype=torch.float64,requires_grad=True)
    T=torch.tensor(T_np,dtype=torch.float64)
    registered=register_hshape_vertices(value,T)
    registered.square().mean().backward()
    once=registered.detach().numpy()
    twice=register_hshape_vertices(registered.detach(),T).numpy()
    raw_rmse=float(np.sqrt(np.mean((hshape-accepted)**2)))
    once_rmse=float(np.sqrt(np.mean((once-accepted)**2)))
    twice_rmse=float(np.sqrt(np.mean((twice-accepted)**2)))
    checks={'shape_and_faces_equal':hshape.shape==accepted.shape and np.array_equal(hfaces,afaces),
            'once_reproduces_accepted_CPU_hand':once_rmse<1e-5,
            'omission_rejected':raw_rmse>100*max(once_rmse,1e-12),
            'double_application_rejected':twice_rmse>100*max(once_rmse,1e-12),
            'registration_gradient_finite_nonzero':value.grad is not None and
                bool(torch.isfinite(value.grad).all()) and float(value.grad.abs().max())>0}
    failed=[k for k,v in checks.items() if not v]
    payload={'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_2_fixed_registration_CPU_closed'
                         if not missing and not failed else
                         'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_2_recheck_fixed_registration_CPU'),
             'rmse':{'raw':raw_rmse,'once':once_rmse,'twice':twice_rmse},
             'checks':checks,'failed':failed,'missing':missing,'errors':errors,
             'GPU_used':False,'optimizer_updates':0}
    if not out.exists(): out.write_text(json.dumps(payload,indent=2)+'\n')
except Exception as exc:
    errors.append(f'{type(exc).__name__}:{exc}')
print(json.dumps(json.loads(out.read_text()) if out.is_file() else
 {'decision':'hold_before_fixed_registration_CPU','missing':missing,'errors':errors}))
