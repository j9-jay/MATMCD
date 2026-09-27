"""Install the approved nine Ubuntu packages and test only PNG rendering.

Run with the pinned WSL Python as root. No apt update/upgrade, pip install,
causal discovery, RCA, model APIs, or edits to the official source.
"""
import argparse
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from setup_chromadb import pins, sha


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def python_packages():
    return {re.sub(r'[-_.]+', '-', d.metadata['Name'].lower()): d.version
            for d in importlib.metadata.distributions()}


def system_packages():
    result = subprocess.check_output(
        ['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${db:Status-Status}\n'], text=True)
    return {name: version for name, version, status in (row.split('\t') for row in result.splitlines())
            if status == 'installed'}


def source_hashes():
    return {p.relative_to(SOURCE).as_posix(): sha(p) for p in SOURCE.rglob('*') if p.is_file()}


def assert_original_source():
    scope = json.loads((PROJECT / 'configs/scope.json').read_text(encoding='utf-8'))
    upstream = json.loads((PROJECT / 'configs/upstream.json').read_text(encoding='utf-8'))
    archive_path = ASSETS / 'raw_downloads/github_d2i_matmcd/ef2c3ec.zip'
    require(sha(archive_path) == upstream['source_archive_sha256'], 'Original archive hash mismatch')
    expected = set()
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            if item.is_dir() or item.filename in scope['excluded_official_files']:
                continue
            expected.add(item.filename)
            require((SOURCE / item.filename).read_bytes() == archive.read(item), item.filename)
    require(set(source_hashes()) == expected and len(expected) == 37, 'Official source file set mismatch')


