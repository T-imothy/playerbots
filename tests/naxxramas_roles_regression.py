"""Execute the actual Naxx role planner/support/election in all native era modes."""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/NaxxramasRoleActions.cpp').read_text()
source = source[source.index('using namespace ai;'):]
fixture = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>
#include "__GEOMETRY__"
#include "__POLICY__"
#include "__NATIVE__"
using uint32=unsigned;
constexpr float M_PI_F=3.14159265f;
constexpr unsigned POWER_MANA=0,UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1,GO_STATE_READY=0;
constexpr unsigned CLASS_PRIEST=5,CLASS_DRUID=11,CLASS_PALADIN=2,CLASS_SHAMAN=7,CLASS_MAGE=8;
constexpr unsigned MECHANIC_POLYMORPH=17,MAX_EFFECT_INDEX=3;
enum CurrentSpellTypes{CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL};
enum class BotState{BOT_STATE_COMBAT};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}bool IsEmpty()const{return !id;}void Clear(){id=0;}
 bool operator<(ObjectGuid b)const{return id<b.id;}bool operator==(ObjectGuid b)const{return id==b.id;}bool operator!=(ObjectGuid b)const{return id!=b.id;}};
struct SpellEntry{unsigned Id=0;bool heal=true;unsigned Mechanic=0,EffectMechanic[3]={};};
struct Unit;
constexpr unsigned SPELL_STATE_FINISHED=9;
struct Targets{Unit*target=nullptr;Unit*getUnitTarget()const{return target;}};
struct Spell{const SpellEntry*m_spellInfo=nullptr;Targets m_targets;unsigned state=0;unsigned getState()const{return state;}static unsigned CalculatePowerCost(const SpellEntry*,void*){return 100;}};
struct Unit;struct Player;struct GameObject;struct PlayerbotAI;
struct Reference{Unit*target=nullptr;Unit*getTarget(){return target;}};
struct Threat{std::list<Reference*>list;std::map<Unit*,float>amount;auto&getThreatList(){return list;}float getThreat(Unit*u){return amount[u];}};
struct Instance{virtual ~Instance()=default;};
struct ScriptedInstance:Instance{GameObject*gate=nullptr;GameObject*GetSingleGameObjectFromStorage(unsigned){return gate;}};
struct Map{bool regular=true;Instance*instance=nullptr;bool IsRegularDifficulty(){return regular;}Instance*GetInstanceData(){return instance;}};
struct Unit{virtual ~Unit()=default;ObjectGuid guid;unsigned entry=0,instance=1;bool world=true,alive=true,charmed=false,combat=true,valid=true,cc=false;float x=0,y=0,z=0,hp=100;Unit*victim=nullptr;Map*map=nullptr;Threat threat;
 ObjectGuid charmer;std::set<unsigned>auras;bool HasAura(unsigned id){return auras.count(id);}bool HasCharmer(ObjectGuid g){return charmed&&charmer==g;}
 virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}float GetHealthPercent(){return hp;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return 0;}float GetCombatReach(){return 2;}
 bool IsInMap(Unit*u){return u&&map==u->map&&instance==u->instance;}float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}bool CanReachWithMeleeAttack(Unit*u){return GetDistance(u)<5;}
 Threat&getThreatManager(){return threat;}Map*GetMap(){return map;}};
struct GameObject:Unit{unsigned state=0;unsigned GetGoState(){return state;}};
struct GroupReference{Player*player=nullptr;GroupReference*following=nullptr;Player*getSource(){return player;}GroupReference*next(){return following;}};
struct Group{std::list<GroupReference>refs;void Add(Player*p){if(!refs.empty()){refs.push_back({p});auto it=refs.end();--it;auto before=it;--before;before->following=&*it;}else refs.push_back({p});}GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs.front();}};
struct Player:Unit{bool tank=false,healer=false,transfer=false,stunned=false,ready=true;unsigned mapid=533,cls=5,mana=1000;Group*group=nullptr;PlayerbotAI*ai=nullptr;Spell*cast=nullptr;
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return transfer;}unsigned GetMapId(){return mapid;}unsigned GetInstanceId(){return instance;}Group*GetGroup(){return group;}
 PlayerbotAI*GetPlayerbotAI(){return ai;}unsigned getClass(){return cls;}Spell*GetCurrentSpell(CurrentSpellTypes t){return t==CURRENT_GENERIC_SPELL?cast:nullptr;}
 bool hasUnitState(unsigned){return stunned;}bool HasSpell(unsigned id){return id!=0;}bool IsSpellReady(const SpellEntry&){return ready;}unsigned GetPower(unsigned){return mana;}};
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<std::list<ObjectGuid>>nearby;Value<unsigned>spell;
 template<class T>Value<T>*GetValue(const char*,const std::string&){if constexpr(std::is_same_v<T,unsigned>)return &spell;else return &nearby;}};
