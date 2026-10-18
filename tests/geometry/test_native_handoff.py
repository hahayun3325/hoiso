import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('native_handoff',ROOT/'src/foho/geometry/native_handoff.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

SOURCE='''class Hunyuan3DDiTFlowMatchingPipeline_main:
    @torch.no_grad()
    def __call__(self, aligned_mano_mesh_path=None,
                 *, h0_live_callback=None, o0_live_callback=None, j0_live_callback=None, **kwargs,
                 ):
        device='cpu'
        scale_hand=torch.tensor([1.0])
        trans_hand=torch.tensor([0.0,0.0,0.0])
        rotation_hand=torch.tensor([1.0,0.0,0.0,0.0])
        mano_verts, mano_faces = load_ply(aligned_mano_mesh_path)
        mano_mesh=Mesh(mano_verts,mano_faces)
        T_h2m='legacy'
        mano_mesh_moge = transform_hunyuan2moge(mano_mesh, T_h2m)
        handopt_start_step=0
        _foho_f3_enabled=False
        phases=[]
        for i in range(4):
            if i>=handopt_start_step:
                with torch.enable_grad():
                    if _foho_f3_enabled and i == handopt_start_step:
                        phases.append('f3')
                    elif i == handopt_start_step:
                        phases.append('hand_init')
                    elif i == handopt_start_step + 1:
                        phases.append('object_init')
                    else:
                        phases.append('joint')
        return scale_hand.value, trans_hand.value, rotation_hand.value, phases, mano_mesh_moge
'''
HELPER='''def get_guidance_params(phase, noise_pred_obj, scale_hand, trans_hand, rotation_hand, device, *, phase1_hand_lrs, phase2_hand_lrs, noise_obj_lr1, noise_obj_lr2, obj_lrs, obj_2half_lrs, scale_obj, trans_obj, rotation_obj):
    values=[x.clone().detach().requires_grad_(True) for x in [noise_pred_obj,scale_hand,trans_hand,rotation_hand,scale_obj,trans_obj,rotation_obj]]
    groups=[{'params':[values[i]]} for i in [1,2,3,4,5,6,0]]
    return (groups,*values)
'''
class Tensor:
    def __init__(self,v):self.value=copy.deepcopy(v)
    def detach(self):return self
    def cpu(self):return self
    def tolist(self):return self.value
class Mesh:
    def __init__(self,v,f):self.v=v;self.f=f
    def verts_packed(self):return Tensor(self.v)
    def faces_packed(self):return Tensor(self.f)
class Context:
    def __enter__(self):return self
    def __exit__(self,*args):pass
class Torch:
    float32='float32'
    @staticmethod
    def tensor(v,**kwargs):return Tensor(v)
    @staticmethod
    def no_grad():return lambda f:f
    @staticmethod
    def enable_grad():return Context()

class NativeHandoff(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.folder=self.root/'packet';self.folder.mkdir()
        self.state=dict(scale=2.4,translation=[.4,-.1,-6.3],rotation_wxyz=[0.,1.,0.,0.])
        self.v=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]];self.f=[[0,1,2]]
        self.pins=patch.object(m,'BACKEND_PINS',(m.pin(SOURCE.encode())['sha256'],m.pin(HELPER.encode())['sha256']))
        self.pins.start();self.addCleanup(self.pins.stop)
        for n,b in zip(m.BACKEND_PATHS,[SOURCE.encode(),HELPER.encode()]):
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        (self.folder/'centered_state.json').write_bytes(m.encode(self.state))
        (self.folder/'native_hand.ply').write_bytes(b'native')
        self.reader=types.SimpleNamespace(regular=lambda p,cap:Path(p).read_bytes(),mesh=lambda raw:(self.v,self.f))
        helper_ns={};exec(compile(HELPER,str(self.root/m.BACKEND_PATHS[1]),'exec'),helper_ns)
        self.transforms=[];self.loaded=[]
        def load(path):self.loaded.append(path);return self.v,self.f
        def transform(mesh,T):self.transforms.append(T);return 'legacy_mesh'
        self.ns=dict(torch=Torch,Mesh=Mesh,load_ply=load,transform_hunyuan2moge=transform,get_guidance_params=helper_ns['get_guidance_params'])
        exec(compile(SOURCE,str(self.root/m.BACKEND_PATHS[0]),'exec'),self.ns)
        self.pipeline=self.ns[m.CLASS]()
        self.verifier=patch.object(m,'verify',return_value={});self.verifier.start();self.addCleanup(self.verifier.stop)
        self.env=patch.dict(os.environ,{},clear=True);self.env.start();self.addCleanup(self.env.stop)
    def bind(self):return m.bind_pipeline(self.pipeline,self.folder,'receipt',self.folder,'source',self.root,self.reader,None)
    def test_opt_in_consumes_saved_scale_rotation_translation(self):
        out=self.bind()();self.assertEqual(out[:3],([2.4],[.4,-.1,-6.3],[0.,1.,0.,0.]));self.assertEqual(self.transforms,[])
    def test_opt_in_skips_both_initialization_phases(self):self.assertEqual(self.bind()()[3],['joint','joint'])
    def test_original_class_remains_unchanged(self):
        call=type(self.pipeline).__call__;self.bind()();self.assertIs(type(self.pipeline).__call__,call)
        out=self.pipeline(aligned_mano_mesh_path='legacy.ply');self.assertEqual(out[3],['hand_init','object_init','joint','joint']);self.assertEqual(out[-1],'legacy_mesh')
    def test_native_route_used(self):self.bind()();self.assertEqual(self.loaded,[str(self.folder/'native_hand.ply')])
    def test_tensor_mesh_changed_refused(self):
        hand=m._HandState('.',self.state,self.v,self.f)
        with self.assertRaisesRegex(ValueError,'runtime_native_mesh_changed'):hand.tensors(Mesh([[9,9,9]],self.f),Torch,'cpu')
    def test_face_order_changed_refused(self):
        hand=m._HandState('.',self.state,self.v,self.f)
        with self.assertRaisesRegex(ValueError,'runtime_native_mesh_changed'):hand.tensors(Mesh(self.v,[[2,1,0]]),Torch,'cpu')
    def test_hand_state_copies_input(self):
        hand=m._HandState('.',self.state,self.v,self.f);self.state['scale']=99
        self.assertEqual(hand.tensors(Mesh(self.v,self.f),Torch,'cpu')[0].value,[2.4])
    def test_positional_args_refused(self):
        with self.assertRaisesRegex(ValueError,'keyword_arguments'):self.bind()('hidden-path')
    def test_overriding_internal_state_refused(self):
        with self.assertRaisesRegex(ValueError,'internal_handoff'):self.bind()(_tracehoi_handoff={})
    def test_incompatible_hand_path_refused(self):
        with self.assertRaisesRegex(ValueError,'hand_path_conflict'):self.bind()(aligned_mano_mesh_path='baked.ply')
    def test_legacy_callback_refused(self):
        with self.assertRaisesRegex(ValueError,'callback_conflict'):self.bind()(h0_live_callback=lambda:None)
    def test_legacy_environment_refused(self):
        os.environ['FOHO_F3_ENABLED']='1'
        with self.assertRaisesRegex(ValueError,'environment_conflict'):self.bind()()
    def test_private_globals(self):
        before=set(self.ns);self.bind()();self.assertEqual(set(self.ns),before);self.assertNotIn('_tracehoi_handoff',self.ns)
    def test_packet_rechecked_before_call(self):
        with patch.object(m,'verify') as v:
            call=self.bind();self.assertEqual(v.call_count,1);call();self.assertEqual(v.call_count,2)
    def test_changed_backend_refused(self):
        with self.assertRaisesRegex(ValueError,'backend_source_changed'):m.patch_source(SOURCE.encode()+b'\n')
    def test_changed_guidance_refused(self):
        with self.assertRaisesRegex(ValueError,'guidance_helper_changed'):m.source_checks(SOURCE.encode(),HELPER.encode()+b'\n')
    def test_missing_seam_refused(self):
        raw=SOURCE.replace('mano_mesh_moge = transform_hunyuan2moge(mano_mesh, T_h2m)','mano_mesh_moge = mano_mesh').encode()
        with patch.object(m,'BACKEND_PINS',(m.pin(raw)['sha256'],m.BACKEND_PINS[1])):
            with self.assertRaisesRegex(ValueError,'seam_changed'):m.patch_source(raw)
    def test_duplicate_seam_refused(self):
        raw=(SOURCE+'\n# mano_verts, mano_faces = load_ply(aligned_mano_mesh_path)\n').encode()
        with patch.object(m,'BACKEND_PINS',(m.pin(raw)['sha256'],m.BACKEND_PINS[1])):
            with self.assertRaisesRegex(ValueError,'seam_changed'):m.patch_source(raw)
    def test_actual_patch_is_valid_python(self):ast.parse(m.patch_source(SOURCE.encode()))
    def test_patch_default_argument_none(self):
        fn=m.backend_function(m.patch_source(SOURCE.encode()));i=[x.arg for x in fn.args.kwonlyargs].index('_tracehoi_handoff');self.assertIsNone(fn.args.kw_defaults[i].value)
    def test_cpu_probe_checks_state_and_parameter_groups(self):
        r=m.cpu_transition_probe(SOURCE.encode(),HELPER.encode(),self.state,self.v,self.f)
        self.assertTrue(r['joint_parameter_values_preserved']);self.assertEqual(r['joint_parameter_groups'],7);self.assertFalse(r['native_tensor_execution'])
    def test_probe_detects_joint_reset(self):
        helper=HELPER.replace('values=[x.clone()', 'scale_hand=type(scale_hand)([1.0])\n    values=[x.clone()')
        with patch.object(m,'BACKEND_PINS',(m.BACKEND_PINS[0],m.pin(helper.encode())['sha256'])):
            with self.assertRaisesRegex(ValueError,'joint_reset'):m.cpu_transition_probe(SOURCE.encode(),helper.encode(),self.state,self.v,self.f)
    def test_purpose_requires_native_handoff(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,None,None,None,purpose='placement')
    def test_runtime_origin_refused(self):
        self.pipeline=type('Other',(),{'__call__':lambda self:None})()
        with self.assertRaisesRegex(ValueError,'runtime_backend_origin'):self.bind()

if __name__=='__main__':unittest.main()
