"""Compile actual Naxx burst value, action and multiplier against native geometry."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/NaxxramasPositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/NaxxramasDungeonActions.cpp').read_text()
multiplier = (root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods = '\n'.join([block(value, signature) for signature in (
    'uint32 ai::NaxxramasBurstAura(', 'float ai::NaxxramasBurstRadius(',
    'bool ai::NaxxramasBurstThreats(', 'EncounterPosition NaxxramasPositionValue::Calculate(')] +
    [block(action, signature) for signature in ('bool NaxxramasPositionAction::GetPlan(',
    'bool NaxxramasPositionAction::isUseful(', 'bool NaxxramasPositionAction::Execute(')] +
    [block(multiplier, 'float PreserveNaxxramasPositionMultiplier::GetValue(')])
code = r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <list>
#include "__GEOMETRY__"
using uint32=unsigned;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}bool IsEmpty()const{return !id;}};
struct Map{};
struct Unit{virtual ~Unit()=default;Map* map=nullptr;unsigned phase=1,entry=0;ObjectGuid guid;
 bool world=true,alive=true,combat=true,charmed=false;float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;
 virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}unsigned GetEntry(){return entry;}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}
 ObjectGuid GetObjectGuid(){return guid;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
struct Group;
struct Player:Unit{unsigned mapId=533,instance=1;bool teleport=false;Group* group=nullptr;
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}
 float GetDistance(float xx,float yy,float zz){return std::sqrt((x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz));}};
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai{struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};}
using namespace ai;
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<EncounterPosition> position;Value<std::list<ObjectGuid>> attackers;
 template<class T>Value<T>* GetValue(const char*){if constexpr(std::is_same_v<T,EncounterPosition>)return &position;else return &attackers;}};
struct PlayerbotAI{Player* bot;Context context;std::map<unsigned,Unit*> units;bool validPath=true,canMove=true;unsigned checked=0,moves=0;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}bool CanMove(){return canMove;}
 Unit* GetUnit(ObjectGuid guid){auto i=units.find(guid);return i==units.end()?nullptr:i->second;}};
struct Event{};
struct Action{virtual ~Action()=default;};struct MovementAction:Action{};struct AttackAction:MovementAction{};
struct MoveAwayFromHazard:MovementAction{};struct VoidZoneMoveAwayAction:MovementAction{};
struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
namespace ai{
 std::map<unsigned,float> radii{{28206,20.0f},{28322,8.0f},{27820,10.0f},{28062,13.0f},{28085,13.0f}};
 float NativeEncounterSpellRadius(unsigned id){return radii[id];}
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&){++ai->checked;return ai->validPath;}
 uint32 NaxxramasBurstAura(Unit*);float NaxxramasBurstRadius(uint32);
 bool NaxxramasBurstThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 struct NaxxramasPositionValue{Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct NaxxramasPositionAction:MovementAction{PlayerbotAI* ai;Player* bot;NaxxramasPositionAction(PlayerbotAI* a):ai(a),bot(a->bot){}
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);bool IsReaction(){return true;}
  bool MoveTo(unsigned,float,float,float,bool idle,bool react,bool noPath,bool ignoreEnemies){assert(!idle&&react&&!noPath&&ignoreEnemies);++ai->moves;return true;}};
 struct PreserveNaxxramasPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
}
__METHODS__
int main(){
 Map map,otherMap;Player bot,ally,second;bot.map=ally.map=second.map=&map;bot.guid=1;ally.guid=2;second.guid=4;ally.x=1;second.y=1;
 Group group,otherGroup;GroupReference r2{&second},r1{&ally,&r2};group.first=&r1;bot.group=ally.group=second.group=&group;
 Unit boss;boss.entry=15931;boss.guid=3;boss.map=&map;
 PlayerbotAI ai{&bot};ai.units={{1,&bot},{2,&ally},{3,&boss},{4,&second}};ai.context.attackers.value={3};
 NaxxramasPositionValue value{&bot,&ai};NaxxramasPositionAction action(&ai);EncounterPosition plan;Event event;
 auto get=[&](){ai.context.position.value=value.Calculate();return NaxxramasPositionAction::GetPlan(&ai,plan);};
 assert(!get());bot.auras={28169};assert(get()&&plan.source==bot.guid&&plan.spell==28169);
 assert(encounter::Distance2d(plan.destination,{ally.x,ally.y,0})>=22&&action.isUseful());
 assert(action.Execute(event)&&ai.moves==1);
 // Moving players can invalidate a previously safe cached destination.
 ally.x=plan.destination.x;ally.y=plan.destination.y;assert(!action.Execute(event)&&ai.moves==1);ally.x=1;ally.y=0;
 ai.validPath=false;assert(!action.Execute(event));ai.checked=0;assert(!get()&&ai.checked<=8);ai.validPath=true;
 assert(get());boss.victim=&bot;assert(!NaxxramasPositionAction::GetPlan(&ai,plan)&&!get());boss.victim=&ally;
 assert(get());boss.alive=false;boss.combat=false;ai.context.attackers.value.clear();bot.combat=false;assert(get());
 bot.auras.clear();assert(!NaxxramasPositionAction::GetPlan(&ai,plan)&&!get());
 ally.auras={27819};assert(get()&&plan.spell==27819&&plan.source==ally.guid);
 second.auras={28169};assert(get()); // Different native burst radii must both be avoided.
 assert(encounter::Distance2d(plan.destination,{second.x,second.y,0})>=22);second.auras.clear();
 ally.teleport=true;assert(!NaxxramasPositionAction::GetPlan(&ai,plan)&&!get());ally.teleport=false;
 ally.charmed=true;assert(!get());ally.charmed=false;ally.phase=2;assert(!get());ally.phase=1;
 ally.map=&otherMap;assert(!get());ally.map=&map;ally.alive=false;assert(!get());ally.alive=true;
 ally.z=20;assert(!get());ally.z=0;ally.x=100;assert(!get());ally.x=1;
 assert(get());ally.group=&otherGroup;assert(!NaxxramasPositionAction::GetPlan(&ai,plan));ally.group=&group;
 assert(get());++bot.instance;assert(!NaxxramasPositionAction::GetPlan(&ai,plan));--bot.instance;
 bot.teleport=true;assert(!get());bot.teleport=false;bot.charmed=true;assert(!get());bot.charmed=false;
 bot.mapId=0;assert(!get());bot.mapId=533;bot.alive=false;assert(!get());bot.alive=true;bot.group=nullptr;assert(!get());bot.group=&group;
 radii[27820]=0;assert(!get());radii[27820]=100;assert(!get());radii[27820]=10;assert(get());
 PreserveNaxxramasPositionMultiplier multiplier{&ai};MovementAction follow;AttackAction attack;MoveAwayFromHazard escape;
 VoidZoneMoveAwayAction fissure;CastSpellAction cast;
 assert(multiplier.GetValue(&follow)==0&&multiplier.GetValue(&attack)==1&&multiplier.GetValue(&escape)==1);
 assert(multiplier.GetValue(&action)==1&&multiplier.GetValue(&cast)==1&&multiplier.GetValue(&fissure)==1);
 cast.movement=true;assert(multiplier.GetValue(&cast)==0);ally.auras.clear();
 assert(multiplier.GetValue(&cast)==1&&multiplier.GetValue(&follow)==1&&!get());
 // Thaddius's native charge damages both opposite-charge and uncharged
 // recipients; matching charges may remain together and keep native buffs.
 bot.auras={28059};ally.auras={28059};second.auras={28059};assert(!get());
 ally.auras={28084};assert(get()&&plan.spell==28059);
 assert(encounter::Distance2d(plan.destination,{ally.x,ally.y,ally.z})>=15);
 assert(action.Execute(event));
 bot.auras={28084};assert(!NaxxramasPositionAction::GetPlan(&ai,plan));
 assert(get()); // second still has the opposite charge
 bot.auras.clear();assert(get()); // no charge is not immunity to either payload
 ally.auras.clear();second.auras.clear();assert(!get());
 ally.auras={28059};assert(get()&&plan.source==ally.guid);
 bot.auras={28059};assert(!NaxxramasPositionAction::GetPlan(&ai,plan));
 second.auras={28084};assert(get());
 boss.entry=15928;boss.alive=true;boss.combat=true;boss.victim=&bot;ai.context.attackers.value={boss.guid};
 assert(!NaxxramasPositionAction::GetPlan(&ai,plan)&&!get()); // preserve the active tank
 boss.victim=&ally;assert(get());boss.alive=false;ai.context.attackers.value.clear();assert(get());
 bot.auras.clear();ally.auras.clear();second.auras.clear();assert(!get());
 std::cout<<"PASS: actual Naxx burst radii, mixed carriers, fresh destination, tanks, native path bounds and lifecycle\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-naxx-burst-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/NaxxramasDungeonStrategies.cpp').read_text()
for state in ('Combat','NonCombat','Reaction'):
    assert 'naxxramas safe position' in block(strategy,f'void NaxxramasDungeonStrategy::Init{state}Triggers(')
