import json
from pathlib import Path
import unittest
from candidate_loop import make_request,parse_candidate
from test_candidate_loop import candidates

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.task=json.loads((Path(__file__).parent/'pilot/public_tasks.json').read_text())[0]
    def test_nested_probabilities_error_identifies_the_received_shape(self):
        candidate=candidates()
        candidate['candidates'][0]['profiles']=[{'theta':0.7,'probabilities':candidate['candidates'][0]['profiles'][0]}]
        with self.assertRaisesRegex(ValueError,'Received keys: probabilities, theta'):
            parse_candidate(json.dumps(candidate),self.task)
    def test_contract_and_rule_disclose_all_interventions_without_oracle(self):
        request=make_request(self.task,0,[])
        profile=request['output_contract']['properties']['candidates']['items']['properties']['profiles']['items']
        self.assertEqual(set(profile['required']),set(self.task['interventions']))
        self.assertFalse(profile['additionalProperties'])
        self.assertEqual(request['inference_rule']['registered_intervention_count'],5)
        self.assertNotIn('reference_candidates',json.dumps(request))
        self.assertNotIn('compatible_families',json.dumps(request))

if __name__=='__main__':unittest.main()
