import importlib.util,json,os,tempfile,types,unittest
from pathlib import Path
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module); return module
BIND=load('bind_under_test',os.environ['GPU_BIND_UNDER_TEST'])
PROBE=load('probe_under_test',os.environ['CUDA_PROBE_UNDER_TEST'])
class FakeCuda:
    def __init__(self,available,count): self.available=available; self.count=count
    def is_available(self): return self.available
    def device_count(self): return self.count
    def get_device_name(self,index): return 'Mock GPU '+str(index)
class BindingAndProbeTest(unittest.TestCase):
    def fixture(self,root):
        path=root/'in.json'; path.write_text(json.dumps({'stages':[
          {'name':'a','kwargs':{'runner_args':['conda','foho','cmd','/tmp',{}]},'env':{}},
          {'name':'b','kwargs':{'runner_args':['conda','foho','cmd','/tmp',{}]},'env':{}}]})); return path
    def test_selected_stage_bound_in_worker_and_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.fixture(root); out=root/'out.json'; receipt=root/'receipt.json'
            packet=BIND.bind(source,out,receipt,['a'],'0'); manifest=json.loads(out.read_text())
            self.assertEqual(packet['decision'],'foundation_manifest_GPU_binding_closed')
            self.assertEqual(manifest['stages'][0]['env']['CUDA_VISIBLE_DEVICES'],'0')
            self.assertEqual(manifest['stages'][0]['kwargs']['runner_args'][4]['CUDA_VISIBLE_DEVICES'],'0')
            self.assertNotIn('CUDA_VISIBLE_DEVICES',manifest['stages'][1]['env'])
    def test_missing_stage_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.fixture(root)
            packet=BIND.bind(source,root/'out.json',root/'receipt.json',['missing'],'0')
            self.assertEqual(packet['decision'],'review_foundation_manifest_GPU_binding')
    def test_probe_available(self):
        fake=types.SimpleNamespace(__version__='mock',version=types.SimpleNamespace(cuda='12.x'),cuda=FakeCuda(True,1))
        with tempfile.TemporaryDirectory() as directory:
            packet=PROBE.write(Path(directory)/'probe.json',fake)
            self.assertEqual(packet['decision'],'foundation_CUDA_probe_available')
    def test_probe_unavailable_is_review(self):
        fake=types.SimpleNamespace(__version__='mock',version=types.SimpleNamespace(cuda='12.x'),cuda=FakeCuda(False,0))
        self.assertEqual(PROBE.collect(fake)['decision'],'review_foundation_CUDA_probe')
if __name__=='__main__': unittest.main(verbosity=2)
