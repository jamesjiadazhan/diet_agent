# Dietary Assessment for AI Agents

**An open-source, scientifically grounded toolkit designed for personal AI agents** to assess what people eat. Agents identify foods and estimate portions from photos or text; this package resolves foods to curated USDA records, calculates nutrients and food-pattern equivalents, and provides validated HEI-2020 scoring and precomputed Food Compass 2.0 lookups. **The AI handles understanding; deterministic software handles the numbers.**

**Meal and daily HEI are now available:** all 5,431 catalog foods have release-matched FPED 2021–2023 equivalents. Supply confirmed foods, edible portions and age; the toolkit sums nutrients and food groups before scoring. The complete catalog and 200 mixed meals were checked against an independent R calculation from the original USDA source files. See [the asset manifest](data/manifest.json) and [validation report](docs/validation_report.json).

## What AI agents can do

- Search 5,431 generic USDA foods, inspect candidates, and confirm food identities.
- Retrieve per-100g nutrients, source-specific portions, provenance and **precomputed Food Compass values for every food**. No user-side Food Compass calculation is required.
- Scale edible portions and aggregate food, meal and daily intakes with explicit missingness and supplied weight ranges.
- Calculate HEI-2020 and HEI-Toddlers-2020 from complete serving/nutrient inputs. Meal/day scoring uses the release-matched food-pattern data. Missing inputs and zero total energy still abstain.
- Resolve explicit ingredient recipes with an explicit final yield; no invented cooking-retention factors.
- Call the Python API, CLI or optional **local stdio MCP** adapter. No maintainer-operated server, account or paid hosted API is required.

The package does not recognize images itself. The calling agent handles recognition, explicit quantities, cooking state and portion uncertainty. Ambiguous descriptions return candidates instead of selecting an arbitrary record.

## Installation and local data

Python **3.10+** with SQLite FTS5 support is required. Runtime dependencies are Python's standard library only. Git/Python execution must be available to the calling agent or its user.

```sh
git clone https://github.com/jamesjiadazhan/diet_agent.git
cd diet_agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .

# Verify and install the checked-in generic database asset locally.
diet-assess data install --file data/generic-fndds-2021-2023-v2.sqlite.gz

# Run a structured meal locally.
diet-assess analyze examples/meal.json
```

Alternatively, install from GitHub and fetch the manifest-pinned asset:

```sh
python -m pip install 'git+https://github.com/jamesjiadazhan/diet_agent.git'
diet-assess data install
```

The wheel contains code and a small manifest, **not the database or large example datasets**. The versioned compressed asset is in `data/`; installation verifies SHA-256 before and after decompression. After installation and asset setup, assessment works offline. Set `DIET_AGENT_DB` or pass `--database` / `database=` to select a different local catalog.

## Python API

```python
from diet_agent import assess_diet
from diet_agent.fooddb import FoodDatabase

with FoodDatabase() as db:
    candidates = db.search_foods("apple raw")
    profile = db.get_food_profile("fndds-2021-2023:63101000")

result = assess_diet(
    [{
        "food_id": profile["id"],
        "portion": {"value": 182, "unit": "g", "min": 170, "max": 190},
        "preparation": "raw",
        "source": "user_text"
    }],
    requested_outputs=["nutrients", "food_patterns", "hei2020", "food_compass"],
    age=30,
)
print(result["status"])
```

Additional implemented functions are `calculate_intake`, `resolve_recipe` and `calculate_dietary_indices` in `diet_agent.assessment`; `hei2020` and `hei2020_from_percent` in `diet_agent.dietaryindex_py`. Their contracts and units are documented in [Validation](docs/VALIDATION.md). Inputs/outputs have [JSON Schemas](schemas/).

## CLI

```sh
diet-assess search 'apple raw' --preparation raw
diet-assess profile 'fndds-2021-2023:63101000'
diet-assess analyze examples/meal.json
diet-assess recipe examples/recipe.json
diet-assess data info
```

`analyze -` and `recipe -` read JSON from stdin. Explicit user quantities are used as supplied. Food-specific `measure_id` values come from `profile`; generic cup-to-gram guessing is not supported. Outputs use `complete`, `partial`, `needs_clarification` or `error`. A result with unresolved foods reports totals for resolved foods only and says that the intake is incomplete.

## Optional local MCP

```sh
diet-assess mcp
```

