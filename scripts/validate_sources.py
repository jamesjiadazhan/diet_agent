"""Full differential check of imported source records and published lookups."""
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_fooddb import NAMES,UNITS,checksum,patterns


def validate():
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    db=sqlite3.connect(ROOT/'data'/manifest['file'].removesuffix('.gz'))
    db.row_factory=sqlite3.Row
    source=ROOT.parent/'USDA_food_central_data/FNDDS_10_2024.json'
    foods=json.loads(source.read_text())['SurveyFoods']
    byid={x['fdcId']:x for x in foods}
    nutrient_checks=0;portion_checks=0;pattern_checks=0;ingredient_checks=0
    fped,_=patterns(ROOT/'data_sources/FPED_2123.xls')
    fpid,_=patterns(ROOT/'data_sources/FPID_2123.xls')
    for record in db.execute('SELECT * FROM foods ORDER BY id'):
        food=byid[record['fdc_id']]
        assert food['foodCode']==record['food_code']
        assert food['description']==record['description']
        actual={x['nutrient_id']:x['value'] for x in db.execute('SELECT * FROM nutrient_values WHERE food_id=?',(record['id'],))}
        expected={}
        for item in food['foodNutrients']:
            nutrient=item['nutrient'];number=nutrient['number'];unit=UNITS.get(nutrient['unitName'].upper(),nutrient['unitName'])
            if item.get('amount') is not None:expected[NAMES.get(number,'usda_'+number+'_'+unit)]=item['amount']
        assert actual==expected,record['id'];nutrient_checks+=len(actual)
        portions=db.execute('SELECT source_portion_id,gram_weight FROM portion_measures WHERE food_id=? ORDER BY source_portion_id',(record['id'],)).fetchall()
        assert [tuple(r) for r in portions]==sorted((p['id'],p['gramWeight']) for p in food.get('foodPortions',[]) if p.get('gramWeight',0)>0)
        portion_checks+=len(portions)
        if record['food_code'] in fped:
            expected=fped[record['food_code']]['values']
            actual={r['component']:(r['value'],r['unit']) for r in db.execute('SELECT * FROM pattern_values WHERE food_id=?',(record['id'],))}
            assert expected==actual;pattern_checks+=len(actual)
    for record in db.execute('SELECT * FROM fpid_ingredients'):
        expected=fpid[record['food_code']]
        assert expected['description']==record['description']
        actual={r['component']:(r['value'],r['unit']) for r in db.execute('SELECT * FROM ingredient_pattern_values WHERE food_code=?',(record['food_code'],))}
        assert expected['values']==actual
        ingredient_checks+=len(actual)
    with (ROOT/'data/source_tables/published_food_compass_scores.csv').open() as f:rows=list(csv.DictReader(f))
    published=defaultdict(list)
    for row in rows:published[row['food_code']].append(row)
    accepted=0
    for record in db.execute('SELECT f.*,c.score,c.method,c.precomputed_reference_value FROM foods f JOIN compass_scores c ON c.food_id=f.id'):
        assert 1<=record['precomputed_reference_value']<=100
        candidates=[r for r in published[record['food_code']] if ' '.join(r['description'].casefold().split())==' '.join(record['description'].casefold().split())]
        scores={float(r['fcs_2_0']) for r in candidates}
        if record['method']=='published_exact':
            assert scores=={record['score']};accepted+=1
        else:
            assert record['score'] is None and len(scores)!=1
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert checksum(ROOT/'data'/manifest['file'])==manifest['sha256']
    assert checksum(ROOT/'data'/manifest['file'].removesuffix('.gz'))==manifest['uncompressed_sha256']
    assert manifest['foods']==5431
    result={'catalog_foods':5431,'source_nutrients_exactly_equal':nutrient_checks,
            'source_portions_exactly_equal':portion_checks,'source_pattern_values_exactly_equal':pattern_checks,
            'source_ingredient_pattern_values_exactly_equal':ingredient_checks,
            'published_scores_exactly_verified':accepted,'precomputed_reference_values':5431,
            'integrity':'ok','foreign_keys':'ok','asset_checksums':'ok',
            'pattern_source_status':manifest['status'],'blockers':manifest['blockers']}
    (ROOT/'docs/source_validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':validate()
