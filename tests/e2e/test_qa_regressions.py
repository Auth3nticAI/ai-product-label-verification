"""HTTP + persistence regressions for Vincent's sample-label QA assignment.

All uploaded bytes are synthetic and committed under fixtures/. Production CI
uses E2E_READONLY=1, which skips every test in this file before any write.
"""

import json
from pathlib import Path

import pytest
from PIL import Image

from conftest import READONLY, SAMPLES, require_implemented, upload


FIXTURES = Path(__file__).with_name("fixtures")
QA = json.loads((FIXTURES / "qa_manifest.json").read_text())


@pytest.mark.parametrize("case", QA["cases"], ids=lambda c: c["id"])
def test_two_independent_defects_are_saved_with_field_evidence(api, spec_ids, case):
    """One label must keep both wrong weight and missing allergens distinct."""
    image = FIXTURES / case["image"]
    spec_id = spec_ids[case["spec_id"]]
    response = require_implemented(api.post(
        "/inspections", data={"spec_id": str(spec_id)}, files=upload(image),
    ))
    assert response.status_code == 201, response.text
    inspection = response.json()

    fields = {row["field"]: row for row in inspection["results"]}
    flagged = {name: row["status"] for name, row in fields.items() if row["status"] != "match"}
    assert inspection["status"] == case["expected_status"]
    assert flagged == case["expected_flags"]
    assert len(flagged) == case["expected_issue_count"]
    assert fields["net_contents"]["found"] == case["printed_changes"]["net_contents"]
    assert fields["allergens"]["found"] is None
    assert fields["allergens"]["confidence"] == 0.0
    assert inspection["image_filename"] == image.name
    assert case["printed_changes"]["net_contents"] in inspection["ocr"]["text"]
    assert "Contains:" not in inspection["ocr"]["text"]

    # The frontend crops evidence from the uploaded image, so every OCR box
    # must be in that image's pixels even when OCR preprocessed it internally.
    with Image.open(image) as source:
        width, height = source.size
    for line in inspection["ocr"]["lines"]:
        x, y, w, h = line["bbox"]
        assert 0 <= x < width and 0 <= y < height
        assert w > 0 and h > 0 and x + w <= width and y + h <= height

    saved = require_implemented(api.get(f"/inspections/{inspection['id']}"))
    assert saved.status_code == 200
    assert saved.json() == inspection
    history = require_implemented(api.get("/inspections", params={"spec_id": spec_id}))
    assert history.status_code == 200
    assert any(row["id"] == inspection["id"] and row["results"] == inspection["results"]
               for row in history.json())


@pytest.mark.parametrize("case", QA["invalid_uploads"], ids=lambda c: c["id"])
def test_invalid_image_never_creates_history_row(api, spec_ids, case):
    """The real HTTP/OCR/database path rejects bad uploads without persistence."""
    spec_id = spec_ids["granola"]
    before = require_implemented(api.get("/inspections", params={"spec_id": spec_id}))
    assert before.status_code == 200
    before_ids = [row["id"] for row in before.json()]

    response = require_implemented(api.post(
        "/inspections",
        data={"spec_id": str(spec_id)},
        files={"image": (case["filename"], case["payload"].encode(), case["content_type"])},
    ))
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == case["expected_detail"]

    after = require_implemented(api.get("/inspections", params={"spec_id": spec_id}))
    assert after.status_code == 200
    assert [row["id"] for row in after.json()] == before_ids


def test_spec_delete_rules_preserve_inspection_history(api):
    """The full API lifecycle allows cleanup but refuses orphaning history."""
    if READONLY:
        pytest.skip("E2E_READONLY=1: spec lifecycle creates data")

    fields = {"brand": "Sunrise Farms"}
    unused = require_implemented(api.post(
        "/specs", json={"name": "QA E2E synthetic unused spec", "fields": fields},
    ))
    used = require_implemented(api.post(
        "/specs", json={"name": "QA E2E synthetic inspected spec", "fields": fields},
    ))
    assert unused.status_code == used.status_code == 201
    unused_id, used_id = unused.json()["id"], used.json()["id"]

    assert api.delete(f"/specs/{unused_id}").status_code == 204
    assert api.get(f"/specs/{unused_id}").status_code == 404

    inspection = require_implemented(api.post(
        "/inspections",
        data={"spec_id": str(used_id)},
        files=upload(SAMPLES / "granola_correct.png"),
    ))
    assert inspection.status_code == 201, inspection.text
    assert inspection.json()["status"] == "pass"

    refused = api.delete(f"/specs/{used_id}")
    assert refused.status_code == 409
    assert "1 inspection(s)" in refused.json()["detail"]
    assert api.get(f"/specs/{used_id}").status_code == 200
    assert api.get(f"/inspections/{inspection.json()['id']}").status_code == 200
