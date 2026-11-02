#!/bin/sh
# Run in an ordinary terminal if this session cannot download large binaries.
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"
mkdir -p data_sources
REFERENCE_URL=https://raw.githubusercontent.com/jamesjiadazhan/dietaryindex_NHANES/0c71198f3cfe3753a5ca66d119d099098cee6e8b/data/NHANES_combined/NHANES_20212023.Rda
REFERENCE_FILE=data_sources/NHANES_20212023.Rda
if [ ! -f "$REFERENCE_FILE" ]; then
  curl --fail --location "$REFERENCE_URL" --output "$REFERENCE_FILE.download"
  mv "$REFERENCE_FILE.download" "$REFERENCE_FILE"
fi
python3 - <<'PY'
from pathlib import Path
import hashlib
p=Path('data_sources/NHANES_20212023.Rda')
data=p.read_bytes()
actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
expected='9a6fe144db8d9862347381141256d41746d7f01b'
if actual!=expected:
    raise SystemExit('Reference does not match pinned GitHub blob; refusing inspection')
print('Pinned 2021-2023 reference checksum verified')
PY
Rscript scripts/inspect_nhanes_reference.R "$REFERENCE_FILE" data_sources/NHANES_20212023_inventory.json
