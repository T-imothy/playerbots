"""Run the actual Mechanar decision against controlled native-interface fixtures."""
from pathlib import Path
import subprocess
import tempfile
import sys
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/MechanarPositionValue.cpp').read_text()
before='--before' in sys.argv
if before:
    source=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show','88f43c09:playerbot/strategy/values/MechanarPositionValue.cpp'],text=True)
helper='' if before else block(source,'bool ai::MechanarThreats(')
method=block(source, 'EncounterPosition MechanarPositionValue::Calculate(')
execute='' if before else block((root/'playerbot/strategy/actions/MechanarDungeonActions.cpp').read_text(),'bool MechanarPositionAction::Execute(')
code=r'''
#include <cassert>
#include <set>
#include <map>
#include <list>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;
struct Map {bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Unit {unsigned entry=0,guid=1,phase=1;bool world=true,alive=true,combat=true;Map* map=nullptr;
 float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;}Map* GetMap(){return map;}unsigned GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}};
struct Group;
struct Player:Unit {bool charmed=false,teleport=false;unsigned mapId=554,instance=1;Group* group=nullptr;
 bool IsInMap(Unit* unit){return map==unit->map&&phase==unit->phase;}
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}};
struct GroupReference {Player* source=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct PlayerbotAI {Player* bot=nullptr;Player* GetBot(){return bot;}bool CanMove(){return true;}std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;bool validPath=true,ranged=false,healer=false;unsigned checked=0;float adjustedY=0;
 void StopMoving(){}
 PlayerbotAI* GetAiObjectContext(){return this;}template<class T>PlayerbotAI* GetValue(const char*){return this;}std::list<ObjectGuid>& Get(){return attackers;}
 bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return healer;}
 Unit* GetUnit(unsigned guid){auto it=units.find(guid);return it==units.end()?nullptr:it->second;}};
std::vector<Unit*> nativeCharges;
namespace MaNGOS {
 struct AllCreaturesOfEntryInRangeCheck {unsigned entry;AllCreaturesOfEntryInRangeCheck(Player*,unsigned e,float):entry(e){}};
 template<class T>struct UnitListSearcher {std::list<Unit*>& result;unsigned entry;UnitListSearcher(std::list<Unit*>& r,T& t):result(r),entry(t.entry){}};
}
namespace Cell {template<class T>void VisitAllObjects(Player*,T& search,float){for(auto* charge:nativeCharges)if(charge->entry==search.entry)search.result.push_back(charge);}}
namespace ai {
 struct EncounterPosition {bool active=false;unsigned map=0,instance=0,boss=0;encounter::Point destination;};
 std::map<unsigned,float> radii{{39088,10.0f},{39091,10.0f},{35151,0.0f},{37670,15.0f},
     {35281,4.0f},{35283,10.0f},{36022,8.0f},{15453,10.0f}}; // controlled radii, not replacement spell data
 float NativeEncounterSpellRadius(unsigned id){return radii[id];}
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition& plan){++ai->checked;plan.destination.y+=ai->adjustedY;return ai->validPath;}
 bool MechanarThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 struct MechanarPositionValue {Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct Event{};
 struct MechanarPositionAction {Player* bot;PlayerbotAI* ai;static EncounterPosition cached;unsigned moves=0;
  static bool GetPlan(PlayerbotAI*,EncounterPosition& plan){plan=cached;return plan.active;}
  bool IsReaction(){return false;}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++moves;return true;}bool Execute(Event&);
  void SetDuration(unsigned){}
 };
 EncounterPosition MechanarPositionAction::cached;
}
using namespace ai;
#define AI_VALUE(type,name) ai->attackers
__HELPER__
__METHOD__
__EXECUTE__
int main(){
 Player bot,other;Map map,otherMap;bot.map=other.map=&map;
 Unit boss;boss.entry=19219;boss.map=&map;PlayerbotAI ai;ai.bot=&bot;ai.attackers={1};ai.units[1]=&boss;
 Group group;GroupReference member{&other};group.first=&member;bot.group=&group;
 MechanarPositionValue value{&bot,&ai};
 bot.auras={39088};other.auras={39091};other.x=1;
#ifdef MANGOSBOT_ZERO
 assert(!value.Calculate().active && ai.checked==0);
#else
 auto plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{other.x,other.y,other.z})>=12);
 other.auras={39088};assert(!value.Calculate().active);other.auras={39091};
 other.alive=false;assert(!value.Calculate().active);other.alive=true;
 other.map=&otherMap;assert(!value.Calculate().active);other.map=&map;
 other.phase=2;assert(!value.Calculate().active);other.phase=1;
 other.teleport=true;assert(!value.Calculate().active);other.teleport=false;
 boss.phase=2;assert(!value.Calculate().active);boss.phase=1;
 other.z=20;assert(!value.Calculate().active);other.z=0;
 bot.charmed=true;assert(!value.Calculate().active);bot.charmed=false;
 bot.teleport=true;assert(!value.Calculate().active);bot.teleport=false;
 bot.mapId=0;assert(!value.Calculate().active);bot.mapId=554;
 boss.entry=19221;assert(!value.Calculate().active);boss.entry=19219;
 ai.validPath=false;ai.checked=0;assert(!value.Calculate().active && ai.checked<=8);ai.validPath=true;
 bot.auras.clear();other.auras.clear();Unit charge;charge.entry=20405;charge.map=&map;charge.auras={37670};
 nativeCharges={&charge};plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=17);
 charge.auras.clear();assert(!value.Calculate().active);charge.auras={37670};
 charge.phase=2;assert(!value.Calculate().active);charge.phase=1;
 charge.alive=false;assert(!value.Calculate().active);charge.alive=true;charge.map=&otherMap;
 assert(!value.Calculate().active);charge.map=&map;charge.x=19;
 plan=value.Calculate();assert(plan.active && plan.destination.x==0 && plan.destination.y==0); // safe hold
 charge.x=30;assert(!value.Calculate().active); // no unrelated movement suppression
 // Sepethrea: combine live flames, follow native fixation, never flee a corpse.
 boss.entry=19221;charge.entry=20481;charge.x=1;charge.auras={35281};
 plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{1,0,0})>=6);
 charge.victim=&bot;
 plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{1,0,0})>=12);
 charge.victim=&other;charge.x=9;plan=value.Calculate();assert(plan.active && plan.destination.x==0);
 charge.auras.insert(35268);plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{9,0,0})>=12);
 charge.auras.erase(35268);charge.auras.insert(39346);plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{9,0,0})>=12);
 charge.auras.erase(39346);
#ifndef BEFORE_CHECK
 charge.x=1;plan=value.Calculate();MechanarPositionAction action{&bot,&ai};Event event;
 MechanarPositionAction::cached=plan;assert(action.Execute(event)&&action.moves==1);
 charge.x=plan.destination.x;charge.y=plan.destination.y;assert(!action.Execute(event)&&action.moves==1); // Flame moved into cached destination.
 charge.x=1;charge.y=0;charge.alive=false;assert(!action.Execute(event));charge.alive=true;
 charge.x=9;
#endif
 charge.alive=false;assert(!value.Calculate().active);charge.alive=true;
 charge.auras.clear();assert(!value.Calculate().active);charge.auras={35281};
 charge.map=&otherMap;assert(!value.Calculate().active);charge.map=&map;
 ai.validPath=false;ai.checked=0;assert(!value.Calculate().active && ai.checked<=8);ai.validPath=true;
 radii[35281]=0;assert(!value.Calculate().active);radii[35281]=4;
 // Pathaleon: native normal/heroic radius, caster/healer-only; melee stays in.
 boss.entry=19220;nativeCharges.clear();assert(!value.Calculate().active);
 ai.ranged=true;plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=10);
#ifndef BEFORE_CHECK
 boss.victim=&bot;assert(!value.Calculate().active);boss.victim=nullptr;
#endif
 map.regular=false;plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=12);
 ai.ranged=false;ai.healer=true;assert(value.Calculate().active);ai.healer=false;assert(!value.Calculate().active);
 boss.entry=1;ai.ranged=true;assert(!value.Calculate().active);
#endif
 std::cout<<"PASS: actual Mechanar polarity/charge/flame-fixation/caster-radius/lifetime/instance/expansion and bounded path decisions\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHOD__',method).replace('__HELPER__',helper).replace('__EXECUTE__',execute)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-mechanar-test-') as tmp:
        tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{expansion}']+(['/DBEFORE_CHECK'] if before else [])+['test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],check=True)
for path in ('actions/ActionContext.h','triggers/TriggerContext.h','generic/MechanarDungeonStrategies.cpp'):
    assert 'mechanar safe position' in (root/'playerbot/strategy'/path).read_text()
