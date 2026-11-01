"""Native taunt-effect immunity must veto the stance prerequisite as well."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
signature='    bool IneffectiveBroodlordTaunt('
method=block(s,signature) if signature in s else 'bool IneffectiveBroodlordTaunt(PlayerbotAI*,const SpellEntry*,Unit*){return false;}'
code=r'''
#include <cassert>
#include <iostream>
enum {CLASS_WARRIOR=1,SPELL_EFFECT_ATTACK_ME=114,SPELL_AURA_MOD_TAUNT=11,MAX_EFFECT_INDEX=3};
enum SpellEffectIndex {EFFECT_INDEX_0,EFFECT_INDEX_1,EFFECT_INDEX_2};
struct SpellEntry{unsigned Effect[3]{},EffectApplyAuraName[3]{};};
struct Unit{unsigned entry=12017;bool immune=true;unsigned GetEntry(){return entry;}
 bool IsImmuneToSpellEffect(const SpellEntry*,SpellEffectIndex,bool){return immune;}};
struct Player:Unit {unsigned map=469,cls=1;unsigned GetMapId(){return map;}unsigned getClass(){return cls;}};
struct PlayerbotAI{Player bot;bool tank=true,ready=true,engaged=true;Player*GetBot(){return &bot;}bool IsTank(Player*){return tank;}};
static bool engaged=true;
bool Ready(PlayerbotAI*a){return a->ready;}bool Engaged(Player*,Unit*u){return u&&engaged;}
__METHOD__
int main(){PlayerbotAI ai;Unit boss;SpellEntry taunt,mocking,damage;taunt.Effect[0]=114;mocking.Effect[0]=2;mocking.Effect[1]=6;mocking.EffectApplyAuraName[1]=11;damage.Effect[0]=2;
#ifdef MANGOSBOT_ZERO
 assert(IneffectiveBroodlordTaunt(&ai,&taunt,&boss));assert(IneffectiveBroodlordTaunt(&ai,&mocking,&boss));
#else
 assert(!IneffectiveBroodlordTaunt(&ai,&taunt,&boss));assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));
#endif
 assert(!IneffectiveBroodlordTaunt(&ai,&damage,&boss));assert(!IneffectiveBroodlordTaunt(&ai,nullptr,&boss));assert(!IneffectiveBroodlordTaunt(&ai,&taunt,nullptr));
 boss.immune=false;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));boss.immune=true;
 ai.tank=false;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));ai.tank=true;
 ai.ready=false;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));ai.ready=true;
 engaged=false;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));engaged=true;
 ai.bot.cls=2;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));ai.bot.cls=1;
 for(unsigned entry:{12057,12056,11982,11583}){boss.entry=entry;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));}boss.entry=12017;
 for(unsigned map:{0,1,229,489,529,30,409,533,531,309}){ai.bot.map=map;assert(!IneffectiveBroodlordTaunt(&ai,&mocking,&boss));}
 std::cout<<"PASS: Classic Broodlord native-immune taunts vetoed; other spells/bosses/maps/eras preserved\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='broodlord-taunt-') as directory:
  p=Path(directory);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
if signature in s:
 multiplier=block(s,'float PreserveClassicRaidPlan::GetValue(')
 assert 'IneffectiveBroodlordTaunt(ai,' in multiplier
 engine=(root/'playerbot/strategy/Engine.cpp').read_text()
 start=engine.index('relevance *= multiplier->GetValue(action)')
 assert engine.index('if (!relevance)',start)<engine.index('actionNode->getPrerequisites()',start)
