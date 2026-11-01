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
#include <map>
constexpr unsigned SPELL_AURA_DAMAGE_SHIELD=15;constexpr unsigned SPELL_AURA_MOD_FEAR=7;constexpr unsigned UNIT_CREATED_BY_SPELL=1;struct PlayerbotAI;using uint32=unsigned;using ObjectGuid=unsigned;using SpellEffectIndex=unsigned;constexpr unsigned MAX_EFFECT_INDEX=3;
struct SpellEntry{unsigned Id=0,MaxAffectedTargets=0;bool damage=false,area=false;unsigned EffectTriggerSpell[3]={};unsigned EffectChainTarget[3]={};unsigned EffectApplyAuraName[3]={};bool aura[3]={};};
bool IsAuraApplyEffect(const SpellEntry*s,unsigned i){return s->aura[i];}
bool IsSpellHaveAura(const SpellEntry*s,unsigned aura){for(unsigned i=0;i<3;++i)if(s->aura[i]&&s->EffectApplyAuraName[i]==aura)return true;return false;}
bool IsSpellEffectDamage(const SpellEntry&s,unsigned){return s.damage;}bool IsAreaOfEffectSpell(const SpellEntry*s){return s->area;}
bool IsSpellEffectTriggerSpell(const SpellEntry*s,unsigned i){return s->EffectTriggerSpell[i]!=0;}
bool IsSpellEffectTriggerSpellByAura(const SpellEntry*,unsigned){return false;}
struct Facade{std::map<unsigned,const SpellEntry*>spells;const SpellEntry*LookupSpellInfo(unsigned id){return spells.count(id)?spells[id]:nullptr;}}sServerFacade;
struct Unit{bool player=false;bool IsPlayer(){return player;}unsigned entry=16506,created=0,spawner=0;unsigned GetUInt32Value(unsigned){return created;}unsigned GetSpawnerGuid(){return spawner;}bool world=true,charmed=false;float distance=10,hp=100;unsigned GetEntry(){return entry;}float GetDistance(Unit*){return distance;}float GetHealthPercent(){return hp;}};
struct Player{unsigned map=533;bool world=true,tank=false,heal=false,buff=false;PlayerbotAI*brain=nullptr;bool HasAura(unsigned){return buff;}PlayerbotAI*GetPlayerbotAI(){return brain;}unsigned GetMapId(){return map;}};
struct ListValue{std::list<unsigned>list;auto Get(){return list;}};
struct Context{ListValue value;template<class T>ListValue*GetValue(const char*,const char*){return &value;}};
struct PlayerbotAI{Player bot;Context context;Unit worshipper,student,boss,spore;Unit*sacrifice=nullptr;std::vector<Player*>roster;bool real=false;bool ready=true;
 PlayerbotAI(){bot.brain=this;roster={&bot};spore.entry=16286;spore.created=29234;spore.spawner=4;student.entry=16803;boss.entry=15953;context.value.list={1,2};}
 Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){return id==1?&worshipper:id==2?&student:id==3?&spore:id==4?&boss:nullptr;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}bool IsRealPlayer(){return real;}};
bool Ready(PlayerbotAI*a){
return a->ready;
}
Unit*FaerlinaSacrifice(PlayerbotAI*a,Unit*){return a->sacrifice;}
std::vector<Player*>Members(PlayerbotAI*a){return a->roster;}float NativeEncounterSpellRadius(unsigned){return 10;}bool Engaged(Player*,Unit*){return true;}
bool Live(Player*,Unit*u){return u&&u->world&&!u->charmed;}
Unit*FindBoss(PlayerbotAI*a,unsigned entry){return a->boss.entry==entry?&a->boss:nullptr;}
namespace ai{bool ClassicRaidOffenseAllowed(PlayerbotAI*,const SpellEntry*,Unit*);}
Unit*nefariusControlled=nullptr;bool NefariusControlledMember(Player*,Unit*u){return u&&u==nefariusControlled;}
unsigned buruCalls=0;bool BuruOffenseAllowed(PlayerbotAI*,const SpellEntry*,Unit*){++buruCalls;return false;}
bool CthunOffenseAllowed(PlayerbotAI*,const SpellEntry*,Unit*){return true;}
bool KelthuzadDormantAdd(Player*,Unit*){return false;} // Separate actual-method phase-one regression.
__BODY__
int main(){PlayerbotAI brain;SpellEntry hit{1,0,true,false},area{2,0,true,true},heal{},taunt{},flurry{13877},sweeping{12328};
 SpellEntry tick{77,0,true,false},channel{78,0,false,true},healChannel{79};
 channel.EffectTriggerSpell[0]=77;healChannel.EffectTriggerSpell[0]=79;sServerFacade.spells={{77,&tick},{79,&healChannel}};
 assert(RaidDamageSpell(&channel)&&!RaidDamageSpell(&healChannel)&&!RaidDamageSpell(&taunt));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&channel,&brain.boss));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&flurry,&brain.bot));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&sweeping,&brain.bot));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&heal,&brain.worshipper));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&taunt,&brain.worshipper));
 brain.bot.tank=true;assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));
 brain.worshipper.hp=50;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));brain.worshipper.hp=100;
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.bot.tank=false;
 brain.sacrifice=&brain.worshipper;assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.worshipper));brain.sacrifice=nullptr;
 brain.worshipper.charmed=true;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.worshipper.charmed=false;
 brain.worshipper.distance=100;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.worshipper.distance=10;
 brain.boss.entry=16061;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.student));
 brain.ready=false;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));brain.ready=true;
 assert(!ai::ClassicRaidOffenseAllowed(&brain,nullptr,&brain.student));

 brain.boss.entry=16011;SpellEntry thorns{9910},shield{10901};thorns.aura[0]=shield.aura[0]=true;
 thorns.EffectApplyAuraName[0]=SPELL_AURA_DAMAGE_SHIELD;shield.EffectApplyAuraName[0]=69;
