PRAGMA foreign_keys=ON;
CREATE TABLE dataset_releases (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, version TEXT NOT NULL,
 source_url TEXT NOT NULL, sha256 TEXT, metadata_json TEXT NOT NULL
);
CREATE TABLE foods (
 id TEXT PRIMARY KEY, release_id TEXT NOT NULL REFERENCES dataset_releases(id),
 food_code TEXT NOT NULL, fdc_id INTEGER NOT NULL UNIQUE,
 description TEXT NOT NULL, category TEXT, preparation TEXT,
 UNIQUE(release_id,food_code)
);
CREATE TABLE nutrient_definitions (
 id TEXT PRIMARY KEY, usda_id INTEGER NOT NULL, nutrient_number TEXT NOT NULL,
 name TEXT NOT NULL, unit TEXT NOT NULL
);
CREATE TABLE nutrient_values (
 food_id TEXT NOT NULL REFERENCES foods(id), nutrient_id TEXT NOT NULL REFERENCES nutrient_definitions(id),
 value REAL, status TEXT NOT NULL, release_id TEXT NOT NULL REFERENCES dataset_releases(id),
 PRIMARY KEY(food_id,nutrient_id)
) WITHOUT ROWID;
CREATE TABLE pattern_values (
 food_id TEXT NOT NULL REFERENCES foods(id), component TEXT NOT NULL,
 value REAL, unit TEXT NOT NULL, status TEXT NOT NULL,
 release_id TEXT NOT NULL REFERENCES dataset_releases(id),
 PRIMARY KEY(food_id,component)
) WITHOUT ROWID;
CREATE TABLE portion_measures (
 id INTEGER PRIMARY KEY, food_id TEXT NOT NULL REFERENCES foods(id),
 description TEXT NOT NULL, gram_weight REAL NOT NULL CHECK(gram_weight>0),
 source_portion_id INTEGER, release_id TEXT NOT NULL REFERENCES dataset_releases(id)
);
CREATE INDEX portion_food ON portion_measures(food_id);
CREATE TABLE food_aliases (alias TEXT NOT NULL,food_id TEXT NOT NULL REFERENCES foods(id), PRIMARY KEY(alias,food_id));
CREATE TABLE food_crosswalks (
 food_id TEXT NOT NULL REFERENCES foods(id),target_release_id TEXT NOT NULL REFERENCES dataset_releases(id),
 target_id TEXT NOT NULL,method TEXT NOT NULL,evidence TEXT NOT NULL,
 PRIMARY KEY(food_id,target_release_id,target_id)
);
CREATE TABLE compass_scores (
 food_id TEXT PRIMARY KEY REFERENCES foods(id),score REAL CHECK(score BETWEEN 1 AND 100),
 method TEXT NOT NULL CHECK(method IN ('published_exact','recomputed_validated','unavailable')),
 release_id TEXT NOT NULL REFERENCES dataset_releases(id),
 precomputed_reference_value REAL NOT NULL CHECK(precomputed_reference_value BETWEEN 1 AND 100),
 precomputed_reference_method TEXT NOT NULL, note TEXT NOT NULL
);
CREATE TABLE curation_overrides (
 id INTEGER PRIMARY KEY,food_id TEXT NOT NULL REFERENCES foods(id),field TEXT NOT NULL,
 original_value TEXT,override_value TEXT,reason TEXT NOT NULL,source TEXT NOT NULL
);
CREATE TABLE recipes (id TEXT PRIMARY KEY,name TEXT NOT NULL,final_edible_grams REAL NOT NULL,provenance TEXT NOT NULL);
CREATE TABLE recipe_ingredients (
 recipe_id TEXT NOT NULL REFERENCES recipes(id),food_id TEXT NOT NULL REFERENCES foods(id),
 edible_grams REAL NOT NULL,PRIMARY KEY(recipe_id,food_id)
);
CREATE TABLE fpid_ingredients (food_code TEXT PRIMARY KEY,description TEXT NOT NULL,release_id TEXT NOT NULL REFERENCES dataset_releases(id));
CREATE TABLE ingredient_pattern_values (
 food_code TEXT NOT NULL REFERENCES fpid_ingredients(food_code),component TEXT NOT NULL,
 value REAL,unit TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(food_code,component)
) WITHOUT ROWID;
CREATE VIRTUAL TABLE foods_fts USING fts5(food_id UNINDEXED,description,category,tokenize='unicode61');
PRAGMA user_version=1;
