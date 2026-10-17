"""Regression tests for scene ownership, coordinate semantics and diagnostic consumption."""
import copy,json,os,tempfile,unittest
from pathlib import Path
import scene_candidates as sc
from scene_candidate_fixture import build
ROOT=Path(__file__).resolve().parent
class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest,cls.files=build()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        for n,b in self.files.items():
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        self.path=self.root/'handoff/scene.json'
    def tearDown(self):self.tmp.cleanup()
    def digest(self):return sc.binding(self.path.read_bytes())['sha256']
    def call(self,cid='primary',purpose='diagnostic',case='alapuse02v3n60',digest=None):
        return sc.load_candidate(self.path,expected_sha256=digest or self.digest(),expected_case_id=case,candidate_id=cid,purpose=purpose)
    def edit(self,fn):
        m=sc.parse(self.path.read_bytes());fn(m);self.path.write_bytes(sc.encode(m))
    def test_all_candidates_have_exact_mesh_identity(self):
        for c in self.manifest['candidates']:
            r=self.call(c['id']);self.assertEqual(sc.binding(r['hand_mesh_bytes']),{k:self.manifest['resources'][c['hand_asset']][k] for k in ['bytes','sha256']})
            self.assertEqual(r['hand_model_matrix'],sc.IDENTITY);self.assertFalse(r['accepted'])
    def test_all_placement_requests_blocked(self):
        for cid in sc.IDS:
            with self.assertRaisesRegex(ValueError,'placement_blocked:'):self.call(cid,'placement')
    def test_crossing_branch_remains_visible_with_blocker(self):
        r=self.call('minimum_scale');self.assertIn('transverse_mesh_crossing',r['diagnostics']['blockers'])
    def test_refined_branch_does_not_inherit_crossing_flag(self):
        r=self.call('minimum_scale_refined');self.assertNotIn('transverse_mesh_crossing',r['diagnostics']['blockers']);self.assertFalse(r['diagnostics']['pipeline_admissible'])
    def test_wrong_case_rejected(self):
        with self.assertRaisesRegex(ValueError,'manifest_identity'):self.call(case='other_case')
    def test_unknown_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown_candidate'):self.call('unknown')
    def test_explicit_purpose_required(self):
        with self.assertRaisesRegex(ValueError,'explicit_purpose_required'):self.call(purpose='auto')
    def test_digest_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'manifest_binding'):self.call(digest='0'*64)
    def test_missing_digest_rejected(self):
        with self.assertRaisesRegex(ValueError,'expected_manifest_digest'):sc.inspect_bundle(self.path,None,'alapuse02v3n60')
    def test_asset_change_rejected(self):
        p=self.root/'handoff/assets/hand_primary.ply';p.write_bytes(p.read_bytes()[:-1]+b'x')
        with self.assertRaisesRegex(ValueError,'resource_binding'):self.call()
    def test_missing_asset_rejected(self):
        (self.root/'handoff/assets/hand_primary.ply').unlink()
        with self.assertRaises(FileNotFoundError):self.call()
    def test_symlink_resource_rejected(self):
        p=self.root/'handoff/assets/hand_primary.ply';b=p.read_bytes();p.unlink();(self.root/'elsewhere.ply').write_bytes(b);p.symlink_to(self.root/'elsewhere.ply')
        with self.assertRaisesRegex(ValueError,'symlink_resource'):self.call()
    def test_path_traversal_rejected_even_if_manifest_rebound(self):
        self.edit(lambda m:m['resources']['object'].update(path='../outside.ply'))
        with self.assertRaisesRegex(ValueError,'resource_path'):self.call()
    def test_duplicate_resource_path_rejected(self):
        self.edit(lambda m:m['resources']['hand_primary'].update(path=m['resources']['object']['path']))
        with self.assertRaisesRegex(ValueError,'duplicate_resource_path'):self.call()
    def test_double_transform_instruction_rejected(self):
        self.edit(lambda m:m.update(mesh_model_matrix=m['candidates'][0]['source_to_scene_provenance_only']))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_wrong_camera_axis_rejected(self):
        self.edit(lambda m:m.update(scene_to_camera=sc.IDENTITY))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_changed_principal_point_rejected(self):
        self.edit(lambda m:m['camera_K'][0].__setitem__(2,256))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_candidate_selection_not_inferred(self):
        self.edit(lambda m:m.update(selected_candidate='minimum_scale_refined',placement_ready=True))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_blocker_removal_rejected(self):
        self.edit(lambda m:m['candidates'][1].update(blockers=[]))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_changed_units_rejected(self):
        self.edit(lambda m:m.update(units='verified_metres'))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_wrong_hand_mesh_assignment_rejected(self):
        self.edit(lambda m:m['candidates'][0].update(hand_asset='hand_minimum_scale'))
        with self.assertRaisesRegex(ValueError,'scene_contract'):self.call()
    def test_evidence_case_mismatch_rejected(self):
        p=self.root/'handoff/evidence/refinement.json';r=sc.parse(p.read_bytes());r['case_id']='another';p.write_bytes(sc.encode(r))
        self.edit(lambda m:m['resources']['refinement'].update(sc.binding(p.read_bytes())))
        with self.assertRaisesRegex(ValueError,'case_or_hand_mismatch'):self.call()
    def test_json_nonfinite_rejected(self):
        self.path.write_bytes(b'{"schema":NaN}')
        with self.assertRaisesRegex(ValueError,'nonfinite_json'):self.call()
    def test_duplicate_json_field_rejected(self):
        self.path.write_bytes(b'{"schema":1,"schema":2}')
        with self.assertRaisesRegex(ValueError,'duplicate_json_key'):self.call()
    def test_camera_projection_uses_documented_axes(self):
        self.assertEqual(sc.project_scene_point([1,2,-4],[[100,0,10],[0,100,20],[0,0,1]]),[35,-30])
        with self.assertRaisesRegex(ValueError,'point_behind_camera'):sc.project_scene_point([0,0,1],[[1,0,0],[0,1,0],[0,0,1]])
    def test_returned_bytes_survive_subsequent_file_change(self):
        r=self.call();saved=r['hand_mesh_bytes'];(self.root/'handoff/assets/hand_primary.ply').write_bytes(b'changed')
        self.assertEqual(r['hand_mesh_bytes'],saved);self.assertIsInstance(saved,bytes)
    def test_caller_mutation_does_not_change_later_frame(self):
        r=self.call();r['scene_to_camera'][1][1]=1;r['hand_model_matrix'][0][0]=99
        later=self.call();self.assertEqual(later['scene_to_camera'][1][1],-1);self.assertEqual(later['hand_model_matrix'],sc.IDENTITY)
if __name__=='__main__':unittest.main()

