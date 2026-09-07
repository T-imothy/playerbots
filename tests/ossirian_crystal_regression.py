"""Actual crystal assignment/planner/action; no fabricated native click outcome."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/OssirianPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/OssirianCrystalAction.cpp').read_text()
methods='\n'.join(block(value,s) for s in ('bool ai::IsOssirianCrystal(', 'bool ai::OssirianNeedsCrystal(', 'Player* ai::OssirianCrystalUser(', 'EncounterPosition OssirianPositionValue::Calculate('))
methods+='\n'+'\n'.join(block(action,'bool OssirianCrystalAction::'+s+'(') for s in ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute'))
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
using uint32=unsigned;
enum{GO_JUST_DEACTIVATED=3,GAMEOBJECT_FLAGS=1,GO_FLAG_NO_INTERACT=16,GO_FLAG_IN_USE=1,IDLE_MOTION_TYPE=0,CMSG_GAMEOBJ_USE=77};
enum class BotState{BOT_STATE_COMBAT};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}void Clear(){id=0;}};
struct SpellAuraHolder{int duration=45000;int GetAuraDuration()const{return duration;}};
struct Unit{ObjectGuid guid=1;unsigned entry=15339,map=509,instance=1,phase=1;float x=0,y=0,z=0;
 bool world=true,alive=true,combat=true,charmed=false,los=true;Unit*victim=nullptr;std::set<unsigned>auras;SpellAuraHolder holder;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 ObjectGuid GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}Unit*GetVictim(){return victim;}
 float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
 bool HasAura(unsigned id){return auras.count(id);}
 const SpellAuraHolder*GetSpellAuraHolder(unsigned id){return HasAura(id)?&holder:nullptr;}
 bool IsWithinLOSInMap(Unit*,bool=false){return los;}
};
struct Player;struct PlayerbotAI;
struct GroupReference{Player*member;GroupReference*following=nullptr;Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
struct WorldPacket{unsigned guid=0;WorldPacket(unsigned){}WorldPacket&operator<<(ObjectGuid g){guid=g;return *this;}};
struct Session{unsigned clicks=0;void HandleGameObjectUseOpcode(WorldPacket&p){assert(p.guid==90);++clicks;}};
struct Motion{unsigned type=1;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Player:Unit{bool teleport=false,stopped=true,tank=false,healer=false,casting=false;Group*group=nullptr;PlayerbotAI*ai=nullptr;Motion motion;Session session;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetInstanceId(){return instance;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}bool IsNonMeleeSpellCasted(bool){return casting;}Session*GetSession(){return &session;}
};
struct GameObject:Unit{bool spawned=true;unsigned flags=0,loot=0;bool IsSpawned(){return spawned;}unsigned GetLootState(){return loot;}
 bool HasFlag(unsigned,unsigned mask){return flags&mask;}bool IsAtInteractDistance(Player*p){return GetDistance(p)<5;}
 float GetInteractionDistance(){return 5;}bool IsWithinDistInMap(Player*p,float distance){return GetDistance(p)<distance;}};
namespace encounter{struct Point{float x=0,y=0,z=0;};}
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};
template<class T>struct Cached{T data;T Get(){return data;}};
struct Context{Cached<EncounterPosition>position;template<class T>Cached<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true,strategy=true;unsigned moves=0,stops=0,interrupts=0;
 std::list<ObjectGuid>attackers;std::map<unsigned,Unit*>units;std::map<unsigned,GameObject*>gos;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}
 bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->healer;}bool HasStrategy(const char*,BotState){return strategy;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid g){auto i=units.find(g);return i==units.end()?nullptr:i->second;}
 GameObject*GetGameObject(ObjectGuid g){auto i=gos.find(g);return i==gos.end()?nullptr:i->second;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}void InterruptSpell(){++interrupts;bot->casting=false;}
};
std::list<GameObject*>nativeObjects;
namespace MaNGOS{template<class C>struct GameObjectListSearcher{std::list<GameObject*>&out;C&check;GameObjectListSearcher(std::list<GameObject*>&o,C&c):out(o),check(c){(void)c.GetFocusObject();}};}
namespace Cell{template<class S>void VisitAllObjects(Unit*,S&s,float){for(auto*o:nativeObjects)if(s.check(o))s.out.push_back(o);}}
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p){return ai->path&&std::isfinite(p.destination.x)&&ai->bot->GetDistance(p.destination.x,p.destination.y,p.destination.z)<=60;}
float NativeEncounterSpellRadius(unsigned spell){assert(spell==25177);return 30;}
bool triggerPresent=true;Unit*FindOssirianCrystalTrigger(Player*,GameObject*object){return triggerPresent?object:nullptr;}
struct Event{};
namespace ai{
 bool IsOssirianCrystal(Player*,GameObject*);bool OssirianNeedsCrystal(Unit*);Player*OssirianCrystalUser(PlayerbotAI*,Unit*,GameObject*);
 struct OssirianPositionValue{PlayerbotAI*ai;Player*bot;ObjectGuid anchorCrystal;encounter::Point tankAnchor;EncounterPosition Calculate();};
 struct OssirianCrystalAction{PlayerbotAI*ai;Player*bot;unsigned duration=0;
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
  bool IsReaction(){return true;}void SetDuration(unsigned d){duration=d;}
  bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}
 };
}
using namespace ai;
#define AI_VALUE(type,key) ai->attackers
__METHODS__
int main(){
 Player bot,tank,spare;bot.guid=10;tank.guid=11;spare.guid=12;tank.tank=true;spare.x=-10;
 Group group;GroupReference spareRef{&spare},tankRef{&tank,&spareRef},botRef{&bot,&tankRef};group.first=&botRef;bot.group=tank.group=spare.group=&group;
 Unit boss;boss.victim=&tank;boss.auras={25176};
 GameObject crystal;crystal.guid=90;crystal.entry=180619;crystal.x=15;nativeObjects={&crystal};
 PlayerbotAI ai{&bot},tankAi{&tank},spareAi{&spare};bot.ai=&ai;tank.ai=&tankAi;spare.ai=&spareAi;
 ai.units[1]=&boss;ai.gos[90]=&crystal;ai.attackers={1};tankAi.units=ai.units;tankAi.gos=ai.gos;tankAi.attackers=ai.attackers;
 OssirianPositionValue planner{&ai,&bot},tankPlanner{&tankAi,&tank};OssirianCrystalAction action{&ai,&bot};Event event;
 auto calculate=[&](){ai.context.position.data=planner.Calculate();return ai.context.position.data;};
 assert(OssirianCrystalUser(&ai,&boss,&crystal)==&bot);auto plan=calculate();assert(plan.active&&plan.destination.x==16);
 assert(action.isUseful()&&action.ShouldReactionInterruptCast()&&action.Execute(event)&&ai.moves==1&&bot.session.clicks==0);
 bot.x=plan.destination.x;bot.casting=true;assert(action.Execute(event)&&bot.session.clicks==1&&ai.interrupts==1);
 for(unsigned aura:{25177u,25178u,25180u,25181u,25183u}){
  boss.auras={aura};boss.holder.duration=45000;assert(!OssirianNeedsCrystal(&boss));
  assert(!action.isUseful()&&!action.ShouldReactionInterruptCast());
  boss.holder.duration=5000;assert(OssirianNeedsCrystal(&boss));boss.holder.duration=-1;assert(!OssirianNeedsCrystal(&boss));
 }
 boss.auras={25176};boss.x=-30;unsigned clicks=bot.session.clicks;assert(!action.Execute(event)&&bot.session.clicks==clicks);boss.x=0;
 triggerPresent=false;assert(!action.Execute(event));triggerPresent=true;
 boss.los=false;assert(!action.Execute(event));boss.los=true;
 crystal.flags=GO_FLAG_IN_USE;assert(!action.Execute(event)&&!calculate().active);crystal.flags=0;
 crystal.spawned=false;assert(!calculate().active);crystal.spawned=true;
 crystal.loot=GO_JUST_DEACTIVATED;assert(!calculate().active);crystal.loot=0;
 ai.path=false;assert(!calculate().active);ai.path=true;
 assert(calculate().active);spare.x=15;assert(!action.Execute(event)&&OssirianCrystalUser(&ai,&boss,&crystal)==&spare);
 spareAi.real=true;assert(OssirianCrystalUser(&ai,&boss,&crystal)==&bot);spareAi.real=false;
 spare.healer=true;assert(OssirianCrystalUser(&ai,&boss,&crystal)==&bot);spare.healer=false;
 spare.teleport=true;assert(OssirianCrystalUser(&ai,&boss,&crystal)==&bot);spare.teleport=false;
 spareAi.strategy=false;assert(OssirianCrystalUser(&ai,&boss,&crystal)==&bot);spareAi.strategy=true;
 spare.x=-10;
 auto anchor=tankPlanner.Calculate();assert(anchor.active&&anchor.destination.x==23);
 boss.x=17;assert(tankPlanner.Calculate().destination.x==23); // never reverse after crossing the crystal
 boss.x=0;tankAi.context.position.data=anchor;OssirianCrystalAction tankAction{&tankAi,&tank};tank.x=23;
 assert(tankAction.Execute(event)&&tank.session.clicks==0);
 assert(calculate().active);boss.alive=false;assert(!action.Execute(event)&&!calculate().active);boss.alive=true;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;
 crystal.phase=2;assert(!calculate().active);crystal.phase=1;
 std::cout<<"PASS: native crystal click gates, single DPS assignment, stable tank pull, native range/weakness timing and stale-plan rejection\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-ossirian-') as directory:
  tmp=Path(directory);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('classic','tbc','wotlk'):
 core=root.parent/f'mangos-{era}-behavior'
 source=(core/'src/game/AI/ScriptDevAI/scripts/kalimdor/ruins_of_ahnqiraj/boss_ossirian.cpp').read_text()
 assert 'GOUse_go_ossirian_crystal' in source and '25176' in source and 'SPELL_SUMMON_CRYSTAL' in source
