"""Approved D06 lossless reader for proven UTF-8 failures only."""
import re
from pathlib import Path


POLICY = "d06_surrogateescape_valid_selected_prompt_v1"
BAD_BYTES = re.compile(r"[\udc80-\udcff]")


class EncodingSelectionError(ValueError):
    pass


def require_valid_prompt(message):
    for field in ("prompt", "system_prompt"):
        value = message[field]
        if BAD_BYTES.search(value):
            raise EncodingSelectionError(f"Invalid source bytes enter selected {field}; no substitution or omission")
        value.encode("utf-8", errors="strict")


class ApprovedReader:
    def __init__(self, pandas, paths, audit):
        self.pandas = pandas
        self.paths = {Path(path).resolve(): kind for kind, path in paths.items()}
        self.audit = audit

    def __getattr__(self, name):
        return getattr(self.pandas, name)

    def read_csv(self, path, *args, **kwargs):
        path = Path(path).resolve()
        if path not in self.paths or args or kwargs:
            raise ValueError("D06 permits only the original exact files and original read_csv call")
        kind = self.paths[path]
        record = {"file": path.name, "kind": kind, "policy": POLICY, "mode": "strict_utf8"}
        self.audit.append(record)
        try:
            return self.pandas.read_csv(path)
        except UnicodeDecodeError as error:
            record["strict_error"] = str(error)
            record["mode"] = "utf8_surrogateescape"
        # No ignored errors, replacement characters, row filtering or encoding
        # guess. Surrogates carry original invalid bytes until selection checks.
        frame = self.pandas.read_csv(path, encoding_errors="surrogateescape")
        if any(BAD_BYTES.search(str(column)) for column in frame.columns):
            raise EncodingSelectionError("Invalid bytes in source CSV column names")
        invalid = {}
        for column in frame.columns:
            count = rows = 0
            for value in frame[column].array:
                if isinstance(value, str):
                    amount = len(BAD_BYTES.findall(value))
                    count += amount
                    rows += amount > 0
            if count:
                invalid[str(column)] = {"invalid_bytes": count, "rows": rows}
        record.update(rows=len(frame), columns=list(frame.columns), invalid_bytes_by_column=invalid,
                      invalid_bytes=sum(v["invalid_bytes"] for v in invalid.values()))
        # These fields control the original event matching/order/stride. All
        # template text is also required to be valid, even past the original cap.
        critical = {"EventId", "EventTemplate", "Occurrence"} if kind == "templates" else {"EventId"}
        if critical & set(invalid):
            raise EncodingSelectionError(f"Invalid bytes affect event identification/selection: {sorted(critical & set(invalid))}")
        record["selection_fields_valid"] = True
        return frame
