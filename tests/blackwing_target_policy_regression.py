"""Compile actual BWL phase admission and add-priority functions with fixtures.
This requires a compiler; the source-only audit does not run this script.
"""
from pathlib import Path
import tempfile
import subprocess
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
methods=block(source,'unsigned BwlAddPriority(')+'\n'+block(source,'bool ai::IsProtectedBlackwingTarget(')
code=r'''
#include <cassert>
#include <set>
#include <iostream>
using uint32=unsigned;
constexpr unsigned SPECIAL=4;
struct InstanceData{unsigned state=1;unsigned GetData(unsigned key){assert(key==0);return state;}};
struct Map{InstanceData* data=nullptr;InstanceData* GetInstanceData(){return data;}};
struct PlayerbotAI{bool real=false;bool IsRealPlayer(){return real;}};
struct Unit{bool world=true;unsigned entry=0;Map* map=nullptr;std::set<unsigned> auras;
 bool IsInWorld(){return world;}unsigned GetEntry(){return entry;}bool HasAura(unsigned id){return auras.count(id);}};
struct Player:Unit{bool alive=true;unsigned mapId=469;PlayerbotAI* ai=nullptr;
 bool IsAlive(){return alive;}unsigned GetMapId(){return mapId;}Map* GetMap(){return map;}
 bool IsInMap(Unit* unit){return unit&&map==unit->map;}PlayerbotAI* GetPlayerbotAI(){return ai;}};
namespace ai{bool IsProtectedBlackwingTarget(Player*,Unit*);}
using namespace ai;
__METHODS__
int main(){
 InstanceData instance;Map map{&instance},other;PlayerbotAI ai;Player bot;bot.map=&map;bot.ai=&ai;
 Unit boss;boss.map=&map;boss.entry=12435;
 assert(IsProtectedBlackwingTarget(&bot,&boss));
 instance.state=SPECIAL;assert(!IsProtectedBlackwingTarget(&bot,&boss));
 instance.state=0;assert(IsProtectedBlackwingTarget(&bot,&boss));
 ai.real=true;assert(!IsProtectedBlackwingTarget(&bot,&boss));ai.real=false;
 bot.mapId=409;assert(!IsProtectedBlackwingTarget(&bot,&boss));bot.mapId=469;
 boss.map=&other;assert(!IsProtectedBlackwingTarget(&bot,&boss));boss.map=&map;
 boss.world=false;assert(!IsProtectedBlackwingTarget(&bot,&boss));boss.world=true;
 map.data=nullptr;assert(!IsProtectedBlackwingTarget(&bot,&boss));map.data=&instance;
 assert(!IsProtectedBlackwingTarget(nullptr,&boss)&&!IsProtectedBlackwingTarget(&bot,nullptr));
 boss.entry=10162;assert(!IsProtectedBlackwingTarget(&bot,&boss));boss.auras.insert(22663);
 assert(IsProtectedBlackwingTarget(&bot,&boss));boss.entry=11583;assert(!IsProtectedBlackwingTarget(&bot,&boss));
 assert(BwlAddPriority(12420)>BwlAddPriority(12416));
 assert(BwlAddPriority(14605)>BwlAddPriority(14261));
 assert(!BwlAddPriority(12435)&&!BwlAddPriority(11583)&&!BwlAddPriority(1));
 std::cout<<"PASS BWL native-phase target admission and add priority policy\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-bwl-target-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)

# Compile the entire production target selector, including the existing tank
# branch, rather than testing a duplicate rank table or an extracted DPS tail.
roles='\n'.join(block(source,marker) for marker in (
    'bool BwlReady(', 'bool BwlMember(', 'bool BwlGroupEngaged(',
    'unsigned BwlAddPriority(', 'Unit* BlackwingLairPriorityTargetAction::GetTarget('))
role_code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <type_traits>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr int CLASS_HUNTER=3;
struct PlayerbotAI;struct Group;
struct Threat{unsigned guid;unsigned getUnitGuid()const{return guid;}};
struct ThreatManager{std::vector<Threat*> refs;auto& getThreatList(){return refs;}};
struct Unit{virtual ~Unit()=default;unsigned guid=0,entry=0,map=469,instance=1;bool world=true,alive=true,combat=true,charm=false,friendly=false,valid=true,cc=false,hardCC=false;Unit* victim=nullptr;Unit* master=nullptr;Unit* charmer=nullptr;std::list<Unit*> attackers;ThreatManager threat;
 virtual bool IsPlayer()const{return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}Unit* GetVictim(){return victim;}Unit* GetMaster(){return master;}Unit* GetCharmer(){return charmer;}auto& getAttackers(){return attackers;}auto& getThreatManager(){return threat;}
 bool IsInMap(Unit* u){return u&&u->map==map&&u->instance==instance;}float GetDistance(Unit*){return 10;}};
struct Player:Unit{bool tank=false,healer=false,ranged=false,transfer=false;int cls=1;Group* group=nullptr;PlayerbotAI* brain=nullptr;bool IsPlayer()const override{return true;}Group* GetGroup(){return group;}bool IsBeingTeleported(){return transfer;}PlayerbotAI* GetPlayerbotAI(){return brain;}unsigned GetMapId(){return map;}int getClass(){return cls;}};
struct GroupReference{Player* p;GroupReference* n=nullptr;Player* getSource(){return p;}GroupReference* next(){return n;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
std::list<unsigned> targets;std::map<unsigned,Unit*> units;
struct PlayerbotAI{Player* bot;bool real=false;std::map<std::string,unsigned> guids;
 Player* GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p&&p->tank;}bool IsHeal(Player*p){return p&&p->healer;}bool IsRanged(Player*p){return p&&p->ranged;}Unit* GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}
 template<class T>T value(const char* name){if constexpr(std::is_same_v<T,std::list<unsigned>>)return targets;else return guids[name];}};
struct Facade{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*,float,bool,bool){return u->valid;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
struct BlackwingLairPriorityTargetAction{PlayerbotAI* ai;Player* bot;Unit* GetTarget();};
bool RazorgoreEggPhase(PlayerbotAI*){return false;}Unit* RazorgoreCreature(Unit*,unsigned){return nullptr;}bool IsProtectedBlackwingTarget(Player*,Unit*){return false;}
#define AI_VALUE(type,name) ai->value<type>(name)
__ROLES__
int main(){
 Player melee,otherMelee,ranged,otherRanged,tank,healer,outsider;
 melee.guid=1;otherMelee.guid=2;ranged.guid=3;otherRanged.guid=4;tank.guid=5;healer.guid=6;outsider.guid=7;
 ranged.ranged=otherRanged.ranged=true;tank.tank=true;healer.healer=true;
 PlayerbotAI ma{&melee},mb{&otherMelee},ra{&ranged},rb{&otherRanged},ta{&tank},ha{&healer};melee.brain=&ma;otherMelee.brain=&mb;ranged.brain=&ra;otherRanged.brain=&rb;tank.brain=&ta;healer.brain=&ha;
 GroupReference r6{&healer},r5{&tank,&r6},r4{&otherRanged,&r5},r3{&ranged,&r4},r2{&otherMelee,&r3},r1{&melee,&r2};Group group{&r1},foreign;for(auto p:{&melee,&otherMelee,&ranged,&otherRanged,&tank,&healer})p->group=&group;outsider.group=&foreign;
 Unit warlock,warlock2,tech,tech2,hatcher,boss;warlock.guid=10;warlock.entry=12459;warlock2.guid=11;warlock2.entry=12459;tech.guid=20;tech.entry=13996;tech2.guid=21;tech2.entry=13996;hatcher.guid=30;hatcher.entry=12468;boss.guid=40;boss.entry=12017;
 for(auto u:{&warlock,&warlock2,&tech,&tech2,&hatcher,&boss}){units[u->guid]=u;u->victim=&tank;}for(auto p:{&melee,&otherMelee,&ranged,&otherRanged,&tank,&healer,&outsider})units[p->guid]=p;
 auto choose=[](PlayerbotAI*a){BlackwingLairPriorityTargetAction action{a,a->bot};return action.GetTarget();};
 targets={21,11,30,20,10};ma.guids["current target"]=11;ra.guids["current target"]=21;
 assert(choose(&ma)==&warlock&&choose(&mb)==&warlock);assert(choose(&ra)==&tech&&choose(&rb)==&tech);assert(!choose(&ha));
 targets.reverse();assert(choose(&ma)==&warlock&&choose(&ra)==&tech); // same role agrees regardless distance/current/list order
 warlock.cc=true;assert(choose(&ma)==&warlock2);warlock2.hardCC=true;assert(choose(&ma)==&hatcher);warlock.cc=warlock2.hardCC=false;
 tech.alive=false;assert(choose(&ra)==&tech2);tech2.alive=false;assert(choose(&ra)==&hatcher);tech.alive=tech2.alive=true;
 ma.guids["attack target"]=30;assert(!choose(&ma));ma.guids["attack target"]=0;ra.guids["rti target"]=10;assert(!choose(&ra));ra.guids["rti target"]=0;
 // An unpulled or foreign-fight pack never becomes a role target, even beside a boss.
 targets={40,10,20};warlock.combat=tech.combat=false;assert(!choose(&ma)&&!choose(&ra));warlock.combat=tech.combat=true;warlock.victim=tech.victim=&outsider;assert(!choose(&ma)&&!choose(&ra));
 Unit pet;pet.master=&tank;warlock.victim=&pet;assert(choose(&ma)==&warlock);warlock.victim=nullptr;Threat threat{5};warlock.threat.refs={&threat};assert(choose(&ma)==&warlock);
 tank.instance=2;assert(!choose(&ma));tank.instance=1;warlock.threat.refs.clear();warlock.victim=&tank;tech.victim=&tank;
 // The full selector still returns the native boss holder and normal tank assignment.
 tank.victim=&boss;assert(choose(&ta)==&boss);boss.victim=&melee;tank.victim=nullptr;targets={10,20};assert(choose(&ta)==&warlock);
 melee.map=409;assert(!choose(&ma));melee.map=469;melee.transfer=true;assert(!choose(&ma));melee.transfer=false;melee.charm=true;assert(!choose(&ma));melee.charm=false;ma.real=true;assert(!choose(&ma));
 std::cout<<"PASS: whole BWL selector role split, deterministic focus, manual override, real group/pet/threat, CC, future packs and preserved tanks\n";
}
'''.replace('__ROLES__',roles)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-bwl-role-target-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(role_code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
