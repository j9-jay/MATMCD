"""Read reproducibly selected raw PR JSON samples; positive matches are evidence, absence is not exhaustive."""
import hashlib
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import PurePosixPath

from inspect_pr_remote_archive import RangeReader
from project_paths import ASSETS, PROJECT


def main():
    index=json.loads((PROJECT/'docs/evidence/d01_pr_original_remote_index.json').read_text(encoding='utf-8'))
    coverage=json.loads((PROJECT/'docs/evidence/d01_log_investigation_20260925T114438415224Z.json').read_text(encoding='utf-8'))
    report={'checked_utc':datetime.now(timezone.utc).isoformat(),'selection':'sorted raw infra JSON: first/middle/last; app JSON: middle; days with non-nested raw JSON',
            'full_archive_sha256_verified':False,'exhaustive_raw_scan':False,'samples':[],'inputs_changed':False}
    for case in index['cases']:
        if case['day'] not in ('20210517','20211203'):continue
        missing={n for c in coverage['cases'] if c['day']==case['day'] for n,v in c['pair_status'].items() if v['status']=='both_absent'}
        selected=[]
        for category in ('infra','app'):
            names=sorted(e['member'] for e in case['entries'] if '/Log/' in e['member'] and '/'+category+'-' in e['member'] and e['member'].endswith('.json'))
            indices=[0,len(names)//2,len(names)-1] if category=='infra' else [len(names)//2]
            selected += [(category,names[i]) for i in sorted(set(indices))] if names else []
        reader=RangeReader(case['url'],case['archive_bytes'])
        with zipfile.ZipFile(reader) as archive:
            for category,name in selected:
                info=archive.getinfo(name)
                if info.file_size>80*1024*1024:raise ValueError('Sample too large for bounded inspection')
                raw=archive.read(name)  # zipfile checks this complete member CRC.
                destination=ASSETS/'raw_downloads/huggingface_lemma_rca_product_review_original/diagnostic_samples'/case['day']/PurePosixPath(name).name
                destination.parent.mkdir(parents=True,exist_ok=True)
                if destination.exists():
                    if destination.read_bytes()!=raw:raise RuntimeError('Existing raw sample differs')
                else:destination.write_bytes(raw)
                data=json.loads(raw)
                hits=data['hits']['hits']; own=Counter(); namespaces=Counter(); missing_counts=Counter(); times=[]; schemas=Counter()
                for hit in hits:
                    source=hit['_source']; kub=source.get('kubernetes',{})
                    pod=kub.get('pod_name')
                    schemas[','.join(sorted(source))]+=1
                    if '@timestamp' in source:times.append(source['@timestamp'])
                    if pod:
                        own[pod]+=1; namespaces[kub.get('namespace_name','<not available>')]+=1
                        if pod in missing:missing_counts[pod]+=1
                result={'day':case['day'],'category':category,'url':case['url'],'member':name,
                    'saved_path':str(destination.relative_to(ASSETS)),'bytes':len(raw),'compressed_bytes':info.compress_size,'member_crc32':f'{info.CRC:08x}',
                    'member_crc_verified':True,'sha256':hashlib.sha256(raw).hexdigest(),'hit_count':len(hits),'pod_count':len(own),
                    'source_pod_record_counts':dict(own),'namespace_record_counts':dict(namespaces),'previously_missing_pod_record_counts':dict(missing_counts),
                    'time_min':min(times) if times else None,'time_max':max(times) if times else None,'source_schema_counts':dict(schemas)}
                report['samples'].append(result)
                print(json.dumps({k:result[k] for k in ('day','category','hit_count','pod_count','previously_missing_pod_record_counts','time_min','time_max')},ensure_ascii=False),flush=True)
    output=PROJECT/'docs/evidence/d01_pr_raw_log_samples.json'
    if output.exists():raise FileExistsError(output)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(str(output),flush=True)


if __name__=='__main__':main()
