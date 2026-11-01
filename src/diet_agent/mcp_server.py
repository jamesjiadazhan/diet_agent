"""Optional local newline-delimited stdio MCP adapter; no sockets or hosted API.

Supports MCP 2024-11-05, 2025-03-26, and 2025-06-18. This is an explicitly
versioned compatibility adapter, not a claim of supporting every future host.
"""
import json
import sys
from .assessment import assess_diet,calculate_intake,calculate_dietary_indices,resolve_recipe
from .fooddb import FoodDatabase

OBSERVATION={'type':'object','properties':{
    'food_id':{'type':'string'},'description':{'type':'string'},
    'preparation':{'type':'string'},'source':{'enum':['photo_estimate','user_text','label','database_measure','user_confirmed']},
    'uncertainty':{'type':['string','object','null']},
    'portion':{'type':'object','required':['value','unit'],'properties':{
        'value':{'type':'number','exclusiveMinimum':0},'unit':{'enum':['g','kg','mg','measure']},
        'min':{'type':'number','exclusiveMinimum':0},'max':{'type':'number','exclusiveMinimum':0},
        'measure_id':{'type':'integer'},'basis':{'const':'edible'}},'additionalProperties':False}},
    'required':['portion'],'anyOf':[{'required':['food_id']},{'required':['description']}],
    'additionalProperties':False}
FOODS={'type':'array','items':OBSERVATION,'minItems':1}


def tool_definitions():
    properties={
        'search_foods':({'query':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':50},'preparation':{'type':'string'}},['query'],'Find candidates; ambiguous names require confirmation.'),
        'get_food_profile':({'food_id':{'type':'string'}},['food_id'],'Get per-100g nutrients, patterns, stored scores, portions and provenance.'),
        'resolve_recipe':({'ingredients':FOODS,'final_edible_grams':{'type':'number','exclusiveMinimum':0},'age':{'type':'number','minimum':1}},['ingredients','final_edible_grams'],'Mass-balance explicit ingredients and yield; does not invent retention factors.'),
        'calculate_intake':({'foods':FOODS},['foods'],'Scale edible portions and aggregate with explicit missingness.'),
        'calculate_dietary_indices':({'nutrients':{'type':'object'},'food_patterns':{'type':'object'},'age':{'type':'number','minimum':1}},['nutrients','food_patterns','age'],'Calculate HEI from aggregated canonical amounts, not averages of food scores.'),
        'assess_diet':({'foods':FOODS,'age':{'type':'number','minimum':1},'requested_outputs':{'type':'array','uniqueItems':True,'items':{'enum':['nutrients','food_patterns','hei2020','food_compass']}}},['foods'],'Resolve and assess structured observations with uncertainty and provenance.')}
    return [{'name':name,'description':description,'inputSchema':{'type':'object','properties':props,'required':required,'additionalProperties':False}}
            for name,(props,required,description) in properties.items()]


def call_tool(name,arguments,database=None):
    definition=next((t for t in tool_definitions() if t['name']==name),None)
    if definition is None:raise ValueError('Unknown tool')
    if not isinstance(arguments,dict):raise ValueError('arguments must be an object')
    schema=definition['inputSchema']
    if not set(schema['required'])<=arguments.keys() or not arguments.keys()<=schema['properties'].keys():
        raise ValueError('Missing or unsupported tool arguments')
    if name in ['search_foods','get_food_profile']:
        with FoodDatabase(database) as db:return getattr(db,name)(**arguments)
    if name=='calculate_dietary_indices':return calculate_dietary_indices(**arguments)
    function={'resolve_recipe':resolve_recipe,'calculate_intake':calculate_intake,'assess_diet':assess_diet}[name]
    return function(database=database,**arguments)


def serve(database=None,stdin=None,stdout=None):
    stdin=stdin or sys.stdin;stdout=stdout or sys.stdout
    initialized=False;negotiated=None
    def respond(value):
        stdout.write(json.dumps(value,allow_nan=False,ensure_ascii=False)+'\n');stdout.flush()
    for line in stdin:
        request=None
        try:
            request=json.loads(line)
            if not isinstance(request,dict) or request.get('jsonrpc')!='2.0' or not isinstance(request.get('method'),str):
                respond({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}});continue
            method=request['method'];params=request.get('params',{})
            if not isinstance(params,dict):raise ValueError('params must be an object')
            if 'id' not in request:
                if method=='notifications/initialized' and negotiated:initialized=True
                continue
            if method=='initialize':
                if negotiated:raise ValueError('Already initialized')
                version=params.get('protocolVersion')
                negotiated=version if version in ['2024-11-05','2025-03-26','2025-06-18'] else '2025-06-18'
                value={'protocolVersion':negotiated,'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'diet-agent','version':'0.1.0'}}
            elif method=='ping':value={}
            elif not initialized:raise ValueError('Initialize and send notifications/initialized first')
            elif method=='tools/list':value={'tools':tool_definitions()}
            elif method=='tools/call':
                try:
                    output=call_tool(params.get('name'),params.get('arguments',{}),database)
                    value={'content':[{'type':'text','text':json.dumps(output,allow_nan=False)}],'isError':False}
                    if negotiated=='2025-06-18':value['structuredContent']=output if isinstance(output,dict) else {'results':output}
                except (ValueError,KeyError,TypeError,OSError) as error:
                    value={'content':[{'type':'text','text':str(error)}],'isError':True}
            else:
                respond({'jsonrpc':'2.0','id':request['id'],'error':{'code':-32601,'message':'Method not found'}});continue
            respond({'jsonrpc':'2.0','id':request['id'],'result':value})
        except json.JSONDecodeError:
            respond({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}})
        except (ValueError,TypeError) as error:
            respond({'jsonrpc':'2.0','id':request.get('id') if isinstance(request,dict) else None,'error':{'code':-32602,'message':str(error)}})