struct PlayerbotAI{Player*bot;Context context;std::map<unsigned,Unit*>units;bool real=false,dungeon=true,path=true,canCast=true;unsigned validations=0;
 PlayerbotAI(Player*p):bot(p){p->ai=this;context.spell.value=100;}Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool HasStrategy(const char*,BotState){return dungeon;}
 bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->healer;}Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid g){return units[g.id];}
 bool CanCastSpell(const char*,Unit*t,unsigned){return canCast&&t&&bot->ready&&bot->GetDistance(t)<40;}static bool IsHealSpell(const SpellEntry*s){assert(s);return s->heal;}};
struct Server{std::map<unsigned,SpellEntry>spells;const SpellEntry*LookupSpellInfo(unsigned id){return spells.count(id)?&spells[id]:nullptr;}}sServerFacade;
struct Config{float sightDistance=100;}sPlayerbotAIConfig;
namespace ai{
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};
struct ClassicRaidPlan{ObjectGuid boss,target;EncounterPosition position;bool emergency=false,holdDamage=false;};
struct Action{virtual ~Action()=default;};struct CastSpellAction:Action{unsigned id=100;unsigned GetDecisionSpellId(){return id;}};
bool NaxxramasEncounterEngaged(Player*p,Unit*u){return u&&p->IsInMap(u)&&u->world&&u->alive&&u->combat&&!u->charmed;}
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&){++a->validations;return a->path;}
float NativeEncounterSpellRadius(unsigned){return 10;}
struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*,float,bool,bool){return u->valid;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*,Player*){return false;}};
bool NaxxramasRolePlan(PlayerbotAI*,ClassicRaidPlan&);bool NaxxramasRoleSupport(PlayerbotAI*,std::string&,Unit*&);float NaxxramasRoleMultiplier(PlayerbotAI*,Action*);
}
__SOURCE__
int main(){
 Map map;ScriptedInstance instance;map.instance=&instance;Group group;
 Player bot,t1,t2,t3,t4,h1,h2;Player*players[]={&bot,&t1,&t2,&t3,&t4,&h1,&h2};unsigned id=1;
 for(auto*p:players){p->guid=id++;p->map=&map;p->group=&group;group.Add(p);}
 t1.tank=t2.tank=t3.tank=t4.tank=true;h1.healer=h2.healer=true;PlayerbotAI ai(&bot),heal1(&h1),heal2(&h2);
 Unit boss;boss.guid=50;boss.map=&map;boss.entry=16028;boss.victim=&t1;
 auto encounter=[&](std::initializer_list<Unit*> units){ai.units.clear();ai.context.nearby.value.clear();for(auto*u:units){u->map=&map;ai.units[u->guid.id]=u;ai.context.nearby.value.push_back(u->guid);}heal1.units=heal2.units=ai.units;heal1.context.nearby=heal2.context.nearby=ai.context.nearby;};
 Reference r1{&t1},r2{&t2},r3{&t3},r4{&t4};boss.threat.list={&r1,&r2,&r3,&r4};for(auto*t:{&t1,&t2,&t3,&t4})boss.threat.amount[t]=100;
 encounter({&boss});ClassicRaidPlan plan;
 assert(!NaxxramasRolePlan(&ai,plan)); // all native slots prepared, ordinary ranged formation remains.
 t2.alive=t3.alive=t4.alive=false;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage);t2.alive=t3.alive=t4.alive=true;
 boss.threat.amount[&t2]=0;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage);boss.threat.amount[&t2]=100;
 r2.target=&bot;boss.threat.amount[&bot]=150;assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage&&plan.target.IsEmpty());r2.target=&t2;
 t2.x=20;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage);t2.x=0;
#ifdef MANGOSBOT_TWO
 t3.x=20;plan={};assert(!NaxxramasRolePlan(&ai,plan));map.regular=false;assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage);map.regular=true;t3.x=0;
#else
 t4.x=20;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage);t4.x=0;
