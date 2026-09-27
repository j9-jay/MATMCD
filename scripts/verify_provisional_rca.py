"""Audit prepared artifacts against raw KPI/timestamps and preserved sources.

Does not run SPOT, causal discovery, RCA, or APIs. Failure records are verified
as failures, never treated as prepared inputs.
"""
import csv
import json
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from inspect_rca_inputs import read_npy
from prepare_provisional_rca import get_recipe, log_matches, require, runtime, sha, write_json
from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from rca_case_scope import select_active_cases, validate_input_scope


def verify_runtime_mapping(cases):
    """Accept the historical unlinked stage or the now-authorized exact links."""
    inputs = json.loads((PROJECT / 'configs/inputs.json').read_text(encoding='utf-8'))
    if not inputs['rca_files']:
        return 'HISTORICAL_UNLINKED_STAGE'
    validate_input_scope(inputs)
    expected = {f'LEMMA_RCA/{c["system"]}/Metrics/{c["system"]}_{c["day"]}.csv':
                f'{c["output_directory"]}/{c["system"]}_{c["day"]}.csv' for c in cases}
    require(inputs.get('input_profile') == 'lemma_rca_provisional_v1', 'Unexpected runtime input profile')
    require(inputs.get('author_equivalence') == 'UNCONFIRMED', 'Provisional inputs must not claim author equivalence')
    require(inputs['rca_files'] == expected, 'Runtime mapping differs from verified provisional cases')
    for name, relative in expected.items():
        target = asset_path('runtime_workspace') / 'data' / name
        require(target.is_symlink() and target.resolve() == (ASSETS / relative).resolve(), f'Runtime link differs: {name}')
    return 'VERIFIED_PROVISIONAL_LINKS'


