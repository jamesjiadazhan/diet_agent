"""Read-only curated food catalog and explicit source identities."""
import json
import os
from pathlib import Path
import re
import sqlite3


def default_path():
    if os.environ.get('DIET_AGENT_DB'):
        return Path(os.environ['DIET_AGENT_DB'])
    name='generic-fndds-2021-2023-v1.sqlite'
    local=Path(__file__).resolve().parents[3]/'data'/name
    return local if local.is_file() else Path.home()/'.cache/diet_agent'/name


class FoodDatabase:
    def __init__(self, path=None):
        self.path=Path(path) if path else default_path()
        if not self.path.is_file():
            raise FileNotFoundError('Install the generic database with diet-assess data install, or pass database= / --database')
        self.db=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
        self.db.row_factory=sqlite3.Row
        if self.db.execute('PRAGMA user_version').fetchone()[0]!=1:
            self.close();raise ValueError('Unsupported food database schema')

    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

    def releases(self):
        return [dict(row) for row in self.db.execute('SELECT * FROM dataset_releases ORDER BY id')]

    def search_foods(self,query,limit=10,preparation=None):
        if not isinstance(query,str) or not query.strip():raise ValueError('query must be nonempty text')
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=50:raise ValueError('limit must be 1..50')
        if preparation is not None and not isinstance(preparation,str):raise ValueError('preparation must be text')
        tokens=re.findall(r'\w+',query.casefold())[:12]
        if not tokens:return []
        match=' AND '.join('"'+token+'"*' for token in tokens)
        rows=self.db.execute('''SELECT f.*,c.score AS food_compass_score,c.method AS food_compass_method
            FROM foods_fts JOIN foods f ON f.id=foods_fts.food_id
            JOIN compass_scores c ON c.food_id=f.id
            WHERE foods_fts MATCH ? AND (? IS NULL OR f.preparation=?)
            ORDER BY bm25(foods_fts),f.description,f.id LIMIT ?''',(match,preparation,preparation,limit)).fetchall()
        aliases=self.db.execute('SELECT f.* FROM food_aliases a JOIN foods f ON f.id=a.food_id WHERE lower(a.alias)=?',(query.casefold(),)).fetchall()
        by_id={r['id']:dict(r) for r in list(aliases)+list(rows)}
        return list(by_id.values())[:limit]

    def get_food_profile(self,food_id):
        if not isinstance(food_id,str):raise ValueError('food_id must be the catalog internal ID returned by search')
        row=self.db.execute('SELECT * FROM foods WHERE id=?',(food_id,)).fetchone()
        if row is None:raise KeyError('Unknown confirmed food_id: '+food_id)
        profile=dict(row)
        profile['nutrients']={r['nutrient_id']:{'value':r['value'],'unit':r['unit'],'status':r['status'],'release_id':r['release_id']}
                              for r in self.db.execute('''SELECT v.*,d.unit FROM nutrient_values v
                              JOIN nutrient_definitions d ON d.id=v.nutrient_id WHERE food_id=? ORDER BY nutrient_id''',(food_id,))}
        profile['food_patterns']={r['component']:{'value':r['value'],'unit':r['unit'],'status':r['status'],'release_id':r['release_id']}
                                  for r in self.db.execute('SELECT * FROM pattern_values WHERE food_id=? ORDER BY component',(food_id,))}
        profile['portions']=[dict(r) for r in self.db.execute('SELECT id,description,gram_weight FROM portion_measures WHERE food_id=? ORDER BY id',(food_id,))]
        compass=dict(self.db.execute('SELECT * FROM compass_scores WHERE food_id=?',(food_id,)).fetchone())
        profile['food_compass']={'score':compass['score'],'method':compass['method'],'release_id':compass['release_id'],'note':compass['note'],
                                 'precomputed_reference':{'value':compass['precomputed_reference_value'],'method':compass['precomputed_reference_method'],
                                                          'validated_for_this_record':compass['method']=='published_exact' and compass['score']==compass['precomputed_reference_value']}}
        profile['basis']='per_100g_edible_portion'
        return profile

    def definitions(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM nutrient_definitions ORDER BY id')]
