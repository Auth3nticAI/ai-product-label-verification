"""Rebuild Tray's public reference pack and exercise its eight cases locally.

Usage: python tests/e2e/web_label_qa.py download OUTPUT_DIR
       python tests/e2e/web_label_qa.py run OUTPUT_DIR --base-url http://127.0.0.1:8767

Downloaded manufacturer artwork stays outside Git. The runner only permits a
loopback API because it creates specs and inspections.
"""

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCES = json.loads((ROOT / "docs/web-label-sources.json").read_text())
CASES = json.loads((ROOT / "docs/web-label-test-cases.json").read_text())["cases"]
MIMES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def verified_image(path, source):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != source["bytes"] or digest != source["sha256"]:
        raise ValueError(f"{path.name}: byte count or SHA256 differs from source manifest")
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    return data


def download(output):
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    for source in SOURCES:
        path = output / source["file"]
        try:
            if not path.is_file():
                url = source["image_url"]
                if urlparse(url).scheme != "https":
                    raise ValueError(f"Non-HTTPS image URL: {url}")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Referer": f"{urlparse(url).scheme}://{urlparse(url).netloc}/",
                }
                try:
                    with httpx.Client(follow_redirects=True, timeout=30, headers=headers) as client:
                        response = client.get(url)
                        response.raise_for_status()
                        data = response.content
                except httpx.HTTPStatusError as error:
                    if error.response.status_code != 403:
                        raise
                    # Some image CDNs reject httpx while allowing a browser-style curl request.
                    data = subprocess.run(
                        ["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "30",
                         "-H", f"Referer: {headers['Referer']}",
                         "-H", f"User-Agent: {headers['User-Agent']}", url],
                        check=True, capture_output=True,
                    ).stdout
                if len(data) > 4_500_000:
                    raise ValueError(f"{path.name}: image exceeds app upload limit")
                path.write_bytes(data)
            verified_image(path, source)
            print(f"VERIFIED {path.name}: {source['bytes']} bytes, SHA256 {source['sha256']}")
        except (httpx.HTTPError, OSError, ValueError, subprocess.CalledProcessError) as error:
            failures.append(source["file"])
            print(f"UNAVAILABLE {source['file']}: {error}")
    if failures:
        print(f"Missing source images: {', '.join(failures)}")


def run(output, base_url):
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("The write runner requires a local HTTP API")
    images = {source["file"]: verified_image(output / source["file"], source)
              for source in SOURCES if (output / source["file"]).is_file()}
    results = []
    with httpx.Client(base_url=base_url, timeout=90) as client:
        for case in CASES:
            if case["image"] not in images:
                results.append({"case": case["case"], "image": case["image"],
                                "target_status": case["target_status"],
                                "actual_status": None, "target_met": None,
                                "persisted": None, "reason": "Source image unavailable"})
                print(f"{case['case']}: NOT RUN (source image unavailable)")
                continue
            spec = client.post("/specs", json=case["spec"])
            spec.raise_for_status()
            spec_id = spec.json()["id"]
            image_name = case["image"]
            inspection = client.post(
                "/inspections", data={"spec_id": str(spec_id)},
                files={"image": (image_name, images[image_name], MIMES[Path(image_name).suffix])},
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
            row = {
                "case": case["case"], "image": image_name,
                "target_status": case["target_status"], "actual_status": actual["status"],
                "target_met": actual["status"] == case["target_status"],
                "persisted": persisted,
                "fields": actual["results"],
                "ocr_text": actual["ocr"]["text"],
            }
            results.append(row)
            print(f"{case['case']}: target={row['target_status']} actual={row['actual_status']} "
                  f"persisted={persisted} fields="
                  f"{[(f['field'], f['status']) for f in row['fields']]}")
    report = output / "local-api-results.json"
    report.write_text(json.dumps(results, indent=2) + "\n")
    print(f"REPORT {report}")
    if not all(row["persisted"] for row in results if row["persisted"] is not None):
        raise SystemExit("At least one inspection did not persist correctly")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download", "run"])
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8767")
    args = parser.parse_args()
    if args.action == "download":
        download(args.output_dir)
    else:
        run(args.output_dir, args.base_url)
