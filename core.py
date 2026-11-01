"""Toy organizational mechanism inference. Exact identification; bounded noisy evidence.
The inference function accepts observed counts, never the simulator truth label.
"""
from fractions import Fraction as F
from itertools import combinations
from math import sqrt,log
import json

SPEC='org-mechanism-identification/2.0'
EXPERIMENTS=['baseline','anonymous','reliability','independent','combined']
FAMILIES=['N','I','S']
THETAS=[F(7,10),F(4,5),F(9,10)]
MASK=(1<<32)-1

def probability(family,theta,experiment):
 theta=F(theta)
 if experiment not in EXPERIMENTS:raise ValueError('Unknown intervention')
 if family not in ['N','I','S','D','H']:raise ValueError('Unknown world')
 if theta not in THETAS:raise ValueError('Theta outside registered finite grid')
 if family=='N':return F(2,5) if experiment in ['anonymous','combined'] else theta
 if family in ['I','H']:return F(1,5) if experiment in ['reliability','combined'] else theta
 if family=='S':return F(3,10) if experiment in ['independent','combined'] else theta
 return theta if experiment=='baseline' else F(3,5)

def models():
 return [{'id':f+'@'+str(t),'family':f,'theta':str(t)} for f in FAMILIES for t in THETAS]

def class_gap(a,b,experiments):
 """min nuisance-pair max intervention Bernoulli TV distance.
 Positive means no cross-family profile overlaps on this registered design.
 """
 if not experiments:return F(0)
 return min(max(abs(probability(a,ta,e)-probability(b,tb,e)) for e in experiments) for ta in THETAS for tb in THETAS)

def matrix():
 return [{'pair':a+' / '+b,'a':a,'b':b,'distances':{e:str(class_gap(a,b,[e])) for e in EXPERIMENTS}} for a,b in combinations(FAMILIES,2)]

def simulate(world='N',theta='4/5',experiments=None,n=400,seed=41):
 if experiments is None:experiments=['baseline']
 if not isinstance(n,int) or not 1<=n<=10000:raise ValueError('n must be an integer in [1,10000]')
 if not isinstance(seed,int) or not 0<=seed<=MASK:raise ValueError('seed must be uint32')
 if not experiments or len(set(experiments))!=len(experiments):raise ValueError('Select distinct interventions')
 evidence=[]
 for e in experiments:
  p=probability(world,F(theta),e);idx=EXPERIMENTS.index(e)
  state=(seed^(((idx+1)*0x9E3779B9)&MASK))&MASK
  successes=0;denominator=10;numerator=int(p*denominator)
  limit=((1<<32)//denominator)*denominator
  for _ in range(n):
   while True:
    state=(state+0x6D2B79F5)&MASK
    z=((state^(state>>15))*(state|1))&MASK
    z^=(z+(((z^(z>>7))*(z|61))&MASK))&MASK
    draw=(z^(z>>14))&MASK
    if draw<limit:break
   successes+=int(draw%denominator<numerator)
  evidence.append({'experiment':e,'n':n,'following_wrong_leader':successes})
 return evidence

def infer(evidence,alpha=.05):
 if not 0<alpha<1:raise ValueError('Invalid alpha')
 if not evidence:raise ValueError('No observations')
 exps=[];bands=[]
 for row in evidence:
  e=row['experiment'];n=row['n'];k=row['following_wrong_leader']
  if e not in EXPERIMENTS or e in exps:raise ValueError('Unknown or repeated intervention')
  if not isinstance(n,int) or not isinstance(k,int) or not 1<=n<=10000 or not 0<=k<=n:raise ValueError('Invalid counts')
  exps.append(e);mean=k/n;eps=sqrt(log(2*len(EXPERIMENTS)/alpha)/(2*n))
  bands.append({'experiment':e,'n':n,'k':k,'mean':mean,'radius':eps,'lower':max(0,mean-eps),'upper':min(1,mean+eps)})
 compatible=[]
 for m in models():
  if all(abs(float(probability(m['family'],F(m['theta']),b['experiment']))-b['mean'])<=b['radius']+1e-12 for b in bands):compatible.append(m)
 families=sorted(set(m['family'] for m in compatible))
 gaps=[{'pair':a+' / '+b,'gap':str(class_gap(a,b,exps))} for a,b in combinations(families,2)]
 if not families:status='no_compatible_candidate'
 elif len(families)==1:status='scoped_singleton'
 elif any(F(g['gap'])==0 for g in gaps):status='structural_ambiguity'
 else:status='finite_sample_ambiguity'
 suggestions=[]
 if len(families)>1:
  for e in EXPERIMENTS:
   if e in exps:continue
   score=min(class_gap(a,b,[e]) for a,b in combinations(families,2))
   suggestions.append({'experiment':e,'worst_pair_distance':str(score)})
  suggestions.sort(key=lambda x:(-F(x['worst_pair_distance']),EXPERIMENTS.index(x['experiment'])))
 return {'schema':SPEC,'evidence':evidence,'alpha':alpha,'planned_interventions':len(EXPERIMENTS),
   'bands':bands,'compatible_models':compatible,'compatible_families':families,'status':status,
   'design_gaps':gaps,'suggestions':suggestions,
   'scope':'Conditional on nine registered candidate profiles, known exclusion restrictions and independent Bernoulli sampling. Candidate-family identification is not identification of an unrestricted real mechanism.',
   'open_world_warning':'An omitted mechanism observationally and interventionally equivalent to a candidate cannot be detected with these observables.',
   'method':'Simultaneous fixed-batch Hoeffding compatibility bands; not posterior model probabilities'}

def verify(certificate):
 expected=infer(certificate['evidence'],certificate['alpha'])
 for k in ['schema','planned_interventions','compatible_models','compatible_families','status','design_gaps','suggestions','scope','open_world_warning','method']:
  if certificate.get(k)!=expected[k]:raise ValueError('Certificate differs: '+k)
 if len(certificate['bands'])!=len(expected['bands']):raise ValueError('Band count differs')
 for actual,wanted in zip(certificate['bands'],expected['bands']):
  for k in wanted:
   if isinstance(wanted[k],float):
    if abs(actual[k]-wanted[k])>1e-12:raise ValueError('Band differs: '+k)
   elif actual[k]!=wanted[k]:raise ValueError('Band differs: '+k)
 return True

def evaluate(world,certificate):
 """Evaluator alone knows truth. This is separate from inference input."""
 families=certificate['compatible_families']
 if world in FAMILIES:
  return {'truth_available_to_inference':False,'world':world,'truth_retained':world in families,
   'supported_singleton_correct':certificate['status']=='scoped_singleton' and families==[world],
   'abstained_from_singleton':len(families)!=1}
 return {'truth_available_to_inference':False,'world':world,'truth_in_candidate_family':False,
  'missing_family_detected_as_incompatibility':world=='D' and not families,
  'undetectable_omission':world=='H',
  'unqualified_singleton_would_be_wrong':bool(len(families)==1)}

if __name__=='__main__':
 print(json.dumps(matrix(),indent=2))
