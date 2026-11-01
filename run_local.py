"""Local interactive runner. No credentials are written to files."""
import argparse
from datetime import datetime,timezone
import getpass
import json
import os
from pathlib import Path
import sys
import uuid
from openai_provider import call
from pilot_runner import run_pilot
from candidate_loop import SCHEMA
from summarize_run import summarize,bundle

ROOT=Path(__file__).resolve().parent

def main(argv=None):
    ap=argparse.ArgumentParser(description='Run the organizational-mechanism pilot locally')
    ap.add_argument('--model',help='Exact model ID available to your API account')
    ap.add_argument('--tasks',type=int,choices=[1,12],help='1 task / 4 requests or 12 tasks / 48 requests')
    ap.add_argument('--max-output-tokens',type=int,default=4096)
    ap.add_argument('--dry-run',action='store_true',help='No key required and no network calls')
    args=ap.parse_args(argv)
    if sys.version_info<(3,10):raise RuntimeError('Python 3.10 or later is required')
    if not 128<=args.max_output_tokens<=32768:raise ValueError('Token ceiling must be in [128,32768]')
    tasks=json.loads((ROOT/'pilot/public_tasks.json').read_text(encoding='utf-8'))
    oracle=json.loads((ROOT/'pilot/evaluator_only.json').read_text(encoding='utf-8'))
    count=args.tasks
    if count is None:
        count=1 if args.dry_run else int(input('Tasks: 1 = small connection run (4 calls), 12 = full pilot (48 calls) [1]: ').strip() or '1')
    if count not in (1,12):raise ValueError('Choose 1 or 12 tasks')
    tasks=tasks[:count]
    model=args.model or os.environ.get('OPENAI_MODEL')
    if not model:
        model='not_selected_dry_run' if args.dry_run else input('OpenAI model ID: ').strip()
    if not model:raise ValueError('A model ID is required')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    output=ROOT/'results'/stamp
    metadata={'model_requested':model,'tasks':count,'repetitions':1,'planned_requests':4*count,
        'max_output_tokens':args.max_output_tokens,'mode':'dry_run_no_generation' if args.dry_run else 'live_api_requested',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version.split()[0],
        'sampling_configuration':'API defaults; fixed output ceiling; no reasoning or temperature overrides',
        'task_scope':'Disclosed registered-family formalization and inference',
        'credential_saved':False,'protocol_version':SCHEMA,
        'api_base':os.environ.get('OPENAI_API_BASE','https://api.openai.com/v1')}
    if args.dry_run:
        output.mkdir(parents=True)
        metadata['completed_model_calls']=0
        (output/'configuration.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        print('Dry run completed: model calls = 0')
        print('Output:',output)
        return 0
    old={k:os.environ.get(k) for k in ['OPENAI_API_KEY','OPENAI_MODEL','MODEL_RUN_LOG','OPENAI_MAX_OUTPUT_TOKENS']}
    key=old['OPENAI_API_KEY'] or getpass.getpass('OpenAI API key (hidden input): ').strip()
    if not key:raise ValueError('An API key is required')
    os.environ['OPENAI_API_KEY']=key
    os.environ['OPENAI_MODEL']=model
    os.environ['MODEL_RUN_LOG']=str(output/'provider_calls.jsonl')
    os.environ['OPENAI_MAX_OUTPUT_TOKENS']=str(args.max_output_tokens)
    stopped={'value':False};calls={'value':0}
    def invoke(request):
        calls['value']+=1
        print(f"[{calls['value']}/{4*count}] Calling model for {request['public_task']['task_id']}...",flush=True)
        try:return call(request)
        except Exception:
            stopped['value']=True
            raise
    try:
        records,status=run_pilot(tasks,oracle,invoke,output,configuration=model,transport='openai_responses_api',stop_requested=lambda:stopped['value'])
        metadata['provider_requests_attempted']=calls['value']
        metadata['completed_run']=status.get('completed_run',True)
        (output/'configuration.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        report=summarize(output);archive=bundle(output)
        print('Saved results:',archive)
        print('Initial outputs eligible for substantive checker feedback:',report['initial_outputs_eligible_for_evidence_feedback'],'/',count)
        if report['initial_outputs_eligible_for_evidence_feedback']<count:
            print('Some evidence-arm revisions received only format feedback. Preserve these failures; do not interpret them as tests of substantive feedback.')
        if stopped['value']:
            print('Stopped after a provider error. The failed attempt is retained. Inspect provider_calls.jsonl for the error; no automatic retry was made.')
            return 1
        print('Send the results ZIP back for analysis. No API key is included.')
        return 0
    finally:
        for k,v in old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nInterrupted. Preserve partial logs in results/.');raise SystemExit(130)
    except Exception as e:
        print('Run error:',type(e).__name__,str(e),file=sys.stderr);raise SystemExit(1)
