import importlib.util,json,os,pickle,tempfile,unittest
from pathlib import Path

def load():
    path=Path(os.environ['SELECTED_HAND_REGISTRATION_SOURCE'])
    spec=importlib.util.spec_from_file_location('selected_hand_registration_under_test',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class Contract(unittest.TestCase):
    def setUp(self): self.m=load()
    def inventory(self,path,files):
        rows=[]
        for item in files: rows.append({'path':str(item),'sha256':self.m.sha(item),'bytes':item.stat().st_size})
        path.write_text(json.dumps({'decision':'foundation_stage_artifact_inventory_closed',
          'output_roots':[{'files':rows}],'file_count':len(rows)})); return path
    def fixture(self,root):
        import numpy as np
        from PIL import Image
        crop=root/'case_cropped_hoi_0.png'; Image.new('RGB',(64,64),'white').save(crop)
        mask=root/'case_hand_mask.png'; mask.write_bytes(b'mask')
        owner=root/'case_selected_hand_owner.json'
        owner.write_text(json.dumps({'decision':'Q0_selected_detector_to_hand_mask_closed',
          'selected_hand_id':'hand-id','canonical_is_right':True,'crop_detector_box':[1,1,9,9],
          'artifacts':{'crop':{'path':str(crop),'sha256':self.m.sha(crop)},
          'hand_mask':{'path':str(mask),'sha256':self.m.sha(mask)}}}))
        preprocess=self.inventory(root/'preprocess.json',[crop,mask,owner])
        candidate=root/(crop.stem+'.npy')
        np.save(candidate,{'cam':np.asarray([[0.0,0.0,1.0]],dtype=float)},allow_pickle=True)
        howner=root/(crop.stem+'_selected_hamer_owner.json')
        howner.write_text(json.dumps({'decision':'selected_hand_HaMeR_candidate_closed','selected_hand_id':'hand-id'}))
        hamer=self.inventory(root/'hamer.json',[candidate,howner])
        h2m_file=root/'case_hoi_mesh.npy'; h2m_file.write_bytes(b'h2m')
        h2m=self.inventory(root/'h2m.json',[h2m_file])
        points=root/'points.exr'; points.write_bytes(b'points')
        moge=self.inventory(root/'moge.json',[points])
        return preprocess,hamer,h2m,moge,howner
    def test_exact_inventory_owned_identity_closes(self):
        with tempfile.TemporaryDirectory() as td:
            values=self.fixture(Path(td)); got=self.m.resolve_owners(
              preprocess_inventory=values[0],hamer_inventory=values[1],
              h2m_inventory=values[2],moge_inventory=values[3],case_id='case')
            self.assertEqual(got['selected_hand_id'],'hand-id'); self.assertEqual(got['selected_side'],'right')
    def test_changed_HaMeR_identity_stops(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); preprocess,hamer,h2m,moge,howner=self.fixture(root)
            packet=json.loads(howner.read_text()); packet['selected_hand_id']='other'
            howner.write_text(json.dumps(packet))
            hamer=self.inventory(root/'hamer2.json',[root/'case_cropped_hoi_0.npy',howner])
            with self.assertRaises(self.m.SelectedHandRegistrationError):
                self.m.resolve_owners(preprocess_inventory=preprocess,hamer_inventory=hamer,
                  h2m_inventory=h2m,moge_inventory=moge,case_id='case')
    def test_manifest_replaces_legacy_MANO(self):
        text=Path(os.environ['FOUNDATION_MANIFEST_SOURCE']).read_text()
        self.assertIn("'mano_registration','foho.automation.selected_hand_registration'",text)
        self.assertNotIn("'mano_registration','foho.alignment.mano'",text)
        for role in ('preprocess_inventory','hamer_inventory','h2m_inventory','moge_inventory'):
            self.assertIn("'"+role+"'",text)
    def test_front_runner_can_stop_before_recovery_and_Q2(self):
        text=Path(os.environ['CASE_RUNNER_SOURCE']).read_text()
        self.assertIn("run.add_argument('--stop-after-q1',action='store_true')",text)
        self.assertIn("'Q1_RECOVERY_PENDING'",text)
        self.assertIn('recovery_started=False',text)
    def test_mock_lifecycle_writes_owned_registered_mesh(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); preprocess,hamer,h2m,moge,_=self.fixture(root)
            module_root=root/'hamer'; mano_root=module_root/'_DATA/data/mano'; mano_root.mkdir(parents=True)
            faces=np.asarray([[i,i+1,i+2] for i in range(300)],dtype=np.int64)
            for side in ('RIGHT','LEFT'):
                with (mano_root/('MANO_'+side+'.pkl')).open('wb') as stream: pickle.dump({'f':faces},stream)
            policy=root/'policy.json'; policy.write_text(json.dumps({
              'packet_fields':{'camera_translation':'root/cam'},
              'global_max_final_reprojection_rmse_px':30.0,'positive_scale_bounds':[0.5,2.0],
              'translation_lower_xyz':[-1,-1,0.1],'translation_upper_xyz':[1,1,5],
              'metric_point_to_surface_weight':1.0,'metric_residual_clip':0.1,
              'metric_max_points':100,'metric_sample_seed':1,'minimum_visible_joints':4}))
            calls=[]
            def fake(arguments):
                calls.append(arguments)
                if '--target-out' in arguments:
                    target=Path(arguments[arguments.index('--target-out')+1])
                    report=Path(arguments[arguments.index('--report-out')+1])
                    config=json.loads(Path(arguments[arguments.index('--config')+1]).read_text())
                    side=config['handedness']
                    target.parent.mkdir(parents=True,exist_ok=True)
                    xy=np.stack((np.linspace(20,40,21),np.linspace(18,42,21)),axis=1)
                    np.savez_compressed(target,keypoints_xy_full_image_px_21x2=xy,
                      confidence_21=np.ones(21),visibility_21=np.ones(21,dtype=bool),
                      handedness=np.asarray(side),image_size_wh=np.asarray([64,64]))
                    report.write_text(json.dumps({'decision':'pass_v99_11_7_5_independent_full_image_vitpose_target',
                      'handedness':side}))
                else:
                    result=Path(arguments[arguments.index('--result-out')+1])
                    report=Path(arguments[arguments.index('--report-out')+1])
                    t=np.linspace(0,1,778); vertices=np.stack((0.09*t,0.08*np.sin(t*3.14),1+0.06*np.cos(t*3.14)),axis=1)
                    np.savez_compressed(result,aligned_vertices_camera_Nx3=vertices,
                      positive_depth_fraction=np.asarray(1.0))
                    report.write_text(json.dumps({'decision':'pass_v99_11_7_13_3_6_CPU_7DoF_global_hand_alignment_raw_result',
                      'full_image_reprojection_rmse_px':5.0}))
            output=root/'out'
            got=self.m.execute(preprocess_inventory=preprocess,hamer_inventory=hamer,
              h2m_inventory=h2m,moge_inventory=moge,vitpose_script=root/'vitpose.py',
              vitpose_module_root=module_root,solver_script=root/'solver.py',policy_template=policy,
              output_dir=output,case_id='case',device='cpu',launcher=fake)
            self.assertEqual(got['decision'],'selected_hand_registration_closed')
            self.assertEqual(got['selected_hand_id'],'hand-id'); self.assertEqual(len(calls),3)
            self.assertTrue(Path(got['registered_mesh']).is_file())
if __name__=='__main__': unittest.main(verbosity=2)
