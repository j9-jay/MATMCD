"""Check the installed Graphviz from the normal WSL user; render synthetic data only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import traceback
from datetime import datetime, timezone

import numpy as np

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from setup_graphviz import assert_original_source, python_packages, require, source_hashes, system_packages, write_json
from setup_chromadb import pins, sha


def main():
    require(sys.platform == 'linux' and sys.prefix == str(asset_path('environment')), 'Use pinned WSL Python')
    require(os.geteuid() != 0, 'Run as the normal experiment user, not root')
    installation = json.loads((PROJECT / 'docs/evidence/graphviz_install.json').read_text(encoding='utf-8'))
    require(installation['status'] == 'PASS', 'Installation did not pass')
    logs = ASSETS / installation['log_directory']
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'uid': os.geteuid(),
              'status': 'IN_PROGRESS', 'author_equivalence': 'UNCONFIRMED',
              'experiments_executed': False, 'model_api_calls': False,
              'implementation_sha256': sha(Path(__file__)), 'installation_sha256': sha(PROJECT / 'docs/evidence/graphviz_install.json')}
    try:
        baseline = pins((PROJECT / 'docs/evidence/installed_freeze_with_openai_embeddings.txt').read_text())
        before_source, before_system = source_hashes(), system_packages()
        require(python_packages() == baseline and len(baseline) == 201, 'Python packages changed')
        require(before_system == json.loads((logs / 'after_system.json').read_text()), 'System packages changed after installation')
        assert_original_source()
        dot = shutil.which('dot')
        require(dot == installation['dot']['path'] and sha(Path(dot)) == installation['dot']['sha256'], 'dot mismatch')
        result = subprocess.run([dot, '-V'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        require(result.returncode == 0, result.stdout)
        matrix = np.array(installation['rendering']['input'])
        snapshot = matrix.copy()
        path = logs / 'synthetic_graph_normal_user.png'
        spec = importlib.util.spec_from_file_location('matmcd_visualize', SOURCE / 'Utils/visualize.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.visualize_graph(matrix, ['synthetic_A', 'synthetic_B', 'synthetic_C'], str(path))
        raw = path.read_bytes()
        require(raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR', 'Invalid PNG')
        width, height = struct.unpack('>II', raw[16:24])
        require(width > 0 and height > 0 and np.array_equal(matrix, snapshot), 'PNG/input invalid')
        require(python_packages() == baseline and system_packages() == before_system and source_hashes() == before_source, 'Runtime check changed packages/source')
        report.update(status='PASS', dot=result.stdout.strip(), png=str(path.relative_to(ASSETS)),
                      png_sha256=sha(path), width=width, height=height, input_matrix_preserved=True,
                      matches_installation_test_png=sha(path) == installation['rendering']['sha256'],
                      python_201_packages_preserved=True, system_packages_preserved=True,
                      official_37_files_preserved=True)
    except Exception as exc:
        report.update(status='FAILED', error={'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
    write_json(logs / 'normal_user_runtime.json', report)
    write_json(PROJECT / 'docs/evidence/graphviz_runtime.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
