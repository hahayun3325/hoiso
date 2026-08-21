import ast, importlib.util, os, unittest
from pathlib import Path

def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ContractTest(unittest.TestCase):
    def test_runtime_uses_resolver(self):
        text=Path(os.environ["CASE_RUNNER_SOURCE"]).read_text()
        self.assertIn("resolve_hand_instance(load(packet))",text)
        self.assertNotIn("select_hand_instance(load(packet))",text)

    def test_single_case_preprocess_reraises(self):
        tree=ast.parse(Path(os.environ["GET_HUNYUAN_INPUT_SOURCE"]).read_text())
        run_fn=next(node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name=="run")
        guarded=0
        for node in ast.walk(run_fn):
            if isinstance(node,ast.If) and ast.unparse(node.test)=="image_path":
                if any(isinstance(child,ast.Raise) for statement in node.body for child in ast.walk(statement)):
                    guarded+=1
        self.assertGreaterEqual(guarded,2)

if __name__=="__main__": unittest.main()
