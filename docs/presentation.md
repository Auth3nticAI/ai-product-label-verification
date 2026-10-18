> **Presenters: use [demo-guide.md](demo-guide.md)** (exact clicks, what to say, screenshots, fallbacks). The slide deck is shared by Tray.

# Final Presentation (Oct 20)

**Owner:** Tray · Rehearsal: Oct 19

| # | Section | Speaker | Time |
|---|---|---|---|
| 1 | Problem: label errors (wrong net weight, missing allergens) cause recalls; manual checks are slow | Tray | 1 min |
| 2 | Live demo (script below) | Tray + Wenyi | 4 min |
| 3 | Architecture and API contract | Tray | 1.5 min |
| 4 | Verification engine: match / missing / incorrect / uncertain | Amzad | 1.5 min |
| 5 | CI/CD and deployment | Vincent | 1 min |
| 6 | AI-assisted development: what we delegated, what we reviewed, the reusable Skill | All | 2 min |
| 7 | Limits and next steps | Tray | 1 min |

## Demo script (https://ai-product-label-verification.vercel.app)
1. Create spec **Golden Harvest Granola** (values from `data/sample_labels/specs.json`).
2. Upload `granola_correct.png` → **Pass**, all fields green.
3. Upload `granola_wrong_net_weight.png` → **Needs Review**, `net_contents` incorrect (10 oz vs 12 oz).
4. Upload `granola_missing_allergens.png` → **Needs Review**, `allergens` missing.
5. Create spec **VitaCore**, then upload `vitamin_low_quality.jpg`. This is the key moment: the label is *correct*, but the photo is bad. OCR reads the date as `06/312028`, and the app says **uncertain, retake the photo** rather than "wrong expiry date". Explain that confidence scores are what prevent a false rejection.
6. Open **History** → all inspections with timestamps.
6b. **Pricing** (professor requirement): open Pricing → toggle Annual ("2 months free") → Professional → **Start 14-day trial** → Stripe Checkout with card 4242 4242 4242 4242 → "Confirming your subscription…" flips to "You're on Professional" → sidebar badge "Professional · Trial" → **Manage billing** opens Stripe's portal. Talking point: Stripe handles payment, renewals and cancellation; our signed webhook is the single source of plan state; test mode, tax out of scope.
7. Show a green GitHub Actions run and a merged PR.

**Fallback:** if the deployed site is down, run locally (`uvicorn` + `npm run dev`) with the same script. Keep screenshots of each step in `docs/demo/` as a last resort.

## Dry-run checklist
- [ ] Deployed URL loads on a phone
- [ ] All demo images on the presenting laptop
- [ ] Cold start warmed up: open `/api/health`, then upload one label ~2 min before (first OCR call takes ~12 s)
- [ ] Demo specs already created, so typing isn't part of the demo
