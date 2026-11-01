#!/usr/bin/env python3
"""Extract published Food Compass 2.0 scores and NOVA values from Table S5."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path


ROW = re.compile(
    r"^\s*(\d{8})\s+(.*?)\s+(\d{4,5}_[A-Za-z ]+?)\s+"
    r"(\d+)\s+(\d+)\s+([+-]?\d+)\s+([1-4](?:\.\d+)?)\b"
)
EXPECTED_ROWS = 9_273
EXPECTED_UNIQUE_CODES = 9_251
EXPECTED_CONFLICTING_CODES = 18


def extract(pdf_path: Path) -> list[dict[str, str | int | float]]:
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    matches = [match for line in text.splitlines() if (match := ROW.match(line))]
    if len(matches) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} Table S5 rows, extracted {len(matches)}")

    values_by_code: dict[int, set[int]] = {}
    rows: list[dict[str, str | int | float]] = []
    for match in matches:
        food_code = int(match.group(1))
        score = int(match.group(4))
        values_by_code.setdefault(food_code, set()).add(score)
        rows.append(
            {
                "food_code": food_code,
                # A small number of descriptions wrap onto adjacent PDF lines.
                # Food code remains the primary key used by the app.
                "description": " ".join(match.group(2).split()),
                "wweia_category": match.group(3),
                "fcs_2_0": score,
                "fcs_1_0": int(match.group(5)),
                "change": int(match.group(6)),
                "nova_group": float(match.group(7)),
            }
        )
    if len(values_by_code) != EXPECTED_UNIQUE_CODES:
        raise RuntimeError(
            f"Expected {EXPECTED_UNIQUE_CODES} unique codes, extracted {len(values_by_code)}"
        )
    conflicts = {code: values for code, values in values_by_code.items() if len(values) > 1}
    if len(conflicts) != EXPECTED_CONFLICTING_CODES:
        raise RuntimeError(
            f"Expected {EXPECTED_CONFLICTING_CODES} conflicting codes, found {len(conflicts)}"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf", type=Path,
        default=Path(__file__).with_name("Food Compass 2 supplements.pdf"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).with_name("published_food_compass_scores.csv"),
    )
    args = parser.parse_args()
    rows = extract(args.pdf)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "food_code", "description", "wweia_category", "fcs_2_0",
            "fcs_1_0", "change", "nova_group",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} published Food Compass/NOVA rows to {args.output}")


if __name__ == "__main__":
    main()
