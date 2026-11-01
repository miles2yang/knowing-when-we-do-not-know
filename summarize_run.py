"""Descriptive pilot summary. Missing usage or costs are never entered as zero."""
import csv
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from pilot_runner import ARMS

def summarize(directory):
    root=Path(directory)
    rows=[json.loads(line) for line in (root/'attempts.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    sidecar=root/'provider_calls.jsonl'
    providers=[json.loads(line) for line in sidecar.read_text(encoding='utf-8').splitlines() if line.strip()] if sidecar.exists() else []
    usage_by_id={r.get('request_id'):r.get('usage') for r in providers if r.get('request_id')}
    results=[]
    for arm in ARMS:
        armrows=[r for r in rows if r['arm']==arm]
        item={'arm':arm,'records':len(armrows),'transport_failures':0,'invalid_specifications':0,'profile_mismatches':0,'unsupported_registered_claims':0,'supported_conditional_claims':0,'unnecessary_abstentions':0,'usage_records':0,'input_tokens_reported':0,'output_tokens_reported':0,'total_tokens_reported':0,'monetary_cost':'not_computed'}
        for r in armrows:
            e=r['evaluation'];status=e['checker']['status']
            item['transport_failures']+=int(status=='transport_failure')
            item['invalid_specifications']+=int(status=='invalid_specification')
            item['profile_mismatches']+=int(e.get('formal_profiles_match_reference') is False)
            for key,col in [('unsupported_registered_claim','unsupported_registered_claims'),('supported_conditional_claim','supported_conditional_claims'),('unnecessary_abstention','unnecessary_abstentions')]:item[col]+=int(e.get(key,False))
            u=usage_by_id.get(r['attempt']['request']['request_id'])
            if u:
                item['usage_records']+=1
                for key in ['input_tokens','output_tokens','total_tokens']:item[key+'_reported']+=u.get(key,0)
        if item['usage_records']==0:
            for key in ['input_tokens','output_tokens','total_tokens']:item[key+'_reported']='not_available'
        results.append(item)
    with (root/'summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    eligible=sum(r['arm']=='initial' and not r['evaluation']['format_or_transport_failure'] for r in rows)
    delivered=sum(r['arm']=='evidence_feedback' and bool(r['attempt']['request'].get('previous_attempts')) and r['attempt']['request']['previous_attempts'][0]['feedback']['status'] not in ['invalid_specification','transport_failure'] for r in rows)
    report={'records':len(rows),'provider_log_entries':len(providers),'returned_model_names':sorted({r['returned_model'] for r in providers if r.get('returned_model')}),'arms':results,
        'initial_outputs_eligible_for_evidence_feedback':eligible,'revisions_with_substantive_evidence_feedback':delivered,
        'failure_interpretation':'Unsupported claims and supported claims are assessed only on format-valid outputs; zero counts among invalid outputs do not establish safe abstention. Evidence-arm revisions following an invalid initial answer receive only format feedback.',
        'interpretation':'Descriptive constructed-task results only. Shared initial outputs and paired cases are dependent. No significance tests or general AI superiority claim.',
        'scope':'Formalization and inference in the disclosed registered family; not unrestricted mechanism discovery.',
        'missing_cost':'not_computed; verify applicable pricing before calculating monetary cost'}
    (root/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['Pilot summary','',f'Recorded arm outputs: {len(rows)}',f'Provider log entries: {len(providers)}','']
    for r in results:lines.append(f"{r['arm']}: records={r['records']}, invalid={r['invalid_specifications']}, transport failures={r['transport_failures']}, unsupported claims={r['unsupported_registered_claims']}, supported conditional claims={r['supported_conditional_claims']}")
    lines+=['',f'Initial outputs eligible for evidence feedback: {eligible}',f'Revisions actually receiving substantive evidence feedback: {delivered}',report['failure_interpretation'],report['interpretation'],report['scope'],'Monetary cost: not computed. Missing usage is not zero.']
    (root/'summary.txt').write_text('\n'.join(lines),encoding='utf-8')
    return report

def bundle(directory):
    root=Path(directory);target=root.parent/(root.name+'_results.zip')
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for p in sorted(root.iterdir()):
            if p.is_file():z.write(p,root.name+'/'+p.name)
        assert z.testzip() is None
    return target

if __name__=='__main__':
    import sys
    summarize(sys.argv[1]);print(bundle(sys.argv[1]))
