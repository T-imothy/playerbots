"""Run native wake, movement-reaction completion and no-mana reach bodies."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
ai=(r/'playerbot/PlayerbotAI.cpp').read_text()
reaction=(r/'playerbot/strategy/ReactionEngine.cpp').read_text()
reach=(r/'playerbot/strategy/actions/ReachTargetActions.h').read_text()
ranged=(r/'playerbot/strategy/generic/RangedCombatStrategy.cpp').read_text()
update=block(ai,'void PlayerbotAI::UpdateAI(')
assert update.index('updateLock.owns_lock()')<update.index('PrepareForPartyCombat()')<update.index('if (!delayAlreadyAdvanced)')
methods='\n'.join([block(ai,'void PlayerbotAI::PrepareForPartyCombat('),block(ai,'void PlayerbotAI::OnCombatStarted('),
 block(reaction,'void ReactionEngine::NotifyPartyCombat('),block(reaction,'void ReactionEngine::StopReaction('),
 block(reaction,'bool ReactionEngine::Update('),block(reaction,'bool ReactionEngine::CanUpdateAIReaction('),
 block(reaction,'bool Reaction::Update('),block(reaction,'void Reaction::SetAction('),
 block(reach,'virtual bool isUseful() override').replace('virtual bool isUseful() override','bool ReachTargetAction::isUseful()'),
 block(ranged,'void RangedCombatStrategy::InitCombatTriggers(')])
code=r'''
#include <cassert>
#include <algorithm>
#include <ctime>
#include <list>
#include <string>
#include <type_traits>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
enum class BotState{BOT_STATE_NON_COMBAT,BOT_STATE_COMBAT,BOT_STATE_DEAD};
enum {UNIT_STAND_STATE_STAND=0,IDLE_MOTION_TYPE=0,FOLLOW_MOTION_TYPE=1,POINT_MOTION_TYPE=2,DIST_CALC_COMBAT_REACH=0};
struct PositionEntry{PositionEntry(float=0,float=0,float=0,unsigned=0){}};struct EncounterPosition{};
struct MotionMaster{int type=FOLLOW_MOTION_TYPE;int GetCurrentMovementGeneratorType(){return type;}};
struct Unit{virtual ~Unit()=default;};
struct Player:Unit{bool world=true,alive=true,transfer=false,charm=false,sit=true,taxi=false,stopped=true,casting=true,los=true;unsigned mana=0,stands=0;float distance=70;MotionMaster motion;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}
 bool IsSitState(){return sit;}void SetStandState(unsigned s){assert(s==0);sit=false;++stands;}unsigned GetMapId(){return 409;}
 float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}MotionMaster*GetMotionMaster(){return &motion;}
 bool IsStopped(){return stopped;}bool IsTaxiFlying(){return taxi;}bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}
 bool IsWithinLOSInMap(Unit*,bool){return los;}float GetDistance(Unit*,bool,int){return distance;}};
template<class T>struct Cached{T value{};unsigned resets=0;T Get(){return value;}void Set(T v){value=v;}void Reset(){++resets;}};
struct Context{Cached<time_t>start;Cached<PositionEntry>pos;Cached<std::list<ObjectGuid>>attackers;Cached<bool>hasAttackers;Cached<EncounterPosition>plan;
 template<class T,class Q=int>Cached<T>*GetValue(const char*,Q={}){
 if constexpr(std::is_same_v<T,time_t>)return &start;else if constexpr(std::is_same_v<T,PositionEntry>)return &pos;
 else if constexpr(std::is_same_v<T,std::list<ObjectGuid>>)return &attackers;else if constexpr(std::is_same_v<T,bool>)return &hasAttackers;else return &plan;}};
struct ReactionEngine;
struct PlayerbotAI{Player*bot;ReactionEngine*reactionEngine=nullptr;Context context;Context*aiObjectContext=&context;
 bool human=false,owned=true,anchor=true,jumping=false,isWaiting=true,followNC=false,followC=false,stay=false;
 BotState state=BotState::BOT_STATE_NON_COMBAT;unsigned aiInternalUpdateDelay=15000,resetCount=0,stops=0,transitions=0,castQueries=0;
 bool IsRealPlayer(){return human;}bool HasRealPlayerMaster(){return owned;}Player*GetBot(){return bot;}bool IsJumping(){return jumping;}
 bool IsStateActive(BotState s){return state==s;}BotState GetState(){return state;}
 bool HasStrategy(const char*n,BotState s){return std::string(n)=="follow"?(s==BotState::BOT_STATE_COMBAT?followC:followNC):std::string(n)=="stay"&&stay;}
 void ChangeEngine(BotState s){state=s;++transitions;}void ResetAIInternalUpdateDelay(){aiInternalUpdateDelay=0;++resetCount;}
 void StopMoving(){++stops;bot->stopped=true;}void PrepareForPartyCombat();void OnCombatStarted();
 bool CanCastSpell(const std::string&,Unit*,int,void*,bool,bool,bool){++castQueries;return bot->mana>0;}};
namespace ai{Player*GetPartyCombatAnchor(PlayerbotAI*a){return a->anchor?a->bot:nullptr;}}
struct Action{virtual ~Action()=default;bool useful=true;unsigned duration=8000;virtual bool isUseful(){return useful;}unsigned GetDuration(){return duration;}};
struct MovementAction:Action{};struct AttackAction:MovementAction{};
struct Reaction{Action*action=nullptr;unsigned duration=0;bool IsValid()const{return action;}bool IsActive()const{return action&&duration>100;}
 Action*GetAction()const{return action;}void Reset(){action=nullptr;duration=0;}void SetDuration(unsigned n){duration=n;}void SetAction(Action*);bool Update(unsigned);};
struct{unsigned reactDelay=100;}sPlayerbotAIConfig;
struct ReactionEngine{PlayerbotAI*ai;unsigned aiReactionUpdateDelay=5000,searches=0,starts=0;Reaction ongoingReaction,incomingReaction;
 bool IsReacting(){return ongoingReaction.IsValid();}bool HasIncomingReaction(){return incomingReaction.IsValid();}
 bool FindReaction(bool){++searches;return false;}bool StartReaction(){++starts;ongoingReaction=incomingReaction;incomingReaction.Reset();return true;}
 void NotifyPartyCombat();void StopReaction();bool CanUpdateAIReaction()const;bool Update(unsigned,bool,bool,bool&);};
struct ReachTargetAction{PlayerbotAI*ai;Player*bot;Unit*target;float range=30;std::string spellName;Unit*GetTarget(){return target;}bool isUseful();};
constexpr float ACTION_MOVE=10;
struct NextAction{std::string name;float priority;NextAction(const char*n,float p):name(n),priority(p){}static NextAction*array(int,NextAction*a,void*){return a;}};
struct TriggerNode{std::string name;NextAction*action;TriggerNode(const char*n,NextAction*a):name(n),action(a){}~TriggerNode(){delete action;}};
struct RangedCombatStrategy{void InitCombatTriggers(std::list<TriggerNode*>&);};
__METHODS__
int main(){Player bot;PlayerbotAI ai{&bot};ReactionEngine engine{&ai};ai.reactionEngine=&engine;
 MovementAction oldFollow;engine.ongoingReaction.SetAction(&oldFollow);
 ai.PrepareForPartyCombat(); // Natural wand pull, zero mana, 15-second drink.
 assert(!bot.sit&&bot.stands==1&&bot.mana==0&&bot.casting&&ai.stops==0);
 assert(ai.state==BotState::BOT_STATE_COMBAT&&ai.aiInternalUpdateDelay==0&&!ai.isWaiting);
 assert(engine.aiReactionUpdateDelay==0&&!engine.IsReacting()&&ai.context.plan.resets==1);
 ai.aiInternalUpdateDelay=1500;ai.PrepareForPartyCombat();assert(ai.aiInternalUpdateDelay==1500&&ai.transitions==1); // not a per-tick cast/GCD reset
 ai.state=BotState::BOT_STATE_NON_COMBAT;bot.sit=false;ai.aiInternalUpdateDelay=9000;
 ai.PrepareForPartyCombat();assert(ai.aiInternalUpdateDelay==0&&bot.stands==1); // standing ranged also wakes
 for(unsigned f=0;f<8;++f){ai.state=BotState::BOT_STATE_NON_COMBAT;ai.human=false;ai.owned=ai.anchor=true;bot.world=bot.alive=true;bot.transfer=bot.charm=false;bot.sit=true;ai.aiInternalUpdateDelay=15000;
  if(f==0)ai.human=true;if(f==1)ai.owned=false;if(f==2)ai.anchor=false;if(f==3)bot.world=false;if(f==4)bot.alive=false;if(f==5)bot.transfer=true;if(f==6)bot.charm=true;if(f==7)ai.state=BotState::BOT_STATE_DEAD;
  ai.PrepareForPartyCombat();assert(bot.sit&&ai.aiInternalUpdateDelay==15000);}
 ai.human=false;ai.owned=ai.anchor=true;bot.world=bot.alive=true;bot.transfer=bot.charm=false;bot.sit=false;
 // Native combat transition stops follow only, retaining a physical hazard point path and native cast.
 ai.followNC=true;bot.motion.type=POINT_MOTION_TYPE;ai.state=BotState::BOT_STATE_NON_COMBAT;ai.OnCombatStarted();assert(ai.stops==0&&bot.casting);
 bot.motion.type=FOLLOW_MOTION_TYPE;ai.state=BotState::BOT_STATE_NON_COMBAT;ai.OnCombatStarted();assert(ai.stops==1);
 bool found=false;bot.stopped=true;engine.ongoingReaction.SetAction(&oldFollow);engine.aiReactionUpdateDelay=5000;
 assert(!engine.Update(50,false,false,found)&&engine.searches==1); // completed native move does not retain 8 seconds
 Action nativeCast;engine.ongoingReaction.SetAction(&nativeCast);engine.NotifyPartyCombat();assert(engine.IsReacting()&&engine.ongoingReaction.duration==8000);
 assert(engine.Update(50,false,false,found)&&engine.searches==1&&engine.ongoingReaction.duration==7950);
 AttackAction attack;engine.ongoingReaction.SetAction(&attack);engine.NotifyPartyCombat();assert(engine.IsReacting());
 bot.stopped=false;engine.ongoingReaction.SetAction(&oldFollow);engine.aiReactionUpdateDelay=0;
 assert(engine.Update(50,false,false,found)&&engine.searches==1); // ordinary ongoing move retains its token
 engine.incomingReaction.SetAction(&oldFollow);engine.NotifyPartyCombat();assert(!engine.IsReacting()&&!engine.HasIncomingReaction()&&!bot.stopped); // never stops physical path itself
 for(unsigned f=0;f<3;++f){ai.owned=true;ai.jumping=false;bot.taxi=false;bot.stopped=true;engine.aiReactionUpdateDelay=0;engine.ongoingReaction.SetAction(&oldFollow);
  if(f==0)ai.owned=false;if(f==1)ai.jumping=true;if(f==2)bot.taxi=true;
  assert(engine.Update(50,false,false,found)&&engine.IsReacting());}
 ai.owned=true;ai.jumping=bot.taxi=false;engine.ongoingReaction.Reset();
 // Execute the actual native unqualified reach admission with no mana.
 Unit enemy;bot.casting=false;ai.stay=false;bot.distance=70;ReachTargetAction approach{&ai,&bot,&enemy};
 assert(approach.isUseful()&&ai.castQueries==0);approach.spellName="frostbolt";assert(!approach.isUseful()&&ai.castQueries==1);
 approach.spellName.clear();bot.distance=20;assert(!approach.isUseful());bot.los=false;assert(approach.isUseful());
 ai.stay=true;assert(!approach.isUseful());ai.stay=false;bot.casting=true;assert(!approach.isUseful());
 RangedCombatStrategy strategy;std::list<TriggerNode*>triggers;strategy.InitCombatTriggers(triggers);
 auto*t=triggers.front();assert(t->name=="enemy out of spell"&&t->action->name=="reach spell"&&t->action->priority==ACTION_MOVE);
 for(auto*t:triggers)delete t;
 std::cout<<"PASS native natural/standing/zero-mana pull wake, guard and cast preservation, completed-move reaction release, independent reach admission\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='party-pull-wake-') as tmp:
  d=Path(tmp);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
