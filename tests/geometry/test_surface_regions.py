import copy,importlib.util,json,math,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('surface_regions');mp=load('adaptive_surface_map')
def leaves(paths,face=0,state='within_bound'):
 return [dict(face_index=face,path=p,area=4.**(-len(p)),state=state) for p in paths]
def graph(faces,ls,n=4):return m.adjacency(faces,ls,n,mp.partition)[0]
class Regions(unittest.TestCase):
 def test_root_has_no_internal_edges(self):self.assertEqual(graph([[0,1,2]],leaves([''])),[])
 def test_split_triangle_three_internal_edges(self):self.assertEqual(graph([[0,1,2]],leaves(list('0123'))),[(0,3),(1,3),(2,3)])
 def test_corner_only_not_connected(self):self.assertNotIn((0,1),graph([[0,1,2]],leaves(list('0123'))))
 def test_shared_root_edges(self):self.assertEqual(graph([[0,1,2],[1,0,3]],leaves([''])+leaves([''],1)),[(0,1)])
 def test_coarse_fine_shared_edge(self):
  e=graph([[0,1,2],[1,0,3]],leaves([''])+leaves(list('0123'),1));self.assertEqual([x for x in e if x[0]==0],[(0,1),(0,2)])
 def test_same_orientation_shared_edge(self):
  e=graph([[0,1,2],[0,1,3]],leaves([''])+leaves(list('0123'),1));self.assertEqual([x for x in e if x[0]==0],[(0,1),(0,2)])
 def test_cyclic_face_order(self):
  e=graph([[0,1,2],[3,1,0]],leaves([''])+leaves(list('0123'),1));self.assertEqual([x for x in e if x[0]==0],[(0,2),(0,3)])
 def test_depth_three_to_root(self):
  paths=[a+b+c for a in '0123' for b in '0123' for c in '0123'];ls=leaves([''])+leaves(paths,1)
  e=graph([[0,1,2],[1,0,3]],ls);self.assertEqual(sum(a==0 for a,b in e),8);self.assertEqual(len(m.components(range(65),e)),1)
 def test_distinct_mesh_indices_not_welded(self):self.assertEqual(graph([[0,1,2],[3,4,5]],leaves([''])+leaves([''],1),6),[])
 def test_shared_vertex_only_not_connected(self):self.assertEqual(graph([[0,1,2],[0,3,4]],leaves([''])+leaves([''],1),5),[])
 def test_nonmanifold_rejected(self):self.assertRaisesRegex(ValueError,'nonmanifold',graph,[[0,1,2],[1,0,3],[0,1,4]],sum((leaves([''],i) for i in range(3)),[]),5)
 def test_duplicate_face_rejected(self):self.assertRaisesRegex(ValueError,'duplicate_face',graph,[[0,1,2],[2,0,1]],leaves([''])+leaves([''],1))
 def test_repeated_vertex_rejected(self):self.assertRaisesRegex(ValueError,'face_indices',graph,[[0,0,2]],leaves(['']))
 def test_invalid_vertex_rejected(self):self.assertRaisesRegex(ValueError,'face_indices',graph,[[0,1,9]],leaves(['']))
 def test_duplicate_cell_rejected(self):self.assertRaisesRegex(ValueError,'duplicate_cell',graph,[[0,1,2]],leaves(['','']))
 def test_missing_partition_rejected(self):self.assertRaisesRegex(ValueError,'incomplete_partition',graph,[[0,1,2]],leaves(['0','1','2']))
 def test_invalid_path_rejected(self):self.assertRaisesRegex(ValueError,'cell_path',m.bary_triangle,'0000')
 def test_exact_grid_sums(self):
  for p in ['','0','12','333','201']:
   for v in m.bary_triangle(p):self.assertEqual(sum(v),8);self.assertTrue(all(type(x) is int and x>=0 for x in v))
 def test_uncertain_bridge_joins_possible_not_cores(self):
  ls=leaves(['0','1','2','3']);ls[3]['state']='unresolved';r=m.regions(ls,graph([[0,1,2]],ls));self.assertEqual(len(r['core_components']),3);self.assertEqual(len(r['possible_regions']),1);self.assertEqual(r['possible_regions'][0]['core_ids'],[0,1,2])
 def test_outside_bridge_excluded(self):
  ls=leaves(['0','1','2','3']);ls[3]['state']='outside_bound';r=m.regions(ls,graph([[0,1,2]],ls));self.assertEqual(len(r['possible_regions']),3)
 def test_zero_area_bridge_excluded(self):
  ls=leaves(['0','1','2','3']);ls[3]['area']=0;r=m.regions(ls,graph([[0,1,2]],ls));self.assertEqual(len(r['possible_regions']),3);self.assertEqual(r['region_index'][3],-1)
 def test_unresolved_only_region(self):
  r=m.regions(leaves([''],state='unresolved'),[]);self.assertEqual(r['core_components'],[]);self.assertEqual(r['area_lower'],0);self.assertEqual(r['area_upper'],1)
 def test_outside_only_no_regions(self):self.assertEqual(m.regions(leaves([''],state='outside_bound'),[])['possible_regions'],[])
 def test_area_conservation(self):
  ls=leaves(list('0123'));ls[0]['state']='outside_bound';ls[1]['state']='unresolved';r=m.regions(ls,graph([[0,1,2]],ls));self.assertEqual((r['area_lower'],r['area_upper'],r['total_area']),(.5,.75,1.))
 def test_negative_area_rejected(self):
  ls=leaves(['']);ls[0]['area']=-1;self.assertRaisesRegex(ValueError,'leaf_state_area',m.regions,ls,[])
 def test_nan_area_rejected(self):
  ls=leaves(['']);ls[0]['area']=math.nan;self.assertRaisesRegex(ValueError,'leaf_state_area',m.regions,ls,[])
 def test_unknown_state_rejected(self):self.assertRaisesRegex(ValueError,'leaf_state_area',m.regions,leaves([''],state='contact'),[])
 def test_source_unchanged_and_deterministic(self):
  ls=leaves(list('0123'));saved=copy.deepcopy(ls);e=graph([[0,1,2]],ls);self.assertEqual(m.regions(ls,e),m.regions(ls,list(reversed(e))));self.assertEqual(ls,saved)
 def test_boundary_edge_count(self):self.assertEqual(m.adjacency([[0,1,2]],leaves(['']),3,mp.partition)[1]['boundary_edges'],3)
 def test_placement_build_refused(self):self.assertRaisesRegex(ValueError,'purpose_required',m.build,*([None]*11),purpose='placement')
 def test_placement_verify_refused(self):self.assertRaisesRegex(ValueError,'purpose_required',m.verify,None,None,purpose='placement')
 def test_html_escaping_links_and_controls(self):
  raw=m.html({'case_id':'</script><img src=x>'},b'rgb');self.assertNotIn(b'</script><img',raw);self.assertIn(b'\\u003c/script',raw);self.assertTrue(set(re.findall(r'href="([^"]+)"',m.TEMPLATE))<=m.FILES);self.assertIn('id="downloadRegion"',m.TEMPLATE)
if __name__=='__main__':unittest.main()
