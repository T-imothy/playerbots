"""Actual cover policy, cached planner and dispatch with controlled native geometry."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/BossCoverPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/BossCoverAction.cpp').read_text()
methods='\n'.join([block(value,s) for s in ('bool ai::IsBossCoverMap(', 'uint32 ai::BossCoverMechanic(', 'bool ai::IsBossCoverPosition(', 'EncounterPosition BossCoverPositionValue::Calculate(')]+[block(action,'bool BossCoverAction::'+s+'(') for s in ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute')])
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <vector>
using uint32=unsigned;
constexpr float M_PI_F=3.14159265358979323846f;
enum{CURRENT_GENERIC_SPELL=0,SPELL_STATE_CASTING=1,SPELL_STATE_FINISHED=2,IDLE_MOTION_TYPE=0};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}void Clear(){id=0;}};
struct SpellEntry{unsigned Id=0;};struct Spell{SpellEntry*m_spellInfo=nullptr;unsigned state=1;unsigned getState()const{return state;}};
struct SpellAuraHolder{unsigned stacks=0;unsigned GetStackAmount()const{return stacks;}};
struct Unit{ObjectGuid guid=1;unsigned entry=11983,map=469,instance=1,phase=1;float x=0,y=0,z=0;
 bool world=true,alive=true,combat=true,charmed=false,wall=true;Unit*victim=nullptr;Spell*cast=nullptr;std::set<unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 ObjectGuid owner;ObjectGuid GetSpawnerGuid(){return owner;}ObjectGuid GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}Unit*GetVictim(){return victim;}
 float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
 const Spell*GetCurrentSpell(unsigned){return cast;}
 bool HasAura(unsigned id){return auras.count(id);}
 bool IsWithinLOS(float a,float,float,bool ignoreM2=false){assert(ignoreM2==(map!=631));return !wall||a<6;}
};
struct GameObject:Unit{bool spawned=true;bool IsSpawned(){return spawned;}};
struct Motion{unsigned type=1;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Player:Unit{bool teleport=false,stopped=true;float heightDelta=0;SpellAuraHolder aura;unsigned auraCaster=1,auraId=23341;Motion motion;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}float GetCollisionHeight(){return 2;}
 using Unit::GetDistance;float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
 void UpdateAllowedPositionZ(float,float,float& value){value+=heightDelta;}
 const SpellAuraHolder*GetSpellAuraHolder(unsigned id,ObjectGuid caster){return id==auraId&&unsigned(caster)==auraCaster&&aura.stacks?&aura:nullptr;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}
};
std::list<Unit*> gridMarkers;
namespace MaNGOS{
 struct AllCreaturesOfEntryInRangeCheck{AllCreaturesOfEntryInRangeCheck(Player*,unsigned id,float range){assert(id==37186&&range==100);}};
 template<class T>struct UnitListSearcher{std::list<Unit*>&out;UnitListSearcher(std::list<Unit*>&o,T&):out(o){}};
}
namespace Cell{template<class T>void VisitAllObjects(Player*,T&search,float){search.out=gridMarkers;}}
#include "__GEOMETRY__"
namespace encounter = ai::encounter;
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss;encounter::Point destination;};
template<class T>struct Cached{T data;T Get(){return data;}};
struct Context{Cached<EncounterPosition>position;template<class T>Cached<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true,healer=false;unsigned pathChecks=0,moves=0,stops=0;
 std::list<ObjectGuid>attackers,objects;std::map<unsigned,Unit*>units;std::map<unsigned,GameObject*>gos;float range=30;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}
 bool IsHeal(Player*){return healer;}
 float GetRange(const char*){return range;}GameObject*GetGameObject(ObjectGuid guid){auto i=gos.find(guid);return i==gos.end()?nullptr:i->second;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid guid){auto i=units.find(guid);return i==units.end()?nullptr:i->second;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
};
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&plan){++ai->pathChecks;return ai->path;}
struct Event{};
namespace ai {
 std::vector<encounter::Circle> spacing;
 bool GruulShatterThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&out){out=spacing;return !out.empty();}
 unsigned CurrentBossEscapeSpell(Player*,Unit*b){return b->cast&&b->cast->state==SPELL_STATE_CASTING&&b->cast->m_spellInfo->Id==70123?70123:0;}
 bool IsBossCoverMap(unsigned);unsigned BossCoverMechanic(PlayerbotAI*,Unit*,bool);
 bool IsBossCoverPosition(PlayerbotAI*,Unit*,const encounter::Point&);
 struct BossCoverPositionValue{PlayerbotAI*ai;Player*bot;ObjectGuid shelterBoss;EncounterPosition Calculate();};
 struct BossCoverAction{PlayerbotAI*ai;Player*bot;
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
  bool IsReaction(){return true;}void SetDuration(unsigned){}
  bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}
 };
}
using namespace ai;
#define AI_VALUE(type,key) (std::string(key)=="attackers"?ai->attackers:ai->objects)
__METHODS__
int main(){
 Player bot;bot.guid=10;Unit boss;PlayerbotAI ai{&bot};ai.units={{1,&boss}};ai.attackers={1};
 BossCoverPositionValue planner{&ai,&bot};BossCoverAction action{&ai,&bot};Event event;
 auto calculate=[&](){ai.context.position.data=planner.Calculate();return ai.context.position.data;};
 bot.aura.stacks=4;assert(!calculate().active);bot.aura.stacks=5;auto plan=calculate();
 assert(plan.active&&plan.destination.x>=6&&ai.pathChecks<=8);assert(action.isUseful()&&action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.moves==1);
 bot.x=plan.destination.x;bot.y=plan.destination.y;bot.z=plan.destination.z;assert(action.isUseful()&&!action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.stops==1&&ai.moves==1&&!action.isUseful());
 bot.aura.stacks=1;assert(calculate().active); // remain sheltered until actual stack expiration
 bot.aura.stacks=0;assert(!calculate().active&&!action.isUseful());
 bot.x=bot.y=bot.z=0;bot.aura.stacks=5;ai.path=false;ai.pathChecks=0;assert(!calculate().active&&ai.pathChecks<=8);ai.path=true;
 boss.wall=false;assert(!calculate().active);boss.wall=true;
 bot.heightDelta=20;assert(!calculate().active);bot.heightDelta=0;
 assert(calculate().active);boss.wall=false;assert(!action.Execute(event));boss.wall=true;
 boss.victim=&bot;assert(!calculate().active);boss.victim=nullptr;
 for(bool Unit::*flag:{&Unit::world,&Unit::alive,&Unit::combat}){boss.*flag=false;assert(!calculate().active);boss.*flag=true;}
 boss.charmed=true;assert(!calculate().active);boss.charmed=false;
 bot.auraCaster=99;assert(!calculate().active);bot.auraCaster=1;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;
 bot.charmed=true;assert(!calculate().active);bot.charmed=false;
 boss.phase=2;assert(!calculate().active);boss.phase=1;
 ai.real=true;assert(!calculate().active);ai.real=false;
 Unit tank;boss.victim=&tank;ai.healer=true;tank.wall=false;assert(calculate().active);
 tank.wall=true;assert(!calculate().active);tank.wall=false;tank.x=100;assert(!calculate().active);
 ai.healer=false;boss.victim=nullptr;
 boss.entry=14020;SpellEntry info;Spell cast{&info};boss.cast=&cast;
 for(unsigned id:{23187,23189,23308,23309,23310,23312,23313,23314,23315,23316}){info.Id=id;assert(calculate().active);}
 info.Id=1;assert(!calculate().active);info.Id=23187;cast.state=SPELL_STATE_FINISHED;assert(!calculate().active);cast.state=SPELL_STATE_CASTING;
 bot.map=boss.map=556;boss.entry=18473;boss.victim=&bot;
 for(unsigned id:{38197,40425}){info.Id=id;
#ifdef MANGOSBOT_ZERO
  assert(!calculate().active);
#else
  assert(calculate().active); // Ikiss's tank also takes cover during scripted explosion.
#endif
 }
 bot.map=boss.map=533;boss.entry=15989;boss.cast=nullptr;boss.victim=nullptr;
 assert(!calculate().active);boss.auras.insert(18430);assert(calculate().active);
 bot.auras.insert(28522);assert(!calculate().active);bot.auras.clear();
 bot.auras.insert(31800);assert(!calculate().active);bot.auras.clear();
 GameObject ice;ice.map=533;ice.entry=181247;ice.x=10;ice.guid=90;ai.gos[90]=&ice;ai.objects={90};
 plan=calculate();assert(plan.active&&plan.destination.x==18);
 ice.spawned=false;assert(calculate().destination.x!=18);ice.spawned=true;
 ice.phase=2;assert(calculate().destination.x!=18);ice.phase=1;
 boss.auras.clear();assert(!action.Execute(event)&&!calculate().active);
 bot.map=boss.map=ice.map=658;boss.entry=36494;ice.entry=196485;
 for(unsigned aura:{68786u,70336u}){
  bot.auraId=aura;bot.aura.stacks=5;
#ifdef MANGOSBOT_TWO
  assert(calculate().active);bot.aura.stacks=1;assert(calculate().active);
  bot.aura.stacks=0;assert(!calculate().active);bot.aura.stacks=4;assert(!calculate().active);
  boss.cast=&cast;info.Id=68774;assert(calculate().active);
  boss.victim=&bot;assert(calculate().active);info.Id=68785;assert(calculate().active);
  cast.state=SPELL_STATE_FINISHED;assert(!calculate().active);cast.state=SPELL_STATE_CASTING;
  boss.victim=nullptr;boss.cast=nullptr;
#else
  assert(!calculate().active);
#endif
 }
 // A noncombat marker, absent from attackers, is the bomb's actual LOS source.
 bot.map=boss.map=ice.map=631;boss.entry=36853;boss.z=32;bot.aura.stacks=0;
 Unit marker;marker.map=631;marker.entry=37186;marker.guid=91;marker.owner=1;marker.combat=false;marker.auras={70022};
 ai.units[91]=&marker;gridMarkers={&marker};ice.entry=201722;
#ifdef MANGOSBOT_TWO
 plan=calculate();assert(plan.active&&unsigned(plan.boss)==91&&plan.spell==69845&&plan.destination.x==18);
 marker.auras.clear();assert(!action.Execute(event)&&!calculate().active);marker.auras={70022};
 marker.owner=99;assert(!calculate().active);marker.owner=1;
 boss.combat=false;assert(!calculate().active);boss.combat=true;
 bot.auras={70126};assert(!calculate().active);bot.auras={70157};assert(!calculate().active);bot.auras.clear();
 marker.phase=2;assert(!calculate().active);marker.phase=1;
 gridMarkers.clear();boss.z=0;bot.auraId=72530;bot.aura.stacks=5;assert(calculate().active);
 bot.aura.stacks=1;assert(calculate().active);bot.aura.stacks=0;assert(!calculate().active);
 bot.aura.stacks=5;boss.victim=&bot;assert(!calculate().active);boss.victim=nullptr;
 plan=calculate();assert(plan.active);spacing={{{plan.destination.x,plan.destination.y,plan.destination.z},20}};
 assert(!action.Execute(event));auto spreadCover=calculate();assert(!spreadCover.active||encounter::OutsideCircles(spreadCover.destination,spacing));spacing.clear();
 plan=calculate();assert(plan.active);boss.cast=&cast;info.Id=70123;cast.state=SPELL_STATE_CASTING;
 assert(!action.Execute(event)&&!calculate().active);boss.cast=nullptr;assert(calculate().active);

#else
 assert(!calculate().active);
#endif
 std::cout<<"PASS: native cover mechanic gates, stack hysteresis, real-path requirement, stale-cover rejection and safe holds\n";
}
'''.replace('__METHODS__',methods).replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-boss-cover-') as directory:
  tmp=Path(directory);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for name in ('InitCombatTriggers','InitReactionTriggers'):
 assert 'boss seek cover' in block(strategy,'void DungeonStrategy::'+name+'(')
for name in ('InitCombatMultipliers','InitReactionMultipliers'):
 assert 'PreserveBossCoverMultiplier' in block(strategy,'void DungeonStrategy::'+name+'(')
