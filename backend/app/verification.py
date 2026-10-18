"""Compare OCR-extracted label text against an approved product specification.

OWNER: Amzad. Signatures and result shape are fixed by docs/api-contract.md.

How a field is judged (thresholds measured on data/sample_labels/, see the contract notes):
  1. Normalize both sides: lowercase, drop whitespace and punctuation ("Contains:Soy" == "Contains: Soy").
  2. A line that equals the expected value, or the value running
     across a line break into the next line         -> MATCH
  3. Otherwise the most similar whole line, if it is at least SIMILAR_RATIO alike:
       - it contains the expected value             -> MATCH
       - it doesn't                                 -> INCORRECT ("Peek Roasters" vs "Peak Roasters")
     Whole lines win over substrings so a correct manufacturer line ("Peak Roasters LLC")
     can't hide a misprinted brand line ("Peek Roasters").
  4. The expected value inside any line            -> MATCH
  5. Nothing close                                  -> MISSING
A MATCH or INCORRECT read from a line below MIN_CONFIDENCE becomes UNCERTAIN: a blurry photo
of a good label must not report a wrong expiry date.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.ocr import OcrLine, OcrResult

# Field-level statuses
MATCH = "match"
MISSING = "missing"
INCORRECT = "incorrect"
UNCERTAIN = "uncertain"

# Overall statuses
PASS = "pass"
NEEDS_REVIEW = "needs_review"

MIN_CONFIDENCE = 0.90  # below this, OCR can't be trusted to tell a misprint from a misread
SIMILAR_RATIO = 0.60  # "Net Wt 10 oz (283 g)" vs "Net Wt 12 oz (340 g)" scores ~0.69
WEAK_MISMATCH_SIMILARITY = 0.80
STRONG_MISMATCH_CONFIDENCE = 0.95


@dataclass
class FieldResult:
    field: str
    expected: str
    found: str | None
    status: str  # match | missing | incorrect | uncertain
    confidence: float  # 0.0 to 1.0: OCR confidence of the line(s) it was judged on

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "expected": self.expected,
            "found": self.found,
            "status": self.status,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class VerificationResult:
    status: str  # pass | needs_review
    fields: list[FieldResult] = field(default_factory=list)


def normalize(text: str) -> str:
    # OCR commonly reads the letter O in the unit "OZ" as zero. Limit this
    # repair to a separate unit after a numeric quantity, leaving SKU digits
    # and the weight's actual numeric value untouched.
    text = re.sub(r"(?i)(\b\d+(?:[.,]\d+)?\s+)0z\b", r"\1oz", text)
    # On some nutrition tables OCR reports the unit column before its value.
    # Only reorder a whole, two-token line: never rearrange arbitrary prose.
    if match := re.fullmatch(r"\s*(g|kg|ml|l|oz)\s+(\d+(?:[.,]\d+)?)\s*", text, re.I):
        text = f"{match.group(2)}{match.group(1)}"
    return re.sub(r"[^a-z0-9]", "", text.lower())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def verify_label(ocr: OcrResult, expected: dict[str, str]) -> VerificationResult:
    """Return one FieldResult per key in `expected`, in the spec's key order."""
    results = [_check_field(name, value, ocr.lines) for name, value in expected.items()]
    overall = PASS if results and all(r.status == MATCH for r in results) else NEEDS_REVIEW
    return VerificationResult(status=overall, fields=results)


def _check_field(name: str, expected: str, lines: list[OcrLine]) -> FieldResult:
    target = normalize(expected)
    normed = [(line, normalize(line.text)) for line in lines]

    def result(status: str, found: str | None, confidence: float) -> FieldResult:
        if status in (MATCH, INCORRECT) and confidence < MIN_CONFIDENCE:
            status = UNCERTAIN
        return FieldResult(name, expected, found, status, confidence)

    if not target:  # an empty spec value can't be checked against anything
        return FieldResult(name, expected, None, MISSING, 0.0)

    for line, text in normed:
        if text == target:
            return result(MATCH, line.text, line.confidence)
    for (a, a_text), (b, b_text) in zip(normed, normed[1:]):  # "Contains: Oats," / "Almonds, Milk"
        if _spans_break(target, a_text, b_text):
            return result(MATCH, f"{a.text}\n{b.text}", min(a.confidence, b.confidence))

    # A precise numeric field at the start of a longer explanatory line is
    # stronger evidence than a second, shorter heading (e.g. "Porción" alone).
    # Require a word boundary so SKU-060 does not match SKU-0600. Brand-only
    # substring matches still wait until after fuzzy whole-line comparison.
    if any(ch.isdigit() for ch in expected):
        needle = expected.strip().casefold()
        for line, _ in normed:
            haystack = line.text.strip().casefold()
            if haystack.startswith(needle) and (len(haystack) == len(needle)
                                             or not haystack[len(needle)].isalnum()):
                return result(MATCH, line.text, line.confidence)

    scored = [(similarity(target, text), line, text) for line, text in normed if text]
    if scored:
        score, line, text = max(scored, key=lambda s: s[0])
        if score >= SIMILAR_RATIO:
            status = MATCH if _contains_target(target, text) else INCORRECT
            # A weakly similar, barely confident OCR line is evidence of an
            # unclear photo, not enough to claim the physical label is wrong.
            if (status == INCORRECT and score <= WEAK_MISMATCH_SIMILARITY
                    and line.confidence < STRONG_MISMATCH_CONFIDENCE):
                status = UNCERTAIN
            return result(status, line.text, line.confidence)

    for line, text in normed:
        if _contains_target(target, text):
            return result(MATCH, line.text, line.confidence)

    return FieldResult(name, expected, None, MISSING, 0.0)


def _contains_target(target: str, text: str) -> bool:
    """Do not count a quantity or SKU as matched by a longer digit sequence."""
    start = text.find(target)
    while start != -1:
        end = start + len(target)
        if not (target[-1].isdigit() and end < len(text) and text[end].isdigit()):
            return True
        start = text.find(target, start + 1)
    return False


def _spans_break(target: str, first: str, second: str) -> bool:
    """True if `target` occurs in first+second starting in `first` and ending in `second`."""
    joined = first + second
    start = joined.find(target)
    while start != -1:
        if start < len(first) < start + len(target):
            return True
        start = joined.find(target, start + 1)
    return False
