# Demo Readiness

**Owner:** Vincent · Issue [#6](https://github.com/Auth3nticAI/ai-product-label-verification/issues/6) · TEMPLATE: complete by Mon Oct 19 rehearsal

## Verdict

**Go / No-go:** ___ · Assessed by: ___ · Date: ___
One-line reason: ___

## Pre-demo checklist (Tue Oct 20, 30 min before)

- [ ] https://ai-product-label-verification.vercel.app loads on the presenting laptop and on a phone
- [ ] `/api/health` returns `"database": "postgresql"` and the latest `main` commit
- [ ] Warm-up: upload one label ~2 minutes before (the first OCR call after idle takes ~12 s)
- [ ] Demo specs already created (Golden Harvest Granola, VitaCore)
- [ ] Demo images downloaded locally: `granola_correct.png`, `granola_wrong_net_weight.png`, `vitamin_wrong_sku.png`, `vitamin_low_quality.jpg`
- [ ] Latest `main` CI run green, including *MVP completeness*
- [ ] Backup video and screenshots on the laptop (in case of network failure)
- [ ] Pricing demo uses a **fresh browser profile/incognito** (a workspace that already subscribed gets "Use Manage billing" instead of a new checkout)
- [ ] GitHub tabs open: a merged PR, the Actions page, `skills/labelguard-testing`

## Demo run-through (matches the tracker's demo script)

| Step | Action | Expected on screen | Rehearsal result |
|---|---|---|---|
| 1 | Landing page → Get Started | Spec form | |
| 2 | Show or create the Granola spec | Saved spec with SKU, best-by, allergens | |
| 3 | Upload `granola_correct.png` | OCR text + **Pass** | |
| 4 | Upload `vitamin_wrong_sku.png` | **Needs Review**: sku incorrect | |
| 5 | Upload `vitamin_low_quality.jpg` | **Needs Review**: best_by **uncertain**, not incorrect | |
| 6 | Open history | All of the above, with timestamps | |
| 6b | Pricing → Professional → Start trial → 4242 card | Success page confirms; sidebar shows "Professional · Trial"; Manage billing opens the portal | **PASS** Oct 18 (scripted real-browser run on production; see `demo-guide.md` §6) |
| 7 | GitHub: PRs, CI, Skill, AI-usage log | Green checks, merged PRs from every member | |

## Test evidence

Summary from [qa-test-plan.md](qa-test-plan.md): ___ of ___ tests pass. Open bugs: ___ (link each)

## Known limitations (say these out loud if asked)

- OCR can misread blurry photos with high confidence. Example: "Health" read as "Heath" at 0.95, which can flag a correct field as incorrect. The overall result is still Needs Review, so nothing bad gets passed.
- Uploads are limited to 4.5 MB by hosting; the app shrinks photos first.
- No user accounts: anyone with the link can create specs and inspections.
- Synthetic sample labels; ___ real phone photos tested.
- ___

## Fallback plan

| If… | Then… |
|---|---|
| The live site is down | Run locally: `uvicorn` in `backend/`, `npm run dev` in `frontend/`, same script |
| The network is down | Play the backup video |
| OCR is slow on the first call | Talk through the architecture slide while it warms up |
