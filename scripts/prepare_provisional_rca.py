"""Approved, explicitly provisional RCA input preparation; never runs RCA.

The upstream spot_detection AST is executed without edits or importing rca.py's
unrelated causal-discovery dependencies. Each channel has its own DSpot object,
exactly as in that function. Native workers are isolated so failures are recorded.
"""
import argparse
import ast
import csv
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np

from inspect_rca_inputs import array_hash, read_npy
from project_paths import ASSETS, PROJECT, SOURCE, asset_path

RECIPE = PROJECT / 'configs/rca_preprocessing_proposal.json'
SUPPORTED_RECIPE = 'fc8a9192a29d487ff2196f659213497fe6ab9f40a884fe8a8fe983b5af05e60a'


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, value, exclusive=False):
    with Path(path).open('x' if exclusive else 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path):
    return str(Path(path).relative_to(ASSETS))


def get_recipe():
    recipe = json.loads(RECIPE.read_text(encoding='utf-8'))
    # This implementation supports the approved v1 only; never ignore a changed option.
    digest = hashlib.sha256(json.dumps(recipe, sort_keys=True, ensure_ascii=True,
                                      separators=(',', ':')).encode()).hexdigest()
    require(digest == SUPPORTED_RECIPE, 'Recipe differs from approved v1; review implementation before use')
    require(recipe['implementation_approved'] and not recipe['execution_limits']['proposal_only'],
            'Preprocessing has not been approved')
    require(all(not v for k, v in recipe['execution_limits'].items()), 'Experiments/APIs must remain disabled')
    return recipe


def runtime():
    require(sys.platform == 'linux' and Path(sys.prefix) == asset_path('environment'),
            'Use the existing WSL reproduction environment')
    packages = {d.metadata['Name'].lower().replace('_', '-'): d.version
                for d in importlib.metadata.distributions()}
    expected = {}
    for line in (PROJECT / 'docs/evidence/installed_freeze_with_openai_embeddings.txt').read_text().splitlines():
        if '==' in line:
            name, version = line.split('==', 1)
            expected[name.lower().replace('_', '-')] = version
    require(packages == expected, 'Installed packages differ from the last approved freeze')
    require(platform.python_version() == '3.11.13' and np.__version__ == '2.2.6', 'Runtime version changed')
    return {'python': platform.python_version(), 'numpy': np.__version__,
            'platform': platform.platform(), 'packages': packages,
            'freeze_sha256': sha(PROJECT / 'docs/evidence/installed_freeze_with_openai_embeddings.txt')}


def load_spot(recipe):
    upstream = json.loads((PROJECT / 'configs/upstream.json').read_text(encoding='utf-8'))
    entry = next(s for s in upstream['sources'] if s['id'] == 'lemma_preprocessing')
    require(entry['commit'] == recipe['sources']['lemma_reference_commit'], 'LEMMA revision mismatch')
    directory = ASSETS / entry['path'] / 'Baseline/FastPC'
    info = {'commit': entry['commit'], 'files': {relative(directory / name): sha(directory / name)
            for name in ('rca.py', 'pyspot.py', 'libspot.so')}}
    # The unmodified wrapper resolves ./libspot.so against the current directory.
    old_cwd = Path.cwd()
    try:
        os.chdir(directory)
        spec = importlib.util.spec_from_file_location('lemma_pinned_pyspot', directory / 'pyspot.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        os.chdir(old_cwd)
    for name in ('up', 'down', 'alert', 'bounded', 'max_excess'):
        require(inspect.signature(module.DSpot).parameters[name].default == recipe['evt'][name],
                f'DSpot default mismatch: {name}')
    code = (directory / 'rca.py').read_text(encoding='utf-8')
    node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'spot_detection')
    info['function_sha256'] = hashlib.sha256(ast.get_source_segment(code, node).encode()).hexdigest()
    namespace = {'np': np, 'DSpot': module.DSpot}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(directory / 'rca.py'), 'exec'), namespace)
    params = {key: recipe['evt'][key] for key in ('d', 'q', 'n_init', 'level')}
    return namespace['spot_detection'], params, info


