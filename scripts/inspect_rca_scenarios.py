"""Read scenario slides already included in the pinned metric archives.

OOXML text extraction only; no deck editing, data selection, or RCA execution.
"""
import hashlib
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import PurePosixPath

from project_paths import ASSETS, PROJECT


def main():
    downloads = json.loads((PROJECT / "docs/evidence/downloads.json").read_text(encoding="utf-8"))
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(), "decks": [],
              "scope": "Text and table text from slide OOXML; notes separately; no visual layout inference"}
    for record in downloads["files"]:
        if not ("Metrics Data/" in record["path"] and record["path"].endswith(".zip")):
            continue
        archive_path = ASSETS / record["path"]
        with zipfile.ZipFile(archive_path) as outer:
            for member in outer.namelist():
                if not member.lower().endswith(".pptx"):
                    continue
                payload = outer.read(member)
                destination = archive_path.parent.parent / "scenario_documents" / PurePosixPath(member).name
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    if destination.read_bytes() != payload:
                        raise RuntimeError(f"Existing scenario differs: {destination}")
                else:
                    destination.write_bytes(payload)
                deck = {"archive": record["path"], "archive_sha256_from_manifest": record["sha256"],
                        "member": member, "path": str(destination.relative_to(ASSETS)),
                        "sha256": hashlib.sha256(payload).hexdigest(), "slides": [], "notes": [], "media": []}
                with zipfile.ZipFile(io.BytesIO(payload)) as pptx:
                    for section, regex in (("slides", r"ppt/slides/slide(\d+)\.xml"),
                                           ("notes", r"ppt/notesSlides/notesSlide(\d+)\.xml")):
                        parts = [(int(re.fullmatch(regex, name)[1]), name) for name in pptx.namelist() if re.fullmatch(regex, name)]
                        for number, name in sorted(parts):
                            root = ET.fromstring(pptx.read(name))
                            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
                            text = ["".join(t.text or "" for t in p.findall(".//a:t", ns)) for p in root.findall(".//a:p", ns)]
                            deck[section].append({"number": number, "text": [t for t in text if t]})
                    deck["media"] = [x.filename for x in pptx.infolist() if x.filename.startswith("ppt/media/")]
                report["decks"].append(deck)
    output = PROJECT / "docs/evidence/rca_scenario_slides.json"
    if output.exists():
        raise FileExistsError("Existing evidence is retained; choose a new evidence version for a new inspection")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for deck in report["decks"]:
        print(json.dumps({"member": deck["member"], "slides": len(deck["slides"]), "evidence": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
