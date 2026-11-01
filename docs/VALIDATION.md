# Scientific validation and limits

The scientific reference is **dietaryindex 2.1**, Git commit
`0cb60bd67c2942d954d20637500c4a921a935f51`. The installed R function bodies,
package metadata, citation and original MIT license are frozen under
`reference/dietaryindex/`. The external R installation is not modified.

Two Python entry points are ported:

- `hei2020_from_percent`: R `HEI2020`. Sodium is in grams; added sugar and
  saturated fat are percent energy; fatty acids are an input ratio.
- `hei2020`: R `HEI2020_V2`. Sodium is mg, added sugar teaspoon equivalents and
  saturated fat grams. The frozen R method uses **16 kcal per teaspoon-equivalent
  of added sugar**. This conversion is preserved, not silently changed to 4.2g.

Both use cup/ounce equivalents for food groups, nonnegative finite inputs,
positive energy and age >=1. Toddler standards apply from 1 to under 2 years.
Neither function estimates usual intake. Zero energy, infants, negative or
nonfinite values are explicitly rejected. Missing values return an unavailable
score with missing fields; no zero imputation is performed. Undefined fatty-acid
ratios abstain instead of being assigned an arbitrary value.

The test suite compares all 13 components and total against:

- `HEI2020_VALIDATION`: 22 rows, including adult and toddler boundaries.
- `HEI2020_V2_VALIDATION`: 22 rows, including adult and toddler boundaries.
- 1,000 seeded R differential cases spanning age, energy and component ranges.

This is **1,044 cases and 14,616 numeric comparisons**, with a tolerance of
`1e-10`. Actual maximum error and frozen file hashes are recorded in
`docs/validation_report.json`. Dataset expected values are also checked.

```sh
Rscript scripts/export_r_reference.R
PYTHONPATH=src python scripts/validation_report.py
python scripts/validate_sources.py
```

The R exporter refuses an unpinned installed version. R and `dietaryindex` are
needed only to regenerate differential fixtures, not for running Python or
ordinary tests. Source comparison validates all 353,015 nutrient values and
22,191 portion weights, and all imported FPED values when available. Published
Food Compass lookups are checked against Table S5; this validates lookup and
crosswalk fidelity, not reconstruction of the authors' scoring model.

Functional tests exercise food IDs, explicit confirmation, preparation
mismatches, edible-weight scaling, catalog measures, uncertainty ranges,
missingness propagation, recipe yield, weighted-score coverage, asset checksums,
CLI/API equality and an actual stdio MCP subprocess. CI reruns Python fixtures
on supported interpreters; GitHub Actions is not a user-serving API.

## Interpretation and unsupported functions

Other dietaryindex methods (DII, DASH, Mediterranean and others) are **not
ported or advertised as available**. R is the frozen reference for later ports.
Complete food-pattern and high-level HEI assessment require matching FPED/FPID
sources; inspect the manifest for the current build's concrete blockers.

Photographic recognition accuracy and portion inference are outside this
package. Ranges supplied by an agent or user are not statistical confidence
intervals. Additive nutrient ranges are propagated; nonlinear dietary indices
are calculated at the point estimate, not presented with fabricated confidence
intervals. Cooking retention and edible fractions are not guessed. Recipe
mass balance requires an explicit final edible yield and assumes no nutrient
loss; use already-cooked food records when appropriate.

The NCI scoring standards used for the independent threshold check are:
https://epi.grants.cancer.gov/hei/hei-2020-table1.html
