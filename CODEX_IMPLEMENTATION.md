# Codex Implementation Brief — AI-Agent Dietary Assessment

## Objective
Build an **open-source, AI-agent-first dietary assessment toolkit**. A personal AI agent (e.g., Muse, ChatGPT, Claude, or a coding agent) should be able to interpret a food photo or written meal description and then invoke **validated software**, rather than improvise calculations, to estimate per-food, meal, and daily nutrients, USDA food-pattern equivalents, HEI-2020, and Food Compass 2.0. Users should supply their own execution resources; **do not require a server operated on the maintainer's computer or a paid hosted API**.

## Core user experience
1. An AI agent recognizes foods/ingredients from a photo or parses the user's text; identify cooking methods, edible portions, and uncertainty. For text with explicit quantities, use those quantities rather than re-estimating them.
2. Agent sends structured food observations to this toolkit.
3. Toolkit resolves each observation to a **curated, versioned USDA food record**; ambiguous matches return candidates or require confirmation. Never fabricate a food ID or nutrient value.
4. Retrieve nutrients and food-pattern equivalents per 100 g; multiply by edible gram weights; aggregate food, meal, and daily results.
5. Compute HEI-2020 with validated rules and Food Compass 2.0 only when a verified published score or independently validated implementation is available. Return machine-readable results with provenance, missingness, and uncertainty.

## Architecture and distribution
- **Python-first**, installable package, with a small dependency footprint. Preserve the existing `dietaryindex` **R package as a frozen scientific reference**; port scoring functionality incrementally and test Python against R. Do not casually replace R methods or alter their scientific definitions.
- Separate modules: `dietaryindex_py` (validated dietary scoring); `fooddb` (curated USDA/Food Compass records); `assessment` (matching, portion scaling, recipe handling, aggregation); interfaces (Python API, CLI, optional **local stdio MCP** server).
- Do **not** make MCP the only access method. An AI coding agent can use the Python API or CLI; MCP-compatible hosts can launch the local MCP server. No promise that any consumer AI host can automatically run GitHub code or attach MCP without setup.
- Publish code on GitHub; package for simple installation (target `pip`/`uv`), with **versioned downloadable local database assets** and reproducible scripts for building them. Do not bundle large example datasets into runtime wheels. Retain test fixtures in the repository. Offline assessment should work after installation of dependencies and data.
- **No cloud backend, user account, or maintainer-provided compute** required. Do not use GitHub Actions as a live user-serving API.

## Authoritative data and scientific rules
- Start with **FNDDS 2021–2023**, matching **FPED/FPID 2021–2023**. Include source release, FNDDS food code, FDC ID where available, units, provenance, and data status. Do not equate FDC IDs with FNDDS food codes or join mismatched releases.
- USDA nutrition sources are not automatically a single complete table of nutrient values, food-pattern equivalents, and Food Compass scores. Keep explicit curated crosswalks and source provenance.
- Food Compass 2.0: begin with verified published food-level scores and exact defensible crosswalks. Any computed score requires independent validation to the published algorithm. Never impute an official score merely because food names look similar.
- HEI-2020: sum nutrients/food-group equivalents first; **then** calculate its 13 component scores and total using the existing validated `dietaryindex` implementation as reference and NCI definitions. Do not average food-level HEI scores. A food/meal/day score is not a measure of usual diet.
- Additive values (nutrients, FPED components) scale as `grams / 100 * value_per_100g`. **HEI and Food Compass scores do not scale or add in that way.** An energy-weighted mean Food Compass can be reported only as a separately named *derived* metric with scored-energy coverage.
- Missing != zero. Preserve measured/calculated/label/estimated/missing statuses. Distinguish raw/cooked, edible/as-purchased, recipes, cooking yields, and nutrient retention. Estimate a range where portions are uncertain; do not create false precision.

## Local data schema (SQLite + FTS5 is a reasonable default)
Required versioned entities: `dataset_releases`, `foods` (internal ID and source IDs), `nutrient_definitions`, `nutrient_values` (per 100 g and units), `pattern_values` (FPED equivalents), `portion_measures`, `food_aliases`, `food_crosswalks`, `recipes`, `recipe_ingredients`, `compass_scores`, and `curation_overrides`. Optional local intake log; default should be stateless. Include migrations, checksums, and searchable food names; keep source records unchanged and overrides auditable.

