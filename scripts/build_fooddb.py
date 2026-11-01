"""Reproducible generic-only import with release-aligned FPED and audited scores."""
import argparse
from collections import defaultdict, Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

NAMES={'208':'energy_kcal','203':'protein_g','204':'fat_g','205':'carbohydrate_g',
       '255':'water_g','269':'sugars_g','291':'fiber_g','307':'sodium_mg',
       '606':'saturated_fat_g','645':'mufa_g','646':'pufa_g','301':'calcium_mg',
       '306':'potassium_mg','221':'alcohol_g'}
UNITS={'G':'g','MG':'mg','UG':'ug','KCAL':'kcal','KJ':'kJ','IU':'IU'}


def checksum(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def patterns(path):
    if not path.exists():return {},{}
    if not re.search(r'2123|2021\D+2023',path.name):
        raise ValueError('Pattern source filename must identify the pinned 2021-2023 release')
    csv_path=path.with_suffix('.csv') if path.suffix.lower()!='.csv' else path
    if path.suffix.lower()!='.csv':
        subprocess.run(['Rscript',str(ROOT/'scripts/extract_patterns.R'),str(path),str(csv_path)],check=True)
    with csv_path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if not rows:raise ValueError('Empty pattern source')
    codekey=next((k for k in rows[0] if re.sub('[^A-Z]','',k.upper()) in ('FOODCODE','INGREDIENTCODE')),None)
    if not codekey:raise ValueError('Pattern source lacks FOODCODE')
    header={}
    for key in rows[0]:
        match=re.match(r'^([A-Z][A-Z0-9_]*)\s*\(([^)]+)\)',key)
        if match:header[key]=(match[1].lower(),match[2].strip())
    if len(header)<30:raise ValueError('Expected at least 30 explicit, unit-bearing FPED/FPID columns')
    desc=next((k for k in rows[0] if 'DESCRIPTION' in k.upper() or k.upper()=='FOODNAME'),None)
    result={}
    for row in rows:
        code=str(int(float(row[codekey])))
        if code in result:raise ValueError('Duplicate pattern code '+code)
        result[code]={'description':row.get(desc,'') if desc else '',
                      'values':{component:(float(row[key]) if row[key] else None,unit)
                                for key,(component,unit) in header.items()}}
    return result,header


def build(args):
    if args.output.exists():raise ValueError('Refusing to overwrite existing database')
    fped,_=patterns(args.fped);fpid,_=patterns(args.fpid)
    if not fped and not args.allow_missing_patterns:
        raise ValueError('FPED 2021-2023 is required. Download it or explicitly build a partial catalog with --allow-missing-patterns')
    if not fpid and not args.allow_missing_patterns:
        raise ValueError('FPID 2021-2023 is required')
    foods=json.loads(args.fndds.read_text())['SurveyFoods']
    with args.precomputed.open() as stream:precomputed={r['fdc_id']:r for r in csv.DictReader(stream)}
    with args.published.open() as stream:published=list(csv.DictReader(stream))
    bycode=defaultdict(list)
    for row in published:bycode[row['food_code']].append(row)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(args.output)
    db.executescript((ROOT/'src/diet_agent/fooddb/schema.sql').read_text())
    sources=[('fndds-2021-2023','fndds','2021-2023 (October 2024)',args.fndds,'https://fdc.nal.usda.gov/download-datasets/'),
             ('compass-2024-s5','food_compass','Barrett et al. 2024 Table S5',args.published,'https://doi.org/10.1038/s43016-024-01053-3'),
             ('legacy-app-compass','legacy_precomputed','app snapshot',args.precomputed,'https://github.com/jamesjiadazhan/diet_agent')]
    for key,path,url,kind in [('fped-2021-2023',args.fped,'https://www.ars.usda.gov/ARSUserFiles/80400530/apps/FPED_2123.xls','fped'),('fpid-2021-2023',args.fpid,'https://www.ars.usda.gov/ARSUserFiles/80400530/apps/FPID_2123.xls','fpid')]:
        if path.exists():sources.append((key,kind,'2021-2023',path,url))
    source_manifest=[]
    for key,kind,version,path,url in sources:
        sha=checksum(path)
        db.execute('INSERT INTO dataset_releases VALUES (?,?,?,?,?,?)',(key,kind,version,url,sha,json.dumps({'file':path.name},sort_keys=True)))
        source_manifest.append({'id':key,'sha256':sha,'url':url,'file':path.name})
    excluded=[];methods=Counter();pattern_count=0
    for food in foods:
        fdc=str(food['fdcId']);code=str(food['foodCode'])
        if fdc not in precomputed:
            excluded.append({'fdc_id':int(fdc),'food_code':code,'description':food['description'],'reason':'not in original generic catalog; no precomputed score'})
            continue
        if not(food['startDate'].endswith('2021') and food['endDate'].endswith('2023')):
            raise ValueError('Mismatched FNDDS release')
        internal='fndds-2021-2023:'+code
        description=food['description'];lower=description.casefold()
        prep=next((term for term in ['raw','fried','boiled','steamed','roasted','baked','cooked'] if re.search(r'\b'+term+r'\b',lower)),None)
        category=food.get('wweiaFoodCategory',{}).get('wweiaFoodCategoryDescription')
        db.execute('INSERT INTO foods VALUES (?,?,?,?,?,?,?)',(internal,'fndds-2021-2023',code,int(fdc),description,category,prep))
        for item in food['foodNutrients']:
            nutrient=item['nutrient'];number=nutrient['number'];unit=UNITS.get(nutrient['unitName'].upper(),nutrient['unitName'])
            key=NAMES.get(number,'usda_'+number+'_'+unit)
            db.execute('INSERT OR IGNORE INTO nutrient_definitions VALUES (?,?,?,?,?)',(key,nutrient['id'],number,nutrient['name'],unit))
            if item.get('amount') is not None:
                db.execute('INSERT INTO nutrient_values VALUES (?,?,?,?,?)',(internal,key,item['amount'],'reported','fndds-2021-2023'))
        for portion in food.get('foodPortions',[]):
            if portion.get('gramWeight',0)>0:
                db.execute('INSERT INTO portion_measures(food_id,description,gram_weight,source_portion_id,release_id) VALUES (?,?,?,?,?)',
                           (internal,portion.get('portionDescription') or portion.get('modifier') or 'source measure',portion['gramWeight'],portion.get('id'),'fndds-2021-2023'))
        if code in fped:
            pattern_count+=1
            for key,(value,unit) in fped[code]['values'].items():
                db.execute('INSERT INTO pattern_values VALUES (?,?,?,?,?,?)',(internal,key,value,unit,'missing' if value is None else 'reported','fped-2021-2023'))
        # No description-only, nearest-name, or food-code-only fallback.
        matches=[r for r in bycode[code] if ' '.join(r['description'].casefold().split())==' '.join(lower.split())]
        scores={float(r['fcs_2_0']) for r in matches}
        legacy=precomputed[fdc];candidate=float(legacy['fcs_2_score'])
        if len(scores)==1:
            score=next(iter(scores));method='published_exact';release='compass-2024-s5'
            note='Historical published score linked by exact food code and description; not recomputed for current nutrients.'
            db.execute('INSERT INTO food_crosswalks VALUES (?,?,?,?,?)',(internal,release,code,'exact_food_code_and_description',note))
        else:
            score=None;method='unavailable';release='legacy-app-compass'
            note='Only an unvalidated precomputed app reference is available. Excluded from validated scoring.'
        methods[method]+=1
        db.execute('INSERT INTO compass_scores VALUES (?,?,?,?,?,?,?)',(internal,score,method,release,candidate,legacy['fcs_2_source'],note))
        db.execute('INSERT INTO foods_fts VALUES (?,?,?)',(internal,description,category))
    for code,row in fpid.items():
        db.execute('INSERT INTO fpid_ingredients VALUES (?,?,?)',(code,row['description'],'fpid-2021-2023'))
        for key,(value,unit) in row['values'].items():
            db.execute('INSERT INTO ingredient_pattern_values VALUES (?,?,?,?,?)',(code,key,value,unit,'missing' if value is None else 'reported'))
    db.execute("INSERT INTO foods_fts(foods_fts) VALUES('optimize')")
    db.commit();db.execute('VACUUM')
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    count=db.execute('SELECT count(*) FROM foods').fetchone()[0]
    assert count==len(precomputed)
    db.close()
    compressed=args.output.with_suffix('.sqlite.gz')
    with args.output.open('rb') as source,compressed.open('wb') as output:
        with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0) as z:
            for block in iter(lambda:source.read(1024*1024),b''):z.write(block)
    manifest={'schema_version':1,'dataset_version':'generic-fndds-2021-2023-v1','file':compressed.name,
              'url':'https://raw.githubusercontent.com/jamesjiadazhan/diet_agent/main/data/'+compressed.name,
              'sha256':checksum(compressed),'uncompressed_sha256':checksum(args.output),
              'bytes':compressed.stat().st_size,'uncompressed_bytes':args.output.stat().st_size,
              'foods':count,'fped_matched_foods':pattern_count,'fpid_ingredients':len(fpid),
              'compass_methods':dict(methods),'precomputed_reference_coverage':count,
              'excluded_source_records':excluded,'sources':source_manifest,
              'status':'complete' if fped and fpid else 'partial',
              'blockers':[] if fped and fpid else ['Matching FPED/FPID 2021-2023 source files unavailable; HEI from catalog intakes abstains']}
    for path in [ROOT/'data/manifest.json',ROOT/'src/diet_agent/asset_manifest.json']:
        path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='sources'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fndds',type=Path,default=ROOT.parent/'USDA_food_central_data/FNDDS_10_2024.json')
    p.add_argument('--fped',type=Path,default=ROOT/'data_sources/FPED_2123.xls')
    p.add_argument('--fpid',type=Path,default=ROOT/'data_sources/FPID_2123.xls')
    p.add_argument('--precomputed',type=Path,default=ROOT/'data/source_tables/legacy_precomputed_scores.csv')
    p.add_argument('--published',type=Path,default=ROOT/'data/source_tables/published_food_compass_scores.csv')
    p.add_argument('--output',type=Path,default=ROOT/'data/generic-fndds-2021-2023-v1.sqlite')
    p.add_argument('--allow-missing-patterns',action='store_true')
    build(p.parse_args())
