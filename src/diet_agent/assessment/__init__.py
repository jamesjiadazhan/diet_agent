"""Matching, edible portions, additive aggregation and validated scoring."""
import itertools
import math
from ..fooddb import FoodDatabase
from ..dietaryindex_py import hei2020

VALID_OUTPUTS={'nutrients','food_patterns','hei2020','food_compass'}
SOURCES={'photo_estimate','user_text','label','database_measure','user_confirmed'}


def _number(value,name,positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (positive and value==0):
        raise ValueError(name+' must be a finite '+('positive' if positive else 'nonnegative')+' number')
    return float(value)


def _grams(observation,profile):
    p=observation.get('portion')
    if not isinstance(p,dict):raise ValueError('An explicit edible portion is required')
    if p.get('basis','edible')!='edible':raise ValueError('Convert as-purchased amounts to edible grams using an explicit edible fraction first')
    value=_number(p.get('value'),'portion.value',positive=True)
    unit=p.get('unit')
    factor={'g':1,'kg':1000,'mg':0.001}.get(unit)
    if unit=='measure':
        record=next((x for x in profile['portions'] if x['id']==p.get('measure_id')),None)
        if record is None:raise ValueError('measure_id must belong to this food')
        factor=record['gram_weight']
    if factor is None:raise ValueError('Use g, kg, mg, or an explicit catalog measure_id; cups are food-specific')
    low=_number(p.get('min',value),'portion.min',positive=True)
    high=_number(p.get('max',value),'portion.max',positive=True)
    if not low<=value<=high:raise ValueError('Require portion.min <= portion.value <= portion.max')
    return value*factor,low*factor,high*factor


def _scale(values,grams,low,high):
    output={}
    for key,item in values.items():
        value=item['value']
        output[key]=dict(item,value=None if value is None else value*grams/100,
                         min=None if value is None else value*low/100,
                         max=None if value is None else value*high/100)
    return output


def _aggregate(items,field,definitions):
    output={}
    keys=set(definitions)
    for item in items:keys.update(item[field])
    for key in sorted(keys):
        present=[item[field].get(key) for item in items]
        good=[x for x in present if x and x['value'] is not None]
        missing=len(items)-len(good)
        unit=good[0]['unit'] if good else definitions.get(key)
        if any(x['unit']!=unit for x in good):raise ValueError('Mixed units for '+key)
        known=sum(x['value'] for x in good)
        output[key]={'value':None if missing else known,'known_amount':known,'unit':unit,
                     'min':None if missing else sum(x['min'] for x in good),
                     'max':None if missing else sum(x['max'] for x in good),
                     'status':'missing' if not good else 'partial' if missing else 'calculated',
                     'missing_food_count':missing}
    return output


def calculate_dietary_indices(nutrients,food_patterns,age):
    """Aggregate amounts go in; HEI food scores are never averaged."""
    if not isinstance(nutrients,dict) or not isinstance(food_patterns,dict):
        raise ValueError('nutrients and food_patterns must be objects')
    def get(values,key):
        item=values.get(key)
        if item is None:return None
        if not isinstance(item,dict):raise ValueError(key+' must contain value and unit')
        value=item.get('value')
        if value is None:return None
        _number(value,key)
        expected={'energy_kcal':'kcal','saturated_fat_g':'g','mufa_g':'g','pufa_g':'g','sodium_mg':'mg'}.get(key)
        if values is food_patterns:
            expected='tsp eq' if key=='add_sugars' else 'oz eq' if key.startswith(('pf_','g_')) else 'cup eq'
        unit=str(item.get('unit','')).replace('.','').strip()
        if expected and unit!=expected:raise ValueError(key+' requires unit '+expected)
        return value
    def total(values,*keys):
        amounts=[get(values,key) for key in keys]
        return None if any(x is None for x in amounts) else sum(amounts)
    kcal=get(nutrients,'energy_kcal');sfa=get(nutrients,'saturated_fat_g')
    unsaturated=total(nutrients,'mufa_g','pufa_g')
    if kcal is not None and kcal<=0:
        return {'status':'partial','total':None,'components':{},'missing':['positive_total_energy']}
    inputs={'age':age,'kcal':kcal,'total_fruit':get(food_patterns,'f_total'),
            'whole_fruit':total(food_patterns,'f_citmlb','f_other'),
            'total_vegetable':total(food_patterns,'v_total','v_legumes'),
            'green_and_bean':total(food_patterns,'v_drkgr','v_legumes'),
            'total_protein':total(food_patterns,'pf_mps_total','pf_eggs','pf_nutsds','pf_soy','pf_legumes'),
            'seafood_plant_protein':total(food_patterns,'pf_seafd_hi','pf_seafd_low','pf_nutsds','pf_soy','pf_legumes'),
            'whole_grain':get(food_patterns,'g_whole'),'dairy':get(food_patterns,'d_total'),
            # The frozen NHANES R wrapper explicitly assigns a ratio of zero
            # for known zero saturated fat. Missing fat data still abstains.
            'fatty_acid':None if sfa is None or unsaturated is None else 0.0 if sfa==0 else unsaturated/sfa,
            'refined_grain':get(food_patterns,'g_refined'),'sodium':get(nutrients,'sodium_mg'),
            'added_sugar':get(food_patterns,'add_sugars'),'saturated_fat':sfa}
    return hei2020(inputs)


def _compass(items):
    total_energy=0;scored_energy=0;weighted=0;missing_energy=False
    for item in items:
        energy=item['nutrients'].get('energy_kcal',{}).get('value')
        if energy is None:
            missing_energy=True;continue
        total_energy+=energy
        score=item['food_compass']['score']
        if score is not None:
            scored_energy+=energy;weighted+=score*energy
    coverage=None if missing_energy or not total_energy else scored_energy/total_energy
    return {'name':'derived_energy_weighted_published_food_compass_mean',
            'value':weighted/scored_energy if scored_energy>0 else None,
            'status':'complete' if coverage==1 else 'partial',
            'scored_energy_kcal':scored_energy,'known_total_energy_kcal':total_energy,
            'scored_energy_coverage':coverage,
            'note':'Derived metric over verified scored foods only; not an official meal/daily Food Compass algorithm.'}


def assess_diet(foods,requested_outputs=None,*,database=None,age=None):
    if not isinstance(foods,list) or not foods:raise ValueError('foods must be a nonempty list')
    outputs=VALID_OUTPUTS if requested_outputs is None else set(requested_outputs)
    if not outputs<=VALID_OUTPUTS:raise ValueError('Unsupported requested_outputs: '+str(sorted(outputs-VALID_OUTPUTS)))
    if age is not None:_number(age,'age',positive=True)
    result={'schema_version':'1.0','status':'complete','foods':[],'unresolved':[],'warnings':[],
            'totals':{},'indices':{},'uncertainty':{'recognition':'supplied by caller','portion_ranges':'provided bounds; not statistical confidence intervals'}}
    with FoodDatabase(database) as db:
        result['dataset_releases']=db.releases()
        definitions={x['id']:x['unit'] for x in db.definitions()}
        for position,obs in enumerate(foods):
            if not isinstance(obs,dict):raise ValueError('Each observation must be an object')
            source=obs.get('source','user_text')
            if source not in SOURCES:raise ValueError('Unsupported observation source')
            food_id=obs.get('food_id');prep=obs.get('preparation')
            if food_id is None:
                query=obs.get('description','')
                candidates=db.search_foods(query,limit=10,preparation=prep)
                exact=[x for x in candidates if x['description'].casefold()==query.strip().casefold()]
                if len(exact)==1:food_id=exact[0]['id']
                else:
                    result['unresolved'].append({'position':position,'reason':'Confirm a candidate food_id; ambiguous or unmatched text is not auto-selected','candidates':candidates});continue
            try:profile=db.get_food_profile(food_id)
            except KeyError:
                result['unresolved'].append({'position':position,'reason':'Unknown food_id','candidates':[]});continue
            if prep is not None and prep!=profile['preparation']:
                result['unresolved'].append({'position':position,'reason':'Preparation state does not match confirmed record','candidates':[]});continue
            try:grams,low,high=_grams(obs,profile)
            except ValueError as error:
                result['unresolved'].append({'position':position,'reason':str(error),'candidates':[]});continue
            item={key:profile[key] for key in ['id','fdc_id','food_code','description','release_id','preparation','food_compass']}
            item.update(position=position,source=source,edible_grams=grams,grams_min=low,grams_max=high,
                        observation_uncertainty=obs.get('uncertainty'),
                        nutrients=_scale(profile['nutrients'],grams,low,high),
                        food_patterns=_scale(profile['food_patterns'],grams,low,high))
            result['foods'].append(item)
            if profile['food_compass']['method']=='unavailable':
                result['warnings'].append(f'{food_id}: stored legacy Food Compass value is unvalidated and excluded from the derived summary')
            if low!=high or source=='photo_estimate':
                result['warnings'].append(f'{food_id}: intake depends on estimated portions; nonlinear indices use the point estimate only')
        items=result['foods']
        if not items:
            result['status']='needs_clarification';return result
        nutrients=_aggregate(items,'nutrients',definitions)
        patterns=_aggregate(items,'food_patterns',{})
        if 'nutrients' in outputs:result['totals']['nutrients']=nutrients
        if 'food_patterns' in outputs:result['totals']['food_patterns']=patterns
        if 'hei2020' in outputs:result['indices']['hei2020']=calculate_dietary_indices(nutrients,patterns,age)
        if 'food_compass' in outputs:result['indices']['food_compass']=_compass(items)
        if result['unresolved']:
            result['status']='needs_clarification'
            result['warnings'].append('Totals and indices describe resolved foods only; the requested intake is incomplete')
        elif any(x.get('status')!='complete' for x in result['indices'].values()) or any(x['value'] is None for x in nutrients.values()):
            result['status']='partial'
        if 'food_patterns' in outputs and (not patterns or any(x['value'] is None for x in patterns.values())):
            if result['status']=='complete':result['status']='partial'
            result['warnings'].append('Food-pattern equivalents are unavailable for one or more foods; missing patterns are not zero.')
        result['warnings'].append('A food, meal, or single day does not establish usual dietary intake.')
    return result


def calculate_intake(foods,*,database=None):
    return assess_diet(foods,requested_outputs=['nutrients','food_patterns'],database=database)


def resolve_recipe(ingredients,final_edible_grams,*,database=None,age=None):
    """Explicit ingredient amounts and final yield; no invented retention factors.

    Use cooked ingredient records, or pass separately validated retained amounts.
    This mass-balance recipe tool does not model nutrient loss during cooking.
    """
    final=_number(final_edible_grams,'final_edible_grams',positive=True)
    result=assess_diet(ingredients,database=database,age=age)
    if result['unresolved']:
        result['recipe_per_100g']=None
    else:
        result['recipe_per_100g']={field:{key:{name:(amount*100/final if amount is not None and name in ['value','known_amount','min','max'] else amount)
                                            for name,amount in value.items()}
                                      for key,value in values.items()}
                                  for field,values in result['totals'].items()}
    result['final_edible_grams']=final
    result['warnings'].append('Recipe mass balance assumes no nutrient loss; cooking yield changes concentration only. Use cooked ingredient records for cooked recipes.')
    return result
