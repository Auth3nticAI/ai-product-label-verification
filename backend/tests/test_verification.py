"""verify_label() unit tests.  OWNER: Amzad

These use hand-built OcrResults, so they test judging only, never reading
(see skills/labelguard-testing/SKILL.md). OCR accuracy lives in test_ocr.py.
"""
import json
from pathlib import Path

import pytest

from app import ocr
from app.verification import (
    INCORRECT,
    MATCH,
    MIN_CONFIDENCE,
    MISSING,
    NEEDS_REVIEW,
    PASS,
    UNCERTAIN,
    normalize,
    verify_label,
)

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "sample_labels"
SPECS = json.loads((SAMPLES / "specs.json").read_text())


def label(*lines: tuple[str, float]) -> ocr.OcrResult:
    return ocr.build_result(
        [ocr.OcrLine(t, c, (0, i * 40, 100, 30)) for i, (t, c) in enumerate(lines)], "test"
    )


def check(lines, expected: str):
    [result] = verify_label(label(*lines), {"f": expected}).fields
    return result


# --- normalization -------------------------------------------------------------


@pytest.mark.parametrize(
    "a, b",
    [
        ("Contains: Soy", "Contains:Soy"),
        ("16 FL OZ (473 mL)", "16 fl. oz. 473ml"),
        ("SKU: SF-GRN-12", "sku sfgrn12"),
        ("Best By: 03/15/2027", "BEST BY 03.15.2027"),
    ],
)
def test_normalize_ignores_case_spacing_and_punctuation(a, b):
    assert normalize(a) == normalize(b)


def test_normalize_keeps_digits_distinct():
    assert normalize("Net Wt 12 oz") != normalize("Net Wt 10 oz")


def test_normalize_recovers_common_unit_ocr_errors_without_changing_quantity():
    assert normalize("NET WT 14 0Z (397g)") == normalize("NET WT 14 OZ (397g)")
    assert normalize("NET WT 14 0Z (397g)") != normalize("NET WT 12 OZ (340g)")
    assert normalize("g 100") == normalize("100 g")
    assert normalize("g 100") != normalize("120 g")


# --- per-field status --------------------------------------------------------------


def test_exact_line_is_match_with_line_confidence():
    r = check([("Sunrise Farms", 0.98)], "Sunrise Farms")
    assert (r.status, r.found, r.confidence) == (MATCH, "Sunrise Farms", 0.98)


def test_match_tolerates_ocr_dropping_spaces():
    assert check([("SKU:VC-MV-060", 0.95)], "SKU: VC-MV-060").status == MATCH


@pytest.mark.parametrize(
    "printed, expected",
    [
        ("Net Wt 10 oz (283 g)", "Net Wt 12 oz (340 g)"),
        ("Peek Roasters", "Peak Roasters"),
        ("Best By: 01/10/2026", "Best By: 01/10/2027"),
        ("SKU: VC-MV-090", "SKU: VC-MV-060"),
    ],
)
def test_similar_but_different_is_incorrect(printed, expected):
    r = check([(printed, 0.99)], expected)
    assert (r.status, r.found) == (INCORRECT, printed)


def test_nothing_close_is_missing():
    r = check([("Sunrise Farms", 0.99), ("Store in a cool, dry place.", 0.99)], "Contains: Oats, Almonds, Milk")
    assert (r.status, r.found, r.confidence) == (MISSING, None, 0.0)


def test_empty_label_is_missing():
    assert check([], "Sunrise Farms").status == MISSING


def test_low_confidence_match_is_uncertain():
    assert check([("Contains: Soy", 0.80)], "Contains: Soy").status == UNCERTAIN


def test_low_confidence_mismatch_is_uncertain_not_incorrect():
    # The measured vitamin_low_quality.jpg misread: a blurry good label must not report a wrong date.
    assert check([("Dest By: 06/312028", 0.87)], "Best By: 08/31/2028").status == UNCERTAIN


def test_confidence_threshold_is_inclusive():
    assert check([("Peek Roasters", MIN_CONFIDENCE)], "Peak Roasters").status == INCORRECT
    assert check([("Peek Roasters", MIN_CONFIDENCE - 0.01)], "Peak Roasters").status == UNCERTAIN


