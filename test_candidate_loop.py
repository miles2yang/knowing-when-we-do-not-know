import copy
import json
from pathlib import Path
import sys
import unittest
from candidate_loop import check,parse_candidate,run_loop,validate_task,command_transport
from core import probability,THETAS,EXPERIMENTS,simulate,infer,matrix

def task(experiments=None):
    return {'task_id':'team-error-001','question':'Which candidate mechanism explains following an incorrect leader?',
        'interventions':EXPERIMENTS,'evidence':simulate('N',experiments=experiments or ['baseline'],n=1600,seed=41),'alpha':.05}

def candidates():
    return {'candidates':[{'id':f,'mechanism':m,'profiles':[{e:str(probability(f,t,e)) for e in EXPERIMENTS} for t in THETAS]} for f,m in [('N','Compliance pressure'),('I','Informational reliance'),('S','Shared erroneous source')]],
        'assumptions':['Independent Bernoulli draws within fixed batches','Stipulated intervention exclusions'],
        'claim':{'selected':None,'scope':'registered_candidates'}}

class CandidateLoopTests(unittest.TestCase):
    def test_reference_parity(self):
        for exps in [['baseline'],['anonymous'],['combined']]:
            t=task(exps);a=check(candidates(),t);b=infer(t['evidence'])
            self.assertEqual(sorted(a['compatible_families']),b['compatible_families']);self.assertEqual(a['status'],b['status'])
    def test_exact_gaps(self):
        from candidate_loop import gap
        cs={c['id']:c for c in candidates()['candidates']}
        for row in matrix():
            for e,g in row['distances'].items():self.assertEqual(str(gap(cs[row['a']],cs[row['b']],[e])),g)
    def test_unrestricted_claim_rejected(self):
        c=candidates();c['claim']={'selected':'N','scope':'unrestricted'}
        self.assertTrue(check(c,task(['combined']))['claim_violations'])
    def test_baseline_singleton_rejected(self):
        c=candidates();c['claim']['selected']='N'
        self.assertEqual(check(c,task())['status'],'structural_ambiguity');self.assertTrue(check(c,task())['claim_violations'])
    def test_hidden_truth_blocked(self):
        t=task();t['hidden_truth']='N'
        with self.assertRaises(ValueError):validate_task(t)
    def test_all_malformed_attempts_retained(self):
        answers=['not JSON',json.dumps(candidates())]
        r=run_loop(task(),lambda q:answers[q['round']])
        self.assertEqual(len(r['attempts']),2);self.assertEqual(r['attempts'][0]['raw_output'],'not JSON')
        self.assertEqual(r['attempts'][1]['request']['previous_attempts'][0]['feedback']['status'],'invalid_specification')
    def test_out_of_range_and_missing_intervention(self):
        c=candidates();c['candidates'][0]['profiles'][0]['baseline']='1.1'
        with self.assertRaises(ValueError):parse_candidate(json.dumps(c),task())
        c=candidates();del c['candidates'][0]['profiles'][0]['combined']
        with self.assertRaises(ValueError):parse_candidate(json.dumps(c),task())
    def test_alias_cannot_be_detected(self):
        t=task();t['evidence']=simulate('H',experiments=['combined'],n=1600,seed=41)
        r=check(candidates(),t)
        self.assertEqual(r['compatible_families'],['I']);self.assertEqual(r['candidate_completeness'],'not_verified')
    def test_failure_does_not_disappear(self):
        def fail(q):raise RuntimeError('transport offline')
        r=run_loop(task(),fail);self.assertEqual([a['feedback']['status'] for a in r['attempts']],['transport_failure']*2)
    def test_command_transport_contract(self):
        invoke=command_transport([sys.executable,'-c','import sys,json; q=json.load(sys.stdin); print(json.dumps({"task_id":q["public_task"]["task_id"]}))'])
        result=json.loads(invoke({'public_task':task()}));self.assertEqual(result['task_id'],'team-error-001')
    def test_revision_cannot_certify_semantics(self):
        c=candidates();c['claim']['selected']='N'
        r=run_loop(task(['combined']),lambda q:json.dumps(c))
        self.assertEqual(r['attempts'][-1]['feedback']['semantic_fidelity'],'not_verified')
        self.assertFalse(r['model_performance_estimated'])
    def test_no_generated_code_execution(self):
        c=candidates();c['candidates'][0]['profiles'][0]['baseline']='__import__("os").system("false")'
        with self.assertRaises(ValueError):parse_candidate(json.dumps(c),task())

if __name__=='__main__':unittest.main()
