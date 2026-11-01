import json
from pathlib import Path
import tempfile
import unittest
from build_pilot_tasks import build
from pilot_runner import run_pilot,evaluate
from test_candidate_loop import candidates

class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.tasks=build(self.root/'input');self.oracle=json.loads((self.root/'input/evaluator_only.json').read_text())
    def tearDown(self):self.temp.cleanup()
    def test_twelve_cases_and_truth_isolation(self):
        self.assertEqual(len(self.tasks),12)
        for t in self.tasks:self.assertNotIn('world',t)
        self.assertEqual(self.tasks[8]['evidence'],self.tasks[11]['evidence'])
    def test_four_arms_keep_initial_output_and_separate_feedback(self):
        requests=[]
        def mock(q):requests.append(q);return json.dumps(candidates())
        rows,status=run_pilot(self.tasks[:1],self.oracle,mock,self.root/'run',transport='mock_transport_not_model')
        self.assertEqual(status['provider_calls_attempted'],4);self.assertEqual(len(rows),4)
        self.assertEqual(len({q['request_id'] for q in requests}),4)
        self.assertEqual(requests[1]['previous_attempts'][0]['feedback']['status'],'not_supplied')
        self.assertEqual(requests[2]['previous_attempts'][0]['feedback']['status'],'schema_valid')
        self.assertEqual(requests[3]['previous_attempts'][0]['feedback']['status'],'structural_ambiguity')
        for q in requests:self.assertNotIn('world',json.dumps(q))
    def test_failure_records_are_not_dropped(self):
        def mock(q):return 'broken'
        rows,status=run_pilot(self.tasks[:1],self.oracle,mock,self.root/'run',transport='mock_transport_not_model')
        self.assertEqual(len(rows),4);self.assertTrue(all(r['evaluation']['format_or_transport_failure'] for r in rows))
    def test_existing_directory_protected(self):
        out=self.root/'exists';out.mkdir()
        with self.assertRaises(FileExistsError):run_pilot(self.tasks[:1],self.oracle,lambda q:'',out)
    def test_aliased_world_does_not_invalidate_scoped_reference_claim(self):
        c=candidates();c['claim']['selected']='I'
        r=evaluate(json.dumps(c),self.tasks[11],self.oracle)
        self.assertTrue(r['supported_conditional_claim']);self.assertFalse(r['hidden_world_matches_selected_label'])
    def test_semantic_profile_error_not_counted_as_supported(self):
        c=candidates();c['claim']['selected']='N';c['candidates'][0]['profiles'][0]['combined']='0.6'
        r=evaluate(json.dumps(c),self.tasks[7],self.oracle)
        self.assertFalse(r['formal_profiles_match_reference']);self.assertFalse(r['supported_conditional_claim'])

if __name__=='__main__':unittest.main()
