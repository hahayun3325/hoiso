import importlib.util, os, sys, types, unittest
from contextlib import contextmanager
from pathlib import Path

def load_adapter():
    path=Path(os.environ['ADAPTER_UNDER_TEST'])
    spec=importlib.util.spec_from_file_location('adapter_under_test',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
@contextmanager
def fake_runner(function):
    foho=types.ModuleType('foho'); foho.__path__=[]
    utils=types.ModuleType('foho.utils'); utils.__path__=[]
    runner=types.ModuleType('foho.utils.runner'); runner.run_in_conda=function
    foho.utils=utils; utils.runner=runner
    names=('foho','foho.utils','foho.utils.runner'); saved={name:sys.modules.get(name) for name in names}
    sys.modules.update({'foho':foho,'foho.utils':utils,'foho.utils.runner':runner})
    try: yield
    finally:
        for name,value in saved.items():
            if value is None: sys.modules.pop(name,None)
            else: sys.modules[name]=value
class AdapterTest(unittest.TestCase):
    def test_exact_forwarding(self):
        adapter=load_adapter(); seen={}
        def call(*args,**kwargs): seen.update(args=args,kwargs=kwargs)
        with fake_runner(call):
            adapter.run(runner_args=['conda.sh','env-a',['python','-m','owner'],'/tmp',{}])
        self.assertEqual(seen['args'],('conda.sh','env-a',['python','-m','owner'],'/tmp',{}))
        self.assertEqual(seen['kwargs'],{})
    def test_keyword_forwarding(self):
        adapter=load_adapter(); seen={}
        with fake_runner(lambda *args,**kwargs: seen.update(args=args,kwargs=kwargs)):
            adapter.run(runner_args=[],runner_kwargs={'env_name':'env-b'})
        self.assertEqual(seen['kwargs'],{'env_name':'env-b'})
    def test_nonzero_is_error(self):
        adapter=load_adapter()
        with fake_runner(lambda *args,**kwargs: 7):
            with self.assertRaisesRegex(RuntimeError,'nonzero status: 7'):
                adapter.run(runner_args=[])
    def test_rejects_untyped_values(self):
        adapter=load_adapter()
        with self.assertRaises(TypeError): adapter.run(runner_args=())
        with self.assertRaises(TypeError): adapter.run(runner_args=[],runner_kwargs=[])
if __name__=='__main__': unittest.main()
