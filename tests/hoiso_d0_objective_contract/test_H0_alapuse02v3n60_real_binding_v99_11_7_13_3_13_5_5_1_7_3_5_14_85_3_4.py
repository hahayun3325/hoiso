import argparse
import ast
import json
import tempfile
from pathlib import Path

import torch

from foho.guidance.h0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4 import create_callback
from foho.guidance.h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9 import H0DiagnosticComplete


class Mesh:
    def __init__(self,vertices):
        self.vertices=vertices
        self.faces=torch.tensor([[0,1,2]],dtype=torch.long)
    def verts_packed(self): return self.vertices
    def faces_packed(self): return self.faces


class Cameras:
    R=torch.eye(3).unsqueeze(0)
    T=torch.zeros(1,3)
    def get_world_to_view_transform(self): return self
    def transform_points(self,points): return points
    def transform_points_screen(self,points,image_size=None):
        result=points.clone(); result[...,0:2]=result[...,0:2]+3.0; return result


class Fragments:
    def __init__(self,dtype):
        self.pix_to_face=torch.zeros((1,8,8,1),dtype=torch.long)
        self.bary_coords=torch.zeros((1,8,8,1,3),dtype=dtype)
        self.bary_coords[...,0]=1.0


class Rasterizer:
    def __init__(self,dtype): self.cameras=Cameras(); self.dtype=dtype
    def __call__(self,mesh): return Fragments(self.dtype)


class Renderer:
    def __init__(self,dtype): self.rasterizer=Rasterizer(dtype)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--receipt',required=True)
    args=parser.parse_args()
    receipt=Path(args.receipt)
    failed=[]; errors=[]; checks={}
    try:
        dtype=torch.float64
        rotation=torch.tensor([1.0,0.1,0.02,0.0],dtype=dtype)
        translation=torch.tensor([0.1,-0.1,0.05],dtype=dtype)
        scale=torch.tensor([1.0],dtype=dtype)
        object_vertices=torch.tensor([[0.,0.,-2.],[1.,0.,-2.],[0.,1.,-2.]],dtype=dtype)
        resources={
            'phase_config_path':None,
            'hook_module':None,
            'zorder_module':None,
            'pad_ids':torch.tensor([0,1],dtype=torch.long),
            'object_depth':torch.full((8,8),2.0,dtype=dtype),
            'object_valid':torch.ones((8,8),dtype=torch.bool),
            'r04':torch.zeros((8,8),dtype=torch.bool),
            'object_vertices':object_vertices,
            'object_faces':torch.tensor([[0,1,2]],dtype=torch.long),
            'object_diagonal':torch.tensor(1.5,dtype=dtype),
            'artifact_hashes':{'fake':'CPU'},
        }
        resources['r04'][3,3]=True
        from foho.guidance import h0_complete_hook_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_1 as hook_module
        import importlib.util
        zpath=Path('/home/fredcui/Projects/FollowMyHold/tools/hoiso_d0_objective_contract/dense_valid_zorder.py')
        spec=importlib.util.spec_from_file_location('_test_zorder',zpath)
        zmodule=importlib.util.module_from_spec(spec); spec.loader.exec_module(zmodule)
        policy=json.loads(Path('/home/fredcui/Projects/FollowMyHold/config/optimization/H0_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4.json').read_text())
        resources['hook_module']=hook_module; resources['zorder_module']=zmodule; resources['policy']=policy

        base=torch.tensor([[0.,0.,-3.],[1.,0.,-3.],[0.,1.,-3.]],dtype=dtype)
        def compute_base_loss(step=0):
            offset=torch.stack((rotation[1],rotation[2],translation[2]))
            mesh=Mesh(base+translation+offset)
            loss=rotation.pow(2).mean()+translation.pow(2).mean()
            return loss,{'transformed_hand_mesh':mesh}
        context={
            'owner':'CPU_fake_Phase1','parameters':{
                'global_hand_rotation':rotation,
                'global_hand_translation':translation},
            'frozen':{'global_hand_scale':scale,'mano_mesh_moge':Mesh(base),
                      'scale_obj':torch.ones(1,dtype=dtype),
                      'trans_obj':torch.zeros(3,dtype=dtype),
                      'rotation_obj':torch.tensor([1.,0.,0.,0.],dtype=dtype)},
            'compute_base_loss':compute_base_loss,
            'rendering':{'renderer':Renderer(dtype),'image_size':(8,8)},
            'metadata':{'outer_step':0,'legacy_updates':0},
        }
        before={name:value.detach().clone() for name,value in context['parameters'].items()}
        flags={name:value.requires_grad for name,value in context['parameters'].items()}
        with tempfile.TemporaryDirectory() as tmp:
            callback=create_callback('backward-only',tmp,resources_override=resources)
            bound=callback.bind_live_context(context)
            hooks=bound['hooks']
            swapped=False
            try: hooks['build_optimizer']([translation,rotation])
            except RuntimeError: swapped=True
            outcome={}
            try: callback(bound)
            except H0DiagnosticComplete as complete: outcome=complete.outcome
            result=outcome.get('result') or {}
            checks={
                'exact_ten_hooks':set(hooks)=={'build_optimizer','capture','compute_loss','frozen_state','gate_pass','object_vertices','rasterize_object','restore','save_checkpoint','snapshot'},
                'swapped_order_rejected':swapped,
                'backward_only_zero_updates':result.get('updates_completed')==0,
                'exact_gradient_owners':set(result.get('gradient_stats',{}))=={'global_hand_rotation','global_hand_translation'},
                'Rt_gradients_finite_nonzero':all(float(row.get('norm',0))>0 for row in result.get('gradient_stats',{}).values()),
                'parameters_restored':all(torch.equal(context['parameters'][name],value) for name,value in before.items()),
                'flags_restored':all(context['parameters'][name].requires_grad==value for name,value in flags.items()),
                'fixed_raster_once':result.get('metrics',{}).get('raster_calls')==1,
                'metric_depth_active':result.get('metrics',{}).get('metric_hand_depth_active') is True,
                'contact_active':result.get('metrics',{}).get('D0_contact_active') is True,
            }

        pipeline=Path('/home/fredcui/Projects/FollowMyHold/third_party_patches/hy3dgen/shapegen/pipelines.py')
        caller=Path('/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run.py')
        p_tree=ast.parse(pipeline.read_text()); c_tree=ast.parse(caller.read_text())
        checks['pipeline_binder_call_present']='bind_live_context' in pipeline.read_text()
        checks['caller_explicit_callback_forwarding']='h0_live_callback=h0_live_callback' in caller.read_text()
        checks['sources_parse']=p_tree is not None and c_tree is not None
        failed=[name for name,value in checks.items() if not value]
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    payload={'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_13_real_H0_binding_CPU_closed'
                         if not failed and not errors and not receipt.exists() else
                         'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_13_recheck_real_H0_binding_CPU'),
             'checks':checks,'failed':failed,'errors':errors,
             'GPU_used':False,'optimizer_updates':0}
    if not receipt.exists():
        receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload))


if __name__=='__main__':
    main()
