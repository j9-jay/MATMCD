"""One deterministic boundary repair for explicit local RE calls; no LLM rewrite."""
from dataclasses import asdict, dataclass
from decimal import Decimal
import re


RE_FORMAT_POLICY = "re_gp_boundary_v1"
_HEADER = re.compile(r"(?m)^(?:---[ \t]*)?([GP])([0-9]+):[ \t]+")
_POSSIBLE_HEADER = re.compile(r"(?m)^[ \t]*(?:---[ \t]*)?[GP][0-9]+\s*:")
_PROBABILITY = re.compile(r"([0-9]+(?:\.[0-9]+)?|\.[0-9]+)[ \t\r\n]*(?:---[ \t\r\n]*)?\Z")
_ANSWER = re.compile(r"<(yes|no)>[>]*\Z")


class REFormatError(ValueError):
    """Response cannot be repaired using boundary changes alone."""


@dataclass(frozen=True)
class RERecord:
    index: int
    guess: str
    probability_text: str
    terminal_answer: str


@dataclass(frozen=True)
class NormalizedRE:
    raw_text: str
    normalized_text: str
    records: tuple[RERecord, ...]

    @property
    def changed(self):
        return self.raw_text != self.normalized_text

    def audit(self):
        return {"policy": RE_FORMAT_POLICY, "status": "NORMALIZED" if self.changed else "UNCHANGED",
                "normalization_passes": 1, "expected_guesses": len(self.records),
                "raw_text": self.raw_text, "normalized_text": self.normalized_text,
                "records": [asdict(record) for record in self.records], "fields_preserved": True}


def _read_records(text, expected_guesses, terminal_answers=("yes", "no")):
    if not isinstance(text, str) or not text.strip():
        raise REFormatError("Missing RE response")
    headers = list(_HEADER.finditer(text))
    expected = [(kind, str(i)) for i in range(1, expected_guesses + 1) for kind in ("G", "P")]
    if [(h.group(1), h.group(2)) for h in headers] != expected:
        raise REFormatError("Expected exactly ordered G1/P1 ... Gn/Pn records; no missing or duplicate labels")
    if len(list(_POSSIBLE_HEADER.finditer(text))) != len(headers):
        raise REFormatError("Ambiguous or unsupported record label")
    if text[:headers[0].start()].strip():
        raise REFormatError("Unexpected text before G1")
    records = []
    for i in range(expected_guesses):
        g, p = headers[2 * i:2 * i + 2]
        # Strip record-edge whitespace as the original parser does, never internal text.
        guess = text[g.end():p.start()].strip()
        if terminal_answers not in (("yes", "no"), ("Yes", "No")):
            raise ValueError("Use the original caller's exact answer case")
        answer = re.search(r"<(" + "|".join(terminal_answers) + r")>[>]*\Z", guess)
        if not answer or "\n\n" in guess or "---" in guess:
            raise REFormatError("Guess must end in <yes>/<no> and have unambiguous internal boundaries")
        end = headers[2 * i + 2].start() if i + 1 < expected_guesses else len(text)
        probability = _PROBABILITY.fullmatch(text[p.end():end])
        if not probability:
            raise REFormatError("Probability must be a bare decimal; no inferred values or extra comments")
        literal = probability.group(1)
        if not Decimal(0) <= Decimal(literal) <= Decimal(1):
            raise REFormatError("Probability outside [0, 1]")
        records.append(RERecord(i + 1, guess, literal, answer.group(1)))
    return tuple(records)


def _original_layout_fields(text):
    """Inspect original G/P chunk boundaries; do not select or reinterpret a guess."""
    fields = []
    for part in text.split("---"):
        chunks = part.strip().split("\n\n")
        for left, right in zip(chunks, chunks[1:]):
            if left.startswith("G") and right.startswith("P"):
                if ": " not in left or ": " not in right:
                    return None
                fields.append((left.split(": ", 1)[1].strip(), right.split(": ", 1)[1].strip()))
    return fields


def normalize_re_response(text, *, expected_guesses, terminal_answers=("yes", "no")):
    if type(expected_guesses) is not int or expected_guesses < 1:
        raise ValueError("An explicit positive guess count is required")
    records = _read_records(text, expected_guesses, terminal_answers)
    fields = [(record.guess, record.probability_text) for record in records]
    if _original_layout_fields(text) == fields:
        return NormalizedRE(text, text, records)
    normalized = "\n\n---".join(
        f"G{record.index}: {record.guess}\n\nP{record.index}: {record.probability_text}" for record in records)
    if _original_layout_fields(normalized) != fields or _read_records(normalized, expected_guesses, terminal_answers) != records:
        raise REFormatError("Boundary repair would change record fields")
    return NormalizedRE(text, normalized, records)


class REFormatClient:
    """Wrap only RE calls; each underlying response is handled once and audited."""
    def __init__(self, client, *, expected_guesses, audit_callback, terminal_answers=("yes", "no")):
        if type(expected_guesses) is not int or expected_guesses < 1 or not callable(audit_callback):
            raise ValueError("Explicit guess count and audit callback are required")
        self.client = client
        self.expected_guesses = expected_guesses
        self.audit_callback = audit_callback
        self.terminal_answers = terminal_answers

    def inquire_LLMs(self, prompt, system_prompt, temperature=0.5):
        raw = self.client.inquire_LLMs(prompt, system_prompt, temperature=temperature)
        try:
            result = normalize_re_response(raw, expected_guesses=self.expected_guesses, terminal_answers=self.terminal_answers)
        except REFormatError as exc:
            self.audit_callback({"policy": RE_FORMAT_POLICY, "status": "REJECTED", "normalization_passes": 1,
                                 "expected_guesses": self.expected_guesses, "raw_text": raw,
                                 "normalized_text": None, "error": str(exc)})
            raise
        self.audit_callback(result.audit())
        return result.normalized_text
