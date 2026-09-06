"""Compile actual Karazhan movement policies; fixtures do not simulate a raid clear."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
base = root / "playerbot/strategy"
extract = (
    ("actions/KarazhanDungeonActions.cpp", ("bool AranFlameWreathValue::Calculate(",
        "bool AranFlameWreathHoldAction::IsHolding(", "bool AranFlameWreathHoldAction::isUseful(",
        "bool AranFlameWreathHoldAction::Execute(")),
    ("actions/GenericSpellActions.cpp", ("bool CastSpellAction::HasMovementEffect(",)),
    ("generic/DungeonMultipliers.cpp", ("float PreserveAranFlameWreathMultiplier::GetValue(",)),
    ("triggers/KarazhanDungeonTriggers.cpp", ("bool PrinceMalchezaarTooCloseTrigger::IsActive(",
        "bool PrinceMalchezaarTooCloseTrigger::MeleeWaitCheck(", "bool PrinceMalchezaarTooCloseTrigger::EnfeeblePart(")),
)
methods = "\n".join(block((base / path).read_text(), signature) for path, names in extract for signature in names)
code = r'''
#include <cassert>
#include <list>
#include <map>
#include <set>
#include <iostream>
#include <cmath>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr int CURRENT_GENERIC_SPELL=1,SPELL_STATE_FINISHED=2,IDLE_MOTION_TYPE=0,MAX_EFFECT_INDEX=3;
enum {SPELL_EFFECT_CHARGE=96,SPELL_EFFECT_LEAP=29,SPELL_EFFECT_TELEPORT_UNITS=5,SPELL_EFFECT_TELEPORT_UNITS_FACE_CASTER=43,
#ifndef MANGOSBOT_ZERO
 SPELL_EFFECT_LEAP_BACK=138,SPELL_EFFECT_CHARGE_DEST=149,
#endif
#ifdef MANGOSBOT_TWO
 SPELL_EFFECT_JUMP=41,SPELL_EFFECT_JUMP_DEST=42,
#endif
 ORDINARY_DAMAGE=2};
struct SpellEntry {unsigned Id=0;unsigned Effect[3]={0,0,0};};
struct Spell {SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}};
struct Map {};
struct Unit {unsigned entry=0,phase=1;bool world=true,alive=true,combat=true,creature=true;Map* map=nullptr;
 Unit* victim=nullptr;Spell* current=nullptr;std::set<unsigned> auras;float x=0,health=100;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsCreature(){return creature;}float GetHealthPercent(){return health;}
 unsigned GetEntry(){return entry;}Map* GetMap(){return map;}Unit* GetVictim(){return victim;}
 bool HasAura(unsigned id){return auras.count(id);}Spell* GetCurrentSpell(int){return current;}
 float GetDistance(Unit* unit){return std::fabs(x-unit->x);}};
struct Motion {int kind=0;int GetCurrentMovementGeneratorType(){return kind;}};
struct Group;
struct Player:Unit {bool charmed=false,teleport=false,stopped=true;unsigned mapId=532;Group* group=nullptr;Motion motion;
 bool IsInMap(Unit* unit){return map==unit->map&&phase==unit->phase;}
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 Group* GetGroup(){return group;}bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}};
struct GroupReference {Player* player=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct StoredBool {bool value=false;bool Get(){return value;}};
struct Context {StoredBool hold;template<class T>StoredBool* GetValue(const char*){return &hold;}};
struct PlayerbotAI {Player* bot;std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;Context context;
 bool ranged=false,melee=true;unsigned stopped=0;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}
 Unit* GetUnit(unsigned id){auto it=units.find(id);return it==units.end()?nullptr:it->second;}
 bool IsRanged(Player*,bool){return ranged;}bool IsMelee(Player*,bool){return melee;}
 void StopMoving(){++stopped;bot->stopped=true;bot->motion.kind=0;}};
struct Facade {std::map<unsigned,SpellEntry> spells;bool IsAlive(Unit* unit){return unit->alive;}
 const SpellEntry* LookupSpellInfo(unsigned id){auto it=spells.find(id);return it==spells.end()?nullptr:&it->second;}}sServerFacade;
struct Event {};
namespace ai {
 struct Action {virtual ~Action()=default;};struct MovementAction:Action {};struct AttackAction:MovementAction {};
 struct CastSpellAction:Action {unsigned spellId=0;void RefreshSpellId(){};bool HasMovementEffect();};
 struct AranFlameWreathValue {Player* bot;PlayerbotAI* ai;bool Calculate();};
 struct AranFlameWreathHoldAction:Action {Player* bot=nullptr;PlayerbotAI* ai=nullptr;
  static bool IsHolding(PlayerbotAI* ai);bool isUseful();bool Execute(Event&);void SetDuration(unsigned){}};
 struct PreserveAranFlameWreathMultiplier {PlayerbotAI* ai;float GetValue(Action* action);};
 struct PullStrategy {static PullStrategy* Get(PlayerbotAI*){return nullptr;}bool HasPullStarted(){return false;}};
 struct CloseToCreatureTrigger {bool IsActive(){return false;}};
 struct PrinceMalchezaarTooCloseTrigger:CloseToCreatureTrigger {Player* bot;PlayerbotAI* ai;
  bool IsActive();bool MeleeWaitCheck(Unit* target);bool EnfeeblePart();};
}
using namespace ai;
#define AI_VALUE(type,name) ai->attackers
__METHODS__
int main(){
 Map map,otherMap;Player bot,member;bot.map=member.map=&map;
 Unit boss;boss.entry=16524;boss.map=&map;PlayerbotAI ai{&bot};ai.attackers={1};ai.units[1]=&boss;
 Group group;GroupReference ref{&member};group.first=&ref;bot.group=&group;
 AranFlameWreathValue value{&bot,&ai};SpellEntry entry;entry.Id=30004;Spell cast{&entry};boss.current=&cast;
#ifdef MANGOSBOT_ZERO
 assert(!value.Calculate());bot.auras={29946};member.auras={29946};assert(!value.Calculate());
#else
 assert(value.Calculate());cast.state=SPELL_STATE_FINISHED;assert(!value.Calculate());
 boss.current=nullptr;member.auras={29946};assert(value.Calculate());
 member.map=&otherMap;assert(!value.Calculate());member.map=&map;
 member.phase=2;assert(!value.Calculate());member.phase=1;
 member.teleport=true;assert(!value.Calculate());member.teleport=false;
 boss.phase=2;assert(!value.Calculate());boss.phase=1;
 member.alive=false;assert(!value.Calculate());member.alive=true;
 member.auras.clear();assert(!value.Calculate());bot.auras={29946};assert(value.Calculate());
 boss.combat=false;assert(!value.Calculate());boss.combat=true;
 boss.entry=15690;assert(!value.Calculate());boss.entry=16524;
 bot.mapId=0;assert(!value.Calculate());bot.mapId=532;
 bot.charmed=true;assert(!value.Calculate());bot.charmed=false;
 bot.teleport=true;assert(!value.Calculate());bot.teleport=false;
#endif
 // Execute stops a current chase, not stationary healing/casting or the aura.
 ai.context.hold.value=true;AranFlameWreathHoldAction hold;hold.bot=&bot;hold.ai=&ai;
 assert(!hold.isUseful());bot.motion.kind=1;assert(hold.isUseful());Event event;
 assert(hold.Execute(event) && ai.stopped==1 && !hold.isUseful());
 bot.mapId=0;assert(!hold.Execute(event) && ai.stopped==1);bot.mapId=532;
 PreserveAranFlameWreathMultiplier multiplier{&ai};MovementAction move;AttackAction attack;Action heal;
 assert(multiplier.GetValue(&move)==0 && multiplier.GetValue(&attack)==1 && multiplier.GetValue(&heal)==1);
 CastSpellAction spell;spell.spellId=1;entry.Effect[0]=ORDINARY_DAMAGE;sServerFacade.spells[1]=entry;
 assert(!spell.HasMovementEffect() && multiplier.GetValue(&spell)==1);
 for(unsigned effect:{unsigned(SPELL_EFFECT_CHARGE),unsigned(SPELL_EFFECT_LEAP),unsigned(SPELL_EFFECT_TELEPORT_UNITS),unsigned(SPELL_EFFECT_TELEPORT_UNITS_FACE_CASTER)
#ifndef MANGOSBOT_ZERO
 ,unsigned(SPELL_EFFECT_LEAP_BACK),unsigned(SPELL_EFFECT_CHARGE_DEST)
#endif
#ifdef MANGOSBOT_TWO
 ,unsigned(SPELL_EFFECT_JUMP),unsigned(SPELL_EFFECT_JUMP_DEST)
#endif
 }){sServerFacade.spells[1].Effect[2]=effect;assert(spell.HasMovementEffect() && multiplier.GetValue(&spell)==0);}
 ai.context.hold.value=false;assert(multiplier.GetValue(&move)==1 && multiplier.GetValue(&spell)==1);
 // Prince: only the actual live boss and same-instance enfeebled members count.
 bot.auras.clear();member.auras={30843};boss.current=nullptr;boss.entry=15690;
 PrinceMalchezaarTooCloseTrigger prince;prince.bot=&bot;prince.ai=&ai;
 assert(prince.IsActive());boss.victim=&bot;assert(!prince.IsActive());boss.victim=nullptr;
 member.map=&otherMap;assert(!prince.IsActive());member.map=&map;
 bot.group=nullptr;assert(!prince.EnfeeblePart() && !prince.IsActive());bot.group=&group;
 boss.entry=1;assert(!prince.IsActive());boss.entry=15690;
 boss.map=&otherMap;assert(!prince.IsActive());boss.map=&map;
 member.auras.clear();assert(!prince.IsActive());
 std::cout<<"PASS: native-effect movement gate, Flame Wreath lifecycle/roles/instance, normal casts retained, Prince target/aura scope\n";
}
'''.replace("__METHODS__", methods)
for expansion in ("ZERO", "ONE", "TWO"):
    with tempfile.TemporaryDirectory(prefix="mantech-karazhan-policy-") as tmp:
        tmp = Path(tmp)
        (tmp / "test.cpp").write_text(code)
        subprocess.run(["cl", "/nologo", "/EHsc", "/std:c++17", f"/DMANGOSBOT_{expansion}",
                        "test.cpp", "/Fe:test.exe"], cwd=tmp, check=True)
        subprocess.run([str(tmp / "test.exe")], check=True)
for path in ("actions/ActionContext.h", "triggers/TriggerContext.h", "generic/KarazhanDungeonStrategies.cpp"):
    assert "aran hold position" in (base / path).read_text()
strategy = (base / "generic/KarazhanDungeonStrategies.cpp").read_text()
assert "KarazhanDungeonStrategy::InitReactionMultipliers" in strategy
assert "KarazhanDungeonStrategy::InitCombatMultipliers" in strategy
header = (base / "generic/KarazhanDungeonStrategies.h").read_text()
kara = block(header, "class KarazhanDungeonStrategy")
nether = block(header, "class NetherspiteFightStrategy")
for method in ("InitCombatTriggers", "InitReactionTriggers", "InitCombatMultipliers", "InitReactionMultipliers"):
    assert kara.count(method + "(") == 1, f"Karazhan must declare {method} exactly once"
assert nether.count("InitCombatMultipliers(") == 1
assert "InitReactionMultipliers(" not in nether
