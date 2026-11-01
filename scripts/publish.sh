#!/bin/sh
# Run from an ordinary terminal after authenticating Git for GitHub.
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"
REPOSITORY_URL=https://github.com/jamesjiadazhan/diet_agent.git

# Check connectivity/access before initializing local metadata.
git ls-remote "$REPOSITORY_URL" >/dev/null
if [ ! -d .git ]; then
  git init -b main
fi
if git remote get-url origin >/dev/null 2>&1; then
  CURRENT_ORIGIN=$(git remote get-url origin)
  if [ "$CURRENT_ORIGIN" != "$REPOSITORY_URL" ] && [ "$CURRENT_ORIGIN" != 'git@github.com:jamesjiadazhan/diet_agent.git' ]; then
    echo 'Existing origin points elsewhere; refusing to replace it.' >&2
    exit 1
  fi
else
  git remote add origin "$REPOSITORY_URL"
fi
git add -- .gitignore .github CITATION.cff CODEX_IMPLEMENTATION.md LICENSE \
  MANIFEST.in NOTICE README.md pyproject.toml docs examples reference schemas \
  scripts src tests data/manifest.json data/source_tables data/*.sqlite.gz
if ! git diff --cached --quiet; then
  git commit -m 'Add local dietary assessment toolkit with R-validated HEI and generic food data'
fi
# A normal push deliberately preserves any remote work and rejects conflicts.
git push -u origin HEAD:main
