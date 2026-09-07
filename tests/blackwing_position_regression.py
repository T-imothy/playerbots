"""Actual BWL value/action/arbitration bodies, native geometry and controlled lifecycle."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root / 'playerbot/strategy/values/BlackwingLairPositionValue.cpp').read_text()
action = (root / 'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
multiplier = (root / 'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods = '\n'.join((block(value, 'uint32 ai::BurningAdrenalineAura('),
                     block(value, 'bool ai::BlackwingLairBurstThreats('),
                     block(value, 'EncounterPosition BlackwingLairPositionValue::Calculate('),
                     block(action, 'bool BlackwingLairPositionAction::GetPlan('),
                     block(action, 'bool BlackwingLairPositionAction::isUseful('),
                     block(action, 'bool BlackwingLairPositionAction::Execute('),
                     block(multiplier, 'float PreserveBlackwingLairPositionMultiplier::GetValue(')))
code = r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <list>
#include "__GEOMETRY__"
using uint32=unsigned;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}
 bool IsEmpty()const{return !id;}};
struct Map{};
struct Unit{virtual ~Unit()=default;Map* map=nullptr;unsigned phase=1,entry=0;ObjectGuid guid;
 bool world=true,alive=true,combat=true,charmed=false;float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;
 virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}unsigned GetEntry(){return entry;}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}
 ObjectGuid GetObjectGuid(){return guid;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
constexpr int IDLE_MOTION_TYPE=0;
struct Motion{int GetCurrentMovementGeneratorType(){return 0;}};
struct Group;
struct Player:Unit{unsigned mapId=469,instance=1;bool teleport=false;Group* group=nullptr;
 bool IsStopped(){return true;}Motion motion;Motion* GetMotionMaster(){return &motion;}
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}
 float GetDistance(float xx,float yy,float zz){return std::sqrt((x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz));}};
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai{struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;
 encounter::Point destination;};}
using namespace ai;
struct Cached{EncounterPosition value;EncounterPosition Get(){return value;}};
struct AttackerCache{std::list<ObjectGuid> value;std::list<ObjectGuid>& Get(){return value;}};
struct Context{Cached cached;AttackerCache attackers;template<class T>auto* GetValue(const char*){
 if constexpr(std::is_same_v<T,EncounterPosition>)return &cached;else return &attackers;}};
struct PlayerbotAI{Player* bot;Context context;std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;
 bool validPath=true,canMove=true;unsigned checked=0,moves=0;Player* GetBot(){return bot;}
 Context* GetAiObjectContext(){return &context;}bool CanMove(){return canMove;}void StopMoving(){}
 Unit* GetUnit(ObjectGuid guid){auto i=units.find(guid);return i==units.end()?nullptr:i->second;}};
struct Event{};
struct Action{virtual ~Action()=default;};
struct MovementAction:Action{};struct AttackAction:MovementAction{};struct MoveAwayFromHazard:MovementAction{};
struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
namespace ai{
 unsigned radiusQueries=0,lastRadius=0;float radius=10;
 float NativeEncounterSpellRadius(unsigned id){++radiusQueries;lastRadius=id;return radius;}
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&){++ai->checked;return ai->validPath;}
 uint32 BurningAdrenalineAura(Unit*);
 bool BlackwingLairBurstThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 struct BlackwingLairPositionValue{Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct BlackwingLairPositionAction:MovementAction{PlayerbotAI* ai;Player* bot;
  BlackwingLairPositionAction(PlayerbotAI* a):ai(a),bot(a->bot){}
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);void SetDuration(unsigned){}
  bool IsReaction(){return true;}
  bool MoveTo(unsigned,float,float,float,bool idle,bool react,bool noPath,bool ignoreEnemies){
   assert(!idle&&react&&!noPath&&ignoreEnemies);++ai->moves;return true;}};
 struct PreserveBlackwingLairPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
}
#define AI_VALUE(type,name) ai->attackers
__METHODS__
int main(){
 Map map,otherMap;Player bot,ally;bot.map=ally.map=&map;bot.guid=1;ally.guid=2;ally.x=1;
 Group group,otherGroup;GroupReference ref{&ally};group.first=&ref;bot.group=ally.group=&group;
 Unit boss;boss.entry=13020;boss.guid=3;boss.map=&map;
 PlayerbotAI ai{&bot};ai.units={{1,&bot},{2,&ally},{3,&boss}};ai.context.attackers.value={3};
 BlackwingLairPositionValue value{&bot,&ai};BlackwingLairPositionAction action(&ai);EncounterPosition plan;Event event;
 auto get=[&](){ai.context.cached.value=value.Calculate();return BlackwingLairPositionAction::GetPlan(&ai,plan);};
 assert(!get());bot.auras={23620};assert(get()&&plan.source==bot.guid&&plan.spell==23620&&lastRadius==23478);
 assert(encounter::Distance2d(plan.destination,{ally.x,0,0})>=12&&action.isUseful());
 assert(action.Execute(event)&&ai.moves==1);
 ally.x=plan.destination.x;ally.y=plan.destination.y;
 assert(!action.Execute(event)&&ai.moves==1);ally.x=1;ally.y=0; // Fresh position invalidates old destination.
 ai.validPath=false;assert(!action.Execute(event)&&ai.moves==1);ai.checked=0;assert(!get()&&ai.checked<=8);ai.validPath=true;
 assert(get());boss.victim=&bot;assert(!BlackwingLairPositionAction::GetPlan(&ai,plan)&&!get()); // Fresh tank protection.
 boss.victim=&ally;assert(get()); // Native victim change allows former tank to separate.
 boss.alive=false;boss.combat=false;bot.combat=false;ai.context.attackers.value.clear();ai.units.erase(3);assert(get());
 // Aura removal, not boss lifetime, ends post-kill separation.
 bot.auras.clear();assert(!BlackwingLairPositionAction::GetPlan(&ai,plan)&&!get());
 ally.auras={18173};assert(get()&&plan.source==ally.guid&&plan.spell==18173);
 ally.teleport=true;assert(!BlackwingLairPositionAction::GetPlan(&ai,plan)&&!get());ally.teleport=false;
 ally.charmed=true;assert(!get());ally.charmed=false;
 ally.phase=2;assert(!get());ally.phase=1;ally.map=&otherMap;assert(!get());ally.map=&map;
 ally.alive=false;assert(!get());ally.alive=true;ally.z=20;assert(!get());ally.z=0;
 ally.x=60;assert(!get());ally.x=1;
 assert(get());ally.group=&otherGroup;assert(!BlackwingLairPositionAction::GetPlan(&ai,plan)&&!get());ally.group=&group;
 assert(get());++bot.instance;assert(!BlackwingLairPositionAction::GetPlan(&ai,plan));--bot.instance;
 bot.teleport=true;assert(!get());bot.teleport=false;bot.charmed=true;assert(!get());bot.charmed=false;
 bot.mapId=0;assert(!get());bot.mapId=469;bot.alive=false;assert(!get());bot.alive=true;
 bot.group=nullptr;assert(!get());bot.group=&group;
 radius=0;assert(!get());radius=46;assert(!get());radius=10;assert(get());
 PreserveBlackwingLairPositionMultiplier multiplier{&ai};MovementAction follow;AttackAction attack;MoveAwayFromHazard escape;
 CastSpellAction cast;Action ordinary;
 assert(multiplier.GetValue(&follow)==0&&multiplier.GetValue(&attack)==1&&multiplier.GetValue(&escape)==1);
 assert(multiplier.GetValue(&action)==1&&multiplier.GetValue(&cast)==1&&multiplier.GetValue(&ordinary)==1);
 cast.movement=true;assert(multiplier.GetValue(&cast)==0);ally.auras.clear();
 assert(multiplier.GetValue(&cast)==1&&multiplier.GetValue(&follow)==1&&!get());
 std::cout<<"PASS: actual BWL aura/radius/paths, tank preservation, post-kill lifetime, phase/group and movement arbitration\n";
}
'''.replace('__GEOMETRY__', (root / 'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__', methods)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-bwl-position-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
strategy = (root / 'playerbot/strategy/generic/BlackwingLairDungeonStrategies.cpp').read_text()
# DungeonMultipliers includes core declarations with a global Action name.
# The existing suppression-room override must remain explicitly in ai::.
assert 'float GetValue(ai::Action* action) override' in strategy
for state in ('Combat', 'NonCombat', 'Reaction'):
    assert 'blackwing lair safe position' in block(strategy, f'void BlackwingLairDungeonStrategy::Init{state}Triggers(')
for state in ('Combat', 'NonCombat'):
    assert 'PreserveBlackwingLairPositionMultiplier' in block(strategy, f'void BlackwingLairDungeonStrategy::Init{state}Multipliers(')
