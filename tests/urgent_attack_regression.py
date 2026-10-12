"""Execute production owning-thread wakeup and explicit healer/attack actions."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
source=(r/'playerbot/PlayerbotAI.cpp').read_text()
handler=block(source,'void PlayerbotAI::HandleCommand(')
assert handler.index('chatFilter.Filter(')<handler.index('urgentAttackPending.store')
assert handler.index('PLAYERBOT_SECURITY_ALLOW_ALL')<handler.index('urgentAttackPending.store')
update=block(source,'void PlayerbotAI::UpdateAI(')
assert update.index('updateLock.owns_lock()')<update.index('ProcessPendingTransition()')<update.index('PrepareForUrgentAttack()')
wake=block(source,'void PlayerbotAI::PrepareForUrgentAttack(')
base=block((r/'playerbot/PlayerbotAIBase.cpp').read_text(),'bool PlayerbotAIBase::AdvanceMinimalUpdateDelay(')
attack=(r/'playerbot/strategy/actions/AttackAction.cpp').read_text()
execute=block(attack,'bool AttackMyTargetAction::Execute(')
useful=block(attack,'bool AttackMyTargetAction::isUseful(')
code=r'''
#include <cassert>
#include <atomic>
#include <string>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr unsigned UNIT_STAND_STATE_STAND=0;
enum class BotState{BOT_STATE_COMBAT};
struct Unit{bool world=true,alive=true,friendly=false;float distance=10;bool IsInWorld(){return world;}bool IsAlive(){return alive;}};
struct Player:Unit{bool transfer=false,charm=false,sit=true;unsigned selected=2,stands=0;bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}
 bool IsSitState(){return sit;}void SetStandState(unsigned s){assert(s==0);sit=false;++stands;}unsigned GetSelectionGuid(){return selected;}bool IsInMap(Unit*u){return u&&u->world;}};
struct{float sightDistance=100;}sPlayerbotAIConfig;
struct{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}float GetDistance2d(Player*,Unit*u){return u->distance;}}sServerFacade;
struct PlayerbotAI{Player*bot;Player*owner;Unit*target;bool human=false,healer=false,offdps=false,isWaiting=true;unsigned aiInternalUpdateDelay=15000,attackGuid=0,followed=0,attacked=0;
 bool moved=true,followUseful=true;std::atomic<bool>urgentAttackPending{false};
 bool IsRealPlayer(){return human;}bool IsHeal(Player*){return healer;}bool HasStrategy(const char*,BotState){return offdps;}
 Unit*GetUnit(unsigned g){return g==2?target:nullptr;}void TellError(Player*,const char*){}
 bool HasUrgentCommand(){return urgentAttackPending.load(std::memory_order_acquire);}
 void PrepareForUrgentAttack();bool AdvanceMinimalUpdateDelay(unsigned);
};
struct Event{Player*owner;Player*getOwner(){return owner;}};
struct FollowAction{PlayerbotAI*ai;explicit FollowAction(PlayerbotAI*a):ai(a){}bool Execute(Event&){++ai->followed;return ai->moved;}bool isUseful(){return ai->followUseful;}};
struct AttackMyTargetAction{PlayerbotAI*ai;Player*bot;bool verbose=true;Player*GetMaster(){return ai->owner;}
 bool IsTargetValid(Player*,Unit*u){return u&&u->world&&u->alive&&!u->friendly&&u->distance<=100;}
 bool Attack(Player*p,Unit*u){if(!IsTargetValid(p,u))return false;++ai->attacked;return true;}bool Execute(Event&);bool isUseful();};
#define SET_AI_VALUE(type,name,value) ai->attackGuid=value
__METHODS__
int main(){Player bot,owner;Unit enemy;PlayerbotAI ai{&bot,&owner,&enemy};AttackMyTargetAction action{&ai,&bot};Event event{&owner};
 assert(!ai.AdvanceMinimalUpdateDelay(50)&&ai.aiInternalUpdateDelay==14950);
 ai.urgentAttackPending=true;assert(ai.AdvanceMinimalUpdateDelay(50));ai.PrepareForUrgentAttack();
 assert(!bot.sit&&bot.stands==1&&ai.aiInternalUpdateDelay==0&&!ai.isWaiting&&!ai.HasUrgentCommand());
 assert(action.isUseful()&&action.Execute(event)&&ai.attacked==1&&ai.attackGuid==2);
 ai.healer=true;ai.attackGuid=0;assert(action.Execute(event)&&ai.followed==1&&ai.attacked==1&&ai.attackGuid==0);
 ai.moved=false;ai.followUseful=false;assert(action.Execute(event)&&ai.attacked==1);
 enemy.distance=150;ai.moved=true;assert(action.Execute(event)&&ai.attackGuid==0);
 ai.healer=false;assert(action.Execute(event)&&ai.attackGuid==2);
 enemy.friendly=true;ai.attackGuid=0;unsigned follow=ai.followed;assert(!action.Execute(event)&&ai.followed==follow);
 for(unsigned fault=0;fault<5;++fault){Player p;PlayerbotAI a{&p,&owner,&enemy};a.urgentAttackPending=true;
  if(fault==0)p.world=false;if(fault==1)p.alive=false;if(fault==2)p.transfer=true;if(fault==3)p.charm=true;if(fault==4)a.human=true;
  a.PrepareForUrgentAttack();assert(p.sit&&p.stands==0&&a.aiInternalUpdateDelay==15000);}
 std::cout<<"PASS native urgent Attack: long drink timer bypass, owner-thread stand, healer support, far-target follow, invalid targets and transfer/possession guards\n";}
'''.replace('__METHODS__',wake+'\n'+base.replace('PlayerbotAIBase::','PlayerbotAI::')+'\n'+execute+'\n'+useful)
with tempfile.TemporaryDirectory(prefix='mantech-urgent-attack-') as tmp:
 folder=Path(tmp);(folder/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=folder,check=True)
 subprocess.run([str(folder/'test.exe')],check=True)
