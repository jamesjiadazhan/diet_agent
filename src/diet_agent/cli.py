"""Python API, CLI and MCP all invoke the same assessment core."""
import argparse
import json
from pathlib import Path
import sys
from .assessment import assess_diet,resolve_recipe
from .data_assets import install_asset,manifest
from .fooddb import FoodDatabase


def main(argv=None):
    parser=argparse.ArgumentParser(prog='diet-assess',description='Local dietary assessment for AI agents')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ['analyze','recipe']:
        command=sub.add_parser(name)
        command.add_argument('input',help='JSON file, or - for stdin')
        command.add_argument('--database')
    search=sub.add_parser('search');search.add_argument('query');search.add_argument('--database');search.add_argument('--limit',type=int,default=10);search.add_argument('--preparation')
    profile=sub.add_parser('profile');profile.add_argument('food_id');profile.add_argument('--database')
    data=sub.add_parser('data');ds=data.add_subparsers(dest='action',required=True)
    ds.add_parser('info');install=ds.add_parser('install');install.add_argument('--file');install.add_argument('--destination')
    mcp=sub.add_parser('mcp');mcp.add_argument('--database')
    args=parser.parse_args(argv)
    try:
        if args.command=='data':
            value=manifest() if args.action=='info' else {'database':install_asset(args.file,args.destination)}
        elif args.command=='mcp':
            from .mcp_server import serve
            serve(database=args.database);return 0
        elif args.command in ['search','profile']:
            with FoodDatabase(args.database) as db:
                value=db.search_foods(args.query,args.limit,args.preparation) if args.command=='search' else db.get_food_profile(args.food_id)
        else:
            raw=sys.stdin.read() if args.input=='-' else Path(args.input).read_text()
            request=json.loads(raw)
            if not isinstance(request,dict):raise ValueError('Input JSON must be an object')
            if args.command=='recipe':
                value=resolve_recipe(request['ingredients'],request['final_edible_grams'],database=args.database,age=request.get('age'))
            else:
                value=assess_diet(request['foods'],request.get('requested_outputs'),database=args.database,age=request.get('age'))
        print(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2));return 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps({'schema_version':'1.0','status':'error','error':str(error)},allow_nan=False),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
