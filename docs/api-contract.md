# API Contract

**Owner:** Tray · **Status:** Draft for team review (Oct 14) · **Implementer:** Amzad · **Consumer:** Wenyi

The frontend and backend build against this file. If you need to change it, open a PR that edits this file first and tag the other side.

Base URL: local `http://localhost:8000` · deployed **`https://ai-product-label-verification.vercel.app/api`** (frontend uses `NEXT_PUBLIC_API_URL=/api`, same origin).
Interactive docs: `/docs` locally · [/api/docs](https://ai-product-label-verification.vercel.app/api/docs) deployed.
**Uploads must be under 4.5 MB on Vercel.** The frontend should resize photos (≤ 1600 px long side) before sending.

## Status values

| Level | Values | Meaning |
|---|---|---|
| Field | `match` | Expected value found on the label |
| | `missing` | Nothing close to the expected value found |
| | `incorrect` | A similar but different value found (e.g. `10 oz` vs `12 oz`, `Peek` vs `Peak`) |
| | `uncertain` | Looks like a match, but OCR confidence is too low to trust |
| Inspection | `pass` | Every field is `match` |
| | `needs_review` | Any field is `missing`, `incorrect` or `uncertain` |

## Endpoints

### `GET /health`
`200 {"status": "ok", "database": "sqlite" | "postgresql"}` · `503` if the database is unreachable

### `POST /ocr` (works now)
OCR only, no comparison. Wenyi can build the upload screen against it before verification is done.
- Request: `multipart/form-data` with `image` (PNG, JPEG, WEBP, BMP or TIFF; max 10 MB)
- `200` → `OcrResult`
- `422` → `{"detail": "File is not a readable image"}`, plus the empty, too-large and unsupported-format errors

### `POST /specs`
Create an approved product specification.
```json
{ "name": "Golden Harvest Granola",
  "fields": { "brand": "Sunrise Farms", "net_contents": "Net Wt 12 oz (340 g)", "allergens": "Contains: Oats, Almonds, Milk" } }
```
`201` → `ProductSpec`. `fields` is free-form: any key → expected text.
`422` if `name` is blank or over 200 characters, `fields` is empty, or any key or value is blank or not a string. Surrounding whitespace is trimmed.

### `GET /specs` · `GET /specs/{id}`
`200` → `ProductSpec[]` (oldest first) / `ProductSpec`; `404` if not found.

### `DELETE /specs/{id}`
Remove a spec that has never been inspected against (for example, a typo or test data).
- `204` deleted · `404` unknown spec · `409` `{"detail": "Spec has N inspection(s) in history; it can't be deleted"}`
- Specs can't be edited: each inspection keeps the expected values it was checked against. To change a spec, create a new one.

### `POST /inspections`
Upload a label and check it against a spec.
- Request: `multipart/form-data` with `spec_id` (int) and `image` (file)
- `201` → `Inspection`
- `404` unknown spec · `422` unreadable image

### `GET /inspections?spec_id=` · `GET /inspections/{id}`
History, newest first. `200` → `Inspection[]` / `Inspection`; `404` if the inspection doesn't exist.
An unknown `spec_id` filter returns `[]`, not `404`.

## Billing (ADR 0003, test mode only)

All billing calls identify the caller by the signed `lg_workspace` cookie (ADR 0004), so the frontend sends requests with `credentials: "include"`. The first call creates the cookie.

| Route | Request | Response |
|---|---|---|
| `GET /plans` | n/a | `200 Plan[]` in order starter, professional, enterprise. Works without Stripe configured |
| `POST /billing/checkout` | `{"plan": "starter\|professional\|enterprise", "interval": "monthly\|annual"}` | `200 {"url"}` (redirect the browser there; the **same** open session is returned again for the same plan, and a different plan expires the old one: one open checkout per workspace, 30 min) · `409` already subscribed ("Use Manage billing…") · `422` bad plan/interval · `502` Stripe price missing · `503` billing not configured |
| `GET /billing/status` | n/a | `200 BillingStatus`. All null before the webhook has recorded a subscription (never 404) |
| `POST /billing/portal` | n/a | `200 {"url"}` (Stripe Customer Portal) · `404` no subscription for this workspace · `503` not configured |
| `POST /billing/webhook` | Stripe only (signed) | `200 {"status": "ok\|duplicate\|ignored"}` · `400` bad signature · `503` no webhook secret or API key (Stripe retries). Events are triggers only: the subscription is re-read from Stripe, so delivery order can't regress state |

```ts
type Plan = { id: "starter" | "professional" | "enterprise"; name: string; monthly_cents: number; annual_cents: number;
  inspections_per_month: number | null; saved_specs: number | null; history_days: number | null; // null = unlimited
  highlight: boolean; trial_days: 14 };
type BillingStatus = { plan: Plan["id"] | null; interval: "monthly" | "annual" | null; status: string | null; // Stripe status
  trial_end: string | null; current_period_end: string | null; payment_failed: boolean };
```

## Schemas

```ts
type ProductSpec = { id: number; name: string; fields: Record<string, string>; created_at: string /* ISO 8601 UTC */ };

type OcrResult = {
  text: string;               // all lines joined with "\n", top to bottom
  lines: { text: string; confidence: number /* 0-1 */; bbox: [left, top, width, height] /* pixels of the uploaded image, EXIF-rotated as browsers display it */ }[];
  mean_confidence: number;    // 0-1
  engine: "rapidocr" | "tesseract";
};

type FieldResult = {
  field: string;              // key from spec.fields
  expected: string;
  found: string | null;       // the OCR line it matched, or null
  status: "match" | "missing" | "incorrect" | "uncertain";
  confidence: number;         // 0-1
};

type Inspection = {
  id: number; spec_id: number; image_filename: string;
  status: "pass" | "needs_review";
  ocr: OcrResult; results: FieldResult[]; created_at: string;
};
```

## Python module boundary (backend-internal)

```python
# app/ocr.py (Tray)
extract_text(image_bytes: bytes) -> OcrResult      # raises OcrError

# app/verification.py (Amzad)
verify_label(ocr: OcrResult, expected: dict[str, str]) -> VerificationResult
```

### Notes for verification (measured Oct 16 on `data/sample_labels/`, rapidocr 3.x)
- Every label has 7 fields: `brand`, `product_name`, `net_contents`, `allergens`, `sku`, `best_by`, `manufacturer`. Spec values include their printed prefix (`"SKU: SF-GRN-12"`, `"Best By: 03/15/2027"`).
- Clean labels: every field read exactly, line confidence **0.97–1.00**.
- `vitamin_low_quality.jpg` is a **correct** label in a bad photo. OCR returns:

  | Line | Read as | Confidence | Must be |
  |---|---|---|---|
  | `Contains: Soy` | `Cons usoy` | 0.64 | `uncertain` |
  | `Best By: 08/31/2028` | `Dest By: 06/312028` | 0.87 | `uncertain`, **not** `incorrect` |
  | `VitaCore Health, Austin, TX` | `VitaCore Heath, Austin, TX` | 0.95 | `incorrect` is an acceptable false alarm |

  So: **check confidence before calling a mismatch `incorrect`**. Below **0.90** → `uncertain`. Otherwise a blurry photo of a good label reports a wrong expiry date.
- **Oct 17, real product labels:** OCR now keeps color and upscales images to ≥ 2000 px on the long side. A grayscale pass erased red-on-yellow text (Kikkoman "15 FL OZ"), and small print was missed at native size. On an 8-case pack of real manufacturer label images it went from 6/8 to **8/8** correct verdicts; the synthetic samples stay 9/9. Cost: about +0.3 s per inspection.
- **Normalize before comparing**: lowercase, strip whitespace and punctuation (OCR drops spaces such as `Contains:Soy`).
- **Oct 18 real-photo hardening:** treat an OCR unit `0Z` after a numeric weight as `OZ`, and a standalone nutrition header `g 100` as `100 g`; the digits themselves remain distinct. Prefer an exact numeric field at the start of a longer explanatory line over a duplicate short heading (`Porción: 12 g (1 cuchara...)` versus `Porción`). A numeric SKU must not match a longer digit sequence (`060` versus `0600`). Weak fuzzy reads (similarity ≤ 0.80 and confidence < 0.95) are `uncertain`, not a claimed physical-label error. The underlying OCR text remains unchanged in evidence.
- `data/sample_labels/manifest.json` is the answer key, and `tests/e2e/` checks every sample against it.
