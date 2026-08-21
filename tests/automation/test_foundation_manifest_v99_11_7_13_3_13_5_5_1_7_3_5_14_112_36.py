import importlib.util, json, os, unittest
from pathlib import Path

def load():
    path=Path(os.environ['FOUNDATION_MANIFEST_SOURCE'])
    spec=importlib.util.spec_from_file_location('manifest_under_test',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
class ManifestTest(unittest.TestCase):
    def test_real_owner_dry_run_and_continuity(self):
        module=load()
        manifest=module.build(os.environ['FOUNDATION_CONFIG'],
                              os.environ['FOUNDATION_MANIFEST_PATH'])
        names=[row['name'] for row in manifest['stages']]
        self.assertEqual(names,['get_hunyuan_input','inpaint','moge','hunyuan',
                                'hamer','h2m','mano_registration'])
        for row in manifest['stages']:
            command=row['kwargs']['runner_args'][2]
            self.assertNotIn('gemini_objname',command)
            self.assertNotIn('foho.guidance.run',command)
        for index,row in enumerate(manifest['stages'][1:],1):
            prior={item['path'] for stage in manifest['stages'][:index]
                   for item in stage['expected_outputs']}
            carried={item['path'] for item in row['inputs'] if 'inventory' in item['role']}
            self.assertTrue(carried); self.assertTrue(carried<=prior)
        from foho.automation.foundation_process_controller import run_manifest
        result=run_manifest(os.environ['FOUNDATION_MANIFEST_PATH'],
                            os.environ['FOUNDATION_DRY_RUN_ROOT'],dry_run=True)
        self.assertEqual(result['decision'],'foundation_process_controller_dry_run_closed')
        self.assertEqual(result['children_started'],0)
if __name__=='__main__': unittest.main(verbosity=2)
