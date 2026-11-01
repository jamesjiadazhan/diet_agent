import csv
import math
from pathlib import Path
import unittest
from diet_agent.dietaryindex_py import hei2020, hei2020_from_percent

FIXTURES=Path(__file__).parent/'fixtures'


class HEIReferenceTests(unittest.TestCase):
    def compare(self, inputs_name, outputs_name, percent=False, expected_fixture=False):
        with (FIXTURES/inputs_name).open() as stream:
            inputs=list(csv.DictReader(stream))
        with (FIXTURES/outputs_name).open() as stream:
            outputs=list(csv.DictReader(stream))
        self.assertEqual(len(inputs),len(outputs))
        for row,reference in zip(inputs,outputs):
            values={k:float(v) for k,v in row.items() if not k.startswith('EXP_')}
            result=(hei2020_from_percent if percent else hei2020)(values)
            actual=dict(result['components'],HEI2020_ALL=result['total'])
            for key,value in actual.items():
                self.assertAlmostEqual(value,float(reference[key]),delta=1e-10,msg=f'{inputs_name} {row["id"]} {key}')
                if expected_fixture:
                    self.assertAlmostEqual(value,float(row['EXP_'+key]),delta=1e-10)

    def test_original_package_validation(self):
        self.compare('HEI2020_VALIDATION.csv','HEI2020_VALIDATION_r_output.csv',percent=True,expected_fixture=True)

    def test_v2_package_validation(self):
        self.compare('HEI2020_V2_VALIDATION.csv','HEI2020_V2_VALIDATION_r_output.csv',expected_fixture=True)

    def test_1000_seeded_differential_cases(self):
        self.compare('hei_random_inputs.csv','hei_random_r_output.csv')

    def test_missing_is_not_zero(self):
        r=hei2020({'age':30,'kcal':2000})
        self.assertIsNone(r['total']);self.assertIn('sodium',r['missing'])

    def test_invalid_energy_age_and_nonfinite_inputs(self):
        for value in [0,-1,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):hei2020({'age':30,'kcal':value})
            with self.assertRaises(ValueError):hei2020_from_percent({'age':30,'kcal':value})
        with self.assertRaises(ValueError):hei2020({'age':0.5,'kcal':1000})


if __name__=='__main__':unittest.main()
