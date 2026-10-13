"""Execute native-facing idle regroup and combat-end wake without cancelling casts."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
ai=(R/'playerbot/PlayerbotAI.cpp').read_text();follow=(R/'playerbot/strategy/actions/FollowActions.cpp').read_text()
methods='\n'.join(block(s,n) for s,n in ((follow,'bool ai::RaidRegroupNeeded('),(ai,'void PlayerbotAI::OnCombatEnded('),(ai,'void PlayerbotAI::PrepareForRaidRegroup(')))
assert 'RaidRegroupNeeded(ai)' in block(follow,'bool FollowAction::isUseful(')
assert 'RaidRegroupNeeded(ai)' in (R/'playerbot/strategy/triggers/RangeTriggers.h').read_text()
assert '!RaidRegroupNeeded(ai)' in block((R/'playerbot/strategy/actions/MovementActions.cpp').read_text(),'bool MovementAction::Follow(Unit* target, float distance, float angle)')
update=block(ai,'void PlayerbotAI::UpdateAI(');assert update.index('PrepareForRaidRegroup()')<update.index('if (!delayAlreadyAdvanced)')
code=r'''
#include <cassert>
#include <cmath>
#include <ctime>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;
enum class BotState{BOT_STATE_NON_COMBAT,BOT_STATE_COMBAT};
struct WorldLocation{unsigned mapid=409;float coord_x=0,coord_y=0,coord_z=0;};
struct Group{bool raid=true;bool IsRaidGroup(){return raid;}};
struct Spline{bool done=true;bool Finalized(){return done;}};
struct Unit{virtual ~Unit()=default;bool alive=true,world=true;unsigned map=409;bool IsAlive(){return alive;}};
struct Player:Unit{Group group;bool grouped=true,transfer=false,charm=false,combat=false,casting=false,taxi=false;float x=20;Spline spline;Spline*movespline=&spline;
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}bool IsInCombat(){return combat;}Group*GetGroup(){return grouped?&group:nullptr;}
 bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}bool IsTaxiFlying(){return taxi;}unsigned GetMapId(){return map;}bool IsInMap(Unit*u){return u->world&&u->map==map;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+b*b+c*c);}};
struct Formation{WorldLocation station;bool null=false;WorldLocation GetLocation(){return station;}static bool IsNullLocation(const WorldLocation&s){return s.mapid==0;}};
struct EncounterPosition{};
template<class T>struct Cached{T value{};unsigned resets=0;T Get(){return value;}void Set(T v){value=v;}void Reset(){++resets;}};
struct Context{template<class T>Cached<T>*GetValue(const char*){static Cached<T>c;return &c;}};
struct ReactionEngine{unsigned wakes=0;void NotifyPartyCombat(){++wakes;}};
struct PlayerbotAI{Player*bot;Unit target;Formation formation;Context context;Context*aiObjectContext=&context;ReactionEngine reaction;ReactionEngine*reactionEngine=&reaction;
 bool human=false,owned=true,mobile=true,jumping=false,follow=true,stay=false,guard=false,party=false,isWaiting=true;BotState state=BotState::BOT_STATE_NON_COMBAT;unsigned aiInternalUpdateDelay=15000,stops=0;
 PlayerbotAI(Player*b):bot(b){context.GetValue<ObjectGuid>("follow target")->value=1;context.GetValue<Formation*>("formation")->value=&formation;}
 Player*GetBot(){return bot;}bool HasRealPlayerMaster(){return owned;}bool IsRealPlayer(){return human;}bool CanMove(){return mobile;}bool IsJumping(){return jumping;}
 bool IsStateActive(BotState s){return state==s;}void ChangeEngine(BotState s){state=s;}void ResetAIInternalUpdateDelay(){aiInternalUpdateDelay=0;}void StopMoving(){++stops;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){return id?&target:nullptr;}bool IsSafe(Unit*u){return u&&u->world&&bot->IsInMap(u);}
 bool HasStrategy(const char*n,BotState s){return std::string(n)=="follow"?follow&&s==BotState::BOT_STATE_NON_COMBAT:std::string(n)=="stay"?stay:std::string(n)=="guard"?guard:false;}
 void PrepareForRaidRegroup();void OnCombatEnded();};
namespace ai{bool RaidRegroupNeeded(PlayerbotAI*);Player*GetPartyCombatAnchor(PlayerbotAI*a){return a->party?a->bot:nullptr;}}
__METHODS__
int main(){Player bot;PlayerbotAI ai(&bot);
 assert(ai::RaidRegroupNeeded(&ai));ai.PrepareForRaidRegroup();assert(!ai.isWaiting&&ai.aiInternalUpdateDelay==0); // stationary master, stopped old generator
 bot.x=2;assert(!ai::RaidRegroupNeeded(&ai));bot.x=20;
 bot.spline.done=false;assert(!ai::RaidRegroupNeeded(&ai));bot.spline.done=true;
 bot.casting=true;ai.aiInternalUpdateDelay=9000;ai.PrepareForRaidRegroup();assert(ai.aiInternalUpdateDelay==9000&&bot.casting); // ongoing resurrection/heal
 bot.casting=false;ai.state=BotState::BOT_STATE_COMBAT;ai.party=true;ai.PrepareForRaidRegroup();assert(ai.state==BotState::BOT_STATE_COMBAT);
 ai.party=false;ai.PrepareForRaidRegroup();assert(ai.state==BotState::BOT_STATE_NON_COMBAT&&ai.reaction.wakes==1&&ai.aiInternalUpdateDelay==0);
 for(unsigned fault=0;fault<11;++fault){bot.world=bot.alive=bot.grouped=bot.group.raid=true;bot.transfer=bot.charm=bot.combat=bot.casting=false;ai.human=ai.stay=ai.guard=ai.jumping=false;ai.owned=ai.mobile=ai.follow=true;
  if(fault==0)bot.world=false;if(fault==1)bot.alive=false;if(fault==2)bot.transfer=true;if(fault==3)bot.charm=true;if(fault==4)bot.combat=true;if(fault==5)bot.group.raid=false;if(fault==6)ai.human=true;if(fault==7)ai.owned=false;if(fault==8)ai.stay=true;if(fault==9)ai.guard=true;if(fault==10)ai.mobile=false;
  assert(!ai::RaidRegroupNeeded(&ai));}
 std::cout<<"PASS stationary raid regroup, arrived spline, no mana dependency, native resurrection/heal preservation, party combat and owner/control guards\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='raid-regroup-') as tmp:
  p=Path(tmp);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
