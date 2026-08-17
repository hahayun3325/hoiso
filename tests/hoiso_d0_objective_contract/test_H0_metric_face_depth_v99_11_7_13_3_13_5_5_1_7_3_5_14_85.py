import importlib.util
import json
import os
from pathlib import Path
import torch

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

target=Path(os.environ['METRIC_TEST_RECEIPT85']); existing=[str(target)] if target.exists() else []; failed=[]; errors=[]; checks={}
try:
    owner=load(os.environ['METRIC_HELPER85'],'h0_metric_face_depth_1485')
    translation_z=torch.tensor(0.25,dtype=torch.float64,requires_grad=True)
    base=torch.tensor([2.0,2.0,2.0],dtype=torch.float64)
    vertex_depth=base+translation_z
    faces=torch.tensor([[0,1,2]],dtype=torch.long)
    pix=torch.tensor([[[[0],[-1]]]],dtype=torch.long)
    bary=torch.tensor([[[[[0.2,0.3,0.5]],[[0.3,0.3,0.4]]]]],dtype=torch.float64)
    depth,valid=owner.interpolate_metric_face_depth(pix,bary,faces,vertex_depth)
    loss=depth[valid].sum(); loss.backward()
    checks={'shape_preserved':tuple(depth.shape)==(1,1,2),'valid_only_first_pixel':valid.tolist()==[[[True,False]]],'metric_depth_preserved':torch.allclose(depth[valid],torch.tensor([2.25],dtype=torch.float64)),'invalid_depth_zero':float(depth[~valid].abs().sum())==0.0,'translation_z_gradient_finite_nonzero':translation_z.grad is not None and torch.isfinite(translation_z.grad) and float(translation_z.grad)>0,'translation_z_gradient_exact':torch.allclose(translation_z.grad,torch.tensor(1.0,dtype=torch.float64))}
    failed.extend(name for name,value in checks.items() if not value)
except Exception as exc:
    errors.append(f'{type(exc).__name__}:{exc}')
payload={'decision':'pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_metric_face_depth_CPU_closed' if not failed and not errors else 'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_metric_face_depth_CPU','checks':checks,'failed':failed,'existing':existing,'errors':errors,'GPU_used':False,'optimizer_updates':0}
if not existing: target.write_text(json.dumps(payload,indent=2)+'\n')
print(f'decision={payload["decision"]} checks={checks} failed={failed} existing={existing} errors={errors}')
