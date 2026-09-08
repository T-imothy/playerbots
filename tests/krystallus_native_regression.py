"""Test actual Krystallus Shatter damage script against controlled spell objects."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/ulduar/halls_of_stone/halls_of_stoneScripts.cpp').read_text(encoding='utf-8')
code=r'''
#include <cassert>
#include <algorithm>
#include <cmath>
using int32=int;using SpellEffectIndex=int;
enum{EFFECT_INDEX_0=0,DIST_CALC_COMBAT_REACH=1};
struct Unit{float x=0,y=0,reach=1.5f;float GetPositionX(){return x;}float GetPositionY(){return y;}float GetDistance2d(float xx,float yy,int){return std::max(0.0f,std::hypot(x-xx,y-yy)-reach);}};
struct SpellEntry{unsigned EffectRadiusIndex[3]={10,0,0};};
struct Radius{float value=30;};struct Store{Radius radius;Radius* LookupEntry(unsigned){return &radius;}}sSpellRadiusStore;
float GetSpellRadius(Radius* r){return r?r->value:0;}
struct Spell{Unit* caster=nullptr;Unit* target=nullptr;SpellEntry info;SpellEntry* m_spellInfo=&info;int damage=25000;
 Unit* GetAffectiveCaster(){return caster;}Unit* GetUnitTarget(){return target;}int GetDamage(){return damage;}void SetDamage(int n){damage=n;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,SpellEffectIndex)const{}};
__SCRIPT__
int main(){spell_krystallus_shatter_damage script;Unit caster,target;Spell spell;spell.caster=&caster;spell.target=&target;
 for(int base:{12500,25000}){spell.damage=base;target.x=0;script.OnEffectExecute(&spell,0);assert(spell.damage==base);
 target.x=16.5f;spell.damage=base;script.OnEffectExecute(&spell,0);assert(spell.damage==base/2);
 target.x=31.5f;spell.damage=base;script.OnEffectExecute(&spell,0);assert(spell.damage==0);
 target.x=100;spell.damage=base;script.OnEffectExecute(&spell,0);assert(spell.damage==0);}
 spell.damage=25000;script.OnEffectExecute(&spell,1);assert(spell.damage==25000);
 spell.target=nullptr;script.OnEffectExecute(&spell,0);assert(spell.damage==25000);spell.target=&target;
 sSpellRadiusStore.radius.value=0;script.OnEffectExecute(&spell,0);assert(spell.damage==25000);
}
'''.replace('__SCRIPT__',block(source,'struct spell_krystallus_shatter_damage')+';')
with tempfile.TemporaryDirectory(prefix='krystallus-native-') as td:
 p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
assert 'RegisterSpellScript<spell_krystallus_shatter_damage>' in source
sql=(root/'wotlk-db-behavior/Updates/5895_krystallus_shatter_damage.sql').read_text(encoding='utf-8')
assert "(50811, 'spell_krystallus_shatter_damage')" in sql and "(61547, 'spell_krystallus_shatter_damage')" in sql
print('PASS native Shatter near/mid/edge/outside falloff, difficulty damage, null targets and binding contracts')
