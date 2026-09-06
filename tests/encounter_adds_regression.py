"""Compile actual encounter add selection with controlled native-interface fixtures."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
methods = []
for filename, cls in (("MechanarDungeonActions.cpp", "PathaleonAddsAction"),
                      ("OnyxiasLairDungeonActions.cpp", "OnyxiaAddsAction")):
    text = (root / "playerbot/strategy/actions" / filename).read_text()
    methods.append(block(text, f"Unit* {cls}::GetTarget("))
    methods.append(block(text, f"bool {cls}::isUseful("))

code = r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <type_traits>
using ObjectGuid=unsigned;
struct Map {};
struct Unit {
 unsigned entry=0;bool world=true,alive=true,combat=true,levitating=false,breakCC=false,hardCC=false;
 Map* map=nullptr;Unit* victim=nullptr;float x=0,z=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsLevitating(){return levitating;}Map* GetMap(){return map;}unsigned GetEntry(){return entry;}
 Unit* GetVictim(){return victim;}float GetPositionZ(){return z;}
 float GetDistance(Unit* other){return std::fabs(x-other->x);}
};
struct Player:Unit {bool charmed=false,teleport=false;unsigned mapId=554;
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}};
struct PlayerbotAI {
 bool healer=false,tank=false;std::list<ObjectGuid> attackers,possible;std::map<unsigned,Unit*> units;
 Unit* current=nullptr;Unit* marked=nullptr;
 bool IsHeal(Player*){return healer;}bool IsTank(Player*){return tank;}
 Unit* GetUnit(unsigned id){auto it=units.find(id);return it==units.end()?nullptr:it->second;}
 template<class T>T Value(const char* key){
  if constexpr(std::is_same_v<T,Unit*>)return std::string(key)=="rti target"?marked:current;
  else return std::string(key)=="attackers"?attackers:possible;
 }
};
namespace ai {
 struct PossibleAttackTargetsValue {
  static bool HasBreakableCC(Unit* unit,Player*){return unit->breakCC;}
  static bool HasUnBreakableCC(Unit* unit,Player*){return unit->hardCC;}
 };
 struct PathaleonAddsAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
 struct OnyxiaAddsAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
}
using namespace ai;
#define AI_VALUE(type,key) ai->Value<type>(key)
__METHODS__

template<class T>void CheckSelection(T& action,Player& bot,PlayerbotAI& ai,Unit& boss,Unit& add,Unit& second,Map& other){
 assert(action.GetTarget()==&add && action.isUseful());
 ai.current=&add;assert(action.GetTarget()==&add && !action.isUseful());
 // An explicit marked add wins even if our current add comes first in the list.
 ai.marked=&second;assert(action.GetTarget()==&second && action.isUseful());
 ai.marked=&boss;assert(!action.GetTarget());ai.marked=nullptr;
 add.x=20;second.x=1;assert(action.GetTarget()==&add); // stable target, no nearest-target thrashing
 ai.current=nullptr;assert(action.GetTarget()==&second);add.x=1;second.x=20;
 ai.possible={2};
 add.breakCC=true;assert(!action.GetTarget());add.breakCC=false;
 add.hardCC=true;assert(!action.GetTarget());add.hardCC=false;
 add.alive=false;assert(!action.GetTarget());add.alive=true;
 add.combat=false;assert(!action.GetTarget());add.combat=true;
 Map* original=add.map;add.map=&other;assert(!action.GetTarget());add.map=original;
 boss.victim=&bot;assert(!action.GetTarget());boss.victim=nullptr;
 boss.combat=false;assert(!action.GetTarget());boss.combat=true;
 boss.map=&other;assert(!action.GetTarget());boss.map=original;
 ai.healer=true;assert(!action.GetTarget());ai.healer=false;
 bot.charmed=true;assert(!action.GetTarget());bot.charmed=false;
 bot.teleport=true;assert(!action.GetTarget());bot.teleport=false;
 const unsigned mapId=bot.mapId;bot.mapId=0;assert(!action.GetTarget());bot.mapId=mapId;
 ai.possible={2,3};
}
int main(){
 Map map,other;Player bot;bot.map=&map;Unit boss,add,second;
 boss.map=add.map=second.map=&map;boss.entry=19220;add.entry=second.entry=21062;
 add.x=1;second.x=20;PlayerbotAI ai;ai.units={{1,&boss},{2,&add},{3,&second}};ai.attackers={1};ai.possible={2,3};
 PathaleonAddsAction pathaleon{&bot,&ai};
#ifdef MANGOSBOT_ZERO
 assert(!pathaleon.GetTarget() && !pathaleon.isUseful());
#else
 CheckSelection(pathaleon,bot,ai,boss,add,second,other);
#endif
 bot.mapId=249;boss.entry=10184;add.entry=second.entry=11262;boss.levitating=true;
 OnyxiaAddsAction onyxia{&bot,&ai};CheckSelection(onyxia,bot,ai,boss,add,second,other);
 boss.levitating=false;assert(!onyxia.GetTarget()); // ground phase DPS stays on boss
 ai.tank=true;assert(onyxia.GetTarget());boss.victim=&bot;assert(!onyxia.GetTarget());
 std::cout<<"PASS: actual encounter add selection: CC, marks, roles, stable target, death, transition, instance, expansion\n";
}
'''.replace("__METHODS__", "\n".join(methods))
for expansion in ("ZERO", "ONE", "TWO"):
    with tempfile.TemporaryDirectory(prefix="mantech-encounter-adds-") as tmp:
        tmp = Path(tmp)
        (tmp / "test.cpp").write_text(code)
        subprocess.run(["cl", "/nologo", "/EHsc", "/std:c++17", f"/DMANGOSBOT_{expansion}",
                        "test.cpp", "/Fe:test.exe"], cwd=tmp, check=True)
        subprocess.run([str(tmp / "test.exe")], check=True)
for filename in ("actions/ActionContext.h", "triggers/TriggerContext.h", "generic/MechanarDungeonStrategies.cpp"):
    assert "pathaleon attack adds" in (root / "playerbot/strategy" / filename).read_text()
