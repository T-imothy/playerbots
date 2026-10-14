"""Actual spell admission for reserved Classic control actors, all era guards."""
from pathlib import Path
import tempfile,subprocess
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <iostream>
#include <list>
#include <vector>
#include <algorithm>
constexpr unsigned UNIT_CREATED_BY_SPELL=1;struct PlayerbotAI;using uint32=unsigned;using ObjectGuid=unsigned;using SpellEffectIndex=unsigned;constexpr unsigned MAX_EFFECT_INDEX=3;
struct SpellEntry{unsigned Id=0,MaxAffectedTargets=0;bool damage=false,area=false;};
bool IsSpellEffectDamage(const SpellEntry&s,unsigned){return s.damage;}bool IsAreaOfEffectSpell(const SpellEntry*s){return s->area;}
struct Unit{unsigned entry=16506,created=0,spawner=0;unsigned GetUInt32Value(unsigned){return created;}unsigned GetSpawnerGuid(){return spawner;}bool world=true,charmed=false;float distance=10;unsigned GetEntry(){return entry;}float GetDistance(Unit*){return distance;}};
struct Player{unsigned map=533;bool world=true,tank=false,heal=false,buff=false;PlayerbotAI*brain=nullptr;bool HasAura(unsigned){return buff;}PlayerbotAI*GetPlayerbotAI(){return brain;}unsigned GetMapId(){return map;}};
struct ListValue{std::list<unsigned>list;auto Get(){return list;}};
struct Context{ListValue value;template<class T>ListValue*GetValue(const char*,const char*){return &value;}};
struct PlayerbotAI{Player bot;Context context;Unit worshipper,student,boss,spore;std::vector<Player*>roster;bool real=false;bool ready=true;
 PlayerbotAI(){bot.brain=this;roster={&bot};spore.entry=16286;spore.created=29234;spore.spawner=4;student.entry=16803;boss.entry=15953;context.value.list={1,2};}
 Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){return id==1?&worshipper:id==2?&student:id==3?&spore:id==4?&boss:nullptr;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}bool IsRealPlayer(){return real;}};
bool Ready(PlayerbotAI*a){
#ifdef MANGOSBOT_ZERO
return a->ready;
#else
return false;
#endif
}
std::vector<Player*>Members(PlayerbotAI*a){return a->roster;}float NativeEncounterSpellRadius(unsigned){return 10;}bool Engaged(Player*,Unit*){return true;}
bool Live(Player*,Unit*u){return u&&u->world&&!u->charmed;}
Unit*FindBoss(PlayerbotAI*a,unsigned entry){return a->boss.entry==entry?&a->boss:nullptr;}
namespace ai{bool ClassicRaidOffenseAllowed(PlayerbotAI*,const SpellEntry*,Unit*);}
__BODY__
int main(){PlayerbotAI brain;SpellEntry hit{1,0,true,false},area{2,0,true,true},heal{},taunt{},flurry{13877},sweeping{12328};
#ifdef MANGOSBOT_ZERO
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&flurry,&brain.bot));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&sweeping,&brain.bot));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&heal,&brain.worshipper));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&taunt,&brain.worshipper));
 brain.bot.tank=true;assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.bot.tank=false;
 brain.worshipper.charmed=true;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.worshipper.charmed=false;
 brain.worshipper.distance=100;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.worshipper.distance=10;
 brain.boss.entry=16061;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.student));
 brain.ready=false;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.ready=true;
 assert(!ai::ClassicRaidOffenseAllowed(&brain,nullptr,&brain.student));
 brain.boss.entry=16011;brain.context.value.list={3};brain.bot.distance=8;
 assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
 brain.bot.distance=20;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.bot.distance=8;
 brain.real=true;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.real=false;
 Player tank;tank.tank=true;tank.distance=5;brain.roster.push_back(&tank); // actual tank would steal native buff
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.roster.pop_back();
 brain.bot.buff=true;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.bot.buff=false;
 brain.bot.map=409;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
#else
 assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
#endif
 std::cout<<"PASS actual damaging AoE/direct/cleave admission reserves Classic control actors, preserves heals/taunts/tanks and MC/era guards\n";
}
'''.replace('__BODY__',block(s,'    std::vector<Player*> SporeRecipients(')+'\n'+block(s,'bool ai::ClassicRaidOffenseAllowed('))
# Healing-self targets use the same Unit interface in the server.
code=code.replace('struct Player{','struct Player:Unit{')
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-offense-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
