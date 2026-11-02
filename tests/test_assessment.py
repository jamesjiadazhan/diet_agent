from contextlib import redirect_stderr,redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from diet_agent import assess_diet
from diet_agent.assessment import calculate_intake,calculate_dietary_indices,resolve_recipe,_aggregate
from diet_agent.cli import main
from diet_agent.data_assets import install_asset,manifest
from diet_agent.fooddb import FoodDatabase
from diet_agent.mcp_server import call_tool,serve,tool_definitions

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/manifest()['file'].removesuffix('.gz')


class AssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=FoodDatabase(DB)
        cls.apple=cls.db.db.execute("SELECT id FROM foods WHERE food_code='63101000'").fetchone()[0]
        cls.profile=cls.db.get_food_profile(cls.apple)

    @classmethod
    def tearDownClass(cls):cls.db.close()

    def food(self,grams=100):
        return {'food_id':self.apple,'portion':{'value':grams,'unit':'g'},'source':'user_text'}

    def test_known_source_identity_and_precomputed_score(self):
        self.assertEqual(self.profile['food_code'],'63101000')
        self.assertNotEqual(str(self.profile['fdc_id']),self.profile['food_code'])
        self.assertEqual(self.profile['food_compass']['score'],95)
        self.assertEqual(self.profile['food_compass']['method'],'published_exact')

    def test_scaling_aggregation_and_uncertainty(self):
        food=self.food(150);food['portion'].update(min=100,max=200)
        result=calculate_intake([food,self.food(50)],database=DB)
        energy=self.profile['nutrients']['energy_kcal']['value']
        total=result['totals']['nutrients']['energy_kcal']
        self.assertAlmostEqual(total['value'],energy*2)
        self.assertAlmostEqual(total['min'],energy*1.5)
        self.assertAlmostEqual(total['max'],energy*2.5)

    def test_missingness_never_becomes_zero(self):
        items=[{'nutrients':{'x':{'value':2,'min':2,'max':2,'unit':'g'}}},{'nutrients':{}}]
        result=_aggregate(items,'nutrients',{'x':'g'})['x']
        self.assertIsNone(result['value']);self.assertEqual(result['known_amount'],2)
        self.assertEqual(result['missing_food_count'],1)

    def test_pattern_only_request_reports_missing_data(self):
        result=assess_diet([self.food()],requested_outputs=['food_patterns'],database=DB)
        if not self.profile['food_patterns']:
            self.assertEqual(result['status'],'partial')
            self.assertTrue(result['warnings'])

    def test_ambiguous_and_fabricated_id_abstain(self):
        for observation in [{'description':'rice','portion':{'value':100,'unit':'g'}},{'food_id':'made-up-id','portion':{'value':100,'unit':'g'}}]:
            result=assess_diet([observation],database=DB)
            self.assertEqual(result['status'],'needs_clarification');self.assertFalse(result['foods'])

    def test_exact_description_resolves_and_preparation_mismatch_abstains(self):
        food=self.food();food.pop('food_id');food['description']=self.profile['description']
        self.assertEqual(assess_diet([food],database=DB)['foods'][0]['id'],self.apple)
        food=self.food();food['preparation']='fried'
        self.assertEqual(assess_diet([food],database=DB)['status'],'needs_clarification')

    def test_portion_measures_and_invalid_cups(self):
        portion=self.profile['portions'][0]
        food=self.food();food['portion']={'value':2,'unit':'measure','measure_id':portion['id']}
        r=assess_diet([food],database=DB)
        self.assertEqual(r['foods'][0]['edible_grams'],2*portion['gram_weight'])
        food['portion']={'value':1,'unit':'cup'}
        self.assertEqual(assess_diet([food],database=DB)['status'],'needs_clarification')

    def test_recipe_yield_and_scaled_bounds(self):
        result=resolve_recipe([self.food(200)],100,database=DB)
        item=result['recipe_per_100g']['nutrients']['energy_kcal']
        expected=self.profile['nutrients']['energy_kcal']['value']*2
        self.assertEqual(item['value'],expected);self.assertEqual(item['known_amount'],expected)
        self.assertEqual(item['min'],expected);self.assertEqual(item['max'],expected)

    def test_only_trusted_scores_enter_derived_mean(self):
        untrusted=self.db.db.execute("SELECT food_id FROM compass_scores WHERE method='unavailable' LIMIT 1").fetchone()[0]
        food=self.food();food['food_id']=untrusted
        result=assess_diet([self.food(),food],database=DB,requested_outputs=['food_compass'])
        metric=result['indices']['food_compass']
        self.assertEqual(metric['value'],95)
        self.assertEqual(metric['status'],'partial')

    def test_invalid_inputs_and_units(self):
        for foods in [[],{},None]:
            with self.assertRaises(ValueError):assess_diet(foods,database=DB)
        with self.assertRaises(ValueError):assess_diet([self.food()],requested_outputs=['invented-index'],database=DB)
        with self.assertRaises(ValueError):calculate_dietary_indices({'energy_kcal':{'value':100,'unit':'g'}},{},30)

    def test_cli_matches_python_and_errors_are_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'meal.json';path.write_text(json.dumps({'age':30,'foods':[self.food()]}))
            stdout=io.StringIO()
            with redirect_stdout(stdout):code=main(['analyze',str(path),'--database',str(DB)])
            self.assertEqual(code,0)
            self.assertEqual(json.loads(stdout.getvalue()),assess_diet([self.food()],database=DB,age=30))
            stderr=io.StringIO()
            with redirect_stderr(stderr):code=main(['analyze','does-not-exist.json'])
            self.assertEqual(code,2);self.assertEqual(json.loads(stderr.getvalue())['status'],'error')

    def test_data_install_checksums_and_repeat_install(self):
        asset=ROOT/'data'/manifest()['file']
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'foods.sqlite'
            self.assertEqual(install_asset(asset,target),str(target))
            self.assertEqual(install_asset(asset,target),str(target))
            with FoodDatabase(target) as database:self.assertTrue(database.search_foods('apple'))
            bad=Path(temp)/'bad.gz';bad.write_bytes(b'not a database')
            with self.assertRaises(ValueError):install_asset(bad,Path(temp)/'other.sqlite')

    def test_mcp_same_core_and_lifecycle(self):
        self.assertEqual(len(tool_definitions()),6)
        direct=assess_diet([self.food()],database=DB)
        self.assertEqual(call_tool('assess_diet',{'foods':[self.food()]},DB),direct)
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                  {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'assess_diet','arguments':{'foods':[self.food()]}}},
                  {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'get_food_profile','arguments':{'food_id':'invalid'}}}]
        output=io.StringIO();serve(DB,io.StringIO('\n'.join(json.dumps(x) for x in requests)+'\n'),output)
        messages=[json.loads(x) for x in output.getvalue().splitlines()]
        self.assertEqual(len(messages),4)
        self.assertEqual(messages[2]['result']['structuredContent'],direct)
        self.assertTrue(messages[3]['result']['isError'])
        process=subprocess.run([sys.executable,'-m','diet_agent.cli','mcp','--database',str(DB)],input='\n'.join(json.dumps(x) for x in requests)+'\n',text=True,capture_output=True,check=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
        self.assertEqual([json.loads(x) for x in process.stdout.splitlines()],messages)


if __name__=='__main__':unittest.main()
