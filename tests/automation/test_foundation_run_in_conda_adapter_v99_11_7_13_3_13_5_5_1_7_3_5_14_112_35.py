import importlib.util, json, os, sys, tempfile, types, unittest
from contextlib import contextmanager
from pathlib import Path

def load():
    path=Path(os.environ['ADAPTER_UNDER_TEST'])
    spec=importlib.util.spec_from_file_location('adapter_under_test',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
@contextmanager
def fake(function):
    foho=types.ModuleType('foho'); foho.__path__=[]
    utils=types.ModuleType('foho.utils'); utils.__path__=[]
    runner=types.ModuleType('foho.utils.runner'); runner.run_in_conda=function
    saved={name:sys.modules.get(name) for name in ('foho','foho.utils','foho.utils.runner')}
    sys.modules.update({'foho':foho,'foho.utils':utils,'foho.utils.runner':runner})
    try: yield
    finally:
        for name,value in saved.items():
            if value is None: sys.modules.pop(name,None)
            else: sys.modules[name]=value
class AdapterInventoryTest(unittest.TestCase):
    def test_forward_and_inventory(self):
        adapter=load()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'out'; receipt=Path(temp)/'inventory.json'; seen={}
            def call(*args,**kwargs):
                seen.update(args=args,kwargs=kwargs); root.mkdir(); (root/'asset.bin').write_bytes(b'asset')
            with fake(call):
                adapter.run(runner_args=['conda.sh','foho','python3 -m owner','/tmp',{}],
                  output_roots=[str(root)],output_receipt=str(receipt))
            self.assertEqual(seen['args'][1],'foho')
            packet=json.loads(receipt.read_text())
            self.assertEqual(packet['decision'],'foundation_stage_artifact_inventory_closed')
            self.assertEqual(packet['file_count'],1)
    def test_empty_root_is_error_and_no_receipt(self):
        adapter=load()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'empty'; root.mkdir(); receipt=Path(temp)/'inventory.json'
            with fake(lambda *args,**kwargs:None):
                with self.assertRaisesRegex(RuntimeError,'empty output root'):
                    adapter.run(runner_args=[],output_roots=[str(root)],output_receipt=str(receipt))
            self.assertFalse(receipt.exists())
    def test_nonzero_is_error(self):
        adapter=load()
        with fake(lambda *args,**kwargs:7):
            with self.assertRaisesRegex(RuntimeError,'nonzero status'):
                adapter.run(runner_args=[])
    def test_type_guards(self):
        adapter=load()
        with self.assertRaises(TypeError): adapter.run(runner_args=())
        with self.assertRaises(TypeError): adapter.run(runner_args=[],output_roots='bad')
if __name__=='__main__': unittest.main(verbosity=2)
