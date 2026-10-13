"""Execute production engagement state/order methods through complete pull/kill sequences.

Native movement, spell admission and network delivery are controlled boundaries;
the state transitions, pending-intent guard and explicit wait policy are actual C++.
"""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
s=(R/'playerbot/PlayerbotAI.cpp').read_text();w=(R/'playerbot/strategy/generic/CombatStrategy.cpp').read_text()
methods='\n'.join(block(s,n) for n in ('void PlayerbotAI::OnCombatStarted(', 'void PlayerbotAI::OnCombatEnded(', 'void PlayerbotAI::PrepareForRaidRegroup(', 'void PlayerbotAI::PrepareForPartyCombat('))
party_source=(R/'playerbot/PartyCombatSupport.cpp').read_text();follow_source=(R/'playerbot/strategy/actions/FollowActions.cpp').read_text()
if '--before-anchor' in sys.argv:party_source=subprocess.run(['git','-C',str(R),'show','HEAD:playerbot/PartyCombatSupport.cpp'],capture_output=True,text=True,check=True).stdout
if '--before-regroup' in sys.argv:follow_source=subprocess.run(['git','-C',str(R),'show','HEAD:playerbot/strategy/actions/FollowActions.cpp'],capture_output=True,text=True,check=True).stdout
methods+='\n'+block(party_source,'Player* ai::GetPartyCombatAnchor(')
methods+='\n'+block(follow_source,'bool ai::RaidRegroupNeeded(')
pending='bool PlayerbotAI::HasPendingCombatEngagement(){return false;}'
if 'bool PlayerbotAI::HasPendingCombatEngagement(' in s:pending=block(s,'bool PlayerbotAI::HasPendingCombatEngagement(')
methods+='\n'+pending
methods+='\n'+'\n'.join(block(w,n) for n in ('WaitForAttackStrategy* WaitForAttackStrategy::Get(', 'void WaitForAttackStrategy::AllowExplicitAttack(', 'bool WaitForAttackStrategy::HasExplicitAttackOrder(', 'bool WaitForAttackStrategy::ShouldWait(', 'uint8 WaitForAttackStrategy::GetWaitTime('))
triggers=(R/'playerbot/strategy/triggers/BotStateTriggers.cpp').read_text();methods+='\n'+block(triggers,'bool CombatEndTrigger::IsActive(')
prefix=r'''
#include <any>
#include <map>
#include <list>
#include <vector>
#include <ctime>
#include <cmath>
#include <string>
#include <iostream>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#undef assert
#define assert(x) do{if(!(x)){fprintf(stderr,"FAIL sequence line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
using uint8=unsigned char;using ObjectGuid=unsigned;using uint32=unsigned;
time_t now=100;time_t fakeTime(time_t*){return now;}
#define time fakeTime
enum class BotState{BOT_STATE_NON_COMBAT,BOT_STATE_COMBAT,BOT_STATE_DEAD};
enum{FOLLOW_MOTION_TYPE=1};
struct Slot{unsigned guid;};struct Group{bool raid=true;std::vector<Slot>slots;const std::vector<Slot>&GetMemberSlots(){return slots;}bool IsRaidGroup(){return raid;}};
struct Map{bool raid=true;bool IsRaid(){return raid;}};
struct PlayerbotAI;
struct Unit{virtual ~Unit()=default;unsigned guid=2,map=409,entry=1;Unit*victim=nullptr;std::vector<Unit*>attackers;const std::vector<Unit*>&getAttackers(){return attackers;}Unit*GetVictim(){return victim;}bool alive=true,world=true,combat=false,friendly=false,moving=false;
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsInCombat(){return combat;}bool IsMoving(){return moving;}virtual bool IsPlayer(){return false;}
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}};
struct Motion{unsigned type=0;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Spline{bool Finalized(){return true;}};
struct Player:Unit{PlayerbotAI*ai=nullptr;PlayerbotAI*GetPlayerbotAI(){return ai;}bool transfer=false,charm=false,casting=false,roleTank=false,roleHeal=false,grouped=true,duel=false,sit=false;Group group;Group*party=&group;Map nativeMap;Motion motion;Spline spline;Spline*movespline=&spline;
 bool IsPlayer()override{return true;}Group*GetGroup(){return grouped?party:nullptr;}Map*GetMap(){nativeMap.raid=group.raid;return &nativeMap;}
 float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}
 bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}bool IsInMap(Unit*u){return u&&u->map==map;}bool IsWithinDistInMap(Unit*,float){return true;}unsigned GetPhaseMask(){return 1;}bool IsTaxiFlying(){return false;}bool IsSitState(){return sit;}void SetStandState(unsigned){sit=false;}float GetDistance(float,float,float){return 20;}
 bool IsNonMeleeSpellCasted(bool,bool=false,bool=false){return casting;}unsigned GetMapId(){return map;}Motion*GetMotionMaster(){return &motion;}};
struct PositionEntry{PositionEntry()=default;PositionEntry(float,float,float,unsigned){}};
struct WorldLocation{unsigned mapid=409;float coord_x=5,coord_y=0,coord_z=0;};struct Formation{WorldLocation station;WorldLocation GetLocation(){return station;}static bool IsNullLocation(const WorldLocation&){return false;}};
struct EncounterPosition{};template<class T>struct Cached{T value{};unsigned resets=0;T Get(){return value;}void Set(T v){value=v;}void Reset(){++resets;}};
struct Context{std::map<std::string,std::any> cells;template<class T>Cached<T>*GetValue(const char*n,const char*q=nullptr){std::string key=n;if(q)key+=q;auto[it,added]=cells.emplace(key,Cached<T>{});return std::any_cast<Cached<T>>(&it->second);}template<class T>Cached<T>*GetValue(const char*n,unsigned q){return GetValue<T>(n,std::to_string(q).c_str());}};
using AiObjectContext=Context;
struct ReactionEngine{unsigned wakes=0;void NotifyPartyCombat(){++wakes;}};
struct PlayerbotAI;
struct WaitForAttackStrategy{ObjectGuid orderedOwner=0,orderedTarget=0;time_t orderedAt=0,orderedCombatStart=0;
 static WaitForAttackStrategy*Get(PlayerbotAI*);static bool ShouldWait(PlayerbotAI*);static uint8 GetWaitTime(PlayerbotAI*);
 void AllowExplicitAttack(PlayerbotAI*,Player*,Unit*);bool HasExplicitAttackOrder(PlayerbotAI*,time_t);
 void ClearExplicitAttackOrder(){orderedOwner=orderedTarget=0;orderedAt=orderedCombatStart=0;}};
struct PullStrategy{Unit*target=nullptr;time_t started=0;unsigned ends=0;
 static PullStrategy*Get(PlayerbotAI*);Unit*GetTarget(){return target;}bool HasTarget(){return target!=nullptr;}bool HasPullStarted(){return started!=0;}
 time_t GetPullStartTime(){return started;}unsigned GetMaxPullTime(){return 15;}void OnPullEnded(){target=nullptr;started=0;++ends;}};
struct PlayerbotAI{Player*bot;Player owner;Unit enemy;Formation formation;Context context;Context*aiObjectContext=&context;WaitForAttackStrategy order;PullStrategy pull;ReactionEngine reaction;ReactionEngine*reactionEngine=&reaction;
 ObjectGuid regroupDeadTarget=0;bool owned=true,human=false,mobile=true,follow=true,stay=false,guard=false,isWaiting=true,partyFlag=false;unsigned aiInternalUpdateDelay=10000,stops=0;
 BotState state=BotState::BOT_STATE_NON_COMBAT;
 PlayerbotAI(Player*b):bot(b){bot->ai=this;owner.guid=1;owner.friendly=bot->friendly=true;owner.party=bot->party;owner.map=enemy.map=bot->map;bot->group.slots={{1}};formation.station.mapid=bot->map;context.GetValue<Formation*>("formation")->value=&formation;context.GetValue<ObjectGuid>("follow target")->value=1;context.GetValue<uint8>("wait for attack time")->value=10;context.GetValue<ObjectGuid>("current target")->value=2;}
 bool HasRealPlayerMaster(){return owned;}bool IsRealPlayer(){return human;}Player*GetBot(){return bot;}Player*GetMaster(){return owned?&owner:nullptr;}
 bool IsStateActive(BotState s){return state==s;}void ChangeEngine(BotState s){state=s;}void ResetAIInternalUpdateDelay(){aiInternalUpdateDelay=0;}void StopMoving(){++stops;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned g){return g==2?&enemy:g==1?&owner:nullptr;}bool IsSafe(Unit*u){return u&&u->world&&bot->IsInMap(u);}
 bool IsTank(Player*p){return p->roleTank;}bool IsHeal(Player*p){return p->roleHeal;}bool CanMove(){return mobile;}bool IsJumping(){return false;}
 bool HasStrategy(const char*n,BotState){return std::string(n)=="wait for attack"?true:std::string(n)=="follow"?follow:std::string(n)=="stay"?stay:std::string(n)=="guard"?guard:false;}
 template<class T>T*GetStrategy(const char*n,BotState){return std::string(n)=="wait for attack"?reinterpret_cast<T*>(&order):std::string(n)=="pull"?reinterpret_cast<T*>(&pull):nullptr;}
 time_t GetCombatStartTime(){return context.GetValue<time_t>("combat start time")->value;}
 bool HasPendingCombatEngagement();void OnCombatStarted();void OnCombatEnded();void PrepareForRaidRegroup();void PrepareForPartyCombat();};
PullStrategy*PullStrategy::Get(PlayerbotAI*a){return &a->pull;}
namespace ai{using ::PullStrategy;using ::WaitForAttackStrategy;
 Player*GetPartyCombatAnchor(PlayerbotAI*);bool RaidRegroupNeeded(PlayerbotAI*);bool RaidRestInProgress(PlayerbotAI*){return false;}}
struct ObjectMgr{Player*member=nullptr;Player*GetPlayer(unsigned guid){return guid==1?member:nullptr;}}sObjectMgr;
struct{float sightDistance=100;}sPlayerbotAIConfig;constexpr unsigned UNIT_STAND_STATE_STAND=0;
bool CanManageBotCommands(PlayerbotAI*a,Player*p){return a->owned&&p==&a->owner;}
struct Facade{bool IsFriendlyTo(Unit*,Unit*t){return t->friendly;}}sServerFacade;
struct CombatEndTrigger{PlayerbotAI*ai;Context*context;bool IsActive();};
#define AI_VALUE(T,N) context->GetValue<T>(N)->Get()
__METHODS__
int main(){for(unsigned map:{409u,0u,530u,571u})for(bool raid:{true,false})for(unsigned role=0;role<3;++role){
 Player bot;bot.map=map;bot.group.raid=raid;bot.roleTank=role==0;bot.roleHeal=role==1;PlayerbotAI a(&bot);sObjectMgr.member=&a.owner;CombatEndTrigger end{&a,&a.context};
 // Pull preparation exists before any native attack/combat flag. It must survive multiple ticks.
 now=100;a.pull.target=&a.enemy;a.pull.started=now;a.OnCombatStarted();
 for(unsigned tick=0;tick<10;++tick){a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_COMBAT);assert(!end.IsActive());assert(a.GetCombatStartTime()==100);}
 // The explicit Attack supersedes the old pull; native target has not acquired combat yet.
 a.pull.OnPullEnded();a.order.AllowExplicitAttack(&a,&a.owner,&a.enemy);
 assert(!WaitForAttackStrategy::ShouldWait(&a));a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_COMBAT);
 now=105;a.enemy.combat=true;bot.combat=true;a.context.GetValue<bool>("has attackers")->value=true;
 assert(!WaitForAttackStrategy::ShouldWait(&a));a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_COMBAT);
 // Killing the final enemy must retire the AI state/old wait even while native combat flags linger.
 now=106;a.enemy.alive=false;a.partyFlag=true;a.context.GetValue<bool>("has attackers")->value=false;
 a.aiInternalUpdateDelay=10000;a.isWaiting=true;a.PrepareForRaidRegroup();
 assert(a.state==BotState::BOT_STATE_NON_COMBAT);assert(a.GetCombatStartTime()==0);assert(a.aiInternalUpdateDelay==0&&!a.isWaiting);
 assert(ai::RaidRegroupNeeded(&a));assert(a.order.orderedAt==0);
 // Native combat grace on every party member must not reenter the ended fight.
 a.owner.combat=true;a.owner.victim=&a.enemy;a.owner.attackers={&a.enemy};
 const unsigned endedWakes=a.reaction.wakes;
 for(unsigned tick=0;tick<12;++tick){a.PrepareForPartyCombat();a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_NON_COMBAT);assert(ai::RaidRegroupNeeded(&a));assert(a.GetCombatStartTime()==0);assert(a.reaction.wakes==endedWakes);}
 // A real live attacker immediately wakes the same companion, preserving native support.
 a.enemy.alive=true;a.enemy.combat=true;a.owner.victim=nullptr;assert(ai::GetPartyCombatAnchor(&a)==&a.owner);a.PrepareForPartyCombat();assert(a.state==BotState::BOT_STATE_COMBAT);
 a.owner.attackers.clear();a.owner.combat=false;
 // A new uncommanded enemy does not inherit the explicit order from the previous pull.
 a.enemy.alive=true;a.enemy.combat=true;a.context.GetValue<ObjectGuid>("current target")->value=2;a.partyFlag=false;bot.roleTank=bot.roleHeal=false;bot.nativeMap.raid=false;a.OnCombatStarted();
 assert(WaitForAttackStrategy::ShouldWait(&a));
 // During a phased boss, a live native combat target is preserved even if cached attackers are empty.
 a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_COMBAT);
 // Transfer and a real player's own AI never receive companion lifecycle changes.
 bot.transfer=true;a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_COMBAT);bot.transfer=false;
 }
 // Abandoned/unengaged pulls expire on the original native deadline.
 Player bot;PlayerbotAI a(&bot);sObjectMgr.member=&a.owner;now=200;a.pull.target=&a.enemy;a.pull.started=now;a.OnCombatStarted();now=216;a.PrepareForRaidRegroup();assert(a.state==BotState::BOT_STATE_NON_COMBAT&&!a.pull.HasTarget());
 std::cout<<"PASS actual shared pull preparation -> explicit Attack -> native engagement -> final kill -> immediate formation; parties/raids, three roles, four maps, no old-order reuse, phases and timeout\n";
}
'''
code=prefix.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='shared-engagement-') as td:
  p=Path(td);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
