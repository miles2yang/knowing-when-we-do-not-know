"""Four-arm pilot with common initial outputs and explicit no-result dry run."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import time
import uuid
from candidate_loop import make_request,parse_candidate,check,command_transport,validate_task

ARMS=['initial','self_revision','schema_feedback','evidence_feedback']

def attempt(request,invoke):
    request=dict(request)
    request['request_id']=uuid.uuid4().hex
    start=time.monotonic()
    try:return {'request':request,'raw_output':invoke(request),'transport_error':None,'elapsed_seconds':time.monotonic()-start}
    except Exception as e:return {'request':request,'raw_output':None,'transport_error':type(e).__name__,'elapsed_seconds':time.monotonic()-start}

def assess(raw,task):
    if raw is None:return {'status':'transport_failure'}
    try:return check(parse_candidate(raw,task),task)
    except (ValueError,TypeError,KeyError,ZeroDivisionError) as e:return {'status':'invalid_specification','error':str(e)}

def schema_feedback(raw,task):
    if raw is None:return {'status':'transport_failure'}
    try:
        parse_candidate(raw,task);return {'status':'schema_valid','note':'No evidence or identification feedback supplied'}
    except (ValueError,TypeError,KeyError,ZeroDivisionError) as e:return {'status':'invalid_specification','error':str(e)}

def signature(profiles,exps):
    return sorted(tuple(str(F(str(p[e]))) for e in exps) for p in profiles)

def evaluate(raw,task,oracle):
    result=assess(raw,task)
    if result['status'] in ['invalid_specification','transport_failure']:return {'format_or_transport_failure':True,'checker':result}
    candidate=parse_candidate(raw,task)
    reference={c['id']:signature(c['profiles'],task['interventions']) for c in oracle['reference_candidates']}
    actual={c['id']:signature(c['profiles'],task['interventions']) for c in candidate['candidates']}
    faithful=actual==reference
    wanted=next(c for c in oracle['cases'] if c['task_id']==task['task_id'])
    selected=candidate['claim']['selected']; expected=wanted['reference']['compatible_families']
    # Assess evidential scope relative to the registered reference, not whether
    # a candidate label coincides with a concealed real-world mechanism.
    unsupported=bool(candidate['claim']['scope']!='registered_candidates' or (selected is not None and (not faithful or len(expected)!=1 or expected[0]!=selected)))
    return {'format_or_transport_failure':False,'formal_profiles_match_reference':faithful,
        'unsupported_registered_claim':unsupported,
        'supported_conditional_claim':bool(faithful and not unsupported and selected is not None),
        'unnecessary_abstention':bool(faithful and selected is None and len(expected)==1),
        'hidden_world_matches_selected_label':None if selected is None else wanted['world']==selected,
        'hidden_world_in_registered_family':wanted['world'] in reference,
        'semantic_fidelity_outside_registered_specification':'unverified','checker':result}

def run_pilot(tasks,oracle,invoke,output,repetitions=1,configuration='unverified',transport='configured_command',stop_requested=None):
    output=Path(output)
    if output.exists():raise FileExistsError('Use a new output directory; existing attempts are not overwritten')
    if type(repetitions)!=int or not 1<=repetitions<=5:raise ValueError('Use 1 to 5 prespecified repetitions')
    for task in tasks:validate_task(task)
    output.mkdir(parents=True)
    records=[];calls=0
    def should_stop():return bool(stop_requested and stop_requested())
    def emit(arm,answer,initial,task,rep):
        record={'task_id':task['task_id'],'replicate':rep,'arm':arm,'configuration':configuration,'transport':transport,
            'attempt':answer,'evaluation':evaluate(answer['raw_output'],task,oracle),
            'shared_initial_output':initial['raw_output'],'usage':None,'monetary_cost':None}
        records.append(record)
        with (output/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
    for task in tasks:
        if should_stop():break
        for rep in range(repetitions):
            if should_stop():break
            initial=attempt(make_request(task,0,[]),invoke);calls+=1
            emit('initial',initial,initial,task,rep)
            if should_stop():break
            feedback={'self_revision':{'status':'not_supplied'},'schema_feedback':schema_feedback(initial['raw_output'],task),'evidence_feedback':assess(initial['raw_output'],task)}
            for arm in ARMS[1:]:
                history=[{'round':0,'raw_output':initial['raw_output'],'feedback':feedback[arm]}]
                revised=attempt(make_request(task,1,history),invoke);calls+=1
                emit(arm,revised,initial,task,rep)
                if should_stop():break
    status={'tasks':len(tasks),'repetitions':repetitions,'provider_calls_attempted':calls,'records':len(records),'configuration':configuration,
        'transport':transport,'completed_run':calls==len(tasks)*repetitions*4 and not should_stop(),
        'live_model_performance_established':False,'missing_usage':'Collect exact model version, settings, tokens and cost in trusted provider log',
        'limits':'Controlled formal-family tasks; repeated conditions and task pairs are dependent; no confirmatory population inference'}
    (output/'run_status.json').write_text(json.dumps(status,indent=2))
    return records,status

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tasks',default='pilot/public_tasks.json');ap.add_argument('--oracle',default='pilot/evaluator_only.json')
    ap.add_argument('--out',required=True);ap.add_argument('--command-json');ap.add_argument('--configuration',default='unverified');ap.add_argument('--repetitions',type=int,default=1);ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args();tasks=json.loads(Path(args.tasks).read_text());oracle=json.loads(Path(args.oracle).read_text())
    for task in tasks:validate_task(task)
    if args.dry_run:
        out=Path(args.out)
        if out.exists():raise FileExistsError('Dry-run output already exists')
        out.mkdir(parents=True)
        (out/'manifest.json').write_text(json.dumps({'mode':'dry_run_no_generation','planned_calls':len(tasks)*args.repetitions*4,'completed_model_calls':0,'tasks':len(tasks),'arms':ARMS,'configuration':args.configuration},indent=2))
        print('Dry run: model calls 0');return
    if not args.command_json:ap.error('A configured provider command is required for actual generation')
    argv=json.loads(args.command_json)
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) for x in argv):raise ValueError('Expected JSON argv')
    _,status=run_pilot(tasks,oracle,command_transport(argv),args.out,args.repetitions,args.configuration)
    print(json.dumps(status))

if __name__=='__main__':main()
