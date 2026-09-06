"""Actual Gruul value/action/hold code in all eras; native movement is mocked.

This checks policy and lifecycle, not a live encounter or pathfinding result.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/GruulPositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/DungeonActions.cpp').read_text()
multiplier = (root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods = '\n'.join([block(value, s) for s in (
    'bool ai::GruulShatterThreats(', 'EncounterPosition GruulPositionValue::Calculate(')] +
    [block(action, s) for s in ('bool GruulSpreadAction::GetPlan(',
    'bool GruulSpreadAction::isUseful(', 'bool GruulSpreadAction::ShouldReactionInterruptCast(',
    'bool GruulSpreadAction::Execute(')] +
    [block(multiplier, 'float PreserveGruulSpreadMultiplier::GetValue(')])
code = r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <list>
#include "__GEOMETRY__"
using uint32=unsigned;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}
 unsigned GetRawValue()const{return id;}};
struct Map{};
struct Unit{virtual ~Unit()=default;Map* map=nullptr;unsigned phase=1,entry=0;ObjectGuid guid;
 bool world=true,alive=true,combat=true,charmed=false;float x=0,y=0,z=0,reach=1.5f;std::set<unsigned> auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}unsigned GetEntry(){return entry;}
 bool HasAura(unsigned id){return auras.count(id);}float GetCombatReach(){return reach;}
 ObjectGuid GetObjectGuid(){return guid;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
constexpr unsigned IDLE_MOTION_TYPE=0;
struct Motion{unsigned type=0;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Group;
struct Player:Unit{unsigned mapId=565,instance=1;bool teleport=false,stopped=true;Group* group=nullptr;Motion motion;
 bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}
 float GetDistance(float xx,float yy,float zz){return std::sqrt((x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz));}};
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai{struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};}
using namespace ai;
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<EncounterPosition> position;Value<std::list<ObjectGuid>> attackers;
 template<class T>Value<T>* GetValue(const char*){if constexpr(std::is_same_v<T,EncounterPosition>)return &position;else return &attackers;}};
struct PlayerbotAI{Player* bot;Context context;std::map<unsigned,Unit*> units;bool validPath=true,canMove=true,unsafeHeight=false;
 unsigned checked=0,moves=0,stops=0;Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}
 bool CanMove(){return canMove;}void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
 Unit* GetUnit(ObjectGuid guid){auto i=units.find(guid);return i==units.end()?nullptr:i->second;}};
struct Event{};
struct Action{virtual ~Action()=default;};struct MovementAction:Action{};struct AttackAction:MovementAction{};
struct MoveAwayFromHazard:MovementAction{};
struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
namespace ai{
 float nativeRadius=20;
 float NativeEncounterSpellRadius(unsigned id){assert(id==33671);return nativeRadius;}
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition& p){++ai->checked;
  if(ai->unsafeHeight)p.destination={0,0,0};return ai->validPath;}
 bool GruulShatterThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 struct GruulPositionValue{Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct GruulSpreadAction:MovementAction{PlayerbotAI* ai;Player* bot;GruulSpreadAction(PlayerbotAI* a):ai(a),bot(a->bot){}
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);bool ShouldReactionInterruptCast()const;
  bool IsReaction(){return true;}void SetDuration(unsigned ms){assert(ms==100);}
  bool MoveTo(unsigned,float,float,float,bool idle,bool react,bool noPath,bool ignoreEnemies){assert(!idle&&react&&!noPath&&ignoreEnemies);++ai->moves;return true;}};
 struct PreserveGruulSpreadMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
}
__METHODS__
int main(){
 Map map,otherMap;Player bot,ally,second;bot.map=ally.map=second.map=&map;bot.guid=1;ally.guid=2;second.guid=4;ally.x=1;second.y=1;
 Group group,otherGroup;GroupReference r2{&second},r1{&ally,&r2};group.first=&r1;bot.group=ally.group=second.group=&group;
 Unit boss;boss.entry=19044;boss.guid=3;boss.map=&map;
 PlayerbotAI ai{&bot};ai.units={{1,&bot},{2,&ally},{3,&boss},{4,&second}};ai.context.attackers.value={3};
 GruulPositionValue value{&bot,&ai};GruulSpreadAction action(&ai);EncounterPosition plan;Event event;
 auto get=[&](){ai.context.position.value=value.Calculate();return GruulSpreadAction::GetPlan(&ai,plan);};
 assert(!get());bot.auras={33572};
#ifdef MANGOSBOT_ZERO
 assert(!get()&&!action.Execute(event));
#else
 assert(get()&&plan.spell==33671&&plan.boss==boss.guid&&action.isUseful());
 assert(action.ShouldReactionInterruptCast()&&action.Execute(event)&&ai.moves==1);
 // Fresh group movement can make an old destination worse than standing still.
 ally.x=plan.destination.x;ally.y=plan.destination.y;second.x=ally.x;second.y=ally.y;
 assert(!action.Execute(event)&&ai.moves==1);ally.x=1;ally.y=0;second.x=0;second.y=1;
 ai.canMove=false;assert(!get()&&!action.Execute(event));ai.canMove=true; // native knockback, falling or Stoned
 ai.validPath=false;ai.checked=0;assert(!get()&&ai.checked<=9);ai.validPath=true;
 // A validator-adjusted point at our feet may stop movement, never starts a
 // fresh move into that overlap. Invalid paths themselves were rejected above.
 assert(get());ai.unsafeHeight=true;assert(action.Execute(event)&&ai.moves==1&&ai.stops==1);ai.unsafeHeight=false;ai.stops=0;
 // Already separated: stop an old chase, without interrupting a stationary heal.
 bot.x=50;assert(get());bot.stopped=false;bot.motion.type=1;
 assert(action.isUseful()&&!action.ShouldReactionInterruptCast()&&action.Execute(event)&&ai.stops==1);
 assert(!action.isUseful());bot.x=0;
 assert(get());bot.auras.clear();assert(!GruulSpreadAction::GetPlan(&ai,plan)&&!get());
 ally.auras={33652};assert(get()); // unaffected neighbors still avoid a native burst carrier
 ally.auras.clear();assert(!get());bot.auras={33572};assert(get());
 boss.alive=false;assert(!get());boss.alive=true;boss.combat=false;assert(!get());boss.combat=true;
 boss.charmed=true;assert(!get());boss.charmed=false;boss.entry=18831;assert(!get());boss.entry=19044;
 ai.context.attackers.value.clear();assert(!get());ai.context.attackers.value={3};
 Unit duplicate=boss;duplicate.guid=5;ai.units[5]=&duplicate;ai.context.attackers.value.push_back(5);assert(!get());ai.context.attackers.value={3};
 bot.teleport=true;assert(!get());bot.teleport=false;bot.charmed=true;assert(!get());bot.charmed=false;
 bot.mapId=0;assert(!get());bot.mapId=565;bot.alive=false;assert(!get());bot.alive=true;
 bot.group=nullptr;assert(!get());bot.group=&group;bot.combat=false;assert(!get());bot.combat=true;
 assert(get());++bot.instance;assert(!GruulSpreadAction::GetPlan(&ai,plan));--bot.instance;
 second.world=false;ally.teleport=true;assert(!get());ally.teleport=false;ally.charmed=true;assert(!get());ally.charmed=false;
 ally.phase=2;assert(!get());ally.phase=1;ally.map=&otherMap;assert(!get());ally.map=&map;
 ally.group=&otherGroup;assert(!get());ally.group=&group;ally.alive=false;assert(!get());ally.alive=true;
 ally.z=20;assert(!get());ally.z=0;second.world=true;
 nativeRadius=0;assert(!get());nativeRadius=100;assert(!get());nativeRadius=20;
 PreserveGruulSpreadMultiplier multiplier{&ai};MovementAction chase;AttackAction attack;MoveAwayFromHazard escape;CastSpellAction cast;
 assert(get());assert(multiplier.GetValue(&chase)==0&&multiplier.GetValue(&attack)==1&&multiplier.GetValue(&escape)==1);
 assert(multiplier.GetValue(&action)==1&&multiplier.GetValue(&cast)==1);cast.movement=true;assert(multiplier.GetValue(&cast)==0);
 bot.auras.clear();assert(multiplier.GetValue(&chase)==1&&multiplier.GetValue(&cast)==1);
#endif
 // Crowded geometry: minimize remaining overlap; no teleport, fictitious safe
 // point or unbounded candidate search when full separation cannot be achieved.
 std::vector<encounter::Circle> circles;
 for(int x=-2;x<=2;++x)for(int y=-2;y<=2;++y)circles.push_back({{float(x*12),float(y*12),0},22.5f});
 auto points=encounter::SpreadCandidates({0,0,0},circles,17);
 assert(points.size()==81&&encounter::SpreadOverlap(points.front(),circles)<encounter::SpreadOverlap({0,0,0},circles));
 for(auto p:points)assert(encounter::Distance2d(p,{0,0,0})<24.01f);
 auto repeated=encounter::SpreadCandidates({0,0,0},circles,17);assert(repeated.front().x==points.front().x);
 auto separated=encounter::SpreadCandidates({100,100,0},circles,17);assert(separated.front().x==100&&separated.front().y==100);
 std::cout<<"PASS: actual Gruul spread, crowded mitigation, path bounds, native control gates, lifecycle and movement arbitration\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-gruul-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for realm in ('tbc','wotlk'):
    core=root.parent/f'mangos-{realm}-behavior'
    native=(core/'src/game/Spells/SpellEffects.cpp').read_text()
    assert 'case 33671:' in native and 'DIST_CALC_COMBAT_REACH' in native[native.index('case 33671:'):][:650]
    shatter=native[native.index('case 33654:'):][:650]
    assert 'HasAura(33652)' in shatter and '33671' in shatter and 'RemoveAurasDueToSpell(33572)' in shatter
    script=(core/'src/game/AI/ScriptDevAI/scripts/outland/gruuls_lair/boss_gruul.cpp').read_text()
    assert 'GetStackAmount() >= 5' in script and 'CastSpell(nullptr, 33652' in script
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for state in ('Combat','Reaction'):
    assert 'gruul shatter spread' in block(strategy,f'void DungeonStrategy::Init{state}Triggers(')
    assert 'PreserveGruulSpreadMultiplier' in block(strategy,f'void DungeonStrategy::Init{state}Multipliers(')
print('PASS: native TBC/Wrath Gruul contracts and actual strategy wiring; not an in-world encounter test')
