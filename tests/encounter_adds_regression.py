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
    if filename == 'OnyxiasLairDungeonActions.cpp':
        onyxia = (root / 'playerbot/strategy/values/OnyxiaPositionValue.cpp').read_text()
        methods.append(block(onyxia, 'Unit* ai::FindOnyxiaBoss(').replace('ai::', ''))
        methods.append(block(text, 'bool IsOnyxiaAddEntry('))
    methods.append(block(text, f"Unit* {cls}::GetTarget("))
    methods.append(block(text, f"bool {cls}::isUseful("))
mc = (root / 'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods += [block(mc, 'unsigned MoltenCoreTargetPriority('),
            block(mc, 'Unit* MoltenCorePriorityTargetAction::GetTarget('),
            block(mc, 'bool MoltenCorePriorityTargetAction::isUseful(')]

code = r'''
#include <cassert>
#include <algorithm>
#include <vector>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <set>
#include <type_traits>
using ObjectGuid=unsigned;
using uint32=unsigned;
struct {float sightDistance=60.0f;} sPlayerbotAIConfig;
struct Map {};
struct Unit {
 virtual ~Unit()=default;bool HasCharmer(){return false;}
 unsigned guid=0;float health=100;unsigned GetObjectGuid(){return guid;} unsigned GetGUIDLow(){return guid;} float GetHealthPercent(){return health;}
 unsigned entry=0;bool world=true,alive=true,combat=true,levitating=false,breakCC=false,hardCC=false;
 bool assignedCC=false,attackable=true;unsigned phase=1;
 Map* map=nullptr;Unit* victim=nullptr;float x=0,z=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsLevitating(){return levitating;}Map* GetMap(){return map;}unsigned GetEntry(){return entry;}
 Unit* GetVictim(){return victim;}float GetPositionZ(){return z;}
 std::set<unsigned>auras;bool HasAura(unsigned id){return auras.count(id);}
 float GetDistance(Unit* other){return std::fabs(x-other->x);}
};
struct Player:Unit {bool charmed=false,teleport=false;unsigned mapId=554;
 bool IsInMap(Unit* unit){return map==unit->map&&phase==unit->phase;}
 void* GetGroup(){return this;}bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}};
struct PlayerbotAI {
 Player* botptr=nullptr;Player* GetBot(){return botptr;}PlayerbotAI* GetAiObjectContext(){return this;}
 template<class T>struct Access{PlayerbotAI* ai;std::string key;T Get(){return ai->Value<T>(key.c_str());}};
 template<class T>Access<T>* GetValue(const char* key,const char* =nullptr){static Access<T> v;v={this,key};return &v;}
 bool healer=false,tank=false,ranged=false;bool IsRanged(Player*){return ranged;}std::list<ObjectGuid> attackers,possible;std::map<unsigned,Unit*> units;
 Unit* current=nullptr;Unit* marked=nullptr;
 ObjectGuid commanded=0;
 bool IsHeal(Player*){return healer;}bool IsTank(Player*){return tank;}
 Unit* GetUnit(unsigned id){auto it=units.find(id);return it==units.end()?nullptr:it->second;}
 template<class T>T Value(const char* key){
  if constexpr(std::is_same_v<T,Unit*>)return std::string(key)=="rti target"?marked:current;
  else if constexpr(std::is_same_v<T,ObjectGuid>){
   if(std::string(key)=="attack target") return commanded;
   Unit* wanted=std::string(key)=="rti target"?marked:current;
   for(auto const& entry:units)if(entry.second==wanted)return entry.first;
   return 0;
  }
  else {if(std::string(key)=="possible targets"){auto raw=attackers;raw.insert(raw.end(),possible.begin(),possible.end());return raw;}return std::string(key)=="attackers"?attackers:possible;}
 }
};
namespace ai {
 std::vector<Unit*> MoltenCorePack(PlayerbotAI*a){std::vector<Unit*>out;for(auto g:a->possible){auto*u=a->GetUnit(g);if(u&&u->entry==11671)out.push_back(u);}return out;} // Native group allocation is executed separately in the support fixture.
 Unit* MoltenCoreNukeTarget(PlayerbotAI*) { return nullptr; }
 struct PossibleAttackTargetsValue {
  static bool HasBreakableCC(Unit* unit,Player*){return unit->breakCC;}
  static bool HasUnBreakableCC(Unit* unit,Player*){return unit->hardCC;}
  static bool IsValid(Unit* unit,Player* bot,float range,bool ignoreCC,bool validate){
   assert(!ignoreCC&&validate);return unit->attackable&&bot->GetDistance(unit)<=range&&!IsCcTarget(unit,bot);}
 private:
  static bool IsCcTarget(Unit* unit,Player*){return unit->assignedCC;}
 };
 struct PathaleonAddsAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
 struct OnyxiaAddsAction {Player* bot;PlayerbotAI* ai;Unit* GetTarget();bool isUseful();};
 Unit* MoltenCoreAssignedTankTarget(PlayerbotAI*) { return nullptr; } // DPS selection fixture; tank allocation is separate.
 Unit* MajordomoFocus(PlayerbotAI* a,Unit*) {
  for(unsigned entry:{11664u,11663u})for(auto g:a->possible){auto* u=a->GetUnit(g);if(u&&u->entry==entry)return u;}return nullptr;
 }
 Unit* GarrFocusTarget(PlayerbotAI*) { return nullptr; } // Dedicated Garr fixture exercises its native controller.
 Unit* LavaTrashFocusTarget(PlayerbotAI*) { return nullptr; } // Dedicated lava fixture exercises its native controller.
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
 ai.commanded=1;assert(!action.GetTarget());ai.commanded=0;
 Unit obsolete=boss;obsolete.world=false;ai.marked=&obsolete;assert(action.GetTarget()==&add);
 obsolete.world=true;obsolete.map=&other;assert(action.GetTarget()==&add);ai.marked=nullptr;
 add.x=20;second.x=1;assert(action.GetTarget()==&add); // stable target, no nearest-target thrashing
 ai.current=nullptr;assert(action.GetTarget()==&second);add.x=1;second.x=20;
 ai.possible={2};
 add.breakCC=true;assert(!action.GetTarget());add.breakCC=false;
 add.hardCC=true;assert(!action.GetTarget());add.hardCC=false;
 add.assignedCC=true;assert(!action.GetTarget());add.assignedCC=false;
 add.attackable=false;assert(!action.GetTarget());add.attackable=true;
 add.phase=2;assert(!action.GetTarget());add.phase=1;
 add.alive=false;assert(!action.GetTarget());add.alive=true;
 add.combat=false;assert(!action.GetTarget());add.combat=true;
 Map* original=add.map;add.map=&other;assert(!action.GetTarget());add.map=original;
 boss.victim=&bot;
#ifdef MANGOSBOT_ZERO
 if constexpr(std::is_same_v<T,OnyxiaAddsAction>) {
  assert(boss.levitating&&action.GetTarget()==&add); // Former ground tank helps with airborne whelps.
  boss.levitating=false;assert(!action.GetTarget());boss.levitating=true;
 } else assert(!action.GetTarget());
#else
 assert(!action.GetTarget());
#endif
 boss.victim=nullptr;
 boss.combat=false;assert(!action.GetTarget());boss.combat=true;
 boss.map=&other;assert(!action.GetTarget());boss.map=original;
 boss.phase=2;assert(!action.GetTarget());boss.phase=1;
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
 ai.botptr=&bot;bot.mapId=249;boss.entry=10184;add.entry=second.entry=11262;boss.levitating=true;
 OnyxiaAddsAction onyxia{&bot,&ai};CheckSelection(onyxia,bot,ai,boss,add,second,other);
 add.entry=second.entry=36561;ai.current=nullptr;
#ifdef MANGOSBOT_TWO
 CheckSelection(onyxia,bot,ai,boss,add,second,other);
#else
 assert(!onyxia.GetTarget());
#endif
 add.entry=second.entry=11262;
 boss.levitating=false;assert(!onyxia.GetTarget()); // ground phase DPS stays on boss
 ai.tank=true;assert(onyxia.GetTarget());boss.victim=&bot;assert(!onyxia.GetTarget());
 // MC support is present in all three eras, with native role/target admission.
 ai=PlayerbotAI{};bot=Player{};boss=Unit{};add=Unit{};second=Unit{};
 bot.map=&map;bot.mapId=409;boss.map=add.map=second.map=&map;
 ai.units={{1,&boss},{2,&add},{3,&second}};ai.attackers={1};ai.possible={2,3};
 MoltenCorePriorityTargetAction mc{&bot,&ai};
 for(auto pair : {std::pair<unsigned,unsigned>{12118,12119},{12259,11661},{12057,12099},{12098,11662}}){
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
 // Majordomo: elites first, regardless of a free healer.
 boss.entry=12018;add.entry=11663;second.entry=11664;ai.current=&second;
 assert(mc.GetTarget()==&second);add.breakCC=true;assert(mc.GetTarget()==&second);add.breakCC=false;
 // Golemagg DPS fixture: ignore Core Ragers; tank allocation is tested separately.
 boss.entry=11988;add.entry=second.entry=11672;ai.possible={1,2,3};ai.current=&add;
 assert(mc.GetTarget()==&boss);ai.tank=true;assert(!mc.GetTarget());ai.tank=false;
 ai.marked=&add;assert(mc.GetTarget()==&boss);ai.marked=nullptr;
 boss.attackable=false;assert(!mc.GetTarget());boss.attackable=true;
 // No unrelated Core Rager target is selected during Garr or Ragnaros.
 boss.entry=12057;assert(!mc.GetTarget());boss.entry=11502;assert(!mc.GetTarget());
 // Native submerged boss can disappear from attackers; live sons still need killing.
 add.entry=second.entry=12143;ai.attackers={2,3};ai.possible={2,3};ai.current=&add;
 assert(mc.GetTarget()==&add&&!mc.isUseful());
 add.breakCC=true;assert(mc.GetTarget()==&second);add.breakCC=false;
 ai.marked=&add;assert(!mc.GetTarget());ai.marked=nullptr;
 ai.commanded=2;assert(!mc.GetTarget());ai.commanded=0;
 ai.attackers={};assert(!mc.GetTarget());ai.attackers={2};
 add.combat=false;assert(!mc.GetTarget());add.combat=true;
 add.world=false;assert(!mc.GetTarget());add.world=true;
 add.phase=2;assert(!mc.GetTarget());add.phase=1;
 ai.tank=true;assert(!mc.GetTarget());ai.tank=false;
 ai.healer=true;assert(!mc.GetTarget());ai.healer=false;
 ai.attackers={1,2};boss.attackable=false;assert(mc.GetTarget()==&add);boss.attackable=true;
 boss.entry=12118;assert(!mc.GetTarget()); // unrelated boss/son pull is ambiguous
 boss.entry=12118;add.entry=12119;second.entry=12098;ai.attackers={1,3};
 assert(!mc.GetTarget()); // ambiguous multi-boss combat retains ordinary handling
 // Small Core Hounds: health balancing, mark tolerance, remaining survivors.
 ai=PlayerbotAI{};bot.mapId=409;bot.guid=7;add=Unit{};second=Unit{};
 add.map=second.map=&map;add.entry=second.entry=11671;add.guid=2;second.guid=3;
 add.health=20;second.health=70;ai.units={{2,&add},{3,&second}};ai.possible={2,3};
 ai.current=&add;ai.marked=&add;assert(mc.GetTarget()==&second);
 second.health=23;assert(mc.GetTarget()==&second); // always release the <=20% dog
 add.health=22;assert(mc.GetTarget()==&add); // two-point hysteresis above 20%
 add.health=20;second.health=21;ai.commanded=2;assert(mc.GetTarget()==&second); // a pull/attack on the low dog cannot pin it
 second.health=20;assert(mc.GetTarget()==&add); // all low: stable highest-health finish
 add.health=22;second.health=23;ai.commanded=0;
 add.alive=false;assert(mc.GetTarget()==&second);
 ai.commanded=3;assert(mc.GetTarget()==&second);ai.commanded=0; // group Attack does not disable balancing
 ai.tank=true;assert(!mc.GetTarget());ai.tank=false;
 ai.healer=true;assert(!mc.GetTarget());ai.healer=false;
 second.breakCC=true;assert(!mc.GetTarget());second.breakCC=false;
 // Firelord trash: a marked parent must not suppress live spawn cleanup.
 ai=PlayerbotAI{};bot=Player{};boss=Unit{};add=Unit{};second=Unit{};
 bot.map=&map;bot.mapId=409;boss.map=add.map=second.map=&map;
 boss.entry=11668;boss.guid=10;add.entry=second.entry=12265;add.guid=20;second.guid=21;
 ai.units={{1,&boss},{2,&add},{3,&second}};ai.attackers={1};ai.possible={1,2,3};ai.current=&boss;ai.marked=&boss;
 assert(mc.GetTarget()==&add); // equal health: stable GUID focus
 add.health=70;second.health=20;assert(mc.GetTarget()==&second);
 ai.current=&add;assert(mc.GetTarget()==&second); // focus the wounded spawn
 ai.commanded=1;assert(!mc.GetTarget());ai.commanded=0;
 second.breakCC=true;assert(mc.GetTarget()==&add);second.breakCC=false;
 second.phase=2;assert(mc.GetTarget()==&add);second.phase=1;
 second.combat=false;assert(mc.GetTarget()==&add);second.combat=true;
 second.alive=add.alive=false;assert(mc.GetTarget()==&boss); // resume the Firelord
 boss.alive=false;assert(!mc.GetTarget());add.alive=true;assert(mc.GetTarget()==&add); // clean up surviving children
 ai.healer=true;assert(!mc.GetTarget());ai.healer=false;ai.tank=true;assert(!mc.GetTarget());ai.tank=false;
 bot.teleport=true;assert(!mc.GetTarget());bot.teleport=false;
 add.attackable=false;assert(!mc.GetTarget());add.attackable=true;
 // Mixed patrol pack: ranged focus the hound, melee the separate mob; respect commands/CC.
 boss=Unit{};add=Unit{};bot=Player{};bot.map=&map;bot.mapId=409;
 boss.map=add.map=&map;boss.entry=11673;add.entry=11661;boss.guid=10;add.guid=20;
 ai=PlayerbotAI{};ai.units={{1,&boss},{2,&add}};ai.possible={1,2};ai.attackers={1,2};
 ai.ranged=true;assert(mc.GetTarget()==&boss);ai.ranged=false;assert(mc.GetTarget()==&add);
 add.breakCC=true;assert(!mc.GetTarget());add.breakCC=false;ai.commanded=2;assert(!mc.GetTarget());ai.commanded=0;
 std::cout<<"PASS: actual encounter add selection: CC, marks, roles, mixed hounds, stable target, death, transition, instance, expansion\n";
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
