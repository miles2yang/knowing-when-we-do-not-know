"""Provider-neutral candidate generation/check/revision harness.

Replay is a transport test, not a live LLM benchmark. Generated outputs are JSON
data, never executed code. The checker verifies finite specifications, not their
organizational meaning or candidate completeness.
"""
import argparse
from fractions import Fraction as F
from itertools import combinations
import json
from math import log, sqrt, isfinite
from pathlib import Path
import subprocess
import time

SCHEMA = 'organizational-candidate-loop/1.1'

def validate_task(task):
    if set(task) != {'task_id','question','interventions','evidence','alpha'}:
        raise ValueError('Only public task fields permitted; hidden truth must remain evaluator-only')
    exps=task['interventions']
    if not exps or len(exps)>20 or len(set(exps))!=len(exps):
        raise ValueError('Register 1 to 20 distinct intervention names')
    if not all(isinstance(e,str) and 0<len(e)<=100 for e in exps):
        raise ValueError('Invalid intervention names')
    if type(task['alpha']) not in (int,float) or not 0<task['alpha']<1:
        raise ValueError('Invalid alpha')
    seen=set()
    for row in task['evidence']:
        e,n,k=row['experiment'],row['n'],row['following_wrong_leader']
        if e not in exps or e in seen or type(n)!=int or type(k)!=int or not 1<=n<=1000000 or not 0<=k<=n:
            raise ValueError('Invalid or repeated observed counts')
        seen.add(e)
    if not seen: raise ValueError('No evidence')

def parse_candidate(raw, task):
    x=json.loads(raw)
    if set(x)!={'candidates','assumptions','claim'}:raise ValueError('Expected candidates, assumptions, claim')
    if not isinstance(x['assumptions'],list) or not x['assumptions'] or not all(isinstance(a,str) and a.strip() for a in x['assumptions']):
        raise ValueError('State nonempty assumptions explicitly')
    if not isinstance(x['candidates'],list) or not 1<=len(x['candidates'])<=20:raise ValueError('Expected 1 to 20 candidate families')
    names=set()
    for c in x['candidates']:
        if set(c)!={'id','mechanism','profiles'}:raise ValueError('Candidate fields differ from contract')
        if not isinstance(c['id'],str) or not c['id'].strip() or c['id'] in names:raise ValueError('Distinct nonempty candidate IDs required')
        names.add(c['id'])
        if not isinstance(c['mechanism'],str) or not c['mechanism'].strip():raise ValueError('Explain the mechanism')
        if not isinstance(c['profiles'],list) or not 1<=len(c['profiles'])<=100:raise ValueError('Expected 1 to 100 nuisance profiles')
        for profile in c['profiles']:
            if set(profile)!=set(task['interventions']):
                raise ValueError('Each profile must be a flat probability map with exactly these keys: '+', '.join(task['interventions'])+'. Received keys: '+', '.join(sorted(profile))+'. Do not add theta, probabilities, intervention, or probability fields; do not nest the map.')
            for v in profile.values():
                if type(v) not in (int,float,str) or len(str(v))>40:raise ValueError('Invalid probability representation')
                if type(v)==float and not isfinite(v):raise ValueError('Nonfinite probability')
                if not 0<=F(str(v))<=1:raise ValueError('Probability outside [0,1]')
    claim=x['claim']
    if set(claim)!={'selected','scope'} or claim['scope'] not in ('registered_candidates','unrestricted'):
        raise ValueError('Declare selected ID or null and claim scope')
    if claim['selected'] is not None and claim['selected'] not in names:raise ValueError('Selected family is not registered')
    return x

def gap(a,b,exps):
    return min(max(abs(F(str(pa[e]))-F(str(pb[e]))) for e in exps) for pa in a['profiles'] for pb in b['profiles'])

def check(candidate,task):
    validate_task(task)
    candidate=parse_candidate(json.dumps(candidate),task)
    bands=[]
    for row in task['evidence']:
        n,k=row['n'],row['following_wrong_leader']
        bands.append((row['experiment'],k/n,sqrt(log(2*len(task['interventions'])/task['alpha'])/(2*n))))
    compatible=[c for c in candidate['candidates'] if any(all(abs(float(F(str(p[e])))-mean)<=radius+1e-12 for e,mean,radius in bands) for p in c['profiles'])]
    pairs=list(combinations(compatible,2)); observed=[b[0] for b in bands]
    distances=[{'pair':[a['id'],b['id']],'distance':str(gap(a,b,observed))} for a,b in pairs]
    if not compatible:status='no_compatible_candidate'
    elif len(compatible)==1:status='scoped_singleton'
    elif any(F(d['distance'])==0 for d in distances):status='structural_ambiguity'
    else:status='finite_sample_ambiguity'
    ids=[c['id'] for c in compatible]; selected=candidate['claim']['selected']
    violations=[]
    if candidate['claim']['scope']!='registered_candidates':violations.append('Unrestricted mechanism claim is unsupported')
    if selected is not None and (len(ids)!=1 or ids[0]!=selected):violations.append('Evidence does not support the selected singleton')
    suggestions=[]
    for e in task['interventions']:
        if e not in observed and pairs:
            suggestions.append({'experiment':e,'minimum_registered_gap':str(min(gap(a,b,[e]) for a,b in pairs))})
    suggestions.sort(key=lambda s:-F(s['minimum_registered_gap']))
    return {'status':status,'compatible_families':ids,'design_distances':distances,
        'claim_violations':violations,'suggestions':suggestions,
        'candidate_completeness':'not_verified','semantic_fidelity':'not_verified',
        'assumptions':'declared_not_empirically_verified',
        'error_guarantee':'Fixed batches and a fixed candidate specification only; adaptive candidate revision does not inherit a joint guarantee'}

