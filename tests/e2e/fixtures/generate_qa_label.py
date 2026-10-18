"""Regenerate the two-error QA label from the team's public synthetic spec.

Run from the repository root with backend requirements installed:
    python tests/e2e/fixtures/generate_qa_label.py

The committed PNG is used in tests; CI does not regenerate it because installed
fonts can differ between machines. No real product or user photo is involved.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "sample_labels"))

from generate_samples import SPECS, render  # noqa: E402 - import the team's label renderer


def main() -> None:
    fields = dict(SPECS["granola"]["fields"])
    fields["net_contents"] = "Net Wt 10 oz (283 g)"
    fields["allergens"] = None
    render(fields).save(Path(__file__).with_name("granola_two_issues.png"))


if __name__ == "__main__":
    main()
