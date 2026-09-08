"""Execute native fixed-size player dispatch beyond encounter capacity."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
parts=[]
for era in ['tbc','wotlk']:
 base=root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland'
 s=(base/'auchindoun/shadow_labyrinth/boss_blackheart_the_inciter.cpp').read_text()
 k=(base/'tempest_keep/the_eye/boss_kaelthas.cpp').read_text()
 parts.append((block(s,'struct InciteChaos'),block(k,'    void SpellHitTarget('),block(k,'static const uint32 m_spellGravityLapseTeleport')))
assert parts[0]==parts[1]
incite,gravity,ports=parts[0]
code=r"""
#include <cassert>
#include <map>
#include <vector>
#include <set>
#include <iostream>
using uint32=unsigned;using SpellEffectIndex=unsigned;
enum{TYPEID_PLAYER=1,TRIGGERED_OLD_TRIGGERED=2,CAST_TRIGGERED=3,SPELL_INCITE_CHAOS_SPAWN_1=33677,SPELL_INCITE_CHAOS_SPAWN_2=33680,SPELL_INCITE_CHAOS_SPAWN_3=33681,SPELL_INCITE_CHAOS_SPAWN_4=33682,SPELL_INCITE_CHAOS_SPAWN_5=33683,SPELL_GRAVITY_LAPSE=35941,SPELL_GRAVITY_LAPSE_KNOCKBACK=34480,SPELL_GRAVITY_LAPSE_AURA=39432,SPELL_MIND_CONTROL=36797};
struct Unit{bool player=true;unsigned guid=1;std::vector<unsigned>casts;unsigned GetTypeId(){return player?TYPEID_PLAYER:0;}bool IsPlayer(){return player;}unsigned GetObjectGuid(){return guid;}void CastSpell(Unit*,unsigned id,unsigned){casts.push_back(id);}};
struct Spell{Unit*target;unsigned value=0;Unit*GetUnitTarget(){return target;}unsigned GetScriptValue(){return value;}void SetScriptValue(unsigned v){value=v;}};struct SpellScript{};struct SpellEntry{unsigned Id;};
__INCITE__;
__PORTS__;
struct Kael{unsigned m_uiGravityIndex=0;std::set<unsigned>m_charmTargets;std::vector<unsigned>casts;void DoCastSpellIfCan(Unit*,unsigned id,unsigned){casts.push_back(id);}
 __GRAVITY__
};
int main(){
 Unit player,pet;pet.player=false;Spell spell{&pet};InciteChaos incite;incite.OnEffectExecute(&spell,0);assert(spell.value==0&&pet.casts.empty());
 spell.target=nullptr;incite.OnEffectExecute(&spell,0);assert(spell.value==0);spell.target=&player;
 for(unsigned i=0;i<8;++i)incite.OnEffectExecute(&spell,0);
 assert(spell.value==5&&(player.casts==std::vector<unsigned>{33677,33680,33681,33682,33683}));
 spell.value=~0u;incite.OnEffectExecute(&spell,0);assert(player.casts.size()==5);
 Kael kael;SpellEntry lapse{SPELL_GRAVITY_LAPSE};player.casts.clear();kael.SpellHitTarget(&pet,&lapse);assert(kael.m_uiGravityIndex==0);
 for(unsigned i=0;i<28;++i)kael.SpellHitTarget(&player,&lapse);
 assert(kael.m_uiGravityIndex==25&&kael.casts.size()==25&&player.casts.size()==50);
 for(unsigned i=0;i<25;++i)assert(kael.casts[i]==35966+i);
 kael.m_uiGravityIndex=0;kael.SpellHitTarget(&player,&lapse);assert(kael.m_uiGravityIndex==1&&kael.casts.back()==35966);
 SpellEntry charm{SPELL_MIND_CONTROL};kael.SpellHitTarget(&player,&charm);assert(kael.m_charmTargets.count(player.guid));
 std::cout<<"PASS: native five/25 player dispatch, extra targets, nonplayer rejection, next-cycle reset and unrelated charm handling; TBC/Wrath sources match\n";
}
""".replace('__INCITE__',incite.replace(' override','')).replace('__PORTS__',ports).replace('__GRAVITY__',gravity.replace(' override',''))
with tempfile.TemporaryDirectory(prefix='encounter-slots-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
