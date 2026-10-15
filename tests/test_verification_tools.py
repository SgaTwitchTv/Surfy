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
