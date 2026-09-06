"""Integrate real mana values with recovery triggers and group readiness."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]/'playerbot/strategy'
stats=(root/'values/StatsValues.cpp').read_text()
triggers=(root/'triggers/GenericTriggers.cpp').read_text()
group=(root/'values/GroupValues.cpp').read_text()
methods='\n'.join(block(stats,key) for key in ('uint8 ManaValue::Calculate(', 'bool HasManaValue::Calculate('))
methods+='\n'+'\n'.join(block(triggers,f'bool {name}::IsActive(') for name in ('NoManaTrigger','LowManaTrigger','MediumManaTrigger','HighManaTrigger','AlmostFullManaTrigger'))
methods+='\n'+block(group,'bool GroupReadyValue::Calculate(')
checker=block((root/'actions/ReadyCheckAction.cpp').read_text(),'class ManaChecker')+';'
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <type_traits>
using uint8=uint8_t;using uint32=uint32_t;using uint64=uint64_t;using ObjectGuid=unsigned;
enum{POWER_MANA};enum class BotState{BOT_STATE_NON_COMBAT};
struct PlayerbotAI;
struct Unit {
 uint32 current=0,maximum=100;bool alive=true,combat=false;float health=100,distance=0;
 uint32 GetPower(int){return current;}uint32 GetMaxPower(int){return maximum;}
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 float GetHealthPercent(){return health;}
 PlayerbotAI* GetPlayerbotAI(){return nullptr;}
};
using Player=Unit;
struct ManaValue{Unit* target;Unit* GetTarget(){return target;}uint8 Calculate();};
struct HasManaValue{Unit* target;Unit* GetTarget(){return target;}bool Calculate();};
struct AiObjectContext{};
struct PlayerbotAI {
 Player* bot;std::list<ObjectGuid> members;
 Player* GetGroupMaster(){return bot;}bool HasStrategy(const char*,BotState){return true;}
 template<class T>T value(const char* key){
   if constexpr(std::is_same_v<T,bool>)return HasManaValue{bot}.Calculate();
   else return ManaValue{bot}.Calculate();
 }
};
#define AI_VALUE2(type,name,qualifier) ai->value<type>(name)
#define AI_VALUE(type,name) ai->members
#define AI_VALUE_LAZY(type,name) 0
struct Trigger{PlayerbotAI* ai;};
struct NoManaTrigger:Trigger{bool IsActive();};
struct LowManaTrigger:Trigger{bool IsActive();};
struct MediumManaTrigger:Trigger{bool IsActive();};
struct HighManaTrigger:Trigger{bool IsActive();};
struct AlmostFullManaTrigger:Trigger{bool IsActive();};
struct GroupReadyValue{PlayerbotAI* ai;Player* bot;bool Calculate();};
struct WorldPosition{WorldPosition(Player*){}bool isOverworld(){return false;}};
struct{uint32 lowMana=20,mediumMana=40,mediumHealth=75,almostFullHealth=95;float sightDistance=100;}sPlayerbotAIConfig;
struct{float GetDistance2d(Player* member,Player*){return member->distance;}}sServerFacade;
struct{std::map<unsigned,Player*> players;Player* GetPlayer(unsigned id){return players[id];}}sObjectMgr;
struct ReadyChecker{virtual bool Check(Player*,PlayerbotAI*,AiObjectContext*)=0;virtual std::string GetName()=0;};
__CHECKER__
__METHODS__
int main(){
 Player caster,member;PlayerbotAI ai{&caster,{2}};sObjectMgr.players[2]=&member;
 NoManaTrigger empty{&ai};LowManaTrigger low{&ai};MediumManaTrigger medium{&ai};
 HighManaTrigger high{&ai};AlmostFullManaTrigger full{&ai};ManaChecker ready;
 GroupReadyValue group{&ai,&caster};
 assert(empty.IsActive() && low.IsActive() && medium.IsActive());
 assert(high.IsActive() && !full.IsActive());assert(!ready.Check(nullptr,&ai,nullptr));
 assert(!group.Calculate()); // An empty healer mana bar must delay an idle group.
 caster.current=19;assert(!empty.IsActive() && low.IsActive());
 caster.current=20;assert(!low.IsActive());caster.current=40;assert(!medium.IsActive());
 caster.current=50;assert(ready.Check(nullptr,&ai,nullptr)); // Uses mana threshold, not health threshold.
 caster.current=100;assert(full.IsActive() && !high.IsActive());
 member.current=39;assert(!group.Calculate());member.current=40;assert(group.Calculate());
 member.current=0;member.combat=true;assert(group.Calculate());member.combat=false;
 member.maximum=0;assert(group.Calculate()); // Warriors/rogues do not need mana recovery.
 caster.maximum=0;caster.current=0;assert(!empty.IsActive()&&!low.IsActive()&&!medium.IsActive());
 assert(ready.Check(nullptr,&ai,nullptr));assert(ManaValue{&caster}.Calculate()==100);
 caster.maximum=100;caster.current=200;assert(ManaValue{&caster}.Calculate()==100);
 assert(ManaValue{nullptr}.Calculate()==100 && !HasManaValue{nullptr}.Calculate());
 member.maximum=100;member.current=0;member.distance=200;assert(group.Calculate());
 member.distance=0;member.alive=false;assert(!group.Calculate());
 std::cout<<"PASS: empty-mana recovery/readiness, mana thresholds, resource-less classes and bounded percentages\n";
}
'''.replace('__CHECKER__',checker).replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-mana-state-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