#ifdef MANGOSBOT_ZERO
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&thorns,&brain.bot));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&flurry,&brain.bot));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&sweeping,&brain.bot));
#else
 assert(ai::ClassicRaidOffenseAllowed(&brain,&thorns,&brain.bot));
#endif
 assert(ai::ClassicRaidOffenseAllowed(&brain,&shield,&brain.bot));
 brain.boss.entry=16011;brain.context.value.list={3};brain.bot.distance=8;
 assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
 brain.bot.distance=20;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.bot.distance=8;
 SpellEntry cleave{20569,0,true,false};cleave.EffectChainTarget[0]=2; // Native Classic spell_template: not an area target.
#ifdef MANGOSBOT_ZERO
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&cleave,&brain.boss));
 brain.context.value.list.clear();assert(ai::ClassicRaidOffenseAllowed(&brain,&cleave,&brain.boss));brain.context.value.list={3};
#endif
 brain.real=true;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.real=false;
 Player tank;tank.tank=true;tank.distance=5;brain.roster.push_back(&tank); // actual tank would steal native buff
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.roster.pop_back();
 brain.bot.buff=true;assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.spore));brain.bot.buff=false;
 brain.bot.map=409;assert(ai::ClassicRaidOffenseAllowed(&brain,&area,&brain.boss));
 brain.bot.map=469;nefariusControlled=&brain.student;
#ifdef MANGOSBOT_ZERO
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.student));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,nullptr,&brain.student));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&channel,&brain.student));
#else
 assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.student));
#endif
 assert(ai::ClassicRaidOffenseAllowed(&brain,&heal,&brain.student));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&taunt,&brain.student));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.boss));
 nefariusControlled=nullptr;assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.student));
 brain.bot.map=509;
#ifdef MANGOSBOT_ZERO
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.boss)&&buruCalls==1);
#else
 assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.boss)&&buruCalls==0);
#endif
 // ZG native serpent run: Fear and Death Coil displace NPCs into fresh packs.
 brain.bot.map=309;SpellEntry fear{6215},horror{17926},stun{1833},sheep{12826};
 fear.aura[0]=horror.aura[1]=stun.aura[0]=sheep.aura[0]=true;
 fear.EffectApplyAuraName[0]=horror.EffectApplyAuraName[1]=SPELL_AURA_MOD_FEAR;
 stun.EffectApplyAuraName[0]=12;sheep.EffectApplyAuraName[0]=56;
#ifdef MANGOSBOT_ZERO
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&fear,&brain.worshipper));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&horror,&brain.worshipper));
 assert(!ai::ClassicRaidOffenseAllowed(&brain,&fear,nullptr));
 brain.worshipper.player=true;assert(ai::ClassicRaidOffenseAllowed(&brain,&fear,&brain.worshipper));brain.worshipper.player=false;
 brain.ready=false;assert(ai::ClassicRaidOffenseAllowed(&brain,&fear,&brain.worshipper));brain.ready=true;
#else
 assert(ai::ClassicRaidOffenseAllowed(&brain,&fear,&brain.worshipper));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&horror,&brain.worshipper));
#endif
 assert(ai::ClassicRaidOffenseAllowed(&brain,&hit,&brain.worshipper));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&stun,&brain.worshipper));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&sheep,&brain.worshipper));
 assert(ai::ClassicRaidOffenseAllowed(&brain,&heal,&brain.worshipper));
 for(unsigned map:{0u,30u,489u,529u,229u,409u}){
  brain.bot.map=map;assert(ai::ClassicRaidOffenseAllowed(&brain,&fear,&brain.worshipper));
 }
 std::cout<<"PASS actual damaging AoE/direct/cleave admission reserves Classic control actors, preserves heals/taunts/tanks and MC/era guards\n";
}
'''.replace('__BODY__',block(s,'    bool RaidDamageSpell(')+'\n'+block(s,'    std::vector<Player*> SporeRecipients(')+'\n'+block(s,'bool ai::ClassicRaidOffenseAllowed('))
# Healing-self targets use the same Unit interface in the server.
code=code.replace('struct Player{','struct Player:Unit{')
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-offense-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
