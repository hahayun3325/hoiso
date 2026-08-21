import hashlib, importlib.util, json, os, tempfile, unittest
from pathlib import Path
from PIL import Image

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); item=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item); return item
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
class PanelTest(unittest.TestCase):
  def test_builds_eight_owned_cells(self):
    q1=module('q1_panel_test',os.environ['Q1_PANEL_SOURCE'])
    with tempfile.TemporaryDirectory() as raw:
      root=Path(raw); stages={}
      names={'get_hunyuan_input':['object_mask.png','hand_mask.png'],
       'inpaint':['inpaint.png'],'moge':['depth_vis.png'],'hunyuan':['object_mesh.ply'],
       'hamer':['hand_overlay.png'],'h2m':['h2m.json'],'mano_registration':['mano_mesh.ply']}
      for stage,items in names.items():
        out=root/stage; out.mkdir(); rows=[]
        for name in items:
          path=out/name
          if path.suffix=='.png': Image.new('RGB',(64,48),(30,80,120)).save(path)
          elif path.suffix=='.ply': path.write_text('ply\nformat ascii 1.0\nelement vertex 3\nproperty float x\nproperty float y\nproperty float z\nelement face 1\nproperty list uchar int vertex_indices\nend_header\n0 0 0\n1 0 0\n0 1 0\n3 0 1 2\n')
          else: path.write_text('{"matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}\n')
          rows.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
        inv=out/'stage_inventory.json'; inv.write_text(json.dumps({'schema':'tracehoi.FoundationStageArtifactInventory.v1',
          'output_roots':[{'root':str(out),'files':rows}],'file_count':len(rows),
          'decision':'foundation_stage_artifact_inventory_closed'}))
        stages[stage]=str(inv)
      crop=root/'crop.png'; Image.new('RGB',(64,48),'gray').save(crop)
      policy=root/'policy.json'; policy.write_text('{"jury":"Q1"}\n')
      cfg=root/'config.json'; cfg.write_text(json.dumps({'case_id':'alapuse02v3n60','model':'fixture',
        'reasoning_effort':'medium','max_output_tokens':1000,
        'accepted_crop':{'path':str(crop),'sha256':sha(crop)},
        'policy':{'path':str(policy),'sha256':sha(policy)},'inventories':stages}))
      panel=root/'panel.png'; manifest=root/'panel.json'
      result=q1.build(cfg,panel,manifest)
      self.assertEqual(result['decision'],'Q1_evidence_panel_closed')
      self.assertEqual(len(result['cells']),8); self.assertEqual(sha(panel),result['panel_sha256'])
if __name__=='__main__': unittest.main()