def fields(paragraph):
    return dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', required=True)
    parser.parse_args()
    require(sys.platform == 'linux' and sys.prefix == str(asset_path('environment')), 'Use the pinned WSL Python')
    require(os.geteuid() == 0, 'Requires root for the approved system installation')
    recipe_path = PROJECT / 'configs/graphviz_packages.json'
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    targets = recipe['packages']
    require(recipe['choice'] == 'B' and len(targets) == 9, 'Unexpected package recipe')
    require(not recipe['allow_existing_package_changes'] and not recipe['install_recommends'], 'Unexpected install policy')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    logs = asset_path('setup_logs') / f'graphviz_{stamp}'
    logs.mkdir(parents=True, exist_ok=False)
    report = {'started_utc': stamp, 'status': 'IN_PROGRESS', 'choice': 'B',
              'author_equivalence': 'UNCONFIRMED', 'recipe_sha256': sha(recipe_path),
              'implementation_sha256': sha(Path(__file__)),
              'log_directory': str(logs.relative_to(ASSETS)), 'approved_packages': targets,
              'experiments_executed': False, 'model_api_calls': False, 'commands': []}
    env = {**os.environ, 'LC_ALL': 'C', 'DEBIAN_FRONTEND': 'noninteractive', 'PYTHONDONTWRITEBYTECODE': '1'}

    def run(name, argv, cwd=PROJECT):
        report['stage'] = name
        print(name, flush=True)
        result = subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (logs / f'{name}.log').write_text(result.stdout, encoding='utf-8')
        report['commands'].append({'name': name, 'argv': argv, 'exit_code': result.returncode})
        require(result.returncode == 0, f'{name} failed ({result.returncode}); see {logs / (name + ".log")}')
        return result.stdout

    def check_plan(output):
        planned = dict(re.findall(r'^Inst (\S+) \((\S+)', output, re.M))
        require(planned == targets and not re.search(r'^(Remv|Purg) ', output, re.M), 'APT plan differs from nine approved additions')
        require('0 upgraded, 9 newly installed, 0 to remove' in output, 'APT would alter existing packages')

    try:
        before_py, before_os, before_source = python_packages(), system_packages(), source_hashes()
        baseline = pins((PROJECT / 'docs/evidence/installed_freeze_with_openai_embeddings.txt').read_text())
        require(before_py == baseline and len(before_py) == 201, 'Python baseline changed')
        assert_original_source()
        require(not (set(targets) & {n.split(':')[0] for n in before_os}), 'Target package already installed; do not silently reinstall')
        write_json(logs / 'before_python.json', before_py)
        write_json(logs / 'before_system.json', before_os)
        write_json(logs / 'before_official_source.json', before_source)
        specs = [f'{name}={version}' for name, version in targets.items()]
        run('apt_policy', ['apt-cache', 'policy', *targets])
        check_plan(run('simulate', ['apt-get', '-s', '--no-install-recommends', '--no-remove', '--no-upgrade', 'install', *specs]))
        metadata = {}
        for name, version in targets.items():
            paragraphs = run('metadata_' + name, ['apt-cache', 'show', f'{name}={version}']).strip().split('\n\n')
            candidates = [fields(p) for p in paragraphs]
            matches = [p for p in candidates if p.get('Package') == name and p.get('Version') == version
                       and p.get('Architecture') == recipe['architecture']]
            require(matches and len({p.get('SHA256') for p in matches}) == 1, f'Ambiguous package metadata: {name}')
            item = matches[0]
            require(re.fullmatch('[a-f0-9]{64}', item.get('SHA256', '')), 'Missing SHA256')
            metadata[name] = {k: item[k] for k in ('Package', 'Version', 'Architecture', 'Filename', 'Size', 'SHA256')}
        report['package_metadata'] = metadata
        write_json(logs / 'package_metadata.json', metadata)
        run('download_uris', ['apt-get', '--print-uris', 'download', *specs])
        downloads = (ASSETS / recipe['raw_downloads_relative_to_asset_root']).resolve()
        require(downloads.is_relative_to(ASSETS), 'Download path outside assets')
        downloads.mkdir(parents=True, exist_ok=True)
        run('download', ['apt-get', 'download', *specs], cwd=downloads)
        archives = {}
        for path in sorted(downloads.glob('*.deb')):
            info = subprocess.check_output(['dpkg-deb', '-f', str(path)], text=True)
            item = fields(info)
            name = item['Package']
            require(name in targets and name not in archives, 'Unexpected or duplicate DEB')
            expected = metadata[name]
            require(item['Version'] == targets[name] and item['Architecture'] == recipe['architecture'], 'DEB identity mismatch')
            require(sha(path) == expected['SHA256'] and path.stat().st_size == int(expected['Size']), 'DEB checksum mismatch')
            archives[name] = path
        require(set(archives) == set(targets), 'Missing DEB')
        report['downloaded_packages'] = {n: {'path': str(p.relative_to(ASSETS)), 'sha256': sha(p), 'bytes': p.stat().st_size}
                                         for n, p in archives.items()}
        # --no-download rejects local DEBs outside APT's archive cache even in
        # simulation; exact local DEBs and the nine-package plan are verified.
        install = ['apt-get', '--no-install-recommends', '--no-remove', '--no-upgrade',
                   'install', *map(str, archives.values())]
        check_plan(run('simulate_local', install[:1] + ['-s'] + install[1:]))
        require(system_packages() == before_os and python_packages() == before_py, 'Environment changed during preparation')
        run('install', install[:1] + ['-y'] + install[1:])
        after_os, after_py = system_packages(), python_packages()
        write_json(logs / 'after_system.json', after_os)
        write_json(logs / 'after_python.json', after_py)
        changed = {n: {'before': v, 'after': after_os.get(n)} for n, v in before_os.items() if after_os.get(n) != v}
        added = {n: v for n, v in after_os.items() if n not in before_os}
        report.update(added_system_packages=added, changed_or_removed_system_packages=changed,
                      python_package_count=len(after_py), python_201_packages_preserved=after_py == before_py,
                      official_37_files_preserved=source_hashes() == before_source,
                      recipe_preserved=sha(recipe_path) == report['recipe_sha256'])
        require(not changed and {n.split(':')[0]: v for n, v in added.items()} == targets, 'System package delta mismatch')
        require(report['python_201_packages_preserved'] and report['official_37_files_preserved'] and report['recipe_preserved'], 'Preservation check failed')
        assert_original_source()
        require(not run('dpkg_audit', ['dpkg', '--audit']).strip(), 'dpkg reports package configuration problems')
        dot = shutil.which('dot')
        require(dot, 'dot missing after install')
        report['dot'] = {'path': dot, 'sha256': sha(Path(dot)),
                         'reported_version': run('dot_version', [dot, '-V']).strip()}
        report['stage'] = 'official_synthetic_PNG'
        print(report['stage'], flush=True)
        import numpy as np
        spec = importlib.util.spec_from_file_location('matmcd_official_visualize', SOURCE / 'Utils/visualize.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        matrix = np.array([[0, 1, 0], [0, 0, -1], [0, 0, 0]])
        original_matrix = matrix.copy()
        png = logs / 'synthetic_graph.png'
        module.visualize_graph(matrix, ['synthetic_A', 'synthetic_B', 'synthetic_C'], str(png))
        raw = png.read_bytes()
        require(raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR', 'Invalid PNG')
        width, height = struct.unpack('>II', raw[16:24])
        require(width > 0 and height > 0 and np.array_equal(matrix, original_matrix), 'PNG/matrix validation failed')
        report['rendering'] = {'official_function': 'Utils/visualize.py:visualize_graph', 'input': matrix.tolist(),
            'png': str(png.relative_to(ASSETS)), 'sha256': sha(png), 'bytes': len(raw), 'width': width, 'height': height,
            'input_matrix_preserved': True, 'synthetic_only': True,
            'python_wrappers': {n: importlib.metadata.version(n) for n in ('pydot', 'graphviz')}}
        require(python_packages() == before_py and source_hashes() == before_source, 'Post-render preservation failed')
        report.update(status='PASS', stage='complete')
    except Exception as exc:
        report.update(status='FAILED', error={'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
        print(report['error']['traceback'], flush=True)
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(logs / 'report.json', report)
    write_json(PROJECT / 'docs/evidence/graphviz_install.json', report)
    print(json.dumps({'status': report['status'], 'log_directory': report['log_directory'], 'stage': report.get('stage')}), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
