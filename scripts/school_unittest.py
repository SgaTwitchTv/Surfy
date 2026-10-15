"""Unittest with machine-readable outcomes (no fixture credentials in JSON)."""
import argparse, json, os, time, unittest
from pathlib import Path

class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.outcomes=[]; self.subtest_failures={}
    def addSuccess(self,test):
        super().addSuccess(test); self.outcomes.append({'id':unittest.TestCase.id(test),'status':'passed'})
    def addFailure(self,test,err):
        super().addFailure(test,err); self.outcomes.append({'id':unittest.TestCase.id(test),'status':'failed'})
    def addError(self,test,err):
        super().addError(test,err); self.outcomes.append({'id':unittest.TestCase.id(test),'status':'error'})
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err is not None:self.subtest_failures[unittest.TestCase.id(test)]={'id':unittest.TestCase.id(test),'status':'failed' if issubclass(err[0],test.failureException) else 'error'}
    def addSkip(self,test,reason):
        super().addSkip(test,reason); self.outcomes.append({'id':unittest.TestCase.id(test),'status':'skipped','reason':reason})

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--pattern',default='test_*.py'); args=parser.parse_args()
    suite=unittest.defaultTestLoader.discover('tests',pattern=args.pattern)
    start=time.monotonic(); result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    dest=Path(os.environ['GW_TEST_RESULT']); dest.parent.mkdir(parents=True,exist_ok=True)
    outcomes={item['id']:item for item in result.outcomes};outcomes.update(result.subtest_failures)
    counts={status:sum(item['status']==status for item in outcomes.values()) for status in ('passed','failed','error','skipped')}
    dest.write_text(json.dumps({'tests':result.testsRun,'passed':counts['passed'],'failed':counts['failed'],'errors':counts['error'],'skipped':counts['skipped'],'seconds':time.monotonic()-start,'outcomes':list(outcomes.values())},indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__': raise SystemExit(main())
