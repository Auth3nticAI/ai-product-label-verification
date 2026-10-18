# QA Test Plan

**Owner:** Vincent · Issue [#6](https://github.com/Auth3nticAI/ai-product-label-verification/issues/6)

Environment: https://ai-product-label-verification.vercel.app (OCR and read-only API checks); isolated local API and SQLite database (workflow checks) · Tester: Vincent via Codex · Dates: Oct 17–18, 2026 UTC

Evidence scope: O1–O10 were measured against the deployed `/api/ocr` endpoint on Oct 17 using sample files from main commit `fe418ca`. On Oct 18, the current branch (based on main `6e838b3`) passed 179/179 backend unit tests and 21/21 local API end-to-end tests against an isolated SQLite database. The prior 16-test suite covered all nine manifest verdicts; this PR adds five synthetic HTTP regression cases and strengthens saved-result assertions. All eight of Tray's public manufacturer image cases also matched their targets through a separate isolated local API. The deployed API passed 7/7 read-only-mode checks before the new cases were added (nine production write tests skipped). The expanded suite also passed in read-only mode locally: 7 passed, 14 write tests skipped. The local verdicts do **not** establish that the production UI, phone upload, or production write flow passed. Those rows remain open below.

Result key: **PASS** matches expected · **FAIL** differs (file a bug, link it) · **BLOCKED** can't run yet (e.g. route not built)

## 1. OCR on the live API (can run now)

`POST /api/ocr` from [/api/docs](https://ai-product-label-verification.vercel.app/api/docs) → "Try it out", upload each file from `data/sample_labels/`.
Expected: every printed field appears in `text`. The blurry label has low-confidence lines.

| # | File | Expected OCR | Actual (mean confidence, anything misread) | Result |
|---|---|---|---|---|
| O1 | granola_correct.png | All 7 fields read; mean ≈ 0.99 | All 7 fields read; mean 0.9972 | PASS |
| O2 | granola_wrong_net_weight.png | Reads "Net Wt 10 oz (283 g)" | Exact line read; mean 0.9946 | PASS |
| O3 | granola_missing_allergens.png | No "Contains:" line | No "Contains:" line; mean 0.9966 | PASS |
| O4 | coffee_correct.png | All 7 fields read | All 7 fields read; mean 0.9894 | PASS |
| O5 | coffee_brand_typo.png | Reads "Peek Roasters" | Exact line read; mean 0.9894 | PASS |
| O6 | coffee_wrong_best_by.png | Reads "Best By: 01/10/2026" | Exact line read; mean 0.9897 | PASS |
| O7 | vitamin_correct.png | All 7 fields read | All 7 fields read; mean 0.9993 | PASS |
| O8 | vitamin_wrong_sku.png | Reads "SKU: VC-MV-090" | Exact line read; mean 0.9993 | PASS |
| O9 | vitamin_low_quality.jpg | Some lines misread with confidence < 0.90 (date ≈ "06/312028") | Mean 0.8732; `Cons usoy` 0.6408, `Dest By: 06/312028` 0.8695, `VitaCore Heath` 0.9527 | PASS |
| O10 | a .txt or .pdf file | 422 "not a readable image" | A plain-text file returned HTTP 422, `File is not a readable image` | PASS |

O9 is the Oct 17 measurement. A read-only repeat of `/api/ocr` on Oct 18 against the current deployed build returned mean confidence 0.9126 and the lines `Cons snoy`, `Dest By: 06/312028`, and only `TX` where the manufacturer line should be. This still demonstrates the expected low-confidence date, but the manufacturer extraction has changed. No production inspection was created to test its verdict.

## 2. Full workflow (live now)

Create the three specs from `data/sample_labels/specs.json`, then upload each label against its spec.

Local automated evidence: F1–F9 matched `data/sample_labels/manifest.json` on Oct 18; inspection history persisted and could be read back. Production UI results, per-field explanation boxes, Issues counts, and image evidence crops were not exercised in this pass, so the live rows remain unscored.

**F9 follow-up:** The local verifier returned `allergens: uncertain`, `best_by: uncertain`, and `manufacturer: missing` from the current blurry vitamin image. The overall `needs_review` verdict and two required flags match the answer key, but the extra missing field would make the Issues count **3**, versus the **2** expected below. The current deployed OCR omits most of that manufacturer line too; the deployed inspection/UI result still needs verification. Treat the exact F9 issue count as an open QA finding, not a pass.

| # | File | Expected status | Expected field flags | Actual | Result |
|---|---|---|---|---|---|
| F1 | granola_correct.png | Pass | all match | Pass, 7/7 match (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| F2 | granola_wrong_net_weight.png | Needs Review | net_contents incorrect | Needs Review; net_contents incorrect ("Net Wt 10 oz (283 g)"), evidence crop shown (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| F3 | granola_missing_allergens.png | Needs Review | allergens missing | | |
| F4 | coffee_correct.png | Pass | all match | | |
| F5 | coffee_brand_typo.png | Needs Review | brand incorrect | | |
| F6 | coffee_wrong_best_by.png | Needs Review | best_by incorrect | | |
| F7 | vitamin_correct.png | Pass | all match | | |
| F8 | vitamin_wrong_sku.png | Needs Review | sku incorrect | | |
| F9 | vitamin_low_quality.jpg | Needs Review | allergens + best_by **uncertain** (not incorrect) | Needs Review; allergens uncertain (0.62), best_by uncertain (0.85), manufacturer **missing** (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS (verdict and both expected flags; see the F9 note) |

For every F row also check: the **Issues** count in History equals the number of non-match fields (F9 → **3**: the two expected *uncertain* fields plus manufacturer *missing*, because since the Oct 17 OCR change that blurry line isn't read at all; the manifest's notes allow a manufacturer false alarm. Found by Vincent's QA pass), every flagged field has its own explanation box under the table (missing ones included), and *Extracted text* lists the OCR lines with low-confidence ones dimmed.

## 2c. Additional synthetic regression pack (local API only)

The committed [QA fixture pack](../tests/e2e/fixtures/README.md) uses the team's synthetic Golden Harvest Granola spec and renderer; no real product or private photo is included. These tests run over HTTP against an isolated local database. They are skipped by `E2E_READONLY=1` on the deployed API.

| # | Input / action | Expected | Actual (Oct 18 local) | Result |
|---|---|---|---|---|
| Q1 | `granola_two_issues.png`: 10 oz net weight and no allergen line | Needs Review; `net_contents` incorrect and `allergens` missing; exactly two issues with persistent per-field evidence | Both flags correct; wrong weight found, missing allergen null; OCR boxes inside uploaded image; result and history agree | PASS |
| Q2 | Plain-text file as an inspection image | 422 readable-image error; no history row | 422; history IDs unchanged | PASS |
| Q3 | Text bytes mislabeled as PNG | 422 readable-image error; no history row | 422; history IDs unchanged | PASS |
| Q4 | Empty PNG upload | 422 empty-upload error; no history row | 422; history IDs unchanged | PASS |
| Q5 | Create two synthetic specs; delete unused one, inspect against the other, then try to delete it | Unused spec deleted (204); inspected spec retained (409) with its inspection still readable | 204 then 404 for unused; 409 for inspected; spec and inspection still readable | PASS |

## 2b. Sample inspection and spec management

| # | Test | Expected | Actual | Result |
|---|---|---|---|---|
| S1 | Home → **Try a Sample Inspection** | Inspect opens with `granola_wrong_net_weight.png` loaded (real file name and size) and **Golden Harvest Granola** selected; the notice says it's a real sample | As expected: real file (57 KB), spec selected, real-sample notice (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| S2 | Press **Verify Label** on S1 | A real result: Needs Review, `net_contents` incorrect ("Net Wt 10 oz (283 g)"), a close-up crop of the net weight line; a new row appears in History | | |
| S3 | Locally with an empty database, run S1–S2 | The sample creates the Golden Harvest Granola spec once, then inspects | | |
| M1 | Specs → **New spec** → name + 2 fields → Save | The spec appears, selected, showing "2 fields • Created {today}" | | |
| M2 | ⋯ → **Duplicate as new spec** | The form opens prefilled; saving creates a second spec; the original is unchanged | | |
| M3 | ⋯ → **Delete** on a spec with no inspections | Confirm prompt, then it disappears and stays gone after reload | | |
| M4 | ⋯ → **Delete** on a spec that has inspections | Refused: "Spec has N inspection(s) in history; it can't be deleted"; the spec stays | | |
| M5 | Look for invented data anywhere | No signed-in user (the sidebar says "Demo workspace · No sign-in yet"), no "Draft/Approved", versions, reviewers or product photos on real specs | | |

## 3. History, errors and edge cases

| # | Test | Expected | Actual | Result |
|---|---|---|---|---|
| H1 | Open history after F1–F9 | All 9 listed, newest first, with timestamps | | |
| H2 | Reopen one inspection from history | Same status and fields as when it ran | Detail page shows the saved result (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| H3 | Reload the page / come back later | History still there (stored in the database) | | |
| E1 | Upload with no spec selected | Clear error, nothing saved | | |
| E2 | Upload a non-image | Clear error message, not a crash | | |
| E3 | Upload a phone photo > 4.5 MB | The app shows "Compressed X MB to Y MB" and the upload succeeds | | |
| E5 | Upload an iPhone photo straight from the camera roll (HEIC) | Either accepted (iOS converts it to JPEG) or a clear "Choose a PNG, JPEG…" message; never a crash | | |
| H4 | History search, date filter and pagination | Search by product or file name filters rows; "Last 7 days" hides older rows; pages move 6 rows at a time | | |
| E4 | Submit the spec form with empty fields | Validation message | | |

## 4. Devices

| # | Device / browser | Spec form | Upload (camera photo) | Results readable | History | Result |
|---|---|---|---|---|---|---|
| D1 | Desktop Chrome | | | | | |
| D2 | Desktop Safari or Firefox | | | | | |
| D3 | iPhone Safari | | | | | |
| D4 | Android Chrome | | | | | |

## 5. Real product labels

Use the local test pack (`artifacts/web-label-test-pack.zip`, **not in the repo**: brand images, testing only) and at least two photos taken with a phone. For each: create a spec from the pack's expected values, upload on **Inspect** (not the sample), confirm the verdict persists in History. Start with `cinnamon-ingredients.jpg`.

On Oct 18, `tests/e2e/web_label_qa.py` rebuilt all seven original manufacturer files from `docs/web-label-sources.json`; their byte sizes, SHA256 hashes, and image decoding matched. The Kikkoman WebP source rejected `httpx` with HTTP 403, but a browser-style `curl` request with the site referer fetched the **exact hash-matching bytes**. Against an isolated local API and SQLite database, all eight cases below created separate specs and inspections, matched the intended verdicts, and persisted identical details in `GET /inspections/{id}` and filtered History. The full OCR text and field evidence are in the local `web-label-test-pack-2026-10-18/local-api-results.json` report. These are API checks with manufacturer artwork, not production UI or phone photos.

| Case | Image | Expected | Actual local API | Result |
|---|---|---|---|---|
| 01 | Cinnamon ingredients | pass | pass; ingredients match; saved | PASS |
| 02 | Cinnamon front | pass | pass; name, form, weight match; saved | PASS |
| 03 | Cinnamon front, wrong expected weight | needs_review | needs_review; weight incorrect; saved | PASS |
| 04 | Soy sauce front | pass | pass; brand, name, weight match; saved | PASS |
| 05 | Soy sauce front, absent ingredients | needs_review | needs_review; ingredients missing; saved | PASS |
| 06 | Oats front | pass | pass; name, variant, weight match; saved | PASS |
| 07 | Oats back | pass | pass; ingredients match; saved | PASS |
| 08 | Cinnamon nutrition | pass | pass; serving size matches; saved | PASS |

Reproduce with `python tests/e2e/web_label_qa.py download <outside-repo-directory>`, then run a **local** backend with an isolated `DATABASE_URL`, then `python tests/e2e/web_label_qa.py run <outside-repo-directory> --base-url http://127.0.0.1:<port>`. The runner refuses non-loopback APIs. The branded image bytes remain outside the Git repository.

### 5b. Harder real-photo challenge (local API only)

The [18-case challenge set](../tests/e2e/challenge/README.md) uses 11 **unchanged** Open Food Facts product photos, each visually inspected before its ground truth was written. [Sources, hashes, product links, and CC BY-SA 3.0 attribution](../tests/e2e/challenge/sources.json) accompany the images. It includes clean paired controls, rotated and glared cans, tiny ingredient text, multilingual panels, a low-light jar, clipped logo, and specs with deliberate wrong values. An Open Food Facts Nutella image tagged `ingredients` actually shows the front; its missing-panel case follows the visible pixels, not the metadata.

On Oct 18, after targeted verifier hardening, the isolated local API produced **16/18 expected overall verdicts, 13/18 exact field-status maps, and 18/18 persisted inspections**. The [full per-case result](../tests/e2e/challenge/results.json) retains OCR text, found values, confidence, expected/actual statuses, and History checks. No expected value was changed to match OCR output. The five remaining divergent cases are:

| Case | Inspected expectation | Actual | Finding |
|---|---|---|---|
| B02 | Wrong `SICILIANA` variant → incorrect | missing; verdict still Needs Review | Wrong spec not localized to visible `GENOVESE` |
| C01 | Clipped product name → missing | `ORIJINAL TAT` marked uncertain | Conservative review of unreadable print; reason differs |
| H01 | Visible Heinz, 14 OZ → pass | brand uncertain at 0.788 confidence; weight now matches | Low-confidence brand remains a review flag |
| H04 | Wrong `PIMIENTO` ingredient → incorrect | missing; verdict still Needs Review | Genuine mismatch not localized to tomato line |
| N01 | Visible Nutella, 400G → pass | stylized brand read `Inutelal` and marked uncertain | Review flag retained for unclear stylized OCR |

The verifier now matches B04's `g 100`/`100 g` table order, H01's `14 0Z`/`14 OZ` unit, and H05's `Porción: 12 g` before a duplicate shorter heading. A separate regression ensures a printed SKU ending `0600` cannot match an expected `060`. These findings are **local real-photo QA results**, separate from the eight simpler manufacturer cases above. They do not establish production UI results. The remaining P1/P2 rows require fresh phone captures and device/browser testing.

| # | Product photographed | Conditions (light, angle) | What OCR read | Verdict | Notes |
|---|---|---|---|---|---|
| P1 | | | | | |
| P2 | | | | | |

## 6. Pricing and billing (Stripe test mode)

| # | Test | Expected | Actual | Result |
|---|---|---|---|---|
| B1 | Open **Pricing** from the nav | 3 plans: Starter $49, Professional $149 (Most popular), Enterprise $499; limits listed; "14-day free trial" | As expected (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| B2 | Toggle **Annual** | Prices show per-month equivalent ($40.83 / $124.17 / $415.83) billed annually, "2 months free" | $40.83 / $124.17 / $415.83; $490 / $1,490 / $4,990 billed annually (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| B3 | Professional → **Start 14-day trial** → card 4242 4242 4242 4242 | Stripe Checkout opens; after paying you land on "Confirming your subscription…", then "You're on Professional" within seconds | Checkout opened (sandbox); after paying: Confirming… then "You're on Professional, trial ends Nov 1". Gotcha: untick Stripe's "Save my information with Link" or it requires a phone number (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| B4 | Sidebar after B3 | Plan badge "Professional · Trial" + **Manage billing** | Badge "Professional · Trial" + Manage billing; Pricing shows "Current plan" (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PASS |
| B5 | **Manage billing** | Stripe Customer Portal opens for this subscription; switch plan / cancel works; badge updates after returning | Portal opened: VeriLabel Professional $149/mo, Visa 4242, $0 trial invoice. Switch/cancel **not tested** (Tray, scripted Edge run on production, Oct 18 (`docs/assets/screenshots/`)) | PARTIAL |
| B6 | Try **Start trial** again while subscribed | Message to use Manage billing; no second checkout | | |
| B7 | Card 4000 0025 0000 3155 | 3-D Secure challenge, then success | | |
| B8 | Cancel on the Stripe Checkout page | Back on /pricing, nothing changed | | |
| B9 | Clear cookies, open the success page | No plan shown (the subscription stays in Stripe; known limitation: no accounts) | | |

## Bug report format

File each bug as a GitHub issue labeled `qa`:
**Steps** (numbered) · **Expected** · **Actual** · **Screenshot** · **Device/browser** · **Test ID** from this plan.
