# Demo Readiness

**Owner:** Vincent · Issue [#6](https://github.com/Auth3nticAI/ai-product-label-verification/issues/6) · TEMPLATE: complete by Mon Oct 19 rehearsal

## Verdict

**Go / No-go:** No-go for final sign-off pending production UI and device tests · Assessed by: Vincent via Codex · Date: Oct 18, 2026 UTC
One-line reason: The sample OCR and local API workflow pass, but the complete deployed UI flow, mobile photo uploads, and rehearsal have not been verified in this QA pass. Reassess after the remaining checks; this is an evidence gap, not a confirmed app failure.

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

Summary from [qa-test-plan.md](qa-test-plan.md): 10/10 deployed OCR cases passed on Oct 17. On Oct 18, the hardened branch passed 182/182 backend unit tests and 21/21 local API end-to-end tests with an isolated SQLite database; strict E2E also passed 21/21. All eight cases using seven hash-verified manufacturer images passed the isolated local spec → inspection → history API workflow. A harder set of 18 cases from 11 public product photos had **16/18 expected verdicts, 13/18 exact field-status maps, and 18/18 saved inspections**. The two remaining verdict misses are conservative review flags for low-confidence Heinz and stylized Nutella brand reads; the correct serving-size line and `0Z` unit read are now handled. The deployed API passed 7/7 read-only-mode checks before the newer cases were added; nine production write checks were skipped. The expanded local suite passed 7 with 14 write tests skipped in read-only mode. One additional open QA finding: current OCR drops most of the blurry vitamin manufacturer line, and local F9 has three issues rather than the plan's expected two. No issue has been filed or production inspection run for that finding. The production UI F/S/M/H/E/D/P/B rows remain unscored; do not count the local API results as those UI tests.

## Known limitations (say these out loud if asked)

- OCR can lose text from a blurry photo. On Oct 18, the deployed OCR returned only `TX` for the vitamin sample's manufacturer line; the local verifier marked that field missing, in addition to the two expected uncertain fields. The overall result is still Needs Review, but F9's issue count needs production verification.
- Uploads are limited to 4.5 MB by hosting; the app shrinks photos first.
- No user accounts: anyone with the link can create specs and inspections.
- Synthetic sample labels, seven manufacturer artwork files, and 11 public real product photos tested through the local API. No fresh phone capture or device/browser upload was tested in this pass.
- Production spec creation, Inspect-to-History UI flow, browser/device coverage, and billing remain to be tested before final sign-off.

## Fallback plan

| If… | Then… |
|---|---|
| The live site is down | Run locally: `uvicorn` in `backend/`, `npm run dev` in `frontend/`, same script |
| The network is down | Play the backup video |
| OCR is slow on the first call | Talk through the architecture slide while it warms up |
