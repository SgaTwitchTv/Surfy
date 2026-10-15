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
