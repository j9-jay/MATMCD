"""공식 배포 원본을 다운로드하고 해시를 기록한다. 전처리/샘플링은 하지 않는다."""
import concurrent.futures
import gzip
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(item):
    item = dict(item)
    target = (ASSETS / item["path"]).resolve()
    if not target.is_relative_to(ASSETS):
        raise ValueError("잘못된 다운로드 경로")
    expected = item.get("sha256")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and (not expected or sha256(target) == expected):
            item.update(status="verified_existing", bytes=target.stat().st_size, sha256=sha256(target))
            return item
        if target.exists():
            raise RuntimeError("기존 파일 해시 불일치: 자동으로 덮어쓰지 않습니다.")
        partial = target.with_name(target.name + ".partial")
        for attempt in range(3):
            try:
                offset = partial.stat().st_size if partial.exists() else 0
                headers = {"User-Agent": "MATMCD-reproduction-asset-setup"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                request = urllib.request.Request(item["url"], headers=headers)
                with urllib.request.urlopen(request, timeout=60) as response:
                    resumed = response.status == 206 and offset > 0
                    with partial.open("ab" if resumed else "wb") as out:
                        while chunk := response.read(8 * 1024 * 1024):
                            out.write(chunk)
                actual = sha256(partial)
                if expected and actual != expected:
                    raise RuntimeError(f"SHA256 불일치: {actual}")
                if item.get("bytes") and partial.stat().st_size != item["bytes"]:
                    raise RuntimeError("파일 크기 불일치")
                partial.replace(target)
                item.update(status="downloaded_verified", sha256=actual, bytes=target.stat().st_size)
                print(f"완료: {item['path']} ({item['bytes']} bytes)", flush=True)
                return item
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
    except Exception as error:
        item.update(status="failed", error=f"{type(error).__name__}: {error}")
        print(f"실패: {item['path']}: {item['error']}", flush=True)
    return item


def main():
    items = []
    for name in ("asia", "child"):
        items.append({"url": f"https://www.bnlearn.com/bnrepository/{name}/{name}.bif.gz",
                      "path": f"raw_downloads/bnlearn_{name}_network/{name}.bif.gz",
                      "role": "Bayesian network; 논문 실제 샘플 아님"})
    selections = {"Product_Review_Preprocessed": ["20210517", "20210524", "20211203", "20220606"],
                  "Cloud_Computing_Preprocessed": ["20231207"]}
    for name, dates in selections.items():
        directory = f"raw_downloads/huggingface_lemma_rca_{name.lower()}"
        metadata = json.loads((ASSETS / directory / "repository_metadata.json").read_text(encoding="utf-8"))
        for entry in metadata["siblings"]:
            filename = entry["rfilename"]
            if filename == "README.md" or any(filename.endswith(f"/{day}.zip") for day in dates):
                items.append({
                    "url": f"https://huggingface.co/datasets/Lemma-RCA-NEC/{name}/resolve/{metadata['sha']}/{urllib.parse.quote(filename)}?download=true",
                    "path": f"{directory}/{filename}",
                    "bytes": entry.get("size"),
                    "sha256": (entry.get("lfs") or {}).get("sha256"),
                    "revision": metadata["sha"],
                    "role": "공식 전처리 배포본; MATMCD의 EVT 필터 후 입력과 동일성 미확인",
                })
    output = PROJECT / "docs" / "evidence" / "downloads.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fetch, item) for item in items]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            output.write_text(json.dumps({"checked_utc": datetime.now(timezone.utc).isoformat(),
                                         "files": sorted(results, key=lambda x: x["path"])},
                                        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in ("asia", "child"):
        archive = ASSETS / f"raw_downloads/bnlearn_{name}_network/{name}.bif.gz"
        if archive.exists():
            target = ASSETS / f"datasets/bnlearn_{name}_network/{name}.bif"
            target.parent.mkdir(parents=True, exist_ok=True)
            data = gzip.decompress(archive.read_bytes())
            if target.exists() and target.read_bytes() != data:
                raise RuntimeError("기존 BIF 불일치")
            target.write_bytes(data)
    return int(any(x["status"] == "failed" for x in results))


if __name__ == "__main__":
    raise SystemExit(main())
