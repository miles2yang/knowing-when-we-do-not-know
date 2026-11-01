import unittest
from copy import deepcopy
from core import probability,class_gap,matrix,simulate,infer,verify,FAMILIES,EXPERIMENTS,THETAS

class IdentificationChecks(unittest.TestCase):
 def test_baseline_nonidentification(self):
  self.assertTrue(all(v['distances']['baseline']=='0' for v in matrix()))
 def test_anonymous_separates_only_normative(self):
  self.assertEqual(str(class_gap('N','I',['anonymous'])),'3/10')
  self.assertEqual(class_gap('I','S',['anonymous']),0)
 def test_combined_separation(self):
  self.assertEqual([str(class_gap(a,b,['combined'])) for a,b in [('N','I'),('N','S'),('I','S')]],['1/5','1/10','1/10'])
 def test_nuisance_overlap(self):
  for t in THETAS:self.assertEqual(probability('N',t,'baseline'),probability('I',t,'baseline'))
 def test_structural_status(self):
  self.assertEqual(infer([{'experiment':'baseline','n':1600,'following_wrong_leader':1280}])['status'],'structural_ambiguity')
 def test_singleton(self):
  r=infer([{'experiment':'baseline','n':1600,'following_wrong_leader':1280},{'experiment':'anonymous','n':1600,'following_wrong_leader':640}])
  self.assertEqual(r['compatible_families'],['N']);self.assertTrue(verify(r))
 def test_finite_sample_ambiguity(self):
  self.assertEqual(infer([{'experiment':'combined','n':25,'following_wrong_leader':10}])['status'],'finite_sample_ambiguity')
 def test_omitted_detectable(self):
  self.assertEqual(infer(simulate('D',experiments=EXPERIMENTS,n=1600))['status'],'no_compatible_candidate')
 def test_omitted_equivalent(self):
  for t in THETAS:
   for e in EXPERIMENTS:self.assertEqual(probability('H',t,e),probability('I',t,e))
  self.assertEqual(simulate('H',experiments=EXPERIMENTS,n=1600),simulate('I',experiments=EXPERIMENTS,n=1600))
 def test_truth_not_in_inference_input(self):
  e=simulate('H',experiments=EXPERIMENTS,n=1600);r=infer(e)
  self.assertNotIn('world',r);self.assertNotIn('truth',r)
 def test_tampered_certificate(self):
  r=infer(simulate());r['compatible_families']=['N']
  with self.assertRaises(ValueError):verify(r)
 def test_invalid_counts(self):
  with self.assertRaises(ValueError):infer([{'experiment':'baseline','n':1,'following_wrong_leader':2}])
  with self.assertRaises(ValueError):simulate(n=0)
 def test_intervention_suggestion(self):
  r=infer(simulate());self.assertEqual(r['suggestions'][0]['experiment'],'combined')
 def test_family_not_parameter_identification(self):
  r=infer([{'experiment':'combined','n':1600,'following_wrong_leader':640}])
  self.assertEqual(r['compatible_families'],['N']);self.assertEqual(len(r['compatible_models']),3)
 def test_fixed_multiplicity(self):
  a=infer(simulate(experiments=['baseline']))
  b=infer(simulate(experiments=EXPERIMENTS))
  self.assertEqual(a['bands'][0]['radius'],b['bands'][0]['radius']);self.assertEqual(a['planned_interventions'],5)

if __name__=='__main__':unittest.main(verbosity=2)