def failure(exc):
    context = []
    tb = exc.__traceback__
    while tb:
        if tb.tb_frame.f_code.co_name == 'spot_detection':
            frame = tb.tb_frame.f_locals
            context.append({k: (float(frame[k]) if np.isfinite(frame[k]) else str(frame[k]))
                            if isinstance(frame[k], (float, np.floating)) else int(frame[k])
                            for k in ('t', 'i', 'xt', 'event', 'upper_threshold', 'lower_threshold')
                            if k in frame and isinstance(frame[k], (int, float, np.number))})
        tb = tb.tb_next
    return {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc(),
            'upstream_function_locals': context}


def native_check(report_path):
    report = {'status': 'RUNNING', 'scope': 'synthetic native compatibility only', 'experiments_executed': False}
    try:
        recipe = get_recipe()
        report['runtime'] = runtime()
        spot, params, report['source'] = load_spot(recipe)
        t = np.arange(3000, dtype=np.float64)
        data = np.column_stack((100 + np.sin(t / 7) + .3 * np.cos(t / 3),
                                20 + np.cos(t / 11) + .2 * np.sin(t / 5)))
        data[500, 0], data[1500, 1], data[2500, 0] = 1e6, -1e6, -1e6
        first = spot(data, **params)
        second = spot(data, **params)
        columns = np.column_stack([spot(data[:, i:i+1], **params)[:, 0] for i in range(data.shape[1])])
        require(np.isfinite(first).all(), 'Nonfinite native scores on synthetic input')
        require(np.array_equal(first, second), 'Native repeatability failed')
        require(np.array_equal(first, columns), 'Independent channel execution differs from original matrix execution')
        require(np.all(first[:params['n_init']] == 0) and np.any(first > 0), 'Native score smoke test failed')
        report.update(status='PASS', input_sha256=array_hash(data), score_sha256=array_hash(first),
                      positive_scores=int(np.count_nonzero(first > 0)),
                      checks=['repeat_exact', 'matrix_vs_channel_exact', 'finite', 'calibration_zero', 'positive_alert'])
    except Exception as exc:
        report.update(status='FAILED', error=failure(exc))
    write_json(report_path, report)
    return 0 if report['status'] == 'PASS' else 1


def records_for(case, recipe):
    records = json.loads((PROJECT / recipe['input_manifest']).read_text(encoding='utf-8'))['files']
    tag = case['system'].lower()
    selected = {}
    revision = recipe['sources']['product_review_revision' if tag == 'product_review' else 'cloud_computing_revision']
    for role in ('Metrics Data', 'Log Data'):
        matches = [r for r in records if tag in r['path'] and f'/{role}/{case["day"]}.zip' in r['path']]
        require(len(matches) == 1, f'Expected one {role} archive')
        record = matches[0]
        require(record['revision'] == revision, f'{role} revision mismatch')
        path = ASSETS / record['path']
        require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], f'{role} archive hash mismatch')
        selected[role] = record
        print(f'{case["day"]}: verified {role} hash', flush=True)
    return selected


def load_metric(archive, metric, key):
    matches = [p for p in archive.namelist() if PurePosixPath(p).name == f'pod_level_data_{metric}.npy']
    require(len(matches) == 1, f'Ambiguous or missing metric {metric}')
    member = matches[0]
    with archive.open(member) as handle:
        data = read_npy(handle)[key]
    pods = list(data['Pod_Name'])
    features = list(data['KPI_Feature'])
    sequence = np.asarray(data['Sequence'])
    times = np.asarray(data['time'])
    require(sequence.ndim == 2 and sequence.shape == (len(times), len(pods) + 1), f'{metric}: shape mismatch')
    require(features == ['Latency'], f'{metric}: unexpected KPI feature {features}')
    require(len(set(pods)) == len(pods) and all(isinstance(p, str) for p in pods), f'{metric}: duplicate/invalid pod names')
    require(np.isfinite(sequence).all() and np.isfinite(times).all(), f'{metric}: nonfinite values')
    require(times.ndim == 1 and len(times) > 100 and np.all(times[1:] > times[:-1]), f'{metric}: invalid timestamps')
    return member, pods, sequence, times


