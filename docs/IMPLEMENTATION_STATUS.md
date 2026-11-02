# Implementation status

Implemented and locally validated in package 0.1.1 / data v2:

- Dependency-free Python package, Python API, CLI and local stdio MCP adapter.
- Generic FNDDS 2021–2023 catalog: 5,431 foods, 353,015 nutrients and 22,191
  source portion measures. Branded and supplement databases are excluded.
- Official FPED 2021–2023 equivalents for **all 5,431 foods**: 200,947 values.
- Official FPID 2021–2023 profiles: 1,720 ingredients and 63,640 values.
- Full source-value comparisons, pinned input hashes, versioned compressed
  database, checksum installer and initial SQLite migration.
- Stored Food Compass reference values for every food; 3,575 conservative
  verified historical published-score links. Other reference values remain
  explicitly unvalidated and excluded from the derived summary.
- Candidate confirmation, preparation checks, edible weights, source measures,
  portion ranges, missingness propagation and explicit-yield recipes.
- Meal and daily HEI from aggregated nutrients and matched food groups, using
  the original R toddler/adult standards and known-zero-fat convention.
- Frozen dietaryindex 2.1 reference, 1,044 serving-input comparisons, and
  independent source-to-score R tests covering all 5,403 positive-calorie foods
  and 200 mixed meals. Total: 6,647 cases / 93,058 numeric comparisons.
- CLI/API/MCP agreement, subprocess tests, package smoke tests and CI workflow.

The supplied `dietaryindex_NHANES` repository was inspected at commit
`0c71198f3cfe3753a5ca66d119d099098cee6e8b`. Its pinned 2021–2023 bundle was
retrieved and checksum-verified. The bundle exposes demographic and nutrient
intake tables but no FPED tables. The import therefore uses the official USDA
FPED/FPID 2021–2023 workbooks, which were successfully downloaded and verified.
No participant-intake records are included in the runtime database or Git files.

The earlier partial v1 asset is preserved unchanged. Current package defaults,
manifest, examples and CI select the complete v2 asset.

Remaining limitations:

- Ambiguous identities, unknown foods, missing portions or age, infants under
  one year, and zero-energy meals require clarification or abstention.
- Additional dietaryindex methods await separate differential ports.
- A fully validated reconstruction of Food Compass is not enabled.
- Image recognition, inferred edible fractions and cooking retention remain
  responsibilities of the calling agent and its sources.
- Alias/override/recipe entities exist, but an interactive curation UI is not
  part of this implementation.

Publishing is separate from validation. The earlier GitHub connection rejected
writes with HTTP 403 and shell Git authentication/network access was unavailable.
`sh scripts/publish.sh` performs a normal non-forced push from an authenticated
ordinary terminal. The local project does not claim that unpublished updates
are already available to remote installations.
