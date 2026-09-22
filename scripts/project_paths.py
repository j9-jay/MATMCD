"""프로젝트/자산 경로만 관리한다. 실험 파라미터를 설정하지 않는다."""
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT / "configs" / "paths.json"
CONFIG = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
ASSETS = (CONFIG_FILE.parent / CONFIG["asset_root"]).resolve()
SOURCE = PROJECT / CONFIG["official_source"]


def asset_path(key):
    path = (ASSETS / CONFIG[key]).resolve()
    if not path.is_relative_to(ASSETS):
        raise ValueError(f"자산 루트 밖의 경로: {key}")
    return path