def log_matches(record, pods):
    with zipfile.ZipFile(ASSETS / record['path']) as archive:
        members = [p for p in archive.namelist()
                   if str(PurePosixPath(p).parent).endswith('log_data/pod_removed')]
    entries = {}
    for pod in pods:
        matches = {role: [p for p in members if PurePosixPath(p).name == f'{pod}_messages_{role}.csv']
                   for role in ('templates', 'structured')}
        entries[pod] = {'members': matches,
                        'exact_unique_pair': all(len(x) == 1 for x in matches.values()),
                        'materialized': False}
    return {'archive': record['path'], 'archive_sha256': record['sha256'], 'pods': entries,
            'matched_unique_pairs': sum(e['exact_unique_pair'] for e in entries.values()),
            'missing_or_ambiguous': [p for p, e in entries.items() if not e['exact_unique_pair']],
            'log_input_ready': False, 'materialization': 'catalog only; not extracted or summarized',
            'pipeline_integration': 'DIFF-09 unresolved'}


def prepare_case(case, recipe, report_path, progress_path):
    started = time.monotonic()
    report = {'case': case, 'status': 'RUNNING', 'author_equivalence': 'UNCONFIRMED',
              'recipe_sha256': sha(RECIPE), 'recipe': recipe, 'channels': [], 'metrics': {},
              'experiments_executed': False, 'API_called': False,
              'execution': {'workers': 1,
                            'method': 'sequential channels; unchanged full ordered stream and native thread settings',
                            'scientific_recipe_changed': False}}
    try:
        report['runtime'] = runtime()
        spot, params, report['spot_source'] = load_spot(recipe)
        report['stage'] = 'verify_source_archives'
        sources = records_for(case, recipe)
        report['source_archives'] = sources
        metric_names = recipe['metric_sets'][case['system']]
        report['stage'] = 'align_timestamps'
        timeline = {}
        candidates = set()
        with zipfile.ZipFile(ASSETS / sources['Metrics Data']['path']) as archive:
            for metric in metric_names:
                member, pods, seq, times = load_metric(archive, metric, case['kpi_key'])
                timeline[metric] = times.copy()
                candidates.update(pods)
                report['metrics'][metric] = {'member': member, 'source_rows': len(times),
                    'source_pods': pods, 'source_sequence_sha256': array_hash(seq), 'source_time_sha256': array_hash(times)}
                del seq
            common = timeline[metric_names[0]]
            for metric in metric_names[1:]:
                common = np.intersect1d(common, timeline[metric], assume_unique=True)
            require(len(common) == case['expected_aligned_rows'], 'Alignment differs from inspected proposal')
            require(len(candidates) == case['expected_candidate_pod_union'], 'Pod union differs from inspected proposal')
            pods_sorted = sorted(candidates)
            pod_indices = {p: i for i, p in enumerate(pods_sorted)}
            fused_sum = np.zeros((len(common), len(pods_sorted)), dtype=np.float64)
            counts = np.zeros(len(pods_sorted), dtype=np.int64)
            retained = np.zeros(len(pods_sorted), dtype=bool)
            kpi = None
            for metric in metric_names:
                member, pods, seq, times = load_metric(archive, metric, case['kpi_key'])
                rows = np.searchsorted(times, common)
                require(np.array_equal(times[rows], common), 'Exact alignment mismatch')
                aligned = seq[rows, :]
                del seq
                report['metrics'][metric]['dropped_rows'] = len(times) - len(common)
                report['metrics'][metric]['dropped_timestamps'] = times[~np.isin(times, common, assume_unique=True)].tolist()
                if kpi is None:
                    kpi = aligned[:, -1].copy()
                    require(float(np.std(kpi, ddof=0)) != 0, 'Constant KPI')
                else:
                    require(np.array_equal(kpi, aligned[:, -1]), f'KPI mismatch: {metric}')
                for column, pod in enumerate(pods):
                    report['stage'] = 'channel_EVT'
                    active = {'metric': metric, 'pod': pod, 'source_column': column,
                              'aligned_rows': len(common), 'started_utc': datetime.now(timezone.utc).isoformat()}
                    report['active_channel'] = active
                    write_json(progress_path, active)
                    x = aligned[:, column]
                    mean, std = float(np.mean(x)), float(np.std(x, ddof=0))
                    require(np.isfinite([mean, std]).all(), 'Nonfinite normalization statistics')
                    channel = {**active, 'mean': mean, 'std_ddof0': std, 'aligned_value_sha256': array_hash(x)}
                    index = pod_indices[pod]
                    if std == 0:
                        channel.update(status='EXCLUDED_CONSTANT', positive_scores=0)
                    else:
                        scores = spot(x.reshape(-1, 1), **params)[:, 0]
                        require(np.isfinite(scores).all(), f'Nonfinite SPOT score: {metric}/{pod}')
                        positives = np.flatnonzero(scores[params['n_init']:] > recipe['evt']['threshold_score']) + params['n_init']
                        channel.update(status='DETECTED', positive_scores=len(positives),
                            first_positive_index=int(positives[0]) if len(positives) else None,
                            maximum_score=float(np.max(scores)), score_sha256=array_hash(scores))
                        retained[index] |= len(positives) > 0
                        fused_sum[:, index] += (x - mean) / std
                        counts[index] += 1
                    report['channels'].append(channel)
                    if (column + 1) % 25 == 0 or column + 1 == len(pods):
                        print(f'{case["day"]} {metric}: {column+1}/{len(pods)} channels; retained so far={retained.sum()}', flush=True)
                del aligned
        report['stage'] = 'fuse_and_write'
        selected = [p for i, p in enumerate(pods_sorted) if retained[i]]
        require(len(selected) >= recipe['metric_fusion']['minimum_retained_pods'], 'Too few retained pods; no fallback')
        fused = fused_sum[:, retained] / counts[retained]
        require(np.isfinite(fused).all() and np.all(np.std(fused, axis=0, ddof=0) != 0), 'Invalid/constant fused channel')
        report['pod_decisions'] = {p: {'retained': bool(retained[i]), 'nonconstant_channels': int(counts[i]),
            'reason': 'positive_EVT' if retained[i] else 'all_constant' if counts[i] == 0 else 'no_positive_EVT',
            'fusion_weight_each': 1 / int(counts[i]) if counts[i] else None,
            'missing_metrics': [m for m in metric_names if p not in report['metrics'][m]['source_pods']]}
            for i, p in enumerate(pods_sorted)}
        report['logs'] = log_matches(sources['Log Data'], selected)
        report['aligned_rows'] = len(common)
        report['retained_pods'] = len(selected)
        report['columns'] = selected + ['Latency']
        report['kpi_array_sha256'] = array_hash(kpi)
        report['timestamps_array_sha256'] = array_hash(common)
        output = ASSETS / recipe['output_relative_to_asset_root'] / case['system'] / case['day']
        require(output.resolve().is_relative_to(ASSETS), 'Output outside assets')
        # A failed/incomplete prior attempt is never overwritten or silently reused.
        output.mkdir(parents=True, exist_ok=False)
        report['output_directory'] = relative(output)
        csv_path = output / f'{case["system"]}_{case["day"]}.csv'
        values = np.column_stack((fused, kpi))
        with csv_path.open('x', encoding='utf-8', newline='') as handle:
            csv.writer(handle, lineterminator='\n').writerow(report['columns'])
            np.savetxt(handle, values, delimiter=',', fmt=recipe['output_contract']['float_format'])
        timestamps_path = output / 'timestamps.csv'
        np.savetxt(timestamps_path, common, delimiter=',', fmt='%.17g', header='timestamp', comments='')
        report['stage'] = 'verify_CSV_roundtrip'
        with csv_path.open(encoding='utf-8') as handle:
            require(next(csv.reader(handle)) == report['columns'], 'CSV header mismatch')
            reread = np.loadtxt(handle, delimiter=',', dtype=np.float64, ndmin=2)
        require(np.array_equal(values, reread), 'CSV values fail exact float64 roundtrip')
        reread_time = np.loadtxt(timestamps_path, delimiter=',', skiprows=1, ndmin=1)
        require(np.array_equal(common, reread_time), 'Timestamp roundtrip mismatch')
        report.update(status='PREPARED_PROVISIONAL', stage='complete', metric_input_ready=True,
                      output_directory=relative(output), elapsed_seconds=time.monotonic() - started)
        report['outputs'] = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in (csv_path, timestamps_path)}
        report['csv_array_sha256'] = array_hash(values)
        report['validation'] = {'exact_csv_roundtrip': True, 'exact_timestamp_roundtrip': True,
                                'all_KPI_values_equal_across_metrics': True, 'finite_and_nonconstant': True}
        write_json(output / 'manifest.json', report, exclusive=True)
        report['manifest_sha256'] = sha(output / 'manifest.json')
        print(f'{case["day"]}: PREPARED {len(common)} rows, {len(selected)} pods; missing logs {len(report["logs"]["missing_or_ambiguous"])}', flush=True)
    except Exception as exc:
        report.update(status='FAILED', metric_input_ready=False, error=failure(exc), elapsed_seconds=time.monotonic()-started)
        print(f'{case["day"]}: FAILED at {report.get("stage")}: {type(exc).__name__}: {exc}', flush=True)
    write_json(report_path, report)
    return 0 if report['status'] == 'PREPARED_PROVISIONAL' else 1


