# Data and provenance

Only generic survey foods are included. There is no branded-food, supplement,
account, intake-log or app-user database in this repository.

The catalog contains the 5,431 foods from the existing app's generic catalog,
reimported from USDA FNDDS **2021–2023**, published October 31, 2024. All 65
nutrient definitions are preserved. The original USDA JSON contains an additional
human-milk record with no nutrient profile; that record is explicitly excluded
and listed in `data/manifest.json`. FDC IDs, eight-digit FNDDS food codes and
internal IDs are separate fields, never interchangeable.

The checked-in asset is `data/generic-fndds-2021-2023-v2.sqlite.gz`. Its SHA-256,
decompressed checksum, byte sizes, source checksums and dataset versions are in
`data/manifest.json`. `diet-assess data install` verifies both checksums before
an atomic installation. Runtime wheels include only a small manifest, not the
database. The local `.sqlite` is ignored by Git to avoid publishing duplicates.

## Food Compass values

Every food has a **precomputed reference value** carried from the original app.
The original labels `published`, `calculated` and `estimated` are retained.
These app labels are not promoted into scientific validation automatically.

Validated lookup is separate: a published Table S5 value is accepted only when
the food code **and full description** match exactly, ignoring case and repeated
whitespace, and matching published rows agree on the score. There is no
name-only, code-only or fuzzy fallback. The current exact crosswalk accepts
3,575 foods. The other 1,856 have `score: null`, `method: unavailable`, while their
stored reference remains inspectable under `precomputed_reference`.

Published scores describe historical foods from the source study; a crosswalk
identifies the food, not proof that its new nutrient profile is unchanged. Each
record includes this warning. No score is recomputed at runtime. The independent
legacy reconstruction has not established exact agreement to published results
and is deliberately not shipped as a validated scoring implementation.

The energy-weighted average is explicitly named
`derived_energy_weighted_published_food_compass_mean`. It includes verified
scores only and reports scored-energy coverage; it is not represented as the
official Food Compass algorithm for a meal or a day. Food-level scores never
scale with grams.

Sources: Barrett et al. *Nature Food* (2024),
https://doi.org/10.1038/s43016-024-01053-3, Supplementary Table S5.
The extracted table was rechecked against the PDF (9,273 rows, 9,251 food codes).
The extraction truncates some wrapped descriptions; the strict crosswalk
abstains for such cases rather than guessing. Source tables live in
`data/source_tables`; they are build inputs and excluded from runtime wheels.

## Release-aligned pattern equivalents

The importer accepts **FPED and FPID 2021–2023 only**. It does not import the
app's FPED 2017–March 2020 crosswalk. The source workbook headers retain units
and exact food-code joins are used. All 5,431 catalog foods match FPED, providing 200,947 reported pattern
values. FPID adds 1,720 ingredients and 63,640 ingredient-pattern values. Both
official workbook checksums are pinned in `data/manifest.json`.

Meal and daily assessment now compute HEI from the matched equivalents and
USDA nutrient totals. Missing values are never represented as zero. A future
partial build remains explicitly marked partial. Known-zero saturated fat uses
the original R NHANES ratio convention of zero; zero total energy abstains.

The superseded partial v1 asset remains unchanged. The complete v2 asset is the
default for package 0.1.1 and later; the installer does not overwrite old caches.

Official sources:

- https://fdc.nal.usda.gov/download-datasets/
- https://www.ars.usda.gov/ARSUserFiles/80400530/apps/FPED_2123.xls
- https://www.ars.usda.gov/ARSUserFiles/80400530/apps/FPID_2123.xls

## Rebuild

Acquire the pinned USDA FNDDS JSON. Run `python scripts/fetch_pattern_sources.py`
to download and verify the two official FPED/FPID workbooks. Checksums of the inputs
used for the current asset are in the manifest. Preserve upstream files unchanged.

```sh
python scripts/build_fooddb.py \
  --fndds /path/to/FNDDS_10_2024.json \
  --fped data_sources/FPED_2123.xls \
  --fpid data_sources/FPID_2123.xls \
  --output /path/to/new/generic-fndds-2021-2023-v2.sqlite
```

Build-time workbook conversion uses R and `readxl`; runtime does not. The builder
refuses to overwrite an existing output. `--allow-missing-patterns` is an
explicit partial-build option and never silently joins another release.
Rebuilding updates the repository and package manifests. To reproduce the
published-table CSV, run `scripts/extract_published_scores.py --pdf ... --output ...`
with the published supplement and Poppler's `pdftotext` installed.

`src/diet_agent/fooddb/schema.sql` is initial schema migration 1
(`PRAGMA user_version=1`). Unknown versions are rejected. Source rows are kept
separate from the auditable curation-override and crosswalk tables; no automatic
overrides are applied.
