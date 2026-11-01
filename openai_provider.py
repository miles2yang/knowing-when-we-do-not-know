"""Optional Responses API transport. No calls without explicit configuration.

Standard library only. Model name is supplied by the user, not a fixed default.
The sidecar log retains response IDs, raw API responses and usage; never headers.
Reference: https://developers.openai.com/api/docs/guides/text
"""
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error
import uuid

def configuration():
    required=['OPENAI_API_KEY','OPENAI_MODEL','MODEL_RUN_LOG']
    missing=[k for k in required if not os.environ.get(k)]
    return {'ready':not missing,'missing_configuration':missing,'completed_calls':0}

def extract_text(response):
    return ''.join(c.get('text','') for item in response.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')

def call(request_data):
    state=configuration()
    if not state['ready']:raise RuntimeError('Model transport is not configured')
    limit=int(os.environ.get('OPENAI_MAX_OUTPUT_TOKENS','4096'))
    if not 128<=limit<=32768:raise ValueError('Output token ceiling must be in [128,32768]')
    timeout=int(os.environ.get('OPENAI_REQUEST_TIMEOUT_SECONDS','180'))
    if not 10<=timeout<=600:raise ValueError('Request timeout must be in [10,600] seconds')
    model_input={k:v for k,v in request_data.items() if k!='request_id'}
    payload={'model':os.environ['OPENAI_MODEL'],'input':json.dumps(model_input),'max_output_tokens':limit,'store':False}
    endpoint=os.environ.get('OPENAI_API_BASE','https://api.openai.com/v1').rstrip('/')+'/responses'
    if not endpoint.startswith('https://'):raise ValueError('API base must use HTTPS')
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json','User-Agent':os.environ.get('OPENAI_HTTP_USER_AGENT','ai-validation-local-run/2.0')},method='POST')
    record={'attempt_id':uuid.uuid4().hex,'request_id':request_data.get('request_id'),'transport':'openai_responses_api','requested_model':payload['model'],'request':payload,'started_at_unix':time.time(),'usage':None,'monetary_cost':None}
    record['endpoint']=endpoint
    start=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            body=response.read().decode();record['http_status']=response.status
        record['raw_api_response']=body
        data=json.loads(body);record['returned_model']=data.get('model');record['response_id']=data.get('id');record['response_status']=data.get('status');record['usage']=data.get('usage')
        return extract_text(data)
    except urllib.error.HTTPError as e:
        record['http_status']=e.code;record['raw_api_response']=e.read().decode(errors='replace')
        raise RuntimeError('Provider returned an HTTP error') from None
    except Exception as e:
        record['transport_error']=type(e).__name__
        raise RuntimeError('Provider execution failed') from None
    finally:
        record['elapsed_seconds']=time.monotonic()-start
        path=Path(os.environ['MODEL_RUN_LOG']);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a') as f:f.write(json.dumps(record)+'\n')

def main():
    if '--preflight' in sys.argv:
        print(json.dumps(configuration()));return 0
    try:
        raw=call(json.load(sys.stdin));sys.stdout.write(raw);return 0
    except Exception as e:
        print(str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
