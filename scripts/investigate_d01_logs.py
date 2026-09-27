"""Read-only D01 coverage investigation; never remap, reparse Drain, or run RCA."""
import csv
import gc
import gzip
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath

from inspect_rca_inputs import read_npy
from project_paths import ASSETS, PROJECT, SOURCE


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(name):
    return unicodedata.normalize("NFKC", name).strip().casefold()


def workload(name):
    # Diagnostic only: Kubernetes names alone do not prove controller identity.
    return re.sub(r"-[a-z0-9]{5}$", "", name)


def feature_entries(data):
    if "Node_Name" in data or "Pod_Name" in data:
        return [("direct_schema", data)]
    if not all(isinstance(e, dict) for e in data.values()):
        raise ValueError("Unexpected log feature schema")
    return list(data.items())


def investigate_case(case, inventory):
    manifest = read(ASSETS / PurePosixPath(case["csv"]).parent / "manifest.json")
    pods = manifest["columns"][:-1]
    with (ASSETS / case["csv"]).open(encoding="utf-8-sig") as stream:
        assert next(csv.reader(stream)) == manifest["columns"]
    expected_missing = set(case["missing_pods"])
    result = {"system": case["system"], "day": case["day"], "metric_pods": len(pods),
              "archive": case["archive"], "manifest_sha256": sha(ASSETS / PurePosixPath(case["csv"]).parent / "manifest.json"),
              "log_features": [], "pair_status": {}, "alternate_name_candidates_diagnostic_only": {}}
    with zipfile.ZipFile(ASSETS / case["archive"]) as archive:
        members = [x for x in archive.infolist() if not x.is_dir()]
        result["all_folder_file_counts"] = dict(Counter(str(PurePosixPath(x.filename).parent) for x in members))
        groups = defaultdict(lambda: defaultdict(list))
        bases = defaultdict(list)
        for item in members:
            base = PurePosixPath(item.filename.replace("\\", "/")).name
            bases[base].append(item.filename)
            for role in ("templates", "structured"):
                suffix = f"_messages_{role}.csv"
                if base.endswith(suffix):
                    groups[base[:-len(suffix)]][role].append(item.filename)
        full_pairs = {n for n,roles in groups.items() if len(roles['templates']) == len(roles['structured']) == 1}
        result['all_archive_unique_pairs'] = len(full_pairs)
        result['paired_metric_pods'] = len(set(pods) & full_pairs)
        result['log_only_pod_count'] = len(full_pairs - set(pods))
        result['metric_names_need_normalization'] = [n for n in pods if n != n.strip() or n != unicodedata.normalize('NFKC',n)]
        for pod in pods:
            matches = groups.get(pod, {})
            counts = {role: len(matches.get(role,[])) for role in ('templates','structured')}
            status = 'exact_unique_pair' if counts == {'templates':1,'structured':1} else 'both_absent' if not any(counts.values()) else 'partial_or_duplicate'
            result['pair_status'][pod] = {'status': status, 'members': dict(matches)}
            if pod in expected_missing:
                normalized = [n for n in groups if normalize(n) == normalize(pod)]
                embedded = [n for n in bases if pod in n]
                same_prefix = sorted(n for n in groups if workload(n) == workload(pod) and n != pod)
                result['alternate_name_candidates_diagnostic_only'][pod] = {'normalization_match': normalized, 'name_contains_full_pod': embedded,
                                                                          'same_stem_before_last_five_chars': same_prefix}
        observed_missing = {n for n,v in result['pair_status'].items() if v['status'] != 'exact_unique_pair'}
        assert observed_missing == expected_missing
        result['matches_prior_missing_classification'] = True
        result['status_counts'] = dict(Counter(v['status'] for v in result['pair_status'].values()))
        for item in members:
            if not item.filename.endswith('.npy'):
                continue
            with archive.open(item) as handle:
                data = read_npy(handle)
            for label, entry in feature_entries(data):
                field = 'Node_Name' if 'Node_Name' in entry else 'Pod_Name'
                names = list(entry[field])
                result['log_features'].append({'member': item.filename, 'label': str(label), 'name_field':field,
                    'pod_count':len(names), 'names':names, 'missing_pods_found': sorted(expected_missing & set(names)),
                    'names_without_pair': sorted(set(names)-full_pairs)})
            del data
        # Active candidates use the approved multi-metric union, not CPU names alone.
        recipe=read(PROJECT/'configs/rca_preprocessing_proposal.json')
        selected=set(recipe['metric_sets'][case['system']])
        names=set(); metric_checks=[]
        with zipfile.ZipFile(ASSETS / inventory['archive']) as metric_zip:
            for metric in inventory['metrics']:
                member=metric['member']
                kind=PurePosixPath(member).name.removeprefix('pod_level_data_').removesuffix('.npy')
                if kind not in selected: continue
                with metric_zip.open(member) as handle: data=read_npy(handle)
                these=set(n for entry in data.values() for n in entry['Pod_Name'])
                metric_checks.append({'member':member,'pod_count':len(these),'active_pods_absent_from_this_metric':sorted(set(pods)-these)})
                names.update(these)
                del data
            result['original_npy_name_check'] = {'metrics':metric_checks,'union_names':len(names),
                'active_pods_not_in_original':sorted(set(pods)-names), 'missing_log_pods_present_in_original':len(expected_missing & names)}
            assert not set(pods)-names
    gc.collect()
    return result


