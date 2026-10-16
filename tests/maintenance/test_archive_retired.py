import copy,io,json,os
from pathlib import Path
import tempfile,unittest,zipfile
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/tracehoi/maintenance'))
from archive_retired import archive_retired
from file_safety import binding

class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name).resolve();self.folder=self.home/'tracehoi-hunyuan-cpu-load-probe-20261014-v1-N7l4Cu9L';self.folder.mkdir()
        content={'review_report.json':json.dumps(dict(attempt_id='N7l4Cu9L',service=dict(submission_attempted=False,service_submitted=False))).encode(),'source.py':b'# retained source\n'}
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w')as z:
            for name,data in content.items():z.writestr(name,data);(self.folder/name).write_bytes(data)
        raw=b.getvalue();(self.folder/'packet.zip').write_bytes(raw);(self.folder/'cache').mkdir()
        self.terminal=self.home/'attempt.terminal.txt';self.terminal.write_bytes(b'original terminal')
        self.row=dict(folder=str(self.folder),zip_name='packet.zip',zip_binding=binding(raw),terminal=str(self.terminal),terminal_binding=binding(self.terminal.read_bytes()),attempt_id='N7l4Cu9L')
    def run_cleanup(self):return archive_retired(copy.deepcopy(self.row),str(self.home))
    def test_verified_archive_and_recoverable_trash(self):
        result=self.run_cleanup();self.assertEqual(result['status'],'trashed');self.assertFalse(self.folder.exists())
        self.assertTrue(self.terminal.is_file());self.assertEqual(Path(result['retained_zip']).read_bytes(),(Path(result['trash'])/'packet.zip').read_bytes())
        self.assertIn(str(self.folder),Path(result['trash_info']).read_text());self.assertEqual(self.run_cleanup()['status'],'already_absent')
    def test_modified_source_is_preserved(self):
        (self.folder/'source.py').write_bytes(b'new work')
        with self.assertRaises(ValueError):self.run_cleanup()
        self.assertTrue(self.folder.is_dir())
    def test_extra_file_is_preserved(self):
        (self.folder/'important.txt').write_bytes(b'keep')
        with self.assertRaises(ValueError):self.run_cleanup()
        self.assertTrue(self.folder.is_dir())
    def test_symlink_is_preserved(self):
        (self.folder/'source.py').unlink();(self.folder/'source.py').symlink_to(self.terminal)
        with self.assertRaises(ValueError):self.run_cleanup()
        self.assertTrue(self.terminal.is_file())
    def test_wrong_folder_is_rejected(self):
        self.row['folder']=str(self.home)
        with self.assertRaises(ValueError):self.run_cleanup()
    def test_missing_terminal_preserves_folder(self):
        self.terminal.unlink()
        with self.assertRaises(FileNotFoundError):self.run_cleanup()
        self.assertTrue(self.folder.is_dir())
    def test_changed_retained_archive_preserves_folder(self):
        archive=self.home/'tracehoi-evidence-archive/N7l4Cu9L';archive.mkdir(parents=True);(archive/'packet.zip').write_bytes(b'different')
        with self.assertRaises(ValueError):self.run_cleanup()
        self.assertTrue(self.folder.is_dir())
    def test_missing_nonessential_source_is_archivable(self):
        (self.folder/'source.py').unlink()
        self.assertEqual(self.run_cleanup()['status'],'trashed')
    def test_concurrent_change_stops_before_move(self):
        import archive_retired as ar
        real=ar.retain;count=[0]
        def change(path,raw):
            real(path,raw);count[0]+=1
            if count[0]==2:(self.folder/'source.py').write_bytes(b'changed meanwhile')
        with patch.object(ar,'retain',change),self.assertRaises(ValueError):self.run_cleanup()
        self.assertTrue(self.folder.is_dir())
    def test_zip_hash_tamper_is_rejected(self):
        self.row['zip_binding']['sha256']='0'*64
        with self.assertRaises(ValueError):self.run_cleanup()
        self.assertTrue(self.folder.is_dir())

    def test_post_move_failure_reports_actual_trash_location(self):
        import archive_retired as ar
        original=ar.snapshot;count=[0]
        def fail_after_move(root,expected):
            count[0]+=1
            if count[0]==3:raise ValueError('readback failure')
            return original(root,expected)
        with patch.object(ar,'snapshot',fail_after_move),self.assertRaises(ValueError)as caught:self.run_cleanup()
        record=caught.exception.cleanup_record
        self.assertEqual(record['status'],'moved_needs_review');self.assertTrue(Path(record['trash']).is_dir())
        self.assertFalse(self.folder.exists());self.assertTrue(Path(record['retained_zip']).is_file())

if __name__=='__main__':unittest.main(verbosity=2)