def test_value_inside_a_longer_line_is_match():
    r = check([("Ingredients: oats, honey. Contains: Milk", 0.97)], "Contains: Milk")
    assert r.status == MATCH


def test_dedicated_line_beats_substring_elsewhere():
    """The manufacturer line contains the correct brand, but the brand line itself is misprinted."""
    lines = [("Peek Roasters", 0.99), ("Peak Roasters LLC, Denver, CO", 0.99)]
    r = check(lines, "Peak Roasters")
    assert (r.status, r.found) == (INCORRECT, "Peek Roasters")


def test_numeric_value_with_explanatory_suffix_beats_short_duplicate_heading():
    lines = [("Porción: 12 g (1 cuchara de sopa)", 0.98), ("Porción", 0.99)]
    r = verify_label(label(*lines), {"serving_size": "Porción: 12 g"}).fields[0]
    assert (r.status, r.found) == (MATCH, "Porción: 12 g (1 cuchara de sopa)")
    assert check([("SKU: VC-MV-0600", 0.99)], "SKU: VC-MV-060").status != MATCH


def test_weak_fuzzy_read_near_confidence_cutoff_is_uncertain():
    assert check([("Inutelal", 0.9029)], "nutella").status == UNCERTAIN
    assert check([("ORIJINAL TAT", 0.9409)], "Coca-Cola Original Taste").status == UNCERTAIN
    assert check([("Peek Roasters", 0.99)], "Peak Roasters").status == INCORRECT


def test_value_wrapped_across_two_lines_is_match():
    r = check([("Contains: Oats,", 0.99), ("Almonds, Milk", 0.97), ("Store cool", 0.99)],
              "Contains: Oats, Almonds, Milk")
    assert r.status == MATCH
    assert r.found == "Contains: Oats,\nAlmonds, Milk"
    assert r.confidence == 0.97


def test_blank_expected_value_is_missing():
    assert check([("anything", 0.99)], "  ").status == MISSING


# --- overall status ------------------------------------------------------------------


def test_all_match_is_pass():
    spec = {"brand": "Sunrise Farms", "net": "Net Wt 12 oz (340 g)"}
    result = verify_label(label(("Sunrise Farms", 0.99), ("Net Wt 12 oz (340 g)", 0.99)), spec)
    assert result.status == PASS
    assert [f.field for f in result.fields] == ["brand", "net"]


@pytest.mark.parametrize("bad_line", [("Net Wt 10 oz (283 g)", 0.99), ("Net Wt 12 oz (340 g)", 0.5), None])
def test_any_non_match_needs_review(bad_line):
    lines = [("Sunrise Farms", 0.99)] + ([bad_line] if bad_line else [])
    result = verify_label(label(*lines), {"brand": "Sunrise Farms", "net": "Net Wt 12 oz (340 g)"})
    assert result.status == NEEDS_REVIEW


def test_empty_spec_needs_review():
    assert verify_label(label(("Sunrise Farms", 0.99)), {}).status == NEEDS_REVIEW


# --- the measured low-quality photo (docs/api-contract.md, "Notes for verification") ------------


def test_low_quality_vitamin_photo_matches_answer_key():
    noisy = label(
        ("VitaCore", 1.00),
        ("Daily Multivitamin", 1.00),
        ("60 Tablets", 1.00),
        ("Cons usoy", 0.63),
        ("SKU:VC-MV-060", 0.93),
        ("Dest By: 06/312028", 0.87),
        ("VitaCore Heath, Austin, TX", 0.95),
        ("Shome in a lt dy pes", 0.56),
    )
    result = verify_label(noisy, SPECS["vitamin"]["fields"])
    got = {f.field: f.status for f in result.fields}
    assert result.status == NEEDS_REVIEW
    assert got["allergens"] == UNCERTAIN
    assert got["best_by"] == UNCERTAIN
    assert got["manufacturer"] in (INCORRECT, UNCERTAIN)  # contract: a false alarm is acceptable
    for field in ("brand", "product_name", "net_contents", "sku"):
        assert got[field] == MATCH, got
