"""Run regression tests and record machine-readable scientific validation."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from diet_agent.dietaryindex_py import hei2020,hei2020_from_percent


def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    tested=unittest.TextTestRunner(verbosity=2).run(suite)
    if not tested.wasSuccessful():raise SystemExit('Validation tests failed')
    catalog=sys.modules['test_meal_hei'].FullCatalogHEITests.metrics
    max_error=0;comparisons=0;cases=0
    for fixture,output,fun in [('HEI2020_VALIDATION.csv','HEI2020_VALIDATION_r_output.csv',hei2020_from_percent),
                               ('HEI2020_V2_VALIDATION.csv','HEI2020_V2_VALIDATION_r_output.csv',hei2020),
                               ('hei_random_inputs.csv','hei_random_r_output.csv',hei2020)]:
        with (ROOT/'tests/fixtures'/fixture).open() as f:inputs=list(csv.DictReader(f))
        with (ROOT/'tests/fixtures'/output).open() as f:expected=list(csv.DictReader(f))
        for x,y in zip(inputs,expected):
            result=fun({k:float(v) for k,v in x.items() if not k.startswith('EXP_')})
            for key,value in dict(result['components'],HEI2020_ALL=result['total']).items():
                error=abs(value-float(y[key]));max_error=max(max_error,error);comparisons+=1
                assert error<=1e-10
            cases+=1
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['tests/fixtures','reference/dietaryindex'] for p in sorted((ROOT/folder).iterdir()) if p.is_file()}
    report={'reference_package':'dietaryindex','version':'2.1','commit':'0cb60bd67c2942d954d20637500c4a921a935f51',
            'functions':['HEI2020','HEI2020_V2','HEI2020_NHANES_FPED (known-zero-fat convention)'],
            'r_differential_cases':cases,'component_and_total_comparisons':comparisons,
            'source_to_score_validation':catalog,'total_r_cases':cases+catalog['cases'],
            'total_numeric_comparisons':comparisons+catalog['component_and_total_comparisons'],
            'maximum_absolute_error':max(max_error,catalog['maximum_absolute_error']),
            'test_count':tested.testsRun,'tolerance':1e-10,'result':'pass','frozen_reference_and_fixture_sha256':hashes,
            'domain':'finite nonnegative inputs, age >=1, positive energy; missing inputs abstain; known zero saturated fat uses the R NHANES ratio convention of zero',
            'not_ported':['other dietaryindex scoring methods'],'food_compass':'published exact lookup only; reconstruction is not enabled'}
    (ROOT/'docs/validation_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='frozen_reference_and_fixture_sha256'},indent=2))


if __name__=='__main__':main()
