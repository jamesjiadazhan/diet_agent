"""Download only the official FPED/FPID versions pinned by the data manifest."""
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen
import shutil

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'data/manifest.json').read_text())
destination=ROOT/'data_sources';destination.mkdir(exist_ok=True)
for source in manifest['sources']:
    if source['id'] not in ['fped-2021-2023','fpid-2021-2023']:continue
    target=destination/source['file']
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=source['sha256']:
            raise SystemExit('Existing source differs from pinned release: '+str(target))
        print('Verified existing',target.name);continue
    with tempfile.TemporaryDirectory(dir=destination) as folder:
        temporary=Path(folder)/source['file']
        with urlopen(source['url'],timeout=60) as response,temporary.open('wb') as output:
            shutil.copyfileobj(response,output)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=source['sha256']:
            raise SystemExit('Upstream file changed; checksum mismatch: '+source['file'])
        temporary.replace(target)
    print('Downloaded and verified',target.name)
