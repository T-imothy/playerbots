"""Run the actual Mechanar decision against controlled native-interface fixtures."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/values/MechanarPositionValue.cpp').read_text(), 'EncounterPosition MechanarPositionValue::Calculate(')
code=r'''
#include <cassert>
#include <set>
#include <map>
#include <list>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;
struct Map {bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Unit {unsigned entry=0,guid=1;bool world=true,alive=true,combat=true;Map* map=nullptr;
 float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;}Map* GetMap(){return map;}unsigned GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}};
struct Group;
struct Player:Unit {bool charmed=false,teleport=false;unsigned mapId=554,instance=1;Group* group=nullptr;
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}};
struct GroupReference {Player* source=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct PlayerbotAI {std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;bool validPath=true,ranged=false,healer=false;unsigned checked=0;
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
     {35281,4.0f},{36022,8.0f},{15453,10.0f}}; // controlled radii, not replacement spell data
 float NativeEncounterSpellRadius(unsigned id){return radii[id];}
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&){++ai->checked;return ai->validPath;}
 struct MechanarPositionValue {Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
}
using namespace ai;
#define AI_VALUE(type,name) ai->attackers
__METHOD__
int main(){
 Player bot,other;Map map,otherMap;bot.map=other.map=&map;
 Unit boss;boss.entry=19219;boss.map=&map;PlayerbotAI ai;ai.attackers={1};ai.units[1]=&boss;
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
 other.z=20;assert(!value.Calculate().active);other.z=0;
 bot.charmed=true;assert(!value.Calculate().active);bot.charmed=false;
 bot.teleport=true;assert(!value.Calculate().active);bot.teleport=false;
 bot.mapId=0;assert(!value.Calculate().active);bot.mapId=554;
 boss.entry=19221;assert(!value.Calculate().active);boss.entry=19219;
 ai.validPath=false;ai.checked=0;assert(!value.Calculate().active && ai.checked<=8);ai.validPath=true;
 bot.auras.clear();other.auras.clear();Unit charge;charge.entry=20405;charge.map=&map;charge.auras={37670};
 nativeCharges={&charge};plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=17);
 charge.auras.clear();assert(!value.Calculate().active);charge.auras={37670};
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
 charge.alive=false;assert(!value.Calculate().active);charge.alive=true;
 charge.auras.clear();assert(!value.Calculate().active);charge.auras={35281};
 charge.map=&otherMap;assert(!value.Calculate().active);charge.map=&map;
 ai.validPath=false;ai.checked=0;assert(!value.Calculate().active && ai.checked<=8);ai.validPath=true;
 radii[35281]=0;assert(!value.Calculate().active);radii[35281]=4;
 // Pathaleon: native normal/heroic radius, caster/healer-only; melee stays in.
 boss.entry=19220;nativeCharges.clear();assert(!value.Calculate().active);
 ai.ranged=true;plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=10);
 map.regular=false;plan=value.Calculate();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=12);
 ai.ranged=false;ai.healer=true;assert(value.Calculate().active);ai.healer=false;assert(!value.Calculate().active);
 boss.entry=1;ai.ranged=true;assert(!value.Calculate().active);
#endif
 std::cout<<"PASS: actual Mechanar polarity/charge/flame-fixation/caster-radius/lifetime/instance/expansion and bounded path decisions\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHOD__',method)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-mechanar-test-') as tmp:
        tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{expansion}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],check=True)
for path in ('actions/ActionContext.h','triggers/TriggerContext.h','generic/MechanarDungeonStrategies.cpp'):
    assert 'mechanar safe position' in (root/'playerbot/strategy'/path).read_text()
