"""Actual Solarian burst/target/action policy in Classic, TBC and Wrath modes."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/SolarianPositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/TempestKeepActions.cpp').read_text()
multiplier = (root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods = '\n'.join([block(value, key) for key in ('float ai::SolarianBurstRadius(',
    'bool ai::SolarianBurstThreats(', 'EncounterPosition SolarianPositionValue::Calculate(')] +
    [block(action,key) for key in ('bool SolarianPositionAction::GetPlan(',
    'bool SolarianPositionAction::isUseful(', 'bool SolarianPositionAction::ShouldReactionInterruptCast(',
    'bool SolarianPositionAction::Execute(', 'Unit* SolarianPriorityTargetAction::GetTarget(',
    'bool SolarianPriorityTargetAction::isUseful(')] +
    [block(multiplier,'float PreserveSolarianPositionMultiplier::GetValue(')])
code = r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <list>
#include <string>
#include <type_traits>
#include "__GEOMETRY__"
using uint32=unsigned;
enum {EFFECT_INDEX_0=0,EFFECT_INDEX_1=1,SPELL_EFFECT_APPLY_AURA=6,IDLE_MOTION_TYPE=0};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}bool IsEmpty()const{return !id;}};
struct SpellEntry{unsigned Effect[3]{6,3,0};int base[3]{-1,42786,0};int CalculateSimpleValue(unsigned index)const{return base[index]+1;}};
struct Facade{SpellEntry aura;bool present=true;const SpellEntry* LookupSpellInfo(unsigned id){assert(id==42783);return present?&aura:nullptr;}}sServerFacade;
struct Map{};
struct Motion{unsigned kind=0;unsigned GetCurrentMovementGeneratorType(){return kind;}};
struct Unit{virtual ~Unit()=default;Map* map=nullptr;unsigned phase=1,entry=0;ObjectGuid guid,spawner;
 bool world=true,alive=true,combat=true,charmed=false,attackable=true,assignedCC=false,breakCC=false,hardCC=false;
 float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;
 virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}unsigned GetEntry(){return entry;}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}
 ObjectGuid GetObjectGuid(){return guid;}ObjectGuid GetSpawnerGuid(){return spawner;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
struct Group;
struct Player:Unit{unsigned mapId=550,instance=1;bool teleport=false,stopped=true;Group* group=nullptr;Motion motion;
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}
 float GetDistance(float xx,float yy,float zz){return std::sqrt((x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz));}
 float GetDistance(Unit* u){return GetDistance(u->x,u->y,u->z);}};
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai{struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};}
using namespace ai;
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<EncounterPosition> position;Value<std::list<ObjectGuid>> attackers;
 template<class T>Value<T>* GetValue(const char*){if constexpr(std::is_same_v<T,EncounterPosition>)return &position;else return &attackers;}};
struct PlayerbotAI{Player* bot;Context context;std::map<unsigned,Unit*> units;bool validPath=true,canMove=true,tank=false,healer=false;
 unsigned checked=0,moves=0,stops=0;std::list<ObjectGuid> possible;Unit* current=nullptr;Unit* marked=nullptr;ObjectGuid commanded;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}bool CanMove(){return canMove;}
 bool IsTank(Player*){return tank;}bool IsHeal(Player*){return healer;}
 Unit* GetUnit(ObjectGuid guid){auto i=units.find(guid);return i==units.end()?nullptr:i->second;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.kind=0;}
 template<class T>T Data(std::string key){if constexpr(std::is_same_v<T,ObjectGuid>)return commanded;
 else if constexpr(std::is_same_v<T,Unit*>)return key=="rti target"?marked:current;else return possible;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit* u,Player*,bool){return u->attackable;}};
struct PossibleAttackTargetsValue{
 static bool IsPossibleTarget(Unit* u,Player* p,float range,bool ignore){assert(!ignore);return !u->assignedCC&&p->GetDistance(u)<=range;}
 static bool HasBreakableCC(Unit* u,Player*){return u->breakCC;}static bool HasUnBreakableCC(Unit* u,Player*){return u->hardCC;}};
struct Event{};
struct Action{virtual ~Action()=default;std::string name;std::string getName(){return name;}};
struct MovementAction:Action{};struct AttackAction:MovementAction{};struct MoveAwayFromHazard:MovementAction{};
struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
namespace ai{
 float radius=10;float NativeEncounterSpellRadius(unsigned id){assert(id==42787);return radius;}
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&){++ai->checked;return ai->validPath;}
 float SolarianBurstRadius();bool SolarianBurstThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 struct SolarianPositionValue{Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct SolarianPositionAction:MovementAction{PlayerbotAI* ai;Player* bot;SolarianPositionAction(PlayerbotAI* a):ai(a),bot(a->bot){}
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);bool ShouldReactionInterruptCast()const;
  bool IsReaction(){return true;}void SetDuration(unsigned duration){assert(duration==100);}
  bool MoveTo(unsigned,float,float,float,bool idle,bool react,bool noPath,bool ignore){assert(!idle&&react&&!noPath&&ignore);++ai->moves;return true;}};
 struct SolarianPriorityTargetAction:AttackAction{PlayerbotAI* ai;Player* bot;SolarianPriorityTargetAction(PlayerbotAI* a):ai(a),bot(a->bot){}
  Unit* GetTarget();bool isUseful();};
 struct PreserveSolarianPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
}
#define AI_VALUE(type,key) ai->Data<type>(key)
__METHODS__
int main(){
 Map map,otherMap;Player bot,ally,second;bot.map=ally.map=second.map=&map;bot.guid=1;ally.guid=2;second.guid=4;ally.x=1;second.y=1;
 Group group,otherGroup;GroupReference r2{&second},r1{&ally,&r2};group.first=&r1;bot.group=ally.group=second.group=&group;
 Unit boss,portal,agent,priest;boss.entry=18805;boss.guid=3;boss.map=&map;portal.entry=18928;portal.guid=5;portal.map=&map;portal.spawner=3;
 agent.entry=18925;agent.guid=6;agent.spawner=5;agent.map=&map;priest=agent;priest.entry=18806;priest.guid=7;priest.x=20;
 PlayerbotAI ai{&bot};ai.units={{1,&bot},{2,&ally},{3,&boss},{4,&second},{5,&portal},{6,&agent},{7,&priest}};
 ai.context.attackers.value={3};ai.possible={6,7};
 SolarianPositionValue value{&bot,&ai};SolarianPositionAction action(&ai);SolarianPriorityTargetAction target(&ai);
 EncounterPosition plan;Event event;PreserveSolarianPositionMultiplier multiplier{&ai};
 auto get=[&](){ai.context.position.value=value.Calculate();return SolarianPositionAction::GetPlan(&ai,plan);};
#ifdef MANGOSBOT_ZERO
 bot.auras={42783};assert(SolarianBurstRadius()==0&&!get()&&!action.Execute(event)&&!target.GetTarget());
#else
 assert(!get());bot.auras={33045};assert(!get());bot.auras={42783};assert(get()&&plan.source==bot.guid);
 assert(encounter::Distance2d(plan.destination,{ally.x,ally.y,0})>=12&&action.isUseful());
 assert(action.ShouldReactionInterruptCast()&&action.Execute(event)&&ai.moves==1);
 ally.x=plan.destination.x;ally.y=plan.destination.y;assert(!SolarianPositionAction::GetPlan(&ai,plan)&&!action.Execute(event));ally.x=1;ally.y=0;
 ai.validPath=false;assert(!action.Execute(event));ai.checked=0;assert(!get()&&ai.checked<=8);ai.validPath=true;
 assert(get());ai.canMove=false;assert(!action.Execute(event)&&!action.ShouldReactionInterruptCast());ai.canMove=true;
 boss.victim=&bot;assert(!SolarianPositionAction::GetPlan(&ai,plan)&&!get());boss.victim=&ally;
 assert(get());boss.alive=false;boss.combat=false;ai.context.attackers.value.clear();bot.combat=false;assert(get());
 bot.auras.clear();assert(!SolarianPositionAction::GetPlan(&ai,plan)&&!get());
 ally.auras={42783};assert(get()&&plan.source==ally.guid);second.auras={42783};assert(get());second.auras.clear();
 ally.teleport=true;assert(!get());ally.teleport=false;ally.charmed=true;assert(!get());ally.charmed=false;
 ally.phase=2;assert(!get());ally.phase=1;ally.map=&otherMap;assert(!get());ally.map=&map;ally.alive=false;assert(!get());ally.alive=true;
 ally.z=11;assert(get());ally.z=14;assert(!get());ally.z=0;ally.x=100;assert(!get());ally.x=1;
 assert(get());ally.group=&otherGroup;assert(!SolarianPositionAction::GetPlan(&ai,plan));ally.group=&group;
 assert(get());++bot.instance;assert(!SolarianPositionAction::GetPlan(&ai,plan));--bot.instance;
 bot.teleport=true;assert(!get());bot.teleport=false;bot.charmed=true;assert(!get());bot.charmed=false;
 bot.mapId=0;assert(!get());bot.mapId=550;bot.group=nullptr;assert(!get());bot.group=&group;
 radius=0;assert(!get());radius=100;assert(!get());radius=std::nanf("");assert(!get());radius=10;
 sServerFacade.present=false;assert(!get());sServerFacade.present=true;sServerFacade.aura.base[1]=42783;assert(!get());sServerFacade.aura.base[1]=42786;
 assert(get());bot.x=plan.destination.x;bot.y=plan.destination.y;bot.stopped=false;bot.motion.kind=1;
 assert(action.isUseful()&&!action.ShouldReactionInterruptCast()&&action.Execute(event)&&ai.stops==1);
 assert(!action.isUseful());bot.x=bot.y=0;assert(get());
 ai.context.position.value.destination.x=std::nanf("");assert(!SolarianPositionAction::GetPlan(&ai,plan));assert(get());
 MovementAction follow;AttackAction attack;MoveAwayFromHazard escape;CastSpellAction cast;
 assert(multiplier.GetValue(&follow)==0&&multiplier.GetValue(&attack)==1&&multiplier.GetValue(&escape)==1);
 assert(multiplier.GetValue(&action)==1&&multiplier.GetValue(&cast)==1);cast.movement=true;assert(multiplier.GetValue(&cast)==0);
 ally.auras.clear();assert(multiplier.GetValue(&cast)==1&&multiplier.GetValue(&follow)==1&&!get());
 // Invisible split boss resolves through the actual physical spotlight owner.
 boss.alive=boss.combat=bot.combat=true;assert(target.GetTarget()==&priest&&target.isUseful());
 ai.current=&agent;assert(target.GetTarget()==&priest);ai.current=&priest;priest.x=25;assert(!target.isUseful());
 Action assist;assist.name="dps assist";assert(multiplier.GetValue(&assist)==0);
 ai.commanded=6;assert(!target.GetTarget()&&multiplier.GetValue(&assist)==1);ai.commanded=0;
 ai.marked=&agent;assert(!target.GetTarget());ai.marked=nullptr;
 priest.assignedCC=true;assert(target.GetTarget()==&agent);priest.assignedCC=false;
 priest.breakCC=true;assert(target.GetTarget()==&agent);priest.breakCC=false;priest.hardCC=true;assert(target.GetTarget()==&agent);priest.hardCC=false;
 ai.possible={7};auto none=[&](){assert(!target.GetTarget());};
 priest.attackable=false;none();priest.attackable=true;priest.combat=false;none();priest.combat=true;
 priest.charmed=true;none();priest.charmed=false;priest.phase=2;none();priest.phase=1;
 priest.spawner=99;none();priest.spawner=5;portal.spawner=99;none();portal.spawner=3;
 portal.alive=false;none();portal.alive=true;portal.phase=2;none();portal.phase=1;
 boss.alive=false;none();boss.alive=true;boss.victim=&bot;none();boss.victim=&ally;
 ai.tank=true;none();ai.tank=false;ai.healer=true;none();ai.healer=false;
 assert(target.GetTarget()==&priest);ai.units.erase(7);none();
#endif
 std::cout<<"PASS: actual Solarian native burst radius/lifetime, fresh paths, hold, summon ownership and CC-safe priorities\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-solarian-policy-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for state in ('Combat','NonCombat','Reaction'):
    assert 'solarian burst position' in block(strategy,f'void DungeonStrategy::Init{state}Triggers(')
    assert 'PreserveSolarianPositionMultiplier' in block(strategy,f'void DungeonStrategy::Init{state}Multipliers(')
for era in ('tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior/src/game'
    native=(core/'AI/ScriptDevAI/scripts/outland/tempest_keep/the_eye/boss_astromancer.cpp').read_text()
    assert 'CalculateSimpleValue(SpellEffectIndex(aura->GetEffIndex() + 1))' in block(native,'struct WrathOfTheAstromancer')
    assert 'AURA_REMOVE_BY_EXPIRE' in block(native,'struct WrathOfTheAstromancer')
    assert 'm_creature->GetObjectGuid()' in block(native,'void HandleSplitAgents()')
    summon=(core/'Spells/SpellEffects.cpp').read_text()
    assert 'TempSpawnSettings(m_trueCaster, creature_entry' in block(summon,'bool Spell::DoSummonWild(')
print('PASS: native expiry dispatch, physical-summoner ownership and combat/noncombat/reaction wiring')
