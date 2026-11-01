"""Manifest-pinned optional assets kept outside the runtime wheel."""
import gzip
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen


def manifest():
    return json.loads(files('diet_agent').joinpath('asset_manifest.json').read_text())


def _hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def install_asset(source=None,destination=None):
    info=manifest()
    target=Path(destination) if destination else Path.home()/'.cache/diet_agent'/info['file'].removesuffix('.gz')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if _hash(target)==info['uncompressed_sha256']:return str(target)
        raise ValueError('Destination exists with different contents; choose another destination')
    with tempfile.TemporaryDirectory(prefix='diet-data-',dir=target.parent) as temp:
        compressed=Path(temp)/'asset.gz';database=Path(temp)/'database.sqlite'
        if source:
            shutil.copyfile(source,compressed)
        else:
            with urlopen(info['url'],timeout=60) as response,compressed.open('wb') as out:
                shutil.copyfileobj(response,out)
        if _hash(compressed)!=info['sha256']:raise ValueError('Compressed asset checksum mismatch')
        with gzip.open(compressed,'rb') as src,database.open('wb') as out:
            shutil.copyfileobj(src,out)
        if _hash(database)!=info['uncompressed_sha256']:raise ValueError('Database checksum mismatch')
        database.replace(target)
    return str(target)
