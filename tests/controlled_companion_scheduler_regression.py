"""Run actual controlled-companion activity, follow setup and reaction-arrival cleanup.

Follow's unchanged geometry/transport branches are native boundaries here;
its duration setup and retained-generator branch are production code.
"""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
def src(p):
 if '--before' in sys.argv:return subprocess.run(['git','-C',str(R),'show','HEAD:'+p],capture_output=True,text=True,check=True).stdout
 return (R/p).read_text()
a=src('playerbot/PlayerbotAI.cpp');f=block(src('playerbot/strategy/actions/MovementActions.cpp'),'bool MovementAction::Follow(Unit* target, float distance, float angle)')
begin=f[f.index('{')+1:f.index('    if (!ai->IsSafe(target))')]
retained=block(f,'if (bot->GetMotionMaster()->GetCurrentMovementGeneratorType() == FOLLOW_MOTION_TYPE)')
code=r'''
#include <cassert>
#include <iostream>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#undef assert
#define assert(x) do{if(!(x)){fprintf(stderr,"FAIL scheduler line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
using uint32=unsigned;enum ActivityType{ALL_ACTIVITY,DETAILED_MOVE_ACTIVITY,REACT_ACTIVITY};enum class BotState{BOT_STATE_NON_COMBAT};
time_t now=100;time_t fakeTime(time_t*){return now;}
#define time fakeTime
enum{FOLLOW_MOTION_TYPE=1};struct Motion{unsigned GetCurrentMovementGeneratorType(){return 1;}};
struct Spline{bool done=true;bool Finalized(){return done;}};
struct Unit{unsigned GetObjectGuid(){return 1;}};
struct Player:Unit{bool world=true,alive=true,transfer=false,charm=false,taxi=false,casting=false;Motion motion;Spline spline;Spline*movespline=&spline;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}bool IsTaxiFlying(){return taxi;}
 bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}Motion*GetMotionMaster(){return &motion;}};
struct Action{virtual ~Action()=default;};struct MovementBase:Action{};using MovementActionType=MovementBase;struct AttackAction:MovementBase{};
struct Reaction{Action*action=nullptr;Action*GetAction()const{return action;}};
namespace ai{using ::Reaction;}
struct ReactionEngine{Reaction r;const Reaction*GetReaction(){return r.action?&r:nullptr;}};
struct PlayerbotAI{Player*bot;bool owned=true,human=false,jumping=false,active=false,isWaiting=true;time_t allowActiveCheckTimer[3]={100,100,100};bool allowActive[3]={false,false,false};unsigned calls=0,aiInternalUpdateDelay=9000;Action*last=nullptr;ReactionEngine reaction;ReactionEngine*reactionEngine=&reaction;
 Player*GetBot(){return bot;}bool HasRealPlayerMaster(){return owned;}bool IsRealPlayer(){return human;}bool IsJumping(){return jumping;}
 bool AllowActive(ActivityType){++calls;return active;}bool AllowActivity(ActivityType,bool=false);void PrepareCompletedMovement();
 const Action*GetLastExecutedAction(BotState){return last;}BotState GetState(){return BotState::BOT_STATE_NON_COMBAT;}void ResetAIInternalUpdateDelay(){aiInternalUpdateDelay=0;}};
// Same production polymorphic names used by the arrival cleanup.
using MovementAction=MovementBase;
__AI_METHODS__
#undef MovementAction
struct Facade{Unit*target=nullptr;Unit*GetChaseTarget(Player*){return target;}float GetChaseAngle(Player*){return 0;}float GetChaseOffset(Player*){return 5;}}sServerFacade;
struct{unsigned reactDelay=100;}sPlayerbotAIConfig;
bool rest=false,regroup=false;bool RaidRestInProgress(PlayerbotAI*){return rest;}bool RaidRegroupNeeded(PlayerbotAI*){return regroup;}
struct FollowNativeBoundary{PlayerbotAI*ai;Player*bot;unsigned duration=9000;void SetDuration(unsigned n){duration=n;}bool Follow(Unit*target,float distance,float angle){__BEGIN__ __RETAINED__ return true;}};
int main(int argc,char**argv){std::string select=argc>1?argv[1]:"all";Player bot;PlayerbotAI a{&bot};
 if(select=="all"||select=="activity"){
  // The companion has just acquired a real controller but still holds its negative idle-mode cache.
  for(auto kind:{ALL_ACTIVITY,DETAILED_MOVE_ACTIVITY,REACT_ACTIVITY})assert(a.AllowActivity(kind));assert(a.calls==0);
  a.owned=false;assert(!a.AllowActivity(ALL_ACTIVITY)&&a.calls==0);now=106;a.active=true;assert(a.AllowActivity(ALL_ACTIVITY)&&a.calls==1);a.owned=true;}
 if(select=="all"||select=="follow"){
  Unit owner;sServerFacade.target=&owner;FollowNativeBoundary follow{&a,&bot};
  assert(follow.Follow(&owner,5,0)&&follow.duration==100);assert(follow.Follow(&owner,5,0)&&follow.duration==100);
  rest=true;assert(!follow.Follow(&owner,5,0));rest=false;}
 if(select=="all"||select=="reaction"){
  Action oldCast;MovementBase follow;AttackAction attack;a.last=&oldCast;a.reaction.r.action=&follow;
  // The movement ran in the reaction engine; the ordinary last action is unrelated.
  a.aiInternalUpdateDelay=9000;a.PrepareCompletedMovement();assert(a.aiInternalUpdateDelay==0&&!a.isWaiting);
  a.reaction.r.action=&attack;a.aiInternalUpdateDelay=9000;a.PrepareCompletedMovement();assert(a.aiInternalUpdateDelay==9000);
  a.reaction.r.action=&follow;bot.casting=true;a.PrepareCompletedMovement();assert(a.aiInternalUpdateDelay==9000);
  bot.casting=false;bot.spline.done=false;a.PrepareCompletedMovement();assert(a.aiInternalUpdateDelay==9000);
  bot.spline.done=true;a.owned=false;a.PrepareCompletedMovement();assert(a.aiInternalUpdateDelay==9000);}
 std::cout<<"PASS shared controlled activity cache, retained native follow and completed reaction release; native casts, attack and unfinished movement retained\n";
}
'''
code=code.replace('__AI_METHODS__',block(a,'bool PlayerbotAI::AllowActivity(')+'\n'+block(a,'void PlayerbotAI::PrepareCompletedMovement(')).replace('__BEGIN__',begin).replace('__RETAINED__',retained)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='shared-scheduler-') as td:
  p=Path(td);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  args=[next((v.split('=',1)[1] for v in sys.argv if v.startswith('--case=')),'all')]
  subprocess.run([str(p/'test.exe'),*args],cwd=p,check=True)