This starts a stdio adapter, not a network server. Tools: `search_foods`, `get_food_profile`, `resolve_recipe`, `calculate_intake`, `calculate_dietary_indices`, `assess_diet`. The adapter uses the same core as Python and CLI and explicitly supports MCP 2024-11-05, 2025-03-26 and 2025-06-18. A host must support launching local MCP tools and be configured to use the executable. There is **no universal zero-setup promise** for consumer AI applications. See [agent integration](docs/AGENT_USAGE.md).

## Data sources and stored scores

- **FNDDS 2021–2023**, October 2024 release: 5,431 generic foods, 353,015 nutrient values and 22,191 portion measures. IDs, units and source hashes are preserved. Human milk's unavailable nutrient profile is explicitly excluded.
- **FPED/FPID 2021–2023**: all 5,431 foods have 37 food-pattern equivalents (200,947 values), plus 1,720 ingredient profiles (63,640 values). Official source workbook checksums are pinned. Older releases are not joined to the new foods.
- **Food Compass 2.0**, Barrett et al. (2024), Table S5: 3,575 exact food-code-and-description crosswalks with unambiguous published scores. These historical scores are not recalculated for new nutrient profiles.
- **All 5,431 foods have a stored precomputed reference value.** Values inherited from broader app matching or unvalidated reconstruction remain labeled as references. For the 1,856 records without a verified exact mapping, validated `score` is `null` and `method` is `unavailable`. They are excluded from the validated summary.

Food Compass scores never multiply by grams. The energy-weighted summary is separately named **`derived_energy_weighted_published_food_compass_mean`**, with scored-energy coverage. It is not advertised as the official Food Compass score for a meal or a day.

Only the generic-food database is included—**no branded-food or supplement catalogs**. See [data provenance, source URLs, schema and rebuild instructions](docs/DATA.md).

## Validation and limitations

Python HEI totals and all 13 components match the frozen **dietaryindex 2.1** R reference in **6,647 cases / 93,058 numeric comparisons**: 1,044 serving-input cases, all 5,403 positive-calorie catalog foods, and 200 mixed meals, including toddler/adult cases. Maximum error is recorded in [the validation report](docs/validation_report.json), with tolerance `1e-10`.

Every imported nutrient and portion was compared with the USDA JSON; all food and ingredient pattern values were checked against the official workbooks. Published scores were checked against a fresh 9,273-row PDF extraction. Functional tests cover scaling, missingness, recipe yield, ambiguous matching, source identities, checksum installation and CLI/MCP/API agreement. To rerun:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
# Regenerate scientific fixtures with the pinned R package installed:
Rscript scripts/export_r_reference.R
python scripts/fetch_pattern_sources.py
# See docs/VALIDATION.md to regenerate the independent meal fixtures.
PYTHONPATH=src python scripts/validation_report.py
python scripts/validate_sources.py
```

Missing values never become zero. Missing fatty-acid inputs and insufficient source data abstain. Known zero saturated fat follows the original R NHANES convention of a zero fatty-acid ratio. Portions remain estimates when the agent estimates them; provided ranges are not statistical confidence intervals. Nonlinear indices use point estimates rather than fabricated bounds. A single food, meal or day does not establish usual intake. Other dietaryindex methods and a fully validated Food Compass reconstruction are **planned, not implemented**. See [detailed validation and limitations](docs/VALIDATION.md).

## Privacy and local execution

Assessment reads local files and does not upload photos, food logs or personal data. It is stateless by default and does not create a user intake log. Initial GitHub installation/asset download requires internet access; runtime assessment does not. Your AI host's handling of images and conversations is separate. GitHub Actions runs tests only; it is not a live assessment API.

## Attribution, license and citation

The earlier partial v1 asset is preserved; new installations use the complete v2 asset. Reinstall the updated package and asset to upgrade.

Code is MIT licensed. The frozen R reference retains its original license; USDA and Food Compass data retain their source attribution and applicable licenses. See [NOTICE](NOTICE).

Zhan JJ, Hodge RA, Dunlop AL, et al. *Dietaryindex: a user-friendly and versatile R package for standardizing dietary pattern analysis in epidemiological and clinical studies*. Am J Clin Nutr. 2024. [doi:10.1016/j.ajcnut.2024.08.021](https://doi.org/10.1016/j.ajcnut.2024.08.021). [Original R package](https://github.com/jamesjiadazhan/dietaryindex).

Barrett EM, Shi P, Blumberg JB, et al. *Food Compass 2.0 is an improved nutrient profiling system to characterize healthfulness of foods and beverages*. Nature Food 5, 911–915 (2024). [doi:10.1038/s43016-024-01053-3](https://doi.org/10.1038/s43016-024-01053-3).
