"""Local loading, failure propagation and entrypoint routing without native libraries."""
import contextlib
import copy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]
def load(name, rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/'src/foho'/rel)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
local=load('local_loader_under_test','geometry/hunyuan_local.py')

class Tensor:
    def __init__(self,shape=(2,),value=3,dtype='half',device='cpu',finite=True):
        self.shape=shape;self.value=value;self.dtype=dtype;self.device=NS(type=device);self.finite=finite
class Truth:
    def __init__(self,value):self.value=value
    def all(self):return self
    def item(self):return self.value

class LocalTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.config={key:dict(target=target,params={})for key,target in local.TARGETS.items()}

    def fixture(self,mode='success'):
        events=[];weights={g+'.w':Tensor()for g in ['model','vae','conditioner']}
        if mode=='missing_group':del weights['conditioner.w']
        if mode=='extra_group':weights['extra.w']=Tensor()
        if mode=='shape':weights['model.w'].shape=(9,)
        if mode=='dtype':weights['model.w'].dtype='float'
        if mode=='device':weights['model.w'].device.type='cuda'
        if mode=='nonfinite':weights['model.w'].finite=False
        def load_file(path,device):
            self.assertEqual((path,device),('local-blob','cpu'));events.append('read');return weights
        class Model:
            def __init__(self,group):
                events.append('construct:'+group);self.group=group;self.values={'w':Tensor(dtype='float')}
                if mode=='constructor':raise RuntimeError('constructor failure')
            def state_dict(self):return self.values.copy()
            def load_state_dict(self,state,strict):
                self.values=copy.deepcopy(state);events.append(('strict',self.group,strict))
                return NS(missing_keys=['missing']if mode=='strict_missing'else[],unexpected_keys=['extra']if mode=='strict_extra'else[])
            def to(self,device,dtype):
                events.append(('convert',self.group,device,dtype))
                for v in self.values.values():
                    v.dtype=dtype;v.device.type='cuda'if mode=='converted_device'else device
                    if mode=='converted_value':v.value=99
            def eval(self):events.append('eval:'+self.group)
        class Pipeline:
            def __init__(self,**kwargs):
                self.parts=kwargs;events.append('assemble')
                if mode=='pipeline':raise RuntimeError('pipeline failure')
            def to(self,device):events.append(('move',device)) # Real API returns None.
        torch=NS(float16='half',no_grad=contextlib.nullcontext,isfinite=lambda t:Truth(t.finite),equal=lambda a,b:a.value==b.value and a.shape==b.shape)
        api=dict(torch=torch,load_file=load_file,pipeline=Pipeline,scheduler=lambda **kw:('scheduler',kw),image_processor=lambda **kw:('processor',kw),
                 **{g:(lambda group=g,**kw:Model(group))for g in ['model','vae','conditioner']})
        return api,events,weights

    def test_cpu_components_then_pipeline_without_gpu_move(self):
        api,events,weights=self.fixture();pipeline=local.assemble(self.config,'local-blob','cpu',api)
        self.assertEqual(set(pipeline.parts),{'model','vae','conditioner','scheduler','image_processor','device','dtype'})
        self.assertEqual(pipeline.parts['device'],'cpu');self.assertEqual(events[-1],'assemble');self.assertEqual(weights,{})
        self.assertEqual([x for x in events if isinstance(x,tuple)and x[0]=='strict'],[('strict',g,True)for g in ['model','vae','conditioner']])
        for group in ['model','vae','conditioner']:
            self.assertLess(events.index(('convert',group,'cpu','half')),events.index('assemble'))

    def test_device_move_keeps_pipeline_despite_none_return(self):
        api,events,_=self.fixture();pipeline=local.assemble(self.config,'local-blob','cuda:1',api)
        self.assertIsNotNone(pipeline);self.assertEqual(events[-2:],['assemble',('move','cuda:1')])

    def test_invalid_checkpoint_and_load_receipts_prevent_assembly(self):
        for mode in ['missing_group','extra_group','shape','dtype','device','nonfinite','constructor','strict_missing','strict_extra','converted_device','converted_value']:
            with self.subTest(mode=mode):
                api,events,weights=self.fixture(mode)
                with self.assertRaises((ValueError,RuntimeError)):local.assemble(self.config,'local-blob','cuda',api)
                self.assertNotIn('assemble',events);self.assertFalse(any(isinstance(x,tuple)and x[0]=='move'for x in events));self.assertEqual(weights,{})

    def test_pipeline_failure_propagates(self):
        api,events,weights=self.fixture('pipeline')
        with self.assertRaisesRegex(RuntimeError,'pipeline failure'):local.assemble(self.config,'local-blob','cuda',api)
        self.assertEqual(weights,{});self.assertEqual(events[-1],'assemble')

    def test_configuration_targets_cannot_select_arbitrary_code(self):
        for name in local.TARGETS:
            bad=copy.deepcopy(self.config);bad[name]['target']='arbitrary.module.Class'
            api,events,_=self.fixture()
            with self.assertRaises(ValueError):local.assemble(bad,'local-blob','cpu',api)
            self.assertEqual(events,[])

    def test_configuration_does_not_mutate_caller(self):
        self.config['model']['params']={'nested':{'values':[1,2]}}
        before=copy.deepcopy(self.config);api,_,_=self.fixture()
        local.assemble(self.config,'local-blob','cpu',api);self.assertEqual(self.config,before)

    def test_missing_local_inputs_fail_before_imports(self):
        for a,b in [(None,None),('config',None),(None,'weights'),('missing','missing')]:
            with self.assertRaises((ValueError,FileNotFoundError)):local.build_local_pipeline(a,b)

    def test_cache_symlink_and_extensionless_blob_are_supported(self):
        c=self.root/'config';w=self.root/'blob';c.write_text('config');w.write_bytes(b'safetensors fixture')
        alias=self.root/'model.safetensors';alias.symlink_to(w)
        self.assertEqual(local.local_inputs(c,alias),(str(c),str(w)))
        w.write_bytes(b'')
        with self.assertRaises(ValueError):local.local_inputs(c,w)
        w.unlink();w.mkdir()
        with self.assertRaises(ValueError):local.local_inputs(c,w)

    def test_wrapper_cli_environment_and_explicit_override(self):
        wrapper=load('hunyuan_cli_under_test','geometry/hunyuan.py')
        args=['hunyuan','--project_root','/repo','--image_dir','/images','--save_dir','/out','--device','cpu']
        with patch.dict(os.environ,{'FOHO_HUNYUAN_CONFIG':'/config','FOHO_HUNYUAN_CHECKPOINT':'/weights','FOHO_HUNYUAN_DEVICE':'cuda:1'}),patch.object(sys,'argv',args),patch.object(wrapper,'run')as run:
            wrapper.main();self.assertEqual(run.call_args.kwargs,dict(project_root='/repo',image_dir='/images',save_dir='/out',config_path='/config',checkpoint_path='/weights',device='cpu'))

    def test_half_config_refused_by_cli(self):
        wrapper=load('hunyuan_cli_invalid','geometry/hunyuan.py')
        with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['hunyuan','--project_root','/r','--image_dir','/i','--save_dir','/o','--config_path','/c']),patch.object(wrapper,'run')as run:
            with self.assertRaises(SystemExit):wrapper.main()
            run.assert_not_called()

    def test_pipeline_forwards_local_settings(self):
        fake_config=NS(PipelineConfig=object,load_config=Mock())
        with patch.dict(sys.modules,{'foho.configs':fake_config,'foho.utils.runner':NS(run_in_conda=Mock())}):
            main=load('main_local_under_test','main.py')
        cfg=NS(project_root='/repo',suppress_warnings=False,gemini_api_key='',hf_token='',hy3dgen_models='',foho_debug_dir='')
        env={'FOHO_HUNYUAN_CONFIG':'/local config','FOHO_HUNYUAN_CHECKPOINT':'/local weights','FOHO_HUNYUAN_DEVICE':'cuda:0'}
        with patch.dict(os.environ,env):
            got=main._env_with_paths(cfg)
        self.assertEqual({key:got[key]for key in env},env)

    def test_local_wrapper_uses_one_mesh_call_without_hub_loader(self):
        # Reuse the existing image/export fixtures to exercise the actual wrapper.
        spec=importlib.util.spec_from_file_location('handoff_fixture',ROOT/'tests/geometry/test_case_handoff.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fixture=module.HandoffTest();fixture.setUp()
        try:
            src=fixture.file('case_occ_obj.png');c=fixture.file('cfg');w=fixture.file('weights')
            stubs,images,calls,factory=fixture.hunyuan_stubs()
            with stubs,patch.dict(sys.modules,{'foho.geometry.hunyuan_local':local}),patch.object(local,'build_local_pipeline',return_value=factory.from_pretrained.return_value)as build:
                fixture.hunyuan._hunyuan_minimal_demo([src],str(fixture.root/'out'),config_path=str(c),checkpoint_path=str(w),device='cpu')
            build.assert_called_once_with(str(c),str(w),device='cpu');factory.from_pretrained.assert_not_called()
            self.assertEqual(len(calls),1);self.assertTrue((fixture.root/'out/case_hoi_mesh.ply').is_file())
        finally:fixture.doCleanups()

if __name__=='__main__':unittest.main()
