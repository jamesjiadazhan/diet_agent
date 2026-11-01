# Implemented versus pending

Implemented and locally checked:

- Installable dependency-free Python package, Python API, CLI and thin local
  stdio MCP adapter with six tools.
- Initial SQLite migration, explicit releases, source identifiers, nutrient
  units/statuses, portions, source crosswalks, auditable override/alias/recipe
  entities and food search.
- Generic catalog of 5,431 FNDDS 2021–2023 foods, every source nutrient and
  portion preserved; optional versioned compressed asset and checksum installer.
- Precomputed Food Compass reference for all foods; 3,575 conservative verified
  historical published-score links. Unvalidated values are inspectable but
  excluded from validated summaries.
- Strict candidate confirmation, preparation checks, edible-weight conversion,
  explicit source measures, ranges, additive aggregation, missingness and
  mass-balance recipes with explicit final yield.
- HEI-2020 adult/toddler serving-input port checked against frozen dietaryindex
  2.1 functions and validation datasets, plus 1,000 differential cases.
- Full nutrient/portion source comparisons, PDF-table extraction check, API/CLI
  and MCP subprocess tests, packaging smoke test and CI test configuration.

Pending source data:

- Official per-100g **FPED and FPID 2021–2023** workbooks. Their importer is
  implemented, but has not been exercised with the absent official workbooks.
  The current partial catalog deliberately has no pattern values. Consequently
  a catalog-driven meal/day assessment abstains from HEI scoring; direct scoring
  with complete serving inputs works and is validated.
- The supplied mirror `jamesjiadazhan/dietaryindex_NHANES`, inspected at commit
  `0c71198f3cfe3753a5ca66d119d099098cee6e8b`, contains combined NHANES `.Rda`
  participant-intake datasets, rather than exposing per-100g FPED/FPID workbooks.
  The connected GitHub reader cannot retrieve its large binary `.Rda` file.
  No per-100g values are fabricated from rounded participant intakes.

Planned, not exposed as implemented:

- Additional dietaryindex scoring methods after separate R differential ports.
- A full independently validated Food Compass 2.0 reconstruction.
- Automatic cooking retention, edible fraction inference, or image recognition.
- Interactive curation workflows beyond the versioned schema/build scripts.

Local environment constraints:

- The requested directory is writable for source and database files. This
  session's policy protects `.git` metadata, so `git init` was denied. Publishing
  uses the authorized GitHub connection, without modifying other repositories.
  For a conventional local checkout, run `git clone` from an ordinary terminal.
- Direct shell network access and elevated network access are unavailable.
  GitHub reads are supplied by the connected GitHub tools. The first attempted
  README creation returned HTTP 403, "Resource not accessible by integration";
  this connection cannot publish. No remote files were changed. Once ordinary
  terminal Git authentication works, `sh scripts/publish.sh` initializes the
  local checkout and performs a normal non-forced push to the requested repo.
