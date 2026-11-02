import csv
import json
from pathlib import Path
import unittest
from diet_agent import assess_diet
from diet_agent.data_assets import manifest
from diet_agent.fooddb import FoodDatabase
from diet_agent.assessment import calculate_dietary_indices

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/manifest()['file'].removesuffix('.gz')


class FullCatalogHEITests(unittest.TestCase):
    def test_every_catalog_food_has_complete_patterns(self):
        with FoodDatabase(DB) as db:
            self.assertEqual(db.db.execute('SELECT count(DISTINCT food_id) FROM pattern_values').fetchone()[0],5431)
            self.assertEqual(db.db.execute('SELECT count(*) FROM pattern_values WHERE value IS NULL').fetchone()[0],0)
            self.assertEqual(db.db.execute('SELECT count(*) FROM fpid_ingredients').fetchone()[0],1720)

    def test_catalog_foods_and_mixed_meals_against_independent_r_sources(self):
        cases=json.loads((ROOT/'tests/fixtures/catalog_meal_inputs.json').read_text())
        with (ROOT/'tests/fixtures/catalog_meal_r_output.csv').open() as stream:
            expected={r['RESPONDENTID']:r for r in csv.DictReader(stream)}
        maximum=0;comparisons=0
        for case in cases:
            # FDC IDs are carried in the scientific fixture only; the public
            # observation contract uses the confirmed internal catalog ID.
            foods=[{k:v for k,v in item.items() if k!='fdc_id'} for item in case['foods']]
            result=assess_diet(foods,requested_outputs=['hei2020'],database=DB,age=case['age'])
            self.assertEqual(result['status'],'complete',case['id'])
            hei=result['indices']['hei2020'];reference=expected[case['id']]
            for key,value in dict(hei['components'],HEI2020_ALL=hei['total']).items():
                error=abs(value-float(reference[key]));maximum=max(maximum,error);comparisons+=1
                self.assertLessEqual(error,1e-10,(case['id'],key))
        self.assertEqual(len(cases),len(expected))
        self.__class__.metrics={'cases':len(cases),'component_and_total_comparisons':comparisons,
                                'maximum_absolute_error':maximum,
                                'individual_food_cases':sum(case['id'].startswith('food-') for case in cases),
                                'mixed_meal_cases':sum(case['id'].startswith('meal-') for case in cases)}

    def test_known_zero_fat_rule_and_zero_energy_abstention(self):
        nutrients={key:{'value':value,'unit':unit} for key,value,unit in [
            ('energy_kcal',100,'kcal'),('saturated_fat_g',0,'g'),('mufa_g',0,'g'),('pufa_g',0,'g'),('sodium_mg',0,'mg')]}
        patterns={key:{'value':0,'unit':'tsp eq' if key=='add_sugars' else 'oz eq' if key.startswith(('pf_','g_')) else 'cup eq'} for key in [
            'f_total','f_citmlb','f_other','v_total','v_legumes','v_drkgr','pf_mps_total','pf_eggs','pf_nutsds','pf_soy','pf_legumes','pf_seafd_hi','pf_seafd_low','g_whole','d_total','g_refined','add_sugars']}
        result=calculate_dietary_indices(nutrients,patterns,30)
        self.assertEqual(result['status'],'complete');self.assertEqual(result['components']['HEI2020_FATTYACID'],0)
        nutrients['energy_kcal']['value']=0
        self.assertIsNone(calculate_dietary_indices(nutrients,patterns,30)['total'])


if __name__=='__main__':unittest.main()
