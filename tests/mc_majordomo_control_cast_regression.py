"""Actual bandage admission must preserve an admitted Majordomo control cast."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
item=(root/'playerbot/strategy/actions/UseItemAction.h').read_text()
method=block(source,'bool ai::HasMajordomoControlCast(')
bandage=block(block(item,'class UseBandageAction'),'virtual bool isUseful() override')
code=r'''
#include <cassert>
#include <iostream>
using uint8=unsigned char;enum{CURRENT_GENERIC_SPELL,SPELL_STATE_FINISHED=7,MECHANIC_POLYMORPH=17,SPELL_AURA_PERIODIC_DAMAGE=3,SPELL_AURA_PERIODIC_DAMAGE_PERCENT=89,SPELL_AURA_PERIODIC_LEECH=53};
enum class BotState{BOT_STATE_COMBAT};
struct Unit{};struct SpellEntry{unsigned Mechanic=MECHANIC_POLYMORPH;};
struct Targets{Unit*target=nullptr;Unit*getUnitTarget(){return target;}};
struct Spell{SpellEntry*m_spellInfo;Targets m_targets;unsigned state=0;unsigned getState(){return state;}};
struct Map{bool IsDungeon()const{return true;}bool IsRaid()const{return true;}};
struct Player:Unit{unsigned map=409,hp=60;bool world=true,alive=true;Spell*cast=nullptr;Map nativeMap;
unsigned GetMapId(){return map;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}float GetHealthPercent(){return hp;}Spell*GetCurrentSpell(unsigned){return cast;}
bool HasAura(unsigned){return false;}bool HasAuraType(unsigned){return false;}unsigned GetSkillValue(unsigned){return 300;}const Map*GetMap(){return &nativeMap;}};
struct PlayerbotAI{Player*bot;bool assignment=true;Unit*assigned=nullptr;Player*GetBot(){return bot;}
bool IsTank(Player*){return false;}bool IsHeal(Player*){return false;}bool IsStateActive(BotState){return true;}unsigned GetManaPercent(){return 80;}bool HasStrategy(const char*,BotState){return false;}};
struct{unsigned criticalHealth=20;}sPlayerbotAIConfig;
namespace ai{bool HasMajordomoControlCast(PlayerbotAI*);bool MajordomoPolymorphAssignment(PlayerbotAI*a,Unit*&u){u=a->assigned;return a->assignment;}}
using namespace ai;
__METHOD__
struct UseTargetedItemIdAction{int calls=0;virtual bool isUseful(){++calls;return true;}};
#define AI_VALUE(type,name) 0
struct Bandage:UseTargetedItemIdAction{PlayerbotAI*ai;Player*bot;__BANDAGE__};
int main(){Player bot;Unit healer,other;SpellEntry poly;Spell cast{&poly,{&healer}};bot.cast=&cast;PlayerbotAI brain{&bot,true,&healer};Bandage bandage;bandage.ai=&brain;bandage.bot=&bot;
#ifdef MANGOSBOT_ZERO
assert(HasMajordomoControlCast(&brain));assert(!bandage.isUseful()&&bandage.calls==0);
bot.hp=20;assert(!HasMajordomoControlCast(&brain)&&bandage.isUseful());bot.hp=60;
brain.assigned=&other;assert(!HasMajordomoControlCast(&brain));brain.assigned=&healer;
brain.assignment=false;assert(!HasMajordomoControlCast(&brain));brain.assignment=true;
brain.assigned=nullptr;assert(!HasMajordomoControlCast(&brain));brain.assigned=&healer;
cast.state=SPELL_STATE_FINISHED;assert(!HasMajordomoControlCast(&brain));cast.state=0;
poly.Mechanic=0;assert(!HasMajordomoControlCast(&brain));poly.Mechanic=MECHANIC_POLYMORPH;
cast.m_spellInfo=nullptr;assert(!HasMajordomoControlCast(&brain));cast.m_spellInfo=&poly;
bot.cast=nullptr;assert(!HasMajordomoControlCast(&brain));bot.cast=&cast;
bot.map=469;assert(!HasMajordomoControlCast(&brain));bot.map=409;
bot.world=false;assert(!HasMajordomoControlCast(&brain));bot.world=true;bot.alive=false;assert(!HasMajordomoControlCast(&brain));bot.alive=true;
assert(!HasMajordomoControlCast(nullptr));
#else
assert(!HasMajordomoControlCast(&brain)&&bandage.isUseful());
#endif
std::cout<<"PASS: admitted Majordomo Polymorph survives optional bandage; emergency, other targets, spells, maps and eras preserved\n";
}
'''.replace('__METHOD__',method).replace('__BANDAGE__',bandage)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-control-cast-')as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
