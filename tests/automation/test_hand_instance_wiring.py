import ast, importlib.util, os, unittest
from pathlib import Path
def load(path):
    spec=importlib.util.spec_from_file_location("candidate_case_runner",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
class HandInstanceWiringTests(unittest.TestCase):
    def test_candidate_runtime_uses_resolved_instance(self):
        text=Path(os.environ["CASE_RUNNER_SOURCE"]).read_text()
        tree=ast.parse(text)
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
        names=[node.func.id for node in calls if isinstance(node.func,ast.Name)]
        self.assertIn("resolve_hand_instance",names)
        self.assertNotIn("select_hand_instance",names)
        runtime=[node for node in calls if isinstance(node.func,ast.Name) and node.func.id=="runtime_config"]
        self.assertEqual(len(runtime),1)
        owned=[kw for kw in runtime[0].keywords if kw.arg=="hand_instance"]
        self.assertEqual(len(owned),1)
        self.assertEqual(ast.unparse(owned[0].value),"hand_resolution['resolved_hand_instance']")
        module=load(os.environ["CASE_RUNNER_SOURCE"])
        got=module.resolve_hand_instance({"gate_b":{"hand_instance":"ambiguous"},"gate_d0":{"active_hand":"right_upper"}})
        self.assertEqual(got["resolved_hand_instance"],"upper_image_hand")
    def test_downstream_transport_surfaces(self):
        expected={
          os.environ["FOUNDATION_MANIFEST_SOURCE"]:["raw_config['HAND_INSTANCE']"],
          os.environ["GET_HUNYUAN_INPUT_SOURCE"]:["hand_instance=args.hand_instance"],
          os.environ["SEGMENT_HOI_SOURCE"]:["select_hand_index","only hand"]}
        for path,needles in expected.items():
            text=Path(path).read_text()
            for needle in needles: self.assertIn(needle,text,msg=path+":"+needle)
if __name__=="__main__": unittest.main(verbosity=2)
