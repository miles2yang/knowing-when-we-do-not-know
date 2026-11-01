"""Twelve controlled formalization/inference tasks; no live model results."""
import json
from pathlib import Path
from core import EXPERIMENTS,simulate,infer,probability,FAMILIES,THETAS

QUESTION='''A team follows an incorrect leader recommendation (binary Y). Register three working candidate families, not an exhaustive account of reality: N compliance pressure, I informational reliance, S shared erroneous information. For each family the unknown baseline probability is theta in {0.7,0.8,0.9}. Under anonymous decisions N becomes 0.4; under reliability disclosure I becomes 0.2; under independent information S becomes 0.3. Other single interventions leave theta unchanged. Combined intervention applies all three changes, giving N 0.4, I 0.2, S 0.3. These are stipulated, not empirically validated, exclusions. Encode all three nuisance profiles per family under all five interventions and assess the strongest justified mechanism claim from the supplied counts. Keep the registered IDs N, I, S. Do not infer candidate completeness. Additional substantive mechanisms should be investigated later rather than silently replacing the registered family. The simulator truth is unavailable.'''

def build(directory):
    p=Path(directory);p.mkdir(parents=True,exist_ok=True)
    cells=[('N',['baseline'],1600),('I',['baseline'],1600),
        ('N',['anonymous'],1600),('I',['reliability'],1600),('S',['independent'],1600),
        ('N',['combined'],25),('I',['combined'],25),
        ('N',['combined'],1600),('I',['combined'],1600),('S',['combined'],1600),
        ('D',['combined'],1600),('H',['combined'],1600)]
    public=[];private=[]
    for i,(world,exps,n) in enumerate(cells):
        evidence=simulate(world,experiments=exps,n=n,seed=41)
        task={'task_id':f'task-{i+1:02d}','question':QUESTION,'interventions':EXPERIMENTS,'evidence':evidence,'alpha':.05}
        public.append(task)
        private.append({'task_id':task['task_id'],'world':world,'theta':'4/5','seed':41,'reference':infer(evidence)})
    reference=[{'id':f,'profiles':[{e:str(probability(f,t,e)) for e in EXPERIMENTS} for t in THETAS]} for f in FAMILIES]
    (p/'public_tasks.json').write_text(json.dumps(public,indent=2))
    (p/'evaluator_only.json').write_text(json.dumps({'cases':private,'reference_candidates':reference},indent=2))
    (p/'STATUS.json').write_text(json.dumps({'live_model_results':0,'tasks':12,'data_origin':'controlled pseudorandom formal testbed','scope':'Registered-family formalization and inference; not unconstrained mechanism discovery','truth_public':False},indent=2))
    return public

if __name__=='__main__':
    build(Path(__file__).parent/'pilot');print('Prepared 12 tasks; zero model results')
