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
mc = (root / 'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods += [block(mc, 'unsigned MoltenCoreTargetPriority('),
            block(mc, 'Unit* MoltenCorePriorityTargetAction::GetTarget('),
            block(mc, 'bool MoltenCorePriorityTargetAction::isUseful(')]

code = r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <type_traits>
using ObjectGuid=unsigned;
using uint32=unsigned;
struct {float sightDistance=60.0f;} sPlayerbotAIConfig;
struct Map {};
struct Unit {
 unsigned entry=0;bool world=true,alive=true,combat=true,levitating=false,breakCC=false,hardCC=false;
 bool assignedCC=false,attackable=true;unsigned phase=1;
 Map* map=nullptr;Unit* victim=nullptr;float x=0,z=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsLevitating(){return levitating;}Map* GetMap(){return map;}unsigned GetEntry(){return entry;}
 Unit* GetVictim(){return victim;}float GetPositionZ(){return z;}
 float GetDistance(Unit* other){return std::fabs(x-other->x);}
};
struct Player:Unit {bool charmed=false,teleport=false;unsigned mapId=554;
 bool IsInMap(Unit* unit){return map==unit->map&&phase==unit->phase;}
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}};
struct PlayerbotAI {
 bool healer=false,tank=false;std::list<ObjectGuid> attackers,possible;std::map<unsigned,Unit*> units;
 Unit* current=nullptr;Unit* marked=nullptr;
 ObjectGuid commanded=0;
 bool IsHeal(Player*){return healer;}bool IsTank(Player*){return tank;}
 Unit* GetUnit(unsigned id){auto it=units.find(id);return it==units.end()?nullptr:it->second;}
 template<class T>T Value(const char* key){
  if constexpr(std::is_same_v<T,Unit*>)return std::string(key)=="rti target"?marked:current;
  else if constexpr(std::is_same_v<T,ObjectGuid>)return commanded;
  else return std::string(key)=="attackers"?attackers:possible;
 }
};
namespace ai {
 struct PossibleAttackTargetsValue {
  static bool HasBreakableCC(Unit* unit,Player*){return unit->breakCC;}
  static bool HasUnBreakableCC(Unit* unit,Player*){return unit->hardCC;}
  static bool IsCcTarget(Unit* unit,Player*){return unit->assignedCC;}
  static bool IsValid(Unit* unit,Player* bot,float range,bool ignoreCC,bool validate){
   assert(!ignoreCC&&validate);return unit->attackable&&bot->GetDistance(unit)<=range;}
 };
 struct PathaleonAddsAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
 struct OnyxiaAddsAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
 struct MoltenCorePriorityTargetAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
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
 // MC support is present in all three eras, with native role/target admission.
 ai=PlayerbotAI{};bot=Player{};boss=Unit{};add=Unit{};second=Unit{};
 bot.map=&map;bot.mapId=409;boss.map=add.map=second.map=&map;
 ai.units={{1,&boss},{2,&add},{3,&second}};ai.attackers={1};ai.possible={2,3};
 MoltenCorePriorityTargetAction mc{&bot,&ai};
 for(auto pair : {std::pair<unsigned,unsigned>{12118,12119},{12259,11661},{12098,11662},{12018,11663}}){
  boss.entry=pair.first;add.entry=second.entry=pair.second;add.x=1;second.x=20;
  assert(mc.GetTarget()==&add&&mc.isUseful());
  ai.current=&second;assert(mc.GetTarget()==&second&&!mc.isUseful());ai.current=nullptr;
  ai.marked=&boss;assert(!mc.GetTarget());ai.marked=&add;assert(!mc.GetTarget());ai.marked=nullptr;
  ai.commanded=1;assert(!mc.GetTarget());ai.commanded=0;
  ai.possible={2};
  add.breakCC=true;assert(!mc.GetTarget());add.breakCC=false;
  add.hardCC=true;assert(!mc.GetTarget());add.hardCC=false;
  add.assignedCC=true;assert(!mc.GetTarget());add.assignedCC=false;
  add.attackable=false;assert(!mc.GetTarget());add.attackable=true;
  add.phase=2;assert(!mc.GetTarget());add.phase=1;
  add.map=&other;assert(!mc.GetTarget());add.map=&map;
  add.alive=false;assert(!mc.GetTarget());add.alive=true;
  add.combat=false;assert(!mc.GetTarget());add.combat=true;
  add.x=100;assert(!mc.GetTarget());add.x=1;
  ai.healer=true;assert(!mc.GetTarget());ai.healer=false;
  ai.tank=true;assert(!mc.GetTarget());ai.tank=false;
  boss.victim=&bot;assert(!mc.GetTarget());boss.victim=nullptr;
  boss.phase=2;assert(!mc.GetTarget());boss.phase=1;
  boss.combat=false;assert(!mc.GetTarget());boss.combat=true;
  bot.teleport=true;assert(!mc.GetTarget());bot.teleport=false;
  bot.charmed=true;assert(!mc.GetTarget());bot.charmed=false;
  bot.mapId=0;assert(!mc.GetTarget());bot.mapId=409;
  ai.possible={2,3};
 }
 // Majordomo: a free healer takes priority over an elite; a sheeped healer does not.
 boss.entry=12018;add.entry=11663;second.entry=11664;ai.current=&second;
 assert(mc.GetTarget()==&add);add.breakCC=true;assert(mc.GetTarget()==&second);add.breakCC=false;
 // Golemagg: use normal attack admission, leave all tank/off-tank assignments alone.
 boss.entry=11988;add.entry=second.entry=11672;ai.possible={1,2,3};ai.current=&add;
 assert(mc.GetTarget()==&boss);ai.tank=true;assert(!mc.GetTarget());ai.tank=false;
 ai.marked=&add;assert(!mc.GetTarget());ai.marked=nullptr;
 boss.attackable=false;assert(!mc.GetTarget());boss.attackable=true;
 // Garr/Ragnaros are not silently assigned a made-up policy by this feature.
 boss.entry=12057;assert(!mc.GetTarget());boss.entry=11502;assert(!mc.GetTarget());
 boss.entry=12118;add.entry=12119;second.entry=12098;ai.attackers={1,3};
 assert(!mc.GetTarget()); // ambiguous multi-boss combat retains ordinary handling
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
for filename in ('actions/ActionContext.h','triggers/TriggerContext.h','generic/MoltenCoreDungeonStrategies.cpp'):
    assert 'molten core priority target' in (root/'playerbot/strategy'/filename).read_text()
multiplier = block((root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text(),
                   'float PreserveMoltenCorePositionMultiplier::GetValue(')
assert 'MoltenCorePriorityTargetAction' in multiplier and '"dps assist"' in multiplier
