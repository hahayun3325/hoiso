import importlib.util, os, tempfile, unittest
from pathlib import Path

def load():
    path=Path(os.environ['MOGE_SOURCE'])
    spec=importlib.util.spec_from_file_location('moge_under_test',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class MoGeOutputPathTest(unittest.TestCase):
    def test_trace_hoi_parent_stays_confined(self):
        module=load()
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/'trace_hoi_automatic_replay'
            input_root=base/'fresh/01_preprocess/cropped_without_background'
            image=input_root/'alapuse02v3n60_cropped_hoi_wo_bckg_0.png'
            output_root=base/'fresh/04_moge'
            image.parent.mkdir(parents=True); image.write_bytes(b'image')
            target=module._confined_output_path(str(input_root),str(output_root),image)
            self.assertEqual(target,output_root.resolve()/'alapuse02v3n60_cropped_hoi')
            target.relative_to(output_root.resolve())
            self.assertNotEqual(target,base.parent/'trace_hoi')
    def test_single_file_input_is_supported(self):
        module=load()
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/'parent_with_hoi'
            image=base/'case_cropped_hoi_0.png'; image.parent.mkdir(); image.write_bytes(b'x')
            output=base/'moge_out'
            target=module._confined_output_path(str(image),str(output),image)
            self.assertEqual(target,output.resolve()/'case_cropped_hoi')
            target.relative_to(output.resolve())
if __name__=='__main__': unittest.main(verbosity=2)