def make_request(task,round_index,history):
    validate_task(task)
    probability={'anyOf':[{'type':'number','minimum':0,'maximum':1},{'type':'string','description':'A probability in [0,1], written as a decimal or rational such as 1/2'}]}
    profile={'type':'object','properties':{e:probability for e in task['interventions']},'required':list(task['interventions']),'additionalProperties':False}
    family={'type':'object','properties':{'id':{'type':'string','minLength':1},'mechanism':{'type':'string','minLength':1},'profiles':{'type':'array','minItems':1,'maxItems':100,'items':profile}},'required':['id','mechanism','profiles'],'additionalProperties':False}
    contract={'type':'object','properties':{'candidates':{'type':'array','minItems':1,'maxItems':20,'items':family},'assumptions':{'type':'array','minItems':1,'items':{'type':'string','minLength':1}},'claim':{'type':'object','properties':{'selected':{'type':['string','null']},'scope':{'enum':['registered_candidates','unrestricted']}},'required':['selected','scope'],'additionalProperties':False}},'required':['candidates','assumptions','claim'],'additionalProperties':False}
    return {'schema':SCHEMA,'round':round_index,'public_task':task,
        'instruction':'Return exactly one JSON object conforming to output_contract. No Markdown fences or surrounding prose. Each profiles entry is ONE complete flat map from ALL registered intervention names to probabilities for ONE nuisance setting. Do not wrap it in probabilities, do not include theta as a key, and do not use intervention/probability rows. Include every nuisance setting stipulated in the question. Candidate IDs must be distinct and selected must be a candidate ID or null. Apply inference_rule consistently, including in the initial answer. Use feedback if supplied; preserve unresolved alternatives. Do not assert candidate completeness. Only return candidates, assumptions, claim, with no additional fields.',
        'output_contract':contract,
        'inference_rule':{'method':'Fixed-batch simultaneous Hoeffding compatibility, not a likelihood winner or an exact binomial test',
            'registered_intervention_count':len(task['interventions']),
            'radius':'For each observed batch, sqrt(log(2*m/alpha)/(2*n)), where m is the count of ALL registered interventions, including unobserved ones.',
            'compatibility':'A family is compatible if at least one of its nuisance profiles satisfies abs(profile[experiment] - following_wrong_leader/n) <= radius for EVERY observed batch.',
            'claim':'Select a family only when exactly one registered family is compatible. Otherwise selected must be null. A singleton is conditional on the registered set and assumptions; it does not establish mechanism completeness in reality.'},
        'previous_attempts':history}

def run_loop(task,invoke,rounds=2,transport_label='unverified_transport'):
    validate_task(task)
    if type(rounds)!=int or not 1<=rounds<=5:raise ValueError('Use 1 to 5 registered rounds')
    attempts=[]
    for i in range(rounds):
        req=make_request(task,i,attempts.copy());start=time.monotonic()
        try:
            raw=invoke(req)
            try:
                parsed=parse_candidate(raw,task);feedback=check(parsed,task)
            except (ValueError,TypeError,KeyError,ZeroDivisionError) as error:
                feedback={'status':'invalid_specification','error':str(error)}
            attempt={'round':i,'request':req,'raw_output':raw,'feedback':feedback,'elapsed_seconds':time.monotonic()-start}
        except Exception as error:
            attempt={'round':i,'request':req,'raw_output':None,'feedback':{'status':'transport_failure','error':type(error).__name__},'elapsed_seconds':time.monotonic()-start}
        attempts.append(attempt)
    return {'schema':SCHEMA,'task_id':task['task_id'],'transport':transport_label,'attempts':attempts,
        'rounds_requested':rounds,'attempts_retained':len(attempts),'model_performance_estimated':False}

def command_transport(argv):
    """User-configured trusted provider command; candidate text never controls argv."""
    def invoke(request):
        result=subprocess.run(argv,input=json.dumps(request),capture_output=True,text=True,timeout=60,check=False)
        if result.returncode:raise RuntimeError('Configured provider command failed')
        return result.stdout
    return invoke

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--task',required=True);ap.add_argument('--out',required=True)
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--replay');group.add_argument('--command-json',help='JSON argv of a trusted provider wrapper')
    ap.add_argument('--rounds',type=int,default=2);args=ap.parse_args()
    task=json.loads(Path(args.task).read_text())
    if args.replay:
        responses=json.loads(Path(args.replay).read_text());label='authored_fixture_replay_not_live_llm'
        invoke=lambda request:responses[request['round']]
    else:
        argv=json.loads(args.command_json)
        if not isinstance(argv,list) or not argv or not all(isinstance(s,str) for s in argv):raise ValueError('Expected nonempty JSON argv')
        invoke=command_transport(argv);label='configured_external_command_not_authenticated_as_llm'
    result=run_loop(task,invoke,args.rounds,label)
    Path(args.out).write_text(json.dumps(result,indent=2))
    print(json.dumps({'attempts':result['attempts_retained'],'statuses':[a['feedback']['status'] for a in result['attempts']],'model_performance_estimated':False}))

if __name__=='__main__':main()
