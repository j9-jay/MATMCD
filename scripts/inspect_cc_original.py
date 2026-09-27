"""Inspect fixed original CC scenario/configuration evidence, not model inputs."""
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

from project_paths import ASSETS, PROJECT


def main():
    root = ASSETS / "raw_downloads/huggingface_lemma_rca_cloud_computing_original"
    receipt = json.loads((root / "download_receipt.json").read_text(encoding="utf-8-sig"))
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(), "download": receipt,
              "configurations": [], "active_inputs_changed": False, "ground_truth_selected": False}
    inputs_before = hashlib.sha256((PROJECT / "configs/inputs.json").read_bytes()).hexdigest()
    with zipfile.ZipFile(root / "20231207.zip") as archive:
        report["entries"] = [{"name": x.filename, "bytes": x.file_size} for x in archive.infolist() if not x.is_dir()]
        report["fault_script_named_candidates"] = [x["name"] for x in report["entries"]
            if re.search(r"(?i)(fault|stress|chaos|inject|\.sh$|\.ya?ml$)", x["name"])]
        for item in archive.infolist():
            if "Configuration/" not in item.filename or not item.filename.endswith(".txt"):
                continue
            data = archive.read(item)
            destination = root / "configuration" / PurePosixPath(item.filename).name
            destination.parent.mkdir(exist_ok=True)
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError("Existing original configuration differs")
            if not destination.exists():
                destination.write_bytes(data)
            lines = data.decode("utf-8-sig").splitlines()
            matches = [line for line in lines if "productpage-v1" in line]
            report["configurations"].append({"member": item.filename, "path": str(destination.relative_to(ASSETS)),
                "sha256": hashlib.sha256(data).hexdigest(), "matching_lines": matches,
                "book_info_productpage_pods": [line.split()[1] for line in matches if line.split()[0] == "book-info"]})
        english = archive.read("AIOps_data_20231207/README_en-US.pptx")
        slides = json.loads((PROJECT / "docs/evidence/rca_scenario_slides.json").read_text(encoding="utf-8"))
        expected = next(d["sha256"] for d in slides["decks"] if d["member"].startswith("20231207/"))
        report["english_scenario_matches_preprocessed_archive"] = hashlib.sha256(english).hexdigest() == expected
    report["active_inputs_unchanged"] = inputs_before == hashlib.sha256((PROJECT / "configs/inputs.json").read_bytes()).hexdigest()
    report["interpretation"] = "Before/after pod replacement is observable, but is not an explicit injected-fault target label. No target chosen by replacement or CPU magnitude."
    output = PROJECT / "docs/evidence/rca_cc_original_inspection.json"
    if output.exists():
        raise FileExistsError("Existing inspection retained")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "configurations": report["configurations"],
                      "english_scenario_matches": report["english_scenario_matches_preprocessed_archive"],
                      "fault_script_named_candidates": len(report["fault_script_named_candidates"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
