"""Compile the actual Netherspite value, action and movement arbitration.

Native-shaped world/path interfaces are controlled here; this is not a raid clear.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
base = root / 'playerbot/strategy'
methods = []
for filename, signatures in (
    ('values/EncounterPositionValue.cpp', ('EncounterPosition NetherspitePositionValue::Calculate(',)),
    ('actions/KarazhanDungeonActions.cpp', ('bool NetherspitePositionAction::GetPlan(', 'bool NetherspitePositionAction::isUseful(', 'bool NetherspitePositionAction::ShouldReactionInterruptCast(',
                                          'bool NetherspitePositionAction::Execute(')),
    ('generic/DungeonMultipliers.cpp', ('float PreserveNetherspitePositionMultiplier::GetValue(',
                                      'float PreserveMoltenCorePositionMultiplier::GetValue(')),
):
    methods.extend(block((base / filename).read_text(), signature) for signature in signatures)
code = r'''
#include <cassert>
#include <map>
#include <set>
#include <list>
#include <string>
#include <iostream>
#include <functional>
#include "__GEOMETRY__"
using uint32=unsigned;using uint64=uint64_t;
constexpr int CLASS_HUNTER=3,POWER_MANA=0;
struct ObjectGuid {unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}
 uint64 GetRawValue()const{return id;}bool IsEmpty()const{return !id;}};
struct Aura {unsigned stack=0;unsigned GetStackAmount(){return stack;}};
struct Map {};
struct Unit {unsigned entry=0,phase=1;ObjectGuid guid;Map* map=nullptr;
 bool world=true,alive=true,combat=true;ObjectGuid spawner;float x=0,y=0,z=0;
 ObjectGuid GetSpawnerGuid(){return spawner;}
 std::set<unsigned> auras;std::map<unsigned,Aura> buffs;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 Map* GetMap(){return map;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}
 bool HasAura(unsigned id){return auras.count(id);}float GetCombatReach(){return 3;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(Unit* other){return std::hypot(x-other->x,y-other->y);}
};
constexpr int IDLE_MOTION_TYPE=0;
struct Motion {int type=1;int GetCurrentMovementGeneratorType(){return type;}};
struct Group;struct PlayerbotAI;
struct Player:Unit {bool teleport=false,charmed=false,session=true,tank=false,healer=false,ranged=false;
 Motion motion;bool stopped=true;bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}
 float GetDistance(float xx,float yy,float zz){return std::sqrt((x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz));}
 using Unit::GetDistance;
 unsigned mapId=532,instance=1,cls=1,mana=100;Group* group=nullptr;PlayerbotAI* controller=nullptr;
 bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 bool IsInMap(Unit* unit){return world&&unit->world&&map==unit->map&&phase==unit->phase;}
 unsigned GetMapId(){return mapId;}unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool GetSession(){return session;}PlayerbotAI* GetPlayerbotAI(){return controller;}
 unsigned getClass(){return cls;}unsigned GetMaxPower(int){return mana;}
 void UpdateAllowedPositionZ(float,float,float&){}
};
struct GroupReference {Player* player;GroupReference* following=nullptr;
 Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai {
struct EncounterPosition {bool active=false;unsigned map=0,instance=0;ObjectGuid boss,source;encounter::Point destination;};
}
using namespace ai;
struct Cached {EncounterPosition plan;std::function<EncounterPosition()> refresh;
 void Reset(){if(refresh)plan=refresh();}EncounterPosition Get(){return plan;}};
struct Context {Cached cache;template<class T>Cached* GetValue(const char*){return &cache;}};
struct PlayerbotAI {Player* bot;bool real=false,validPath=true,canMove=true;unsigned pathChecks=0,moves=0,stops=0;void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
 bool mcHold=false,mcPriority=false;std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;Context context;
 Player* GetBot(){return bot;}bool IsRealPlayer(){return real;}
 bool IsTank(Player* p){return p->tank;}bool IsHeal(Player* p){return p->healer;}bool IsRanged(Player* p){return p->ranged;}
 Context* GetAiObjectContext(){return &context;}bool CanMove(){return canMove;}
 Unit* GetUnit(ObjectGuid id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}
 Aura* GetAura(unsigned id,Player* p){auto i=p->buffs.find(id);return i==p->buffs.end()?nullptr:&i->second;}
};
std::list<Unit*> grid;
namespace MaNGOS {
struct AllCreaturesOfEntryInRangeCheck {unsigned entry;AllCreaturesOfEntryInRangeCheck(Player*,unsigned e,float):entry(e){}};
template<class T>struct UnitListSearcher {std::list<Unit*>& found;T& check;
 UnitListSearcher(std::list<Unit*>& f,T& c):found(f),check(c){}};
}
namespace Cell {template<class T>void VisitAllObjects(Player*,T& searcher,float){
 for(Unit* unit:grid)if(unit&&unit->entry==searcher.check.entry)searcher.found.push_back(unit);}}
struct Event {};
namespace ai {
bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition& plan){assert(plan.active);++ai->pathChecks;return ai->validPath;}
struct Action {std::string name;virtual ~Action()=default;std::string getName(){return name;}};
struct MovementAction:Action {};
struct AttackAction:MovementAction {};
struct MoveAwayFromHazard:MovementAction {};
struct VoidZoneMoveAwayAction:MovementAction {};
struct CastSpellAction:Action {bool movement=false;bool HasMovementEffect(){return movement;}};
struct NetherspitePositionValue {Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
struct NetherspitePositionAction:MovementAction {Player* bot;PlayerbotAI* ai;
 static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;void SetDuration(unsigned){}bool Execute(Event&);bool IsReaction(){return false;}
 bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
struct MoltenCorePositionAction:MovementAction {static bool GetPlan(PlayerbotAI* ai,EncounterPosition&){return ai->mcHold;}};
struct MoltenCorePriorityTargetAction {PlayerbotAI* ai;MoltenCorePriorityTargetAction(PlayerbotAI* p):ai(p){}
 Unit* GetTarget(){return ai->mcPriority?ai->bot:nullptr;}};
struct PreserveNetherspitePositionMultiplier {PlayerbotAI* ai;float GetValue(Action*);};
struct PreserveMoltenCorePositionMultiplier {PlayerbotAI* ai;float GetValue(Action*);};
}
#define AI_VALUE(type,key) ai->attackers
__METHODS__
int main(){
 Map map,other;Player bot,human;Unit boss,red;bot.map=human.map=boss.map=red.map=&map;
 bot.guid=1;human.guid=2;boss.guid=3;red.guid=4;bot.tank=true;bot.x=10;bot.y=5;
 boss.entry=15689;red.entry=17369;red.x=50;human.x=20;human.y=0;
 PlayerbotAI ai{&bot};bot.controller=&ai;ai.units={{1,&bot},{2,&human},{3,&boss},{4,&red}};ai.attackers={3};grid={&red};
 GroupReference humanRef{&human},selfRef{&bot,&humanRef};Group group{&selfRef};bot.group=human.group=&group;red.spawner=boss.guid;
 NetherspitePositionValue value{&bot,&ai};EncounterPosition plan;
 ai.context.cache.refresh=[&](){return value.Calculate();};
 auto calculate=[&](){ai.pathChecks=0;ai.context.cache.plan=value.Calculate();return ai.context.cache.plan.active;};
#ifdef MANGOSBOT_ZERO
 assert(!calculate()); // Karazhan cannot activate in Classic.
#else
 assert(!calculate()); // A human actually blocking the red beam has precedence.
 human.group=nullptr;assert(calculate());human.group=&group; // stale roster entry cannot claim a beam
 human.y=10;red.spawner=99;assert(!calculate());red.spawner=boss.guid;human.y=0;
 human.phase=2;assert(calculate()); // Other-phase players must not reserve our beam.
 assert(ai.context.cache.plan.source==red.guid&&ai.pathChecks==1);
 human.phase=1;assert(!calculate());human.world=false;assert(calculate());human.world=true;
 human.teleport=true;assert(calculate());human.teleport=false;
 human.x=20;human.y=10;assert(calculate());
 assert(NetherspitePositionAction::GetPlan(&ai,plan));
 boss.phase=2;assert(!NetherspitePositionAction::GetPlan(&ai,plan));assert(!calculate());boss.phase=1;
 red.phase=2;assert(!calculate());red.phase=1;assert(calculate());
 red.map=&other;assert(!NetherspitePositionAction::GetPlan(&ai,plan));assert(!calculate());red.map=&map;
 bot.charmed=true;assert(!calculate());bot.charmed=false;
 boss.auras={38542};assert(!calculate());boss.auras.clear();
 bot.auras={38637};assert(!calculate()); // exhaustion alone must not drag us back toward a beam
 bot.y=0;assert(calculate());
 assert(!encounter::InBeam(ai.context.cache.plan.destination,{50,0,0},{0,0,0})); // exhaustion => step aside, never remove aura
 assert(bot.HasAura(38637));bot.auras.clear();bot.y=5;
 ai.validPath=false;assert(!calculate()&&ai.pathChecks==4);ai.validPath=true;assert(calculate());
 // A hazard/path failure between plan creation and execution must veto the move.
 NetherspitePositionAction move;move.bot=&bot;move.ai=&ai;Event event;
 ai.validPath=false;assert(!move.Execute(event)&&ai.moves==0);ai.validPath=true;
 assert(move.Execute(event)&&ai.moves==1);
 // A human enters the assigned beam after selection: recompute before dispatch.
 assert(calculate());human.y=0;assert(!move.Execute(event)&&ai.moves==1);human.y=10;assert(calculate());
 bot.group=nullptr;assert(!NetherspitePositionAction::GetPlan(&ai,plan));bot.group=&group;
 bot.teleport=true;assert(!move.Execute(event));bot.teleport=false;assert(calculate());
 ai.units.erase(4);assert(!NetherspitePositionAction::GetPlan(&ai,plan));ai.units[4]=&red;
 // At the assigned beam point, stop a surviving chase without interrupting a stationary cast.
 assert(calculate());auto safe=ai.context.cache.plan.destination;bot.x=safe.x;bot.y=safe.y;bot.z=safe.z;
 assert(calculate()&&move.isUseful()&&!move.ShouldReactionInterruptCast());
 unsigned oldMoves=ai.moves;assert(move.Execute(event)&&ai.moves==oldMoves&&ai.stops==1&&!move.isUseful());
 bot.x=10;bot.y=5;assert(calculate());
 PreserveNetherspitePositionMultiplier multiplier{&ai};
 MovementAction chase;AttackAction attack;MoveAwayFromHazard escape;Action stationary;CastSpellAction spell;
 assert(multiplier.GetValue(nullptr)==1&&multiplier.GetValue(&chase)==0);
 assert(multiplier.GetValue(&attack)==1&&multiplier.GetValue(&escape)==1&&multiplier.GetValue(&stationary)==1);
 assert(multiplier.GetValue(&spell)==1);spell.movement=true;assert(multiplier.GetValue(&spell)==0);
 boss.auras={38542};assert(multiplier.GetValue(&spell)==1&&multiplier.GetValue(&chase)==1);boss.auras.clear();
#endif
 PreserveMoltenCorePositionMultiplier mc{&ai};MovementAction chase2;CastSpellAction charge;charge.movement=true;
 CastSpellAction heal;MoveAwayFromHazard escape2;AttackAction attack2;Action assist;assist.name="dps assist";
 assert(mc.GetValue(&charge)==1);ai.mcHold=true;
 assert(mc.GetValue(&charge)==0&&mc.GetValue(&chase2)==0);
 assert(mc.GetValue(&heal)==1&&mc.GetValue(&attack2)==1&&mc.GetValue(&escape2)==1&&mc.GetValue(nullptr)==1);
 ai.mcHold=false;assert(mc.GetValue(&charge)==1);ai.mcPriority=true;assert(mc.GetValue(&assist)==0);
 ai.mcPriority=false;assert(mc.GetValue(&assist)==1);
 std::cout<<"PASS: actual Netherspite value/plan/action, phase/human/exhaustion, bounded fresh paths and native movement-spell arbitration\n";
}
'''.replace('__GEOMETRY__', (base / 'EncounterGeometry.h').as_posix()).replace('__METHODS__', '\n'.join(methods))
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-netherspite-runtime-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
