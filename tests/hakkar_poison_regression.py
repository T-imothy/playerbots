"""Actual pre-kill poison positioning, bounded coordination and dispatch."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/HakkarPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/HakkarPoisonAction.cpp').read_text()
methods='\n'.join(block(value,s) for s in ('bool ai::IsHakkarPoisonSource(', 'EncounterPosition HakkarPositionValue::Calculate(', 'bool ai::HasHakkarPoisonPreparation('))
methods+='\n'+'\n'.join(block(action,'bool HakkarPoisonAction::'+s+'(') for s in ('GetPlan','isUseful','Execute'))
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <ctime>
using uint32=unsigned;using ObjectGuid=unsigned;
time_t clockNow=100;
enum class BotState{BOT_STATE_COMBAT};
enum{UNIT_CREATED_BY_SPELL=1,IDLE_MOTION_TYPE=0};
struct Unit{unsigned guid=1,entry=14834,map=309,instance=1,phase=1,createdSpell=24319;float x=0,y=0,z=0;
 bool world=true,alive=true,combat=true,charmed=false,player=false;float health=100;Unit*victim=nullptr;std::set<unsigned>auras;
 bool IsPlayer(){return player;}float GetHealthPercent(){return health;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}unsigned GetUInt32Value(unsigned){return createdSpell;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}Unit*GetVictim(){return victim;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
 bool HasAura(unsigned id){return auras.count(id);}
};
struct Motion{unsigned type=1;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Player;struct PlayerbotAI;
struct GroupReference{Player*member;GroupReference*following=nullptr;Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
struct Player:Unit{Player(){player=true;}bool teleport=false,stopped=true;Group*group=nullptr;PlayerbotAI*ai=nullptr;Motion motion;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetInstanceId(){return instance;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}
};
namespace encounter{struct Point{float x=0,y=0,z=0;};}
struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination;};
template<class T>struct Cached{T data;T Get(){return data;}};
struct Context{Cached<EncounterPosition>position;template<class T>Cached<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true;unsigned paths=0,moves=0,stops=0;
 std::list<ObjectGuid>attackers;std::map<unsigned,Unit*>units;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}
 bool HasStrategy(const char*,BotState){return true;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned g){auto i=units.find(g);return i==units.end()?nullptr:i->second;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
};
std::list<Unit*>nativeClouds;
namespace MaNGOS{
 struct AllCreaturesOfEntryInRangeCheck{AllCreaturesOfEntryInRangeCheck(Unit*,unsigned entry,float){assert(entry==11357);}};
 template<class C>struct UnitListSearcher{std::list<Unit*>&out;UnitListSearcher(std::list<Unit*>&o,C&):out(o){}};
}
namespace Cell{template<class S>void VisitAllObjects(Unit*,S&s,float){s.out=nativeClouds;}}
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p){++ai->paths;return ai->path&&std::isfinite(p.destination.x);}
float NativeEncounterSpellRadius(unsigned spell){assert(spell==24320);return 8;}
struct Event{};
namespace ai{
 bool IsHakkarPoisonSource(Player*,Unit*);bool HasHakkarPoisonPreparation(Player*);
 struct HakkarPositionValue{PlayerbotAI*ai;Player*bot;ObjectGuid preparationSon=0;time_t preparationStarted=0;EncounterPosition Calculate();};
 struct HakkarPoisonAction{PlayerbotAI*ai;Player*bot;
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);
  bool IsReaction(){return false;}void SetDuration(unsigned){}
  bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}
 };
}
using namespace ai;
#define AI_VALUE(type,key) ai->attackers
#define time(x) clockNow
__METHODS__
int main(){
 Player bot,member;bot.guid=10;member.guid=11;member.x=15;Group group;GroupReference memberRef{&member},botRef{&bot,&memberRef};group.first=&botRef;bot.group=member.group=&group;
 Unit boss,cloud;cloud.guid=2;cloud.entry=11357;cloud.x=15;cloud.victim=&member;nativeClouds={&cloud};
 PlayerbotAI ai{&bot},memberAi{&member};bot.ai=&ai;member.ai=&memberAi;ai.attackers={1};ai.units={{1,&boss},{2,&cloud}};
 HakkarPositionValue planner{&ai,&bot};HakkarPoisonAction action{&ai,&bot};Event event;
 auto calculate=[&](){ai.context.position.data=planner.Calculate();return ai.context.position.data;};
 auto plan=calculate();assert(plan.active&&plan.destination.x==15&&action.Execute(event)&&ai.moves==1);
 assert(!HasHakkarPoisonPreparation(&bot));cloud.health=30;calculate();assert(HasHakkarPoisonPreparation(&bot));
 clockNow=110;calculate();assert(!HasHakkarPoisonPreparation(&bot));clockNow=100;calculate();
 bot.x=15;assert(action.isUseful());assert(action.Execute(event)&&ai.stops==1&&!action.isUseful());
 assert(!HasHakkarPoisonPreparation(&bot));
 assert(!bot.HasAura(24321)); // no fabricated poison or successful cast
 bot.auras.insert(24321);member.auras.insert(24321);assert(!action.Execute(event)&&!calculate().active);bot.auras.clear();member.auras.clear();
 bot.x=0;boss.victim=&bot;assert(!calculate().active);bot.x=12;plan=calculate();assert(plan.active&&plan.destination.x==12);
 boss.victim=nullptr;bot.x=0;assert(calculate().active);cloud.x=30;assert(!action.Execute(event));cloud.x=15;
 cloud.victim=nullptr;assert(!calculate().active);cloud.victim=&member;
 cloud.entry=14989;assert(!calculate().active);cloud.entry=11357; // lingering visual never used
 cloud.phase=2;assert(!calculate().active);cloud.phase=1;cloud.z=10;assert(!calculate().active);cloud.z=0;
 cloud.alive=false;assert(!calculate().active);cloud.alive=true;
 assert(calculate().active);cloud.world=false;assert(!action.Execute(event));cloud.world=true;
 boss.combat=false;assert(!calculate().active);boss.combat=true;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;
 bot.charmed=true;assert(!calculate().active);bot.charmed=false;
 ai.real=true;assert(!calculate().active);ai.real=false;
 ai.path=false;assert(!calculate().active);ai.path=true;
 nativeClouds.clear();assert(!calculate().active);
 std::cout<<"PASS: pre-kill poison positioning, bounded damage hold, actual aura acquisition, tank anchor and lifecycle gates\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-hakkar-') as directory:
  tmp=Path(directory);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('classic','tbc','wotlk'):
 core=root.parent/f'mangos-{era}-behavior'
 native=(core/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/zulgurub/boss_hakkar.cpp').read_text()
 assert 'HasAura(24321) ? 24323 : 24322' in native
 effects=(core/'src/game/Spells/SpellEffects.cpp').read_text()
 assert 'case 24320:' in effects and '24321, TRIGGERED_OLD_TRIGGERED' in effects
