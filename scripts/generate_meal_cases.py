"""Deterministic catalog-wide and mixed-meal inputs for independent R tests."""
import json
from pathlib import Path
import random
import sqlite3
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'data/manifest.json').read_text())
db=sqlite3.connect(ROOT/'data'/manifest['file'].removesuffix('.gz'))
rows=db.execute("SELECT f.id,f.fdc_id FROM foods f JOIN nutrient_values n ON n.food_id=f.id AND n.nutrient_id='energy_kcal' WHERE n.value>0 ORDER BY f.id").fetchall()
cases=[]
for i,(food_id,fdc_id) in enumerate(rows):
    cases.append({'id':'food-'+str(fdc_id),'age':1.5 if i%2 else 30,
                  'foods':[{'food_id':food_id,'fdc_id':fdc_id,'portion':{'value':100,'unit':'g'},'source':'user_confirmed'}]})
rng=random.Random(20261101)
for i in range(200):
    foods=[{'food_id':food_id,'fdc_id':fdc_id,'portion':{'value':round(rng.uniform(10,300),2),'unit':'g'},'source':'user_confirmed'}
           for food_id,fdc_id in rng.sample(rows,rng.randint(2,8))]
    cases.append({'id':'meal-'+str(i),'age':rng.choice([1,1.5,2,18,65]),'foods':foods})
(ROOT/'tests/fixtures/catalog_meal_inputs.json').write_text(json.dumps(cases,separators=(',',':'))+'\n')
print(f'Generated {len(rows)} individual-food and 200 mixed-meal cases')
