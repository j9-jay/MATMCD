"""Fix the TASK_070 category 1 evaluation set (B plan, user decision 2026-10-19).

Evaluation set = repetition 2 of every (target service x fault) combination in
RCAEval RE2-OB: 5 x 6 = 30 cases, identical for every method. Repetition 3 is
not used. Writes configs/task070_testset.json with opaque ids, paths and the
zip CRC32/size of every case file so later runs can verify they read the same
bytes. Refuses to overwrite an existing file.
"""
import collections
import zipfile

import task070_rcaeval as rc
from project_paths import PROJECT
from task070_common import RCAEVAL_OB_ZIP, sha256_file, write_json

OUT = PROJECT / "configs/task070_testset.json"


def main():
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite {OUT}")
    chosen = [p for p in rc.case_paths() if p.rsplit("/", 1)[1] == "2"]
    combos = collections.Counter(p.split("/")[1] for p in chosen)
    services = {c.rsplit("_", 1)[0] for c in combos}
    faults = {c.rsplit("_", 1)[1] for c in combos}
    if len(chosen) != 30 or len(services) != 5 or len(faults) != 6 or set(combos.values()) != {1}:
        raise SystemExit(f"Unexpected design: {len(chosen)} cases, {sorted(services)}, {sorted(faults)}")
    with zipfile.ZipFile(RCAEVAL_OB_ZIP) as zf:
        infos = {i.filename: i for i in zf.infolist()}
    cases = []
    for path in sorted(chosen, key=rc.case_id):
        files = {name.rsplit("/", 1)[1]: {"crc32": f"{info.CRC:08x}", "size": info.file_size}
                 for name, info in infos.items() if name.startswith(path + "/") and not name.endswith("/")}
        cases.append({"id": rc.case_id(path), "path": path, "files": files})
    write_json(OUT, {
        "profile_id": "task070_testset_rep2_v1",
        "decided_kst": "2026-10-19",
        "authorization": "사용자 결정: B안 - 평가는 반복 2의 30사례, 모든 방법 동일, 반복 3 미사용",
        "rule": "RE2-OB 각 (장애 대상 서비스 x 장애 유형) 조합의 반복 2 사례 1개",
        "services": sorted(services), "faults": sorted(faults),
        "not_used": "반복 3의 30사례. 결과를 본 뒤 평가 사례를 늘리거나 바꾸지 않는다",
        "development_split": "반복 1의 30사례",
        "source_zip": {"path": str(RCAEVAL_OB_ZIP), "sha256": sha256_file(RCAEVAL_OB_ZIP)},
        "note": "path에는 정답(서비스_장애)이 들어 있다. 방법 코드는 id만 쓰고 path→정답은 평가 단계에서만 읽는다",
        "cases": cases,
    })
    print(OUT, len(cases))


if __name__ == "__main__":
    main()
