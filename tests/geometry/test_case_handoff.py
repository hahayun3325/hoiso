"""Native-free regression tests for case ownership and geometry wrapper routing.

Run directly with Python: no torch, Pillow, numpy, models or network needed.
"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/foho'


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, SOURCE / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Array:
    shape = (2, 2, 3)
    def cpu(self): return self
    def numpy(self): return self
    def permute(self, *args): return self
    def astype(self, *args): return self
    def __truediv__(self, other): return self
    def __mul__(self, other): return self
    def __add__(self, other): return self
    def __and__(self, other): return self
    def __invert__(self): return self


class Image:
    def __init__(self, source): self.source, self.closed = Path(source), False
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def convert(self, mode):
        self.converted = Image(self.source)
        return self.converted
    def getdata(self): return [(255, 255, 255, 255), (0, 1, 2, 255)]
    def putdata(self, pixels): self.pixels = pixels
    def close(self): self.closed = True


class HandoffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.contract = load('contract_under_test', 'case_artifacts.py')
        config = types.ModuleType('foho.configs')
        config.third_party_root = lambda: '/unused/third_party'
        self.modules = patch.dict(sys.modules, {'foho.configs': config, 'foho.case_artifacts': self.contract})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.moge = load('moge_under_test', 'geometry/moge.py')
        self.hunyuan = load('hunyuan_under_test', 'geometry/hunyuan.py')
        self.h2m = load('h2m_under_test', 'alignment/h2m.py')

    def file(self, name, data=b'fixture'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_suffix_contract(self):
        for suffix in ('_occ_obj', '_cropped_hoi', '_cropped_hoi_0', '_cropped_hoi_1',
                       '_cropped_hoi_wo_bckg_0', '_cropped_hoi_wo_bckg_True', '_cropped_hoi_wo_bckg_False', ''):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.contract.image_case_id('hoi_case_07' + suffix + '.png'), 'hoi_case_07')
        self.assertEqual(self.contract.mesh_case_id('hoi_case_07_hoi_mesh.ply'), 'hoi_case_07')

    def test_only_trailing_suffix_is_removed(self):
        self.assertEqual(self.contract.image_case_id('case_cropped_hoi_extra.png'), 'case_cropped_hoi_extra')
        self.assertEqual(self.contract.image_case_id('hoi_thing.png'), 'hoi_thing')

    def test_empty_case_rejected(self):
        with self.assertRaises(ValueError): self.contract.image_case_id('_occ_obj.png')

    def test_bad_mesh_suffix_rejected(self):
        with self.assertRaises(ValueError): self.contract.mesh_case_id('case.ply')

    def test_hunyuan_images_sorted_and_directories_ignored(self):
        self.file('images/z.PNG'); self.file('images/a.jpg'); self.file('images/ignored.txt')
        (self.root / 'images/folder.png').mkdir()
        self.assertEqual([Path(p).name for p in self.hunyuan._collect_images(str(self.root/'images'))], ['a.jpg','z.PNG'])

    def test_hunyuan_duplicate_case_rejected_before_imports(self):
        paths = [self.file('case_occ_obj.png'), self.file('case_cropped_hoi_0.png')]
        with self.assertRaisesRegex(ValueError, 'Multiple images'):
            self.hunyuan._hunyuan_minimal_demo(paths, str(self.root/'out'))
        self.assertFalse((self.root/'out').exists())

    def test_hunyuan_no_inputs_fails(self):
        with self.assertRaises(FileNotFoundError): self.hunyuan._hunyuan_minimal_demo([], str(self.root/'out'))

    def test_hunyuan_missing_input_fails(self):
        with self.assertRaises(FileNotFoundError): self.hunyuan._hunyuan_minimal_demo([self.root/'missing.png'], str(self.root/'out'))

    def test_hunyuan_existing_output_skips_native_imports(self):
        src = self.file('case_occ_obj.png'); self.file('out/case_hoi_mesh.ply')
        self.hunyuan._hunyuan_minimal_demo([src], str(self.root/'out'))

    def test_hunyuan_empty_existing_output_fails(self):
        src = self.file('case_occ_obj.png'); self.file('out/case_hoi_mesh.ply', b'')
        with self.assertRaises(ValueError): self.hunyuan._hunyuan_minimal_demo([src], str(self.root/'out'))

    def test_hunyuan_output_symlink_fails(self):
        src = self.file('case_occ_obj.png'); kept = self.file('other.ply')
        (self.root/'out').mkdir(); (self.root/'out/case_hoi_mesh.ply').symlink_to(kept)
        with self.assertRaises(ValueError): self.hunyuan._hunyuan_minimal_demo([src], str(self.root/'out'))
        self.assertEqual(kept.read_bytes(), b'fixture')

    def hunyuan_stubs(self, result_count=1, fail_export=False, competing_output=False):
        images, calls = [], []
        def opened(source):
            img = Image(source); images.append(img); return img
        def inference(**kwargs):
            calls.append(kwargs)
            mesh = Mock()
            def export(path):
                Path(path).write_bytes(b'partial' if fail_export else b'mesh')
                if fail_export: raise RuntimeError('export failed')
                if competing_output: (Path(path).parent/'case_hoi_mesh.ply').write_bytes(b'other writer')
            mesh.export.side_effect = export
            return [mesh] * result_count
        pipeline = Mock(side_effect=inference)
        factory = Mock(); factory.from_pretrained.return_value = pipeline
        modules = {
            'PIL': types.SimpleNamespace(Image=types.SimpleNamespace(open=opened)),
            'torch': types.SimpleNamespace(manual_seed=lambda seed: seed),
            'hy3dgen.shapegen': types.SimpleNamespace(Hunyuan3DDiTFlowMatchingPipeline=factory,
                FaceReducer=lambda: lambda mesh: mesh, FloaterRemover=lambda: lambda mesh: mesh,
                DegenerateFaceRemover=lambda: lambda mesh: mesh),
        }
        return patch.dict(sys.modules, modules), images, calls, factory

    def test_hunyuan_one_case_per_call_and_exact_filenames(self):
        a=self.file('hoi_case_a_occ_obj.png'); b=self.file('hoi_case_b_occ_obj.png')
        stubs, images, calls, factory = self.hunyuan_stubs()
        with stubs: self.hunyuan._hunyuan_minimal_demo([b,a], str(self.root/'out'))
        self.assertEqual(len(calls),2); factory.from_pretrained.assert_called_once_with('tencent/Hunyuan3D-2')
        self.assertEqual([c['image'].source for c in calls],[a,b])
        self.assertTrue(all(c['multi_view'] is False for c in calls))
        self.assertTrue(all(i.closed and i.converted.closed for i in images))
        self.assertEqual(calls[0]['image'].pixels, [(255,255,255,0),(0,1,2,255)])
        self.assertEqual(sorted(p.name for p in (self.root/'out').iterdir()), ['hoi_case_a_hoi_mesh.ply','hoi_case_b_hoi_mesh.ply'])

    def test_hunyuan_wrong_output_counts_never_export(self):
        source = self.file('case_occ_obj.png')
        for count in (0,2):
            with self.subTest(count=count):
                stubs, images, _, _ = self.hunyuan_stubs(count)
                with stubs, self.assertRaisesRegex(ValueError, 'exactly one'):
                    self.hunyuan._hunyuan_minimal_demo([source], str(self.root/'out'))
                self.assertTrue(images[0].converted.closed)
                self.assertFalse((self.root/'out/case_hoi_mesh.ply').exists())

    def test_hunyuan_export_failure_retains_partial_not_final(self):
        source=self.file('case_occ_obj.png'); stubs,images,_,_=self.hunyuan_stubs(fail_export=True)
        with stubs, self.assertRaisesRegex(RuntimeError,'export failed'):
            self.hunyuan._hunyuan_minimal_demo([source],str(self.root/'out'))
        self.assertFalse((self.root/'out/case_hoi_mesh.ply').exists())
        self.assertEqual(len(list((self.root/'out').glob('*.partial.ply'))),1)
        self.assertTrue(images[0].converted.closed)

    def test_hunyuan_concurrent_output_not_overwritten(self):
        source=self.file('case_occ_obj.png'); stubs,_,_,_=self.hunyuan_stubs(competing_output=True)
        with stubs, self.assertRaises(FileExistsError):
            self.hunyuan._hunyuan_minimal_demo([source],str(self.root/'out'))
        self.assertEqual((self.root/'out/case_hoi_mesh.ply').read_bytes(),b'other writer')

    def test_moge_nested_case_path(self):
        source=self.file('trace_hoi/input/nested/hoi_case_07_cropped_hoi_wo_bckg_0.png')
        output=self.root/'trace_hoi/output'
        self.assertEqual(self.moge._confined_output_path(str(self.root/'trace_hoi/input'),str(output),source),output/'nested/hoi_case_07_cropped_hoi')

    def test_moge_single_file_path(self):
        source=self.file('case_cropped_hoi_0.png'); output=self.root/'output'
        self.assertEqual(self.moge._confined_output_path(str(source),str(output),source),output/'case_cropped_hoi')

    def test_moge_output_symlink_escape(self):
        source=self.file('case_occ_obj.png'); outside=self.root/'outside'; outside.mkdir()
        (self.root/'out').mkdir(); (self.root/'out/case_cropped_hoi').symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError,'escaped'):
            self.moge._confined_output_path(str(source),str(self.root/'out'),source)

    def test_moge_input_escape(self):
        outside=self.file('outside.png'); (self.root/'input').mkdir()
        (self.root/'input/case.png').symlink_to(outside)
        with self.assertRaises(ValueError):
            self.moge._confined_output_path(str(self.root/'input'),str(self.root/'out'),self.root/'input/case.png')

    def test_moge_collisions_fail_before_native_imports(self):
        self.file('input/case_cropped_hoi_0.png'); self.file('input/case_cropped_hoi_1.png')
        with self.assertRaisesRegex(ValueError,'Multiple images'):
            self.moge.run(str(self.root),str(self.root/'input'),str(self.root/'out'))

    def test_moge_missing_input_fails_before_native_imports(self):
        with self.assertRaises(FileNotFoundError): self.moge.run('',str(self.root/'missing.png'),str(self.root/'out'))

    def test_moge_export_flags_control_actual_writers(self):
        source=self.file('case_cropped_hoi_0.png'); a=Array()
        model=Mock(); model.to.return_value=model; model.eval.return_value=model
        model.infer.return_value={key:a for key in ('points','depth','mask','intrinsics')}
        factory=Mock(); factory.from_pretrained.return_value=model
        glb,ply,imwrite=Mock(),Mock(),Mock()
        native={
            'cv2':types.SimpleNamespace(imread=lambda p:a,cvtColor=lambda *args:a,imwrite=imwrite,
                COLOR_BGR2RGB=1,COLOR_RGB2BGR=2,IMWRITE_EXR_TYPE=3,IMWRITE_EXR_TYPE_FLOAT=4),
            'numpy':types.SimpleNamespace(float32='f32',uint8='u8',int32='i32',zeros=lambda *a,**k:Array(),rad2deg=lambda x:x),
            'torch':types.SimpleNamespace(device=lambda x:x,float32='f32',tensor=lambda *a,**k:Array()),
            'tqdm':types.SimpleNamespace(tqdm=lambda it,**kw:it),
            'moge.model':types.SimpleNamespace(import_model_class_by_version=lambda v:factory),
            'moge.utils.io':types.SimpleNamespace(save_glb=glb,save_ply=ply),
            'moge.utils.vis':types.SimpleNamespace(colorize_depth=lambda x:x,colorize_normal=lambda x:x),
            'utils3d':types.SimpleNamespace(numpy=types.SimpleNamespace(depth_edge=lambda *a,**k:Array(),
                image_mesh=lambda *a,**k:(Array(),Array(),Array(),Array()),image_uv=lambda **k:Array(),
                intrinsics_to_fov=lambda x:(1.,2.))),
        }
        for maps,g,p in [(True,False,False),(False,True,False),(False,False,True),(False,True,True)]:
            with self.subTest(maps=maps,glb=g,ply=p),patch.dict(sys.modules,native),patch.object(sys,'path',sys.path.copy()),patch.dict(os.environ):
                glb.reset_mock();ply.reset_mock();imwrite.reset_mock()
                self.moge.run('',str(source),str(self.root/'out'),save_maps=maps,save_glb=g,save_ply=p)
                self.assertEqual(glb.call_count,int(g));self.assertEqual(ply.call_count,int(p))
                self.assertEqual(imwrite.call_count,5 if maps else 0)

    def test_h2m_fallback_order_and_case_id(self):
        self.file('hy/hoi_case_a_hoi_mesh.ply')
        for name in ('mesh.ply','pointcloud.ply','mesh.glb'): self.file('mo/hoi_case_a_cropped_hoi/'+name)
        for expected in ('mesh.ply','pointcloud.ply','mesh.glb'):
            pairs=self.h2m._alignment_pairs(str(self.root/'hy'),str(self.root/'mo'))
            self.assertEqual(pairs[0][1].name,expected);pairs[0][1].unlink()

    def test_h2m_missing_case_blocks_entire_batch(self):
        self.file('hy/a_hoi_mesh.ply');self.file('hy/b_hoi_mesh.ply');self.file('mo/a_cropped_hoi/pointcloud.ply')
        with self.assertRaisesRegex(FileNotFoundError,'b: no nonempty'):
            self.h2m.run(str(self.root/'hy'),str(self.root/'mo'),str(self.root/'rt'))
        self.assertFalse((self.root/'rt').exists())

    def test_h2m_empty_source_rejected(self):
        self.file('hy/a_hoi_mesh.ply',b'');self.file('mo/a_cropped_hoi/pointcloud.ply')
        with self.assertRaisesRegex(FileNotFoundError,'empty'):
            self.h2m._alignment_pairs(str(self.root/'hy'),str(self.root/'mo'))

    def test_h2m_empty_directory_rejected(self):
        with self.assertRaises(FileNotFoundError): self.h2m._alignment_pairs(str(self.root/'hy'),str(self.root/'mo'))

    def test_h2m_sorted_calls_preserve_transform_names(self):
        for case in ('hoi_z','hoi_a'):
            self.file(f'hy/{case}_hoi_mesh.ply');self.file(f'mo/{case}_cropped_hoi/pointcloud.ply')
        align=Mock()
        with patch.dict(sys.modules,{'foho.alignment.mesh_align':types.SimpleNamespace(align_meshes_impl=align)}):
            self.h2m.run(str(self.root/'hy'),str(self.root/'mo'),str(self.root/'rt'))
        self.assertEqual([Path(c.kwargs['transform_path']).name for c in align.call_args_list],['hoi_a_hoi_mesh','hoi_z_hoi_mesh'])
        self.assertTrue(all(c.kwargs['fixed_scale'] is False for c in align.call_args_list))


if __name__ == '__main__': unittest.main(verbosity=2)