## Public interfaces
Implement a simple high-level `assess_diet(foods, requested_outputs=...)` Python API and `diet-assess analyze input.json` CLI, with stable JSON schemas. Add optional local MCP tools: `search_foods`, `get_food_profile`, `resolve_recipe`, `calculate_intake`, `calculate_dietary_indices`, and `assess_diet`. MCP should be a thin wrapper over the same core. Input food observations include description or confirmed food ID, portion value/unit/range, preparation state, and source (`photo_estimate`, `user_text`, `label`, etc.). Output includes source IDs and versions, per-food/total nutrients, food-pattern equivalents, HEI components and total, Food Compass score + method, ambiguity candidates, missing fields, warnings, and computation status (`complete`, `partial`, `needs_clarification`, `error`). Never return an unsupported number as if measured.

## Implementation sequence
1. **Inspect the repository and existing R package first.** Inventory scoring methods, existing tests, dependencies, and useful code. Avoid destructive refactoring.
2. Define canonical nutrient/food-pattern identifiers, JSON schemas, provenance/status conventions, and package layout; add a minimal README immediately.
3. Build reproducible importers and SQLite database for pinned FNDDS + FPED/FPID data, including exact joins, units, and validation.
4. Implement strict candidate food search, alias resolution, preparation-aware matching, portion scaling, recipe handling, missing-data policies, and aggregation. Start with a small golden dataset before scaling to the full catalog.
5. Port **HEI-2020 first** to Python, using golden differential tests against the R package; preserve the architecture to port other dietary indices later.
6. Import and conservatively map Food Compass 2.0 published scores; independently validate any scoring reconstruction before enabling it.
7. Implement and test Python API, CLI, then local stdio MCP adapter; write agent-integration instructions and examples.
8. Run unit, integration, scientific regression, and representative end-to-end tests; document limitations and release as an installable open-source package.

## Acceptance criteria
- Same structured input + same data and algorithm versions => reproducible output.
- Exact USDA nutrient/FPED records reproduce source values; missing or ambiguous records explicitly abstain rather than guess.
- HEI-2020 **total and components** match the R reference for identical inputs within defined numerical tolerance, including edge cases.
- Food Compass results clearly distinguish `published_exact`, `recomputed_validated`, and `unavailable`.
- One command can run a sample structured meal through Python CLI locally; same core can be called via local MCP with no hosted services.
- Lightweight install without runtime example datasets, but preserved scientific test fixtures and manifest-driven optional food database download.
- README prominently identifies the **primary audience as AI agents and their users**, explains that the agent handles recognition while the package handles validated calculation, gives practical agent/CLI/MCP usage, discloses installation/execution prerequisites, and does not claim universal zero-setup agent compatibility.

## README.md — required opening and structure
Start the README with wording equivalent to:

> # Dietary Assessment for AI Agents
> **An open-source, scientifically grounded toolkit designed for personal AI agents** to assess what people eat. Agents identify foods and estimate portions from photos or text; this package resolves foods to curated USDA records, calculates nutrients and food-pattern equivalents, and runs validated HEI-2020 and Food Compass 2.0 assessments. **The AI handles understanding; deterministic software handles the numbers.**

Then cover: (1) What AI agents can do with it; (2) Installation and local data setup; (3) Python, CLI, and MCP examples using actual implemented commands; (4) Data sources and versions; (5) Validation and limitations; (6) Privacy/local execution; (7) Attribution, license, and citation to the original `dietaryindex` R package. Clearly mark planned/unimplemented functionality instead of presenting it as available.

## Codex working rules
Make changes incrementally, run tests after each major step, and report what is implemented versus planned. Use placeholders only in documentation/examples, never as fake scientific results. Do not invent USDA IDs, published Food Compass scores, tested performance, or client integrations. If source data, full R code, or official algorithm details are unavailable, create documented interfaces and list concrete blockers rather than approximating scientific calculations.
