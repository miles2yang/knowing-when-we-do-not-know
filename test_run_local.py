import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from build_pilot_tasks import build
from test_candidate_loop import candidates
import run_local
import openai_provider

class LocalRunTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        build(self.root/'pilot')
        self.root_patch=patch.object(run_local,'ROOT',self.root)
        self.root_patch.start()
        self.env_patch=patch.dict(os.environ,{},clear=True)
        self.env_patch.start()
    def tearDown(self):
        self.env_patch.stop();self.root_patch.stop();self.temp.cleanup()
    def execute(self,args):
        with contextlib.redirect_stdout(io.StringIO()):return run_local.main(args)
    def directory(self):return next(p for p in (self.root/'results').iterdir() if p.is_dir())
    def test_dry_run_needs_no_key_and_makes_no_calls(self):
        with patch.object(run_local,'call',side_effect=AssertionError('Unexpected API call')),patch.object(run_local.getpass,'getpass',side_effect=AssertionError('Unexpected key prompt')):
            self.assertEqual(self.execute(['--dry-run','--tasks','12']),0)
        config=json.loads((self.directory()/'configuration.json').read_text())
        self.assertEqual(config['completed_model_calls'],0)
        self.assertEqual(config['planned_requests'],48)
        self.assertFalse(config['credential_saved'])
    def test_full_mock_run_keeps_48_outputs_and_usage_without_key(self):
        secret='test-only-credential-never-persist'
        calls=[]
        def fake(request):
            calls.append(request)
            with Path(os.environ['MODEL_RUN_LOG']).open('a') as f:
                f.write(json.dumps({'request_id':request['request_id'],'returned_model':'mock-version','usage':{'input_tokens':10,'output_tokens':20,'total_tokens':30}})+'\n')
            return json.dumps(candidates())
        with patch.object(run_local.getpass,'getpass',return_value=secret),patch.object(run_local,'call',side_effect=fake):
            self.assertEqual(self.execute(['--model','mock-model','--tasks','12']),0)
        self.assertEqual(len(calls),48)
        self.assertNotIn('OPENAI_API_KEY',os.environ)
        report=json.loads((self.directory()/'summary.json').read_text())
        self.assertEqual(report['records'],48)
        self.assertEqual(report['initial_outputs_eligible_for_evidence_feedback'],12)
        self.assertEqual(report['revisions_with_substantive_evidence_feedback'],12)
        self.assertTrue(all(r['records']==12 and r['total_tokens_reported']==360 for r in report['arms']))
        archives=list((self.root/'results').glob('*_results.zip'))
        self.assertEqual(len(archives),1)
        with ZipFile(archives[0]) as z:
            self.assertIsNone(z.testzip())
            self.assertTrue(all(secret.encode() not in z.read(name) for name in z.namelist()))
    def test_provider_failure_stops_after_first_request_and_keeps_failure(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-secret'}),patch.object(run_local,'call',side_effect=RuntimeError('Provider returned an HTTP error')) as fake:
            self.assertEqual(self.execute(['--model','mock','--tasks','12']),1)
            self.assertEqual(fake.call_count,1)
        status=json.loads((self.directory()/'run_status.json').read_text())
        self.assertFalse(status['completed_run'])
        self.assertEqual(status['records'],1)
        report=json.loads((self.directory()/'summary.json').read_text())
        self.assertEqual(report['arms'][0]['transport_failures'],1)
        self.assertEqual(report['arms'][0]['total_tokens_reported'],'not_available')
    def test_invalid_model_output_is_retained_without_stopping(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-secret'}),patch.object(run_local,'call',return_value='broken') as fake:
            self.assertEqual(self.execute(['--model','mock','--tasks','1']),0)
            self.assertEqual(fake.call_count,4)
        report=json.loads((self.directory()/'summary.json').read_text())
        self.assertTrue(all(r['invalid_specifications']==1 for r in report['arms']))
        self.assertEqual(report['revisions_with_substantive_evidence_feedback'],0)
    def test_configured_proxy_endpoint_is_logged_without_credential(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps({'model':'proxy/alias','output':[],'usage':None}).encode()
        log=self.root/'proxy.jsonl'
        with patch.dict(os.environ,{'OPENAI_API_KEY':'proxy-secret','OPENAI_MODEL':'alias','MODEL_RUN_LOG':str(log),'OPENAI_API_BASE':'https://example.org/v1'}),patch.object(openai_provider.urllib.request,'urlopen',return_value=Response()) as mocked:
            openai_provider.call({'request_id':'proxy-test'})
        request=mocked.call_args.args[0]
        self.assertEqual(request.full_url,'https://example.org/v1/responses')
        self.assertTrue(request.get_header('User-agent'))
        self.assertEqual(json.loads(log.read_text())['endpoint'],request.full_url)
        self.assertNotIn('proxy-secret',log.read_text())
    def test_provider_posts_to_expected_endpoint_and_does_not_log_headers(self):
        secret='mock-api-credential-only'
        payload={'model':'mock-returned','id':'resp_mock','status':'completed','usage':{'input_tokens':5,'output_tokens':7,'total_tokens':12},'output':[{'type':'message','content':[{'type':'output_text','text':'test output'}]}]}
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps(payload).encode()
        def urlopen(request,timeout):
            self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
            self.assertEqual(request.get_header('Authorization'),'Bearer '+secret)
            sent=json.loads(request.data)
            self.assertFalse(sent['store'])
            self.assertNotIn('request_id',json.loads(sent['input']))
            self.assertEqual(timeout,180)
            return Response()
        logfile=self.root/'provider.jsonl'
        with patch.dict(os.environ,{'OPENAI_API_KEY':secret,'OPENAI_MODEL':'mock','MODEL_RUN_LOG':str(logfile)}),patch.object(openai_provider.urllib.request,'urlopen',side_effect=urlopen):
            self.assertEqual(openai_provider.call({'request_id':'req_1','public_task':{'task_id':'mock'}}),'test output')
        content=logfile.read_text()
        self.assertNotIn(secret,content)
        self.assertNotIn('Authorization',content)
        self.assertEqual(json.loads(content)['usage']['total_tokens'],12)

if __name__=='__main__':unittest.main()
