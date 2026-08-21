import importlib.util,json,os,tempfile,unittest
from pathlib import Path

def load_module():
    path=Path(os.environ['CASE_RUNNER_SOURCE'])
    spec=importlib.util.spec_from_file_location('case_runner_under_test',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class CaseRunnerCPU(unittest.TestCase):
  def setUp(self): self.module=load_module()
  def test_plan_contains_single_bounded_jury_recovery(self):
    self.assertEqual(self.module.FLOW.count('Q1'),1)
    self.assertEqual(self.module.FLOW.count('Q2_terminal'),1)
    self.assertIn('READY_FOR_GATE_A',self.module.FLOW)
  def test_prompt_views_primary_and_recovery(self):
    with tempfile.TemporaryDirectory() as temp:
      root=Path(temp); image=root/'alapuse02v3n60.png'; image.write_bytes(b'image')
      cfg={'case_id':'alapuse02v3n60','image':{'path':str(image),
        'sha256':self.module.sha(image)},'prompt_policy':{
        'hand_segmentation':'only hand','recovery_object_single_label':'laptop'}}
      packet={'foundation_primary':{'category_compatibility':['articulated laptop'],
        'object_segmentation':['display','hinge','base'],'flux_inpainting':['open laptop']},
        'foundation_recovery':{'category_compatibility':['laptop'],
        'object_segmentation':['laptop'],'flux_inpainting':['open laptop']}}
      packet_path=root/'q0.json'; packet_path.write_text(json.dumps(packet))
      primary=self.module.prompt_views(packet_path,cfg,'primary',root/'primary')
      recovery=self.module.prompt_views(packet_path,cfg,'recovery',root/'recovery')
      self.assertIn('display, hinge, base',Path(primary['object']).read_text())
      rows=Path(recovery['object']).read_text()
      self.assertIn('laptop',rows); self.assertNotIn('display, hinge, base',rows)
      self.assertEqual(json.loads((root/'recovery/prompt_views.json').read_text())
                       ['hand_segmentation_prompt'],'only hand')
  def test_runtime_config_rewrites_all_owned_values(self):
    with tempfile.TemporaryDirectory() as temp:
      root=Path(temp); template=root/'template.env'; output=root/'out.env'; image=root/'i.png'
      image.write_bytes(b'i')
      template.write_text('IMAGE_PATH=old.png\nBASE_DIR=/old\nGEMINI_RESPONSES=a\n'
        'OBJECT_PROMPT_CSV=b\nFLUX_PROMPT_CSV=c\nOUT=/old/output\n')
      self.module.runtime_config(template,'/old','/new',image,
        {'category':'cat.csv','object':'obj.csv','flux':'flux.csv'},output)
      text=output.read_text(); self.assertNotIn('/old',text); self.assertIn('/new/output',text)
      self.assertIn('OBJECT_PROMPT_CSV=obj.csv',text)
  def test_decision_reads_typed_jury_packet(self):
    packet={'decoded':{'overall_decision':'RETRY_ONE_OWNER',
                       'retry_owner':'get_hunyuan_input'}}
    self.assertEqual(self.module.decision(packet),('RETRY_ONE_OWNER','get_hunyuan_input'))
  def test_state_is_restartable_and_atomic(self):
    with tempfile.TemporaryDirectory() as temp:
      root=Path(temp); self.module.state(root,'case','Q0_CLOSED',value=1)
      result=self.module.state(root,'case','Q1_CLOSED',value=2)
      self.assertEqual(result['stage'],'Q1_CLOSED')
      self.assertEqual([row['stage'] for row in result['transitions']],
                       ['Q0_CLOSED','Q1_CLOSED'])
if __name__=='__main__': unittest.main(verbosity=2)
