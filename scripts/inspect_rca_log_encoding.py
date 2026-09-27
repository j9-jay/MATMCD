"""Read-only invalid UTF-8 diagnosis; never supplies replacement text to RCA."""
import codecs
import json
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, asset_path
from rca_log_evidence import read_json, within, sha256
from check_rca_log_memory import official_prompt_functions


def inspect(path):
    offset, count, samples = 0, 0, []
    decoder = codecs.getincrementaldecoder("utf-8")("surrogateescape")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            pending = len(decoder.getstate()[0])
            text = decoder.decode(block, final=False)
            if any(0xdc80 <= ord(c) <= 0xdcff for c in text):
                byte_pos = offset - pending
                for char in text:
                    if 0xdc80 <= ord(char) <= 0xdcff:
                        count += 1
                        if len(samples) < 12:
                            samples.append({"byte_offset": byte_pos, "byte_hex": f"{ord(char)-0xdc00:02x}"})
                    byte_pos += len(char.encode("utf-8", errors="surrogateescape"))
            offset += len(block)
        tail = decoder.decode(b"", final=True)
        for char in tail:
            if 0xdc80 <= ord(char) <= 0xdcff:
                count += 1
    return {"invalid_utf8_bytes": count, "first_positions": samples, "bytes": offset}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    failed_dir = ASSETS / "processed_data/lemma_rca_original_prompts_v1/Product_Review/20211203/f5667c75f2ad6deea80ff6cba60f8cb5b6a56c205f757780d1cd7f64726ab251"
    request = read_json(failed_dir / "request.json")
    report = {"status": "IN_PROGRESS", "case": request["case"], "pod": request["pod"],
              "diagnostic_only": True, "data_modified": False, "replacement_policy_applied_to_experiment": False}
    try:
        import pandas as pd
        template = within(ASSETS, request["sources"]["templates"]["path"])
        structured = within(ASSETS, request["sources"]["structured"]["path"])
        report["source_sha256_matches"] = sha256(structured) == request["sources"]["structured"]["sha256"]
        report["encoding"] = inspect(structured)
        # Surrogateescape is diagnostic here: undecodable bytes survive exactly
        # for detecting whether original event/example selection includes them.
        # No resulting text is sent to a model or used as prepared RCA input.
        frame = pd.read_csv(structured, encoding_errors="surrogateescape")
        templates = pd.read_csv(template)
        prompt = official_prompt_functions(pd)["generate_log_prompt"](
            request["theme"], request["pod"], request["columns"], templates, frame)
        selected = [f"{ord(c)-0xdc00:02x}" for c in prompt if 0xdc80 <= ord(c) <= 0xdcff]
        report.update(status="DIAGNOSED", rows=len(frame), selected_prompt_invalid_byte_count=len(selected),
                      selected_invalid_byte_hex=selected[:24], prompt_characters=len(prompt),
                      diagnostic_reader="utf8+surrogateescape; not an approved experiment reader")
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    output = PROJECT / f"docs/evidence/rca_log_encoding_{stamp}.json"
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(output), "encoding": report.get("encoding"),
                      "selected_invalid_bytes": report.get("selected_prompt_invalid_byte_count"), "error": report.get("error")}), flush=True)


if __name__ == "__main__":
    main()
