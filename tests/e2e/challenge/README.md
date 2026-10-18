# Real product photo challenge set

This set adds **11 unchanged Open Food Facts photos** and **18 human-annotated cases** for VeriLabel QA. Four products contribute clean front controls and difficult original views: tiny ingredients, curved cans and jars, glare, rotated text, blur, low light, a clipped logo, and multilingual panels. Seven cases reuse an unchanged image with a deliberately wrong or absent spec field. No label text was edited to manufacture a mismatch.

## Rights and provenance

The photos come from [Open Food Facts](https://world.openfoodfacts.org/data), which states that product images are available under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/deed.en). Credit: **Open Food Facts contributors**. Each file's source image URL, product page, barcode, SHA256, and byte size is recorded in [sources.json](sources.json). The photos are included unchanged; this directory's photos are licensed separately from any repository code. Open Food Facts cautions that product packaging may contain graphical elements subject to other rights. Use these photos for the course QA task; do not treat them as marketing artwork.

The `image_ingredients_url` for Nutella barcode `3017620422003` returns a low-light **front** photo, not an ingredients panel. Human inspection, not the database view tag, establishes the answer key. The duplicate nutrition URL was excluded.

## Ground truth

[cases.json](cases.json) records the text visibly present or absent in each original image, the spec sent to the API, the expected verdict and field status, difficulty tags, and whether the case is a visible match, a genuine spec mismatch, or an unreadable/absent field. These were set after visual inspection of the downloaded pixels. The expectation is **not** adjusted to the OCR response. In a wrong-spec case, the image is exactly the same bytes as its control. A field that cannot be read should be missing or uncertain, rather than called an actual label error.

## Reproduce

Run `python tests/e2e/challenge/download_off.py` from the repo root to verify or re-download all pinned images. Start the backend on `127.0.0.1:8767` with a **temporary SQLite `DATABASE_URL`**. Then run `python tests/e2e/challenge/run_challenge.py`. The runner refuses non-loopback targets and writes [results.json](results.json). It creates 18 local specs and inspections, checks saved details and filtered History, and records actual OCR text and field evidence. It exits successfully when the HTTP workflow persists even if the model fails the human answer key; the printed summary and JSON expose those failures.

## Measured on Oct 18, 2026

With the hardened local verifier, the 18 real-photo cases yielded **16/18 expected overall verdicts**, **13/18 exact field-status maps**, and **18/18 persisted inspections**. The remaining verdict misses are H01 and N01; B02, C01, and H04 have the expected Needs Review verdict with a different field reason. See `results.json` for every OCR line, found value, confidence, and expected-versus-actual status.

The verifier now handles B04's table order (`g 100` / `100 g`), H01's `0Z` unit read, and H05's exact numeric prefix before a second `Porción` heading. Weak fuzzy reads near the confidence cutoff are classified as uncertain rather than genuine label errors. H01 still marks the correctly printed `HEINZ` uncertain because that OCR line's confidence is only 0.7881; N01 reads stylized `nutella` as `Inutelal` and is also uncertain. Neither is silently converted to a pass. The existing simple manufacturer test pack's eight expected verdicts still pass locally.