def main():
    runtime()
    recipe = get_recipe()
    summary_path = PROJECT / 'docs/evidence/rca_preprocessing_applied.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              'preparation_summary_sha256': sha(summary_path), 'checks': {}, 'cases': [],
              'author_equivalence': 'UNCONFIRMED', 'experiments_executed': False, 'API_called': False}
    upstream = json.loads((PROJECT / 'configs/upstream.json').read_text(encoding='utf-8'))
    scope = json.loads((PROJECT / 'configs/scope.json').read_text(encoding='utf-8'))
    source_zip = ASSETS / 'raw_downloads/github_d2i_matmcd/ef2c3ec.zip'
    require(sha(source_zip) == upstream['source_archive_sha256'], 'Official archive changed')
    expected_files = set()
    with zipfile.ZipFile(source_zip) as archive:
        archive_files = {item.filename for item in archive.infolist() if not item.is_dir()}
        require(set(scope['excluded_official_files']) <= archive_files, 'Excluded names absent from pinned archive')
        for item in archive.infolist():
            if item.is_dir():
                continue
            # This pinned archive is already rooted at Client/, Utils/, etc.
            # Preserve its names exactly, as scripts/audit_setup.py does.
            name = item.filename
            if name in scope['excluded_official_files']:
                continue
            expected_files.add(name)
            require((SOURCE / name).read_bytes() == archive.read(item), f'Official source changed: {name}')
    actual_files = {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
    require(actual_files == expected_files, 'Official file set differs from approved scope')
    report['checks']['official_37_files_match_pinned_archive'] = len(expected_files) == 37
    for name, expected_hash in summary['native']['source']['files'].items():
        require(sha(ASSETS / name) == expected_hash, f'LEMMA source changed: {name}')
    report['checks']['LEMMA_source_preserved'] = True
    require(summary['recipe_sha256'] == sha(PROJECT / 'configs/rca_preprocessing_proposal.json'), 'Recipe changed since run')
    require(summary['implementation_sha256'] == sha(PROJECT / 'scripts/prepare_provisional_rca.py'), 'Preparer changed since run')
    report['checks']['recipe_and_implementation_match_run'] = True
    for result in select_active_cases(summary['cases'], key=lambda result: result['case']):
        case = result['case']
        recorded = json.loads((ASSETS / result['report']).read_text(encoding='utf-8'))
        entry = {'system': case['system'], 'day': case['day'], 'preparation_status': result['status']}
        if result['status'] != 'PREPARED_PROVISIONAL':
            require(recorded['status'] == 'FAILED', 'Failed case incorrectly marked ready')
            entry['failure_preserved'] = True
            entry['stage'] = recorded.get('stage', 'worker_exit')
            entry['error'] = recorded.get('error')
            entry['input_ready'] = False
            report['cases'].append(entry)
            continue
        directory = ASSETS / result['output_directory']
        require(sha(directory / 'manifest.json') == result['manifest_sha256'], 'Manifest hash mismatch')
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        for name, artifact in manifest['outputs'].items():
            require(sha(directory / name) == artifact['sha256'] and (directory / name).stat().st_size == artifact['bytes'],
                    f'Output changed: {name}')
        expected_pods = sorted(p for p, decision in manifest['pod_decisions'].items() if decision['retained'])
        columns = expected_pods + [recipe['kpi']['column_name']]
        require(columns == manifest['columns'], 'Pod column order mismatch')
        for pod, decision in manifest['pod_decisions'].items():
            channels = [c for c in manifest['channels'] if c['pod'] == pod]
            require(decision['retained'] == any(c['positive_scores'] > 0 for c in channels), 'EVT decision mismatch')
            require(decision['nonconstant_channels'] == sum(c['status'] == 'DETECTED' for c in channels), 'Channel count mismatch')
        with (directory / f'{case["system"]}_{case["day"]}.csv').open(encoding='utf-8') as handle:
            require(next(csv.reader(handle)) == columns, 'CSV header mismatch')
            data = np.loadtxt(handle, delimiter=',', ndmin=2)
        timestamps = np.loadtxt(directory / 'timestamps.csv', delimiter=',', skiprows=1, ndmin=1)
        require(data.shape == (case['expected_aligned_rows'], len(columns)), 'CSV shape mismatch')
        require(len(timestamps) == len(data) and np.all(timestamps[1:] > timestamps[:-1]), 'Invalid time axis')
        require(np.isfinite(data).all() and np.all(np.std(data, axis=0) != 0), 'Invalid CSV numeric values')
        # Independent comparison to published CPU KPI; no processing-result copy is used.
        metric_archive = ASSETS / manifest['source_archives']['Metrics Data']['path']
        with zipfile.ZipFile(metric_archive) as archive:
            member = manifest['metrics']['cpu_usage']['member']
            with archive.open(member) as handle:
                raw = read_npy(handle)[case['kpi_key']]
        raw_times = np.asarray(raw['time'])
        positions = np.searchsorted(raw_times, timestamps)
        require(np.array_equal(raw_times[positions], timestamps), 'Generated timestamp absent from raw data')
        require(np.array_equal(np.asarray(raw['Sequence'])[positions, -1], data[:, -1]), 'KPI values changed')
        # Same CSV reader/options as the unchanged Utils.data.load_Lemma_data.
        # Do not change its parser precision or wire the original runtime inputs.
        frame = pd.read_csv(directory / f'{case["system"]}_{case["day"]}.csv', header=0)
        require(list(frame.columns) == columns and frame.shape == data.shape, 'Original reader format mismatch')
        parsed = frame.to_numpy()
        require(np.isfinite(parsed).all(), 'Original reader produced nonfinite data')
        reader = {'pandas_version': pd.__version__, 'options': {'header': 0},
                  'shape_and_columns_match': True, 'finite': True,
                  'exact_equal_to_roundtrip_reader': bool(np.array_equal(parsed, data)),
                  'different_values': int(np.count_nonzero(parsed != data)),
                  'maximum_absolute_difference': float(np.max(np.abs(parsed - data))),
                  'KPI_maximum_absolute_difference': float(np.max(np.abs(parsed[:, -1] - data[:, -1]))),
                  'source': 'official/matmcd/Utils/data.py:load_Lemma_data pd.read_csv call; original path not changed'}
        del frame, parsed
        logs = log_matches(manifest['source_archives']['Log Data'], expected_pods)
        require(logs == manifest['logs'], 'Exact log inventory differs')
        entry.update(input_ready=True, rows=len(data), retained_pods=len(expected_pods),
                     exact_raw_KPI=True, sorted_unique_times=True, output_hashes_valid=True,
                     EVT_decisions_consistent=True, log_pair_matches=logs['matched_unique_pairs'],
                     missing_log_pairs=len(logs['missing_or_ambiguous']), log_input_ready=False,
                     original_reader_check=reader,
                     output_directory=result['output_directory'], outputs=manifest['outputs'],
                     manifest_sha256=result['manifest_sha256'])
        report['cases'].append(entry)
        print(f'Verified {case["day"]}: {len(data)} rows, {len(expected_pods)} pods', flush=True)
    report['runtime_mapping_stage'] = verify_runtime_mapping(report['cases'])
    report['checks']['runtime_mapping_matches_current_authorized_stage'] = True
    report['task_states_at_verification'] = {}
    for number in ('007', '008', '009', '018'):
        task = next((PROJECT / 'tasks').glob(f'TASK_{number}_*.md')).read_text(encoding='utf-8')
        report['task_states_at_verification'][number] = task.split('## 상태')[-1].strip()
    report['checks']['runtime_preserved_201_packages'] = len(runtime()['packages']) == 201
    report['checked_source_sha256'] = {name: sha(PROJECT / name) for name in (
        'scripts/prepare_provisional_rca.py', 'scripts/verify_provisional_rca.py',
        'scripts/inspect_rca_inputs.py', 'scripts/project_paths.py',
        'configs/paths.json', 'configs/upstream.json', 'docs/evidence/downloads.json')}
    report['all_checks_pass'] = all(report['checks'].values())
    report['prepared_case_count'] = sum(c['input_ready'] for c in report['cases'])
    report['all_five_metric_inputs_ready'] = report['prepared_case_count'] == 5
    output = PROJECT / 'docs/evidence/rca_preprocessing_validation.json'
    if output.exists():
        output = PROJECT / ('docs/evidence/rca_preprocessing_revalidation_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    write_json(output, report)
    print(f'Artifact audit passed; prepared inputs: {report["prepared_case_count"]}/5', flush=True)
    return 0 if report['all_checks_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
