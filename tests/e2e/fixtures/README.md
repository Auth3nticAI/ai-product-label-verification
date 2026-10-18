# Additional QA label

`granola_two_issues.png` is a fully synthetic, committed PNG made by
`generate_qa_label.py` using the team's public label renderer and Golden Harvest
Granola spec. Its net weight is printed as 10 oz instead of the approved 12 oz,
and its allergen line is absent. The expected result is **Needs Review** with
two independent issues: `net_contents` incorrect and `allergens` missing.

`qa_manifest.json` is the answer key for this added scenario. The PNG is kept
in `tests/e2e/fixtures/`, Vincent's QA area, so the team's original sample pack
and its answer key remain unchanged. The generator requires Pillow from
`backend/requirements.txt`. Tests use the committed image, because installed
fonts can render slightly differently across machines.

The same manifest includes three wholly synthetic invalid upload payloads:
plain text, bytes pretending to be PNG, and an empty PNG. The HTTP tests check
that each is rejected without adding an inspection to history.