def run_child(arguments, report_path, log_path):
    with log_path.open('x', encoding='utf-8') as output:
        result = subprocess.run([sys.executable, '-B', '-u', str(Path(__file__).resolve()), *arguments],
                                stdout=output, stderr=subprocess.STDOUT, cwd=PROJECT)
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {
        'status': 'FAILED', 'error': {'type': 'WorkerExit', 'message': f'Worker exit {result.returncode}; inspect log/progress'}}
    report['worker_returncode'] = result.returncode
    report['worker_log'] = relative(log_path)
    if result.returncode != 0:
        report['status'] = 'FAILED'
    write_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-native', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--native-worker', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--case-worker', help=argparse.SUPPRESS)
    parser.add_argument('--report', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--progress', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    recipe = get_recipe()
    if args.native_worker:
        return native_check(args.native_worker)
    if args.case_worker:
        case = next(c for c in recipe['cases'] if c['day'] == args.case_worker)
        return prepare_case(case, recipe, args.report, args.progress)
    require(args.check_native != args.prepare, 'Choose exactly --check-native or --prepare')
    versions = runtime()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log_dir = asset_path('setup_logs') / f'provisional_rca_{stamp}'
    log_dir.mkdir(parents=True, exist_ok=False)
    report = {'started_utc': stamp, 'status': 'RUNNING', 'recipe_sha256': sha(RECIPE),
              'implementation_sha256': sha(Path(__file__)),
              'log_directory': relative(log_dir), 'runtime': versions, 'cases': [],
              'experiments_executed': False, 'API_called': False, 'author_equivalence': 'UNCONFIRMED'}
    write_json(log_dir / 'recipe.json', recipe, exclusive=True)
    original = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob('*') if p.is_file()}
    print(f'Log directory: {log_dir}', flush=True)
    native_path = log_dir / 'native.json'
    report['native'] = run_child(['--native-worker', str(native_path)], native_path, log_dir / 'native.log')
    print(f'Native check: {report["native"]["status"]}', flush=True)
    if report['native']['status'] == 'PASS' and args.prepare:
        for case in recipe['cases']:
            path = log_dir / f'{case["day"]}.json'
            print(f'Start preprocessing {case["system"]}/{case["day"]}', flush=True)
            child = run_child(['--case-worker', case['day'], '--report', str(path), '--progress',
                               str(log_dir / f'{case["day"]}_progress.json')], path, log_dir / f'{case["day"]}.log')
            compact = {k: child[k] for k in ('case', 'status', 'stage', 'retained_pods', 'aligned_rows',
                       'metric_input_ready', 'error', 'manifest_sha256', 'output_directory', 'worker_returncode') if k in child}
            compact['case'] = case
            compact['report'] = relative(path)
            if 'logs' in child:
                compact['missing_log_pairs'] = len(child['logs']['missing_or_ambiguous'])
                compact['log_input_ready'] = child['logs']['log_input_ready']
            report['cases'].append(compact)
            write_json(log_dir / 'summary.json', report)
            print(f'{case["day"]}: {child["status"]}', flush=True)
    after = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob('*') if p.is_file()}
    report['official_source_unchanged'] = original == after
    report['runtime_unchanged'] = runtime() == versions
    report['recipe_unchanged'] = sha(RECIPE) == report['recipe_sha256']
    success = report['native']['status'] == 'PASS' and all(
        r['status'] == 'PREPARED_PROVISIONAL' for r in report['cases']) and (
        args.check_native or len(report['cases']) == len(recipe['cases']))
    report['status'] = 'PASS' if success and all(report[k] for k in (
        'official_source_unchanged', 'runtime_unchanged', 'recipe_unchanged')) else 'BLOCKED'
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(log_dir / 'summary.json', report)
    evidence = PROJECT / 'docs/evidence' / ('rca_native_preprocessing.json' if args.check_native else 'rca_preprocessing_applied.json')
    write_json(evidence, report)
    print(f'{report["status"]}: {evidence}', flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