#endif
 bot.tank=true;bot.x=20;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.position.active&&!plan.holdDamage);ai.path=false;plan={};assert(NaxxramasRolePlan(&ai,plan)&&!plan.position.active);ai.path=true;bot.tank=false;bot.x=0;
 boss.entry=16060;boss.valid=false;GameObject gate;gate.map=&map;gate.y=0;instance.gate=&gate;bot.y=-5;
 Unit living,spectral;living.guid=51;living.entry=16124;living.y=-10;spectral.guid=52;spectral.entry=16127;spectral.y=10;spectral.hp=1;
 encounter({&boss,&living,&spectral});plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.target==living.guid&&!plan.holdDamage);
 living.alive=false;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.holdDamage&&plan.target.IsEmpty());living.alive=true;
 bot.y=5;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.target==spectral.guid);gate.state=1;plan={};assert(!NaxxramasRolePlan(&ai,plan));bot.y=0;
 boss.entry=15953;boss.valid=true;bot.tank=true;Unit worshipper;worshipper.guid=53;worshipper.entry=16506;encounter({&boss,&worshipper});plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.target==worshipper.guid);worshipper.cc=true;plan={};assert(!NaxxramasRolePlan(&ai,plan));worshipper.cc=false;
 boss.entry=15990;worshipper.entry=16441;plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.target==worshipper.guid);bot.tank=false;
 Unit gargoyle;gargoyle.guid=54;gargoyle.entry=16168;gargoyle.hp=29;encounter({&gargoyle});plan={};assert(NaxxramasRolePlan(&ai,plan)&&plan.target==gargoyle.guid);gargoyle.combat=false;plan={};assert(!NaxxramasRolePlan(&ai,plan));gargoyle.combat=true;gargoyle.hp=31;assert(!NaxxramasRolePlan(&ai,plan));
 boss.entry=16011;encounter({&boss});sServerFacade.spells[100]={100,true};t1.hp=50;std::string spell;Unit*target=nullptr;CastSpellAction action;
#ifndef MANGOSBOT_TWO
 assert(NaxxramasRoleSupport(&heal1,spell,target)&&spell=="greater heal"&&target==&t1);assert(!NaxxramasRoleSupport(&heal2,spell,target));
 assert(NaxxramasRoleMultiplier(&heal1,&action)==1&&NaxxramasRoleMultiplier(&heal2,&action)==0);
 h1.ready=false;assert(NaxxramasRoleSupport(&heal2,spell,target));h1.ready=true;
 Spell flight{&sServerFacade.spells[100],{&t1}};h2.cast=&flight;assert(!NaxxramasRoleSupport(&heal1,spell,target));flight.state=SPELL_STATE_FINISHED;assert(NaxxramasRoleSupport(&heal1,spell,target));h2.cast=nullptr;
 flight.state=0;h2.cast=&flight;h2.ai=nullptr;assert(!NaxxramasRoleSupport(&heal1,spell,target));h2.ai=&heal2;heal2.real=true;assert(!NaxxramasRoleSupport(&heal1,spell,target));heal2.real=false;h2.cast=nullptr;
 h1.mana=0;assert(NaxxramasRoleSupport(&heal2,spell,target));h1.mana=1000;
 bot.hp=1;bot.x=100;assert(NaxxramasRoleSupport(&heal1,spell,target)&&target==&t1);bot.hp=100;bot.x=0;
 t1.hp=100;assert(!NaxxramasRoleSupport(&heal1,spell,target));action.id=0;assert(NaxxramasRoleMultiplier(&heal1,&action)==1);
#else
 assert(!NaxxramasRoleSupport(&heal1,spell,target)&&NaxxramasRoleMultiplier(&heal2,&action)==1);
#endif
 boss.entry=15990;bot.cls=h1.cls=CLASS_MAGE;h1.healer=false;t1.charmed=t2.charmed=true;t1.charmer=t2.charmer=boss.guid;t1.auras.insert(28410);t2.auras.insert(28410);
 assert(NaxxramasRoleSupport(&ai,spell,target)&&spell=="polymorph"&&target==&t1);assert(NaxxramasRoleSupport(&heal1,spell,target)&&target==&t2);
 t1.cc=true;assert(NaxxramasRoleSupport(&ai,spell,target)&&target==&t2);t1.cc=false;
 SpellEntry poly{118,false,MECHANIC_POLYMORPH};Spell sheep{&poly,{&t1}};bot.cast=&sheep;assert(NaxxramasRoleSupport(&heal1,spell,target)&&target==&t2);bot.cast=nullptr;
 t1.charmer=999;t2.charmer=999;assert(!NaxxramasRoleSupport(&ai,spell,target));t1.charmer=t2.charmer=boss.guid;boss.combat=false;assert(!NaxxramasRoleSupport(&ai,spell,target));boss.combat=true;
 boss.entry=16028;bot.transfer=true;plan={};assert(!NaxxramasRolePlan(&ai,plan));bot.transfer=false;ai.dungeon=false;assert(!NaxxramasRolePlan(&ai,plan));ai.dungeon=true;bot.mapid=409;assert(!NaxxramasRolePlan(&ai,plan));
 std::cout<<"PASS actual Naxx role plan, native hateful slots, gate sides, add duties, healing election and lifecycle\n";
}
'''
for marker, path in [('__GEOMETRY__','playerbot/strategy/EncounterGeometry.h'),('__POLICY__','playerbot/strategy/ClassicRaidPolicy.h'),('__NATIVE__','playerbot/strategy/NaxxramasNativePolicy.h')]:
    fixture=fixture.replace(marker,(root/path).as_posix())
fixture=fixture.replace('__SOURCE__',source)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='naxx-roles-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(fixture)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
