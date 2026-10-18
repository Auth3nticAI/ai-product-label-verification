"""Run the human-annotated real-photo challenge against an isolated local API.

Example: python tests/e2e/challenge/run_challenge.py --base-url http://127.0.0.1:8767
This creates 18 specs and inspections; it refuses non-loopback URLs.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCES = {row["file"]: row for row in json.loads((ROOT / "sources.json").read_text())}
CASES = json.loads((ROOT / "cases.json").read_text())["cases"]


def main(base_url, output):
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Challenge writes are permitted only to a loopback HTTP API")
    images = {}
    for filename in {case["image"] for case in CASES}:
        source = SOURCES[filename]
        path = ROOT / "images" / filename
        data = path.read_bytes()
        if len(data) != source["bytes"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"{filename}: source bytes differ from pinned manifest")
        with Image.open(path) as image:
            image.verify()
        images[filename] = data

    results = []
    with httpx.Client(base_url=base_url, timeout=90) as client:
        for case in CASES:
            spec = client.post("/specs", json=case["spec"])
            spec.raise_for_status()
            spec_id = spec.json()["id"]
            filename = case["image"]
            inspection = client.post(
                "/inspections", data={"spec_id": str(spec_id)},
                files={"image": (filename, images[filename], "image/jpeg")},
            )
            inspection.raise_for_status()
            actual = inspection.json()
            saved = client.get(f"/inspections/{actual['id']}")
            saved.raise_for_status()
            history = client.get("/inspections", params={"spec_id": spec_id})
            history.raise_for_status()
            persisted = saved.json() == actual and any(
                row["id"] == actual["id"] and row["results"] == actual["results"]
                for row in history.json()
            )
            fields = {row["field"]: row for row in actual["results"]}
            actual_statuses = {name: row["status"] for name, row in fields.items()}
            expected_statuses = case["expected_fields"]
            verdict_met = actual["status"] == case["expected_status"]
            fields_met = actual_statuses == expected_statuses
            result = {
                "id": case["id"], "image": filename,
                "difficulty": case["difficulty"], "truth_kind": case["truth_kind"],
                "visible_truth": case["visible_truth"],
                "expected_status": case["expected_status"], "actual_status": actual["status"],
                "expected_fields": expected_statuses, "actual_fields": actual_statuses,
                "verdict_met": verdict_met, "fields_met": fields_met,
                "persisted": persisted, "ocr_mean_confidence": actual["ocr"]["mean_confidence"],
                "ocr_text": actual["ocr"]["text"], "field_evidence": actual["results"],
            }
            results.append(result)
            print(f"{case['id']}: expected={case['expected_status']}/{expected_statuses} "
                  f"actual={actual['status']}/{actual_statuses} "
                  f"verdict={'PASS' if verdict_met else 'FAIL'} "
                  f"fields={'PASS' if fields_met else 'FAIL'} saved={persisted}")
    output.write_text(json.dumps({"cases": results}, indent=2) + "\n")
    print(f"SUMMARY verdicts={sum(r['verdict_met'] for r in results)}/{len(results)} "
          f"fields={sum(r['fields_met'] for r in results)}/{len(results)} "
          f"persisted={sum(r['persisted'] for r in results)}/{len(results)}")
    print(f"REPORT {output}")
    if not all(row["persisted"] for row in results):
        raise SystemExit("Inspection persistence failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8767")
    parser.add_argument("--output", type=Path, default=ROOT / "results.json")
    args = parser.parse_args()
    main(args.base_url, args.output)
