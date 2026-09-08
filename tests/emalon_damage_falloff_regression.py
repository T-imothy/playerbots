"""Execute the native 25-player Nova falloff, leaving target-radius data intact."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/vault_of_archavon/boss_emalon.cpp').read_text(encoding='utf-8')
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
using int32=int;using SpellEffectIndex=unsigned;constexpr unsigned EFFECT_INDEX_0=0;
struct Unit{float distance=0;float GetDistance(Unit*){return distance;}};
struct Spell{Unit*caster=nullptr,*target=nullptr;int damage=30000;Unit*GetCaster(){return caster;}Unit*GetUnitTarget(){return target;}
 int GetDamage(){return damage;}void SetDamage(int value){damage=value;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,unsigned)const{}};
__SCRIPT__
int main(){Unit caster,target;Spell spell{&caster,&target};spell_emalon_lightning_nova handler;
 for(float distance:{0.0f,17.5f,35.0f,52.5f,70.0f,100.0f}){
  caster.distance=distance;spell.damage=30000;handler.OnEffectExecute(&spell,0);
  assert(spell.damage==int(30000*std::max(0.0f,1.0f-distance/70.0f)));
 }
 spell.damage=30000;handler.OnEffectExecute(&spell,1);assert(spell.damage==30000);
 spell.target=nullptr;handler.OnEffectExecute(&spell,0);assert(spell.damage==30000);
 spell.target=&target;spell.caster=nullptr;handler.OnEffectExecute(&spell,0);assert(spell.damage==30000);
 std::cout<<"PASS native Nova near/mid/edge/outside falloff and effect/null guards\n";
}
'''.replace('__SCRIPT__',block(source,'struct spell_emalon_lightning_nova')+';')
with tempfile.TemporaryDirectory(prefix='emalon-falloff-') as td:
 p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
bot=(root/'playerbots-behavior/playerbot/strategy/values/GruulPositionValue.cpp').read_text(encoding='utf-8')
assert 'constexpr float falloffDistance = 70.0f;' in bot and 'constexpr float falloffDistance = 70.0f;' in source
migration=(root/'wotlk-db-behavior/Updates/5883_emalon_lightning_nova.sql').read_text(encoding='utf-8')
assert "(65279,'spell_emalon_lightning_nova')" in migration and '64216' not in migration and 'UPDATE' not in migration
