import importlib.util, json, os, tempfile, unittest
from pathlib import Path

SOURCE=Path(os.environ['CONTROLLER_CANDIDATE'])
spec=importlib.util.spec_from_file_location('candidate_controller',SOURCE)
controller=importlib.util.module_from_spec(spec); spec.loader.exec_module(controller)

MOCK="""from pathlib import Path
def write(output_path,text='one'):
    path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
def copy(input_path,output_path):
    path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(Path(input_path).read_text()+'-two')
def fail(output_path):
    raise RuntimeError('intentional_mock_failure')
"""

class ControllerLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/'mock_stages.py').write_text(MOCK)
        self.out=self.root/'fresh'; self.run=self.root/'run'; self.manifest=self.root/'manifest.json'
    def tearDown(self): self.temp.cleanup()
    def stage(self,name,callable_name,kwargs,inputs,outputs):
        return {'name':name,'callable':'mock_stages:'+callable_name,'kwargs':kwargs,
                'inputs':inputs,'expected_outputs':outputs,
                'env':{'PYTHONPATH':str(self.root)}}
    def write_manifest(self,stages):
        self.manifest.write_text(json.dumps({'schema':'tracehoi.FreshFoundationManifest.v1',
          'case_id':'alapuse02v3n60','fresh_output_root':str(self.out),'stages':stages}))
    def two_stages(self):
        one=self.out/'one.txt'; two=self.out/'two.txt'
        return [self.stage('one','write',{'output_path':str(one),'text':'one'},[],
                    [{'role':'one','path':str(one)}]),
                self.stage('two','copy',{'input_path':str(one),'output_path':str(two)},
                    [{'role':'one','path':str(one)}],[{'role':'two','path':str(two)}])]
    def test_success_and_output_to_input_continuity(self):
        self.write_manifest(self.two_stages())
        result=controller.run_manifest(self.manifest,self.run)
        self.assertEqual(result['decision'],'foundation_process_controller_closed')
        self.assertEqual(result['children_started'],2)
        self.assertEqual((self.out/'two.txt').read_text(),'one-two')
    def test_restart_skips_hash_matching_stages(self):
        self.write_manifest(self.two_stages()); controller.run_manifest(self.manifest,self.run)
        result=controller.run_manifest(self.manifest,self.run)
        self.assertEqual(result['decision'],'foundation_process_controller_closed')
        self.assertEqual(result['children_started'],0)
        self.assertEqual([row['status'] for row in result['completed']],['resumed','resumed'])
    def test_failure_stops_before_next_stage(self):
        bad=self.out/'bad.txt'; later=self.out/'later.txt'
        stages=[self.stage('bad','fail',{'output_path':str(bad)},[],
                    [{'role':'bad','path':str(bad)}]),
                self.stage('later','write',{'output_path':str(later)},[],
                    [{'role':'later','path':str(later)}])]
        self.write_manifest(stages); result=controller.run_manifest(self.manifest,self.run)
        self.assertEqual(result['decision'],'review_foundation_process_controller')
        self.assertFalse(later.exists()); self.assertIn('intentional_mock_failure',result['errors'][0])
    def test_mutated_output_invalidates_resume_without_overwrite(self):
        self.write_manifest(self.two_stages()); controller.run_manifest(self.manifest,self.run)
        (self.out/'one.txt').write_text('mutated')
        result=controller.run_manifest(self.manifest,self.run)
        self.assertEqual(result['decision'],'review_foundation_process_controller')
        self.assertEqual(result['children_started'],0)
        self.assertIn('preexisting_unowned_output',result['errors'][0])
    def test_dry_run_starts_no_child_and_writes_no_stage_output(self):
        self.write_manifest(self.two_stages())
        result=controller.run_manifest(self.manifest,self.run,dry_run=True)
        self.assertEqual(result['decision'],'foundation_process_controller_dry_run_closed')
        self.assertEqual(result['children_started'],0); self.assertFalse((self.out/'one.txt').exists())

if __name__=='__main__': unittest.main(verbosity=2)