def original_cc(cases):
    case = next(c for c in cases if c['system'] == 'Cloud_Computing')
    missing = {n for n,v in case['pair_status'].items() if v['status'] != 'exact_unique_pair'}
    root = ASSETS / 'raw_downloads/huggingface_lemma_rca_cloud_computing_original'
    result = {'archive':str((root/'20231207.zip').relative_to(ASSETS)), 'files':[], 'config_pods':{},
              'missing_mentions':defaultdict(list), 'scan_scope':'all dataplane and host gzip records; full pod names, diagnostic mentions only'}
    token = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*')
    with zipfile.ZipFile(root/'20231207.zip') as archive:
        logs = [i for i in archive.infolist() if '/Log/' in i.filename and not i.is_dir()]
        result['log_category_file_counts'] = dict(Counter('/'.join(i.filename.split('/')[2:4]) for i in logs))
        result['application_entries'] = [{'member':i.filename,'bytes':i.file_size} for i in logs if '/Log/application/' in i.filename]
        for item in archive.infolist():
            if '/Configuration/' in item.filename and item.filename.endswith('.txt'):
                text = archive.read(item).decode('utf-8-sig')
                rows = [line.split() for line in text.splitlines()]
                result['config_pods'][item.filename] = {row[1]:row[0] for row in rows if len(row)>2 and row[1] in missing}
        for item in logs:
            if not item.filename.endswith('.gz') or not any('/Log/eks/'+g+'/' in item.filename for g in ('host','dataplane')):
                continue
            count=0; byte_count=0; matched=Counter(); digest=hashlib.sha256()
            with archive.open(item) as stream, gzip.GzipFile(fileobj=stream) as gz:
                for line in gz:
                    count+=1; byte_count+=len(line); digest.update(line)
                    text=line.decode('utf-8')
                    for pod in missing & set(token.findall(text)):
                        matched[pod]+=1
            record={'member':item.filename,'records':count,'decoded_bytes':byte_count,'decoded_sha256':digest.hexdigest(),'full_name_mentions':dict(matched)}
            result['files'].append(record)
            for pod,n in matched.items():
                result['missing_mentions'][pod].append({'member':item.filename,'records':n})
    result['missing_pods_with_node_log_mentions'] = sorted(result['missing_mentions'])
    result['ground_truth_or_mapping_changed'] = False
    return result


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=PROJECT/f'docs/evidence/d01_log_investigation_{stamp}.json'
    before = {str(p.relative_to(PROJECT)):sha(p) for root in [SOURCE,PROJECT/'configs'] for p in root.rglob('*') if p.is_file()}
    inputs=read(PROJECT/'docs/evidence/rca_input_connection_20260925T105701596179Z.json')
    inventory=read(PROJECT/'docs/evidence/rca_input_inventory.json')
    report={'checked_utc':stamp,'cases':[],'active_inputs_changed':False,'RCA_executed':False,'D01_policy_applied':False}
    try:
        for case in inputs['cases']:
            inv=next(i for i in inventory['cases'] if i['system']==case['system'] and i['day']==case['day'])
            result=investigate_case(case,inv)
            report['cases'].append(result)
            print(json.dumps({'case':case['day'],'status_counts':result['status_counts'],'log_features':[(e['pod_count'],len(e['missing_pods_found'])) for e in result['log_features']] }),flush=True)
        report['cc_original']=original_cc(report['cases'])
        after = {str(p.relative_to(PROJECT)):sha(p) for root in [SOURCE,PROJECT/'configs'] for p in root.rglob('*') if p.is_file()}
        report['source_and_configs_preserved'] = before == after
        assert before == after
        report['status']='INVESTIGATED_NO_LOCAL_FILENAME_FALSE_NEGATIVES_FOUND'
    except Exception as error:
        report.update(status='FAILED',error=repr(error))
        raise
    finally:
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(str(output),flush=True)


if __name__=='__main__':
    main()
