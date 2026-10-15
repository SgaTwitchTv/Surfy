"""Test the test reporter without assuming fixture names cannot shadow TestCase.id."""
import io
import unittest
from scripts.school_unittest import Result

class ReporterTests(unittest.TestCase):
    def run_case(self,case):
        return unittest.TextTestRunner(stream=io.StringIO(),resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    def test_fixture_id_attribute_does_not_break_report(self):
        class Fixture(unittest.TestCase):
            def setUp(self):self.id='synthetic-resource-id'
            def test_success(self):pass
        result=self.run_case(Fixture)
        self.assertTrue(result.wasSuccessful());self.assertEqual(result.testsRun,1)
        self.assertEqual(result.outcomes[0]['status'],'passed')
        self.assertTrue(result.outcomes[0]['id'].endswith('Fixture.test_success'))
    def test_failed_subtests_remain_failed_parent_not_success(self):
        class Fixture(unittest.TestCase):
            def test_subtests(self):
                for value in [1,2]:
                    with self.subTest(value=value):self.assertEqual(value,0)
        result=self.run_case(Fixture)
        self.assertFalse(result.wasSuccessful());self.assertEqual(len(result.failures),2)
        self.assertEqual(len(result.subtest_failures),1);self.assertFalse(result.outcomes)


class RunnerEncodingTests(unittest.TestCase):
    def test_utf8_child_is_not_decoded_with_windows_parent_codepage(self):
        import os,sys
        from unittest.mock import patch
        from scripts.school_verify import run_captured
        text='Zażółć gęślą jaźń → ā'
        with patch('locale.getencoding',return_value='cp1252'):
            result=run_captured([sys.executable,'-c',f'print({text!r});raise SystemExit(7)'],env={**os.environ,'PYTHONIOENCODING':'utf-8'})
        self.assertEqual(result.stdout.strip(),text)
        self.assertEqual(result.returncode,7)  # Never convert a failing child to success.

    def test_legacy_terminal_cannot_break_utf8_artifact_reporting(self):
        from unittest.mock import patch
        from scripts.school_verify import show
        binary=io.BytesIO();terminal=io.TextIOWrapper(binary,encoding='cp1252',write_through=True)
        with patch('sys.stdout',terminal):show('Zażółć → ā')
        self.assertIn(b'\\u0101',binary.getvalue())


class SourceOriginTests(unittest.TestCase):
    def test_origin_accepts_export_with_normal_and_windows_short_paths(self):
        import ctypes,os,tempfile
        from pathlib import Path
        from scripts.school_verify import check_source_origin
        with tempfile.TemporaryDirectory(prefix='gw-source-origin-') as temporary:
            root=Path(temporary);(root/'greenwave').mkdir()
            (root/'greenwave/__init__.py').write_text('',encoding='utf-8')
            (root/'greenwave/application.py').write_text('',encoding='utf-8')
            cwd=root
            if os.name=='nt':
                buffer=ctypes.create_unicode_buffer(32768)
                self.assertTrue(ctypes.windll.kernel32.GetShortPathNameW(str(root),buffer,len(buffer)))
                cwd=Path(buffer.value)
                # Some volumes disable 8.3 aliases; canonical paths must still work.
                self.assertEqual(cwd.resolve(),root.resolve())
            check_source_origin(cwd,{**os.environ,'PYTHONIOENCODING':'utf-8'},root)
            check_source_origin(root,{**os.environ,'PYTHONIOENCODING':'utf-8'},root)
            self.assertIn('Isolated source origin PASS',(root/'runner-origin.txt').read_text(encoding='utf-8'))

    def test_origin_rejects_external_import_and_saves_failure(self):
        import os,subprocess,tempfile
        from pathlib import Path
        from scripts.school_verify import check_source_origin
        with tempfile.TemporaryDirectory(prefix='gw-external-origin-') as temporary:
            root=Path(temporary);export=root/'export';export.mkdir()
            external=root/'external';(external/'greenwave').mkdir(parents=True)
            (external/'greenwave/__init__.py').write_text('',encoding='utf-8')
            (external/'greenwave/application.py').write_text('',encoding='utf-8')
            env={**os.environ,'PYTHONPATH':str(external),'PYTHONIOENCODING':'utf-8'}
            with self.assertRaises(subprocess.CalledProcessError):check_source_origin(export,env,root)
            self.assertIn('AssertionError',(root/'runner-origin.txt').read_text(encoding='utf-8'))
