"""Execute the native timed wait and explicit order admission across all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/generic/CombatStrategy.cpp').read_text()
methods='\n'.join(block(s,x) for x in ('WaitForAttackStrategy* WaitForAttackStrategy::Get(',
    'void WaitForAttackStrategy::AllowExplicitAttack(', 'bool WaitForAttackStrategy::HasExplicitAttackOrder(',
    'bool WaitForAttackStrategy::ShouldWait(', 'uint8 WaitForAttackStrategy::GetWaitTime('))
access=block((r/'playerbot/strategy/actions/BotCommandAccess.h').read_text(),'inline bool CanManageBotCommands(')
code=r'''
#include <cassert>
#include <ctime>
#include <map>
#include <string>
#include <type_traits>
#include <iostream>
using uint8=unsigned char;using ObjectGuid=unsigned;
enum{SEC_PLAYER=0};enum class PlayerbotSecurityLevel{PLAYERBOT_SECURITY_ALLOW_ALL};
namespace BotState{enum{BOT_STATE_COMBAT};}
time_t now=100;time_t fakeTime(time_t*){return now;}
#define time fakeTime
struct Map{bool raid=false;bool IsRaid(){return raid;}};struct Group{};struct PlayerbotAI;struct WaitForAttackStrategy;
struct Unit{virtual ~Unit()=default;bool world=true,alive=true,combat=true,friendly=false;unsigned guid=3,entry=1,instance=1;
 Unit*victim=nullptr;Unit*GetVictim(){return victim;}virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}};
struct Session{unsigned security=0;unsigned GetSecurity(){return security;}};
struct Player:Unit{Map map;Map*GetMap(){return &map;}unsigned GetMapId(){return 409;}bool roleTank=false;bool IsPlayer()override{return true;}bool real=true,transfer=false,charm=false;Group*group=nullptr;PlayerbotAI*ai=nullptr;Session session;
 bool isRealPlayer(){return real;}Group*GetGroup(){return group;}bool IsInMap(Unit*u){return u&&u->instance==instance;}
 bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}Session*GetSession(){return &session;}PlayerbotAI*GetPlayerbotAI(){return ai;}};
template<class T>struct Cached{T value{};T Get(){return value;}};
struct AiObjectContext{Cached<time_t>combat;Cached<uint8>wait;Cached<ObjectGuid>target;
 template<class T>Cached<T>*GetValue(const char*){if constexpr(std::is_same_v<T,time_t>)return &combat;
 else if constexpr(std::is_same_v<T,uint8>)return &wait;else return &target;}};
struct Security{bool allowed=true;bool CheckLevelFor(PlayerbotSecurityLevel,bool,Player*){return allowed;}};
struct PlayerbotAI{Player*bot,*owner;AiObjectContext context;Security security;bool healer=false;bool IsHeal(Player*){return healer;}bool enabled=true,human=false,tank=false;WaitForAttackStrategy*strategy=nullptr;std::map<unsigned,Unit*>units;
 PlayerbotAI(Player*b,Player*o):bot(b),owner(o){b->ai=this;context.wait.value=10;context.combat.value=100;context.target.value=3;}
 Player*GetBot(){return bot;}Player*GetMaster(){return owner;}Security*GetSecurity(){return &security;}bool HasRealPlayerMaster(){return owner&&owner->real;}
 bool IsRealPlayer(){return human;}bool IsTank(Player*p){return p==bot?tank:p->roleTank;}AiObjectContext*GetAiObjectContext(){return &context;}bool HasStrategy(const char*,int){return enabled;}
 time_t GetCombatStartTime(){return context.combat.value;}Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}
 template<class T>T*GetStrategy(const char*,int){return enabled?static_cast<T*>(strategy):nullptr;}};
struct WaitForAttackStrategy{ObjectGuid orderedOwner=0,orderedTarget=0;time_t orderedAt=0,orderedCombatStart=0;
 static WaitForAttackStrategy*Get(PlayerbotAI*);static bool ShouldWait(PlayerbotAI*);static uint8 GetWaitTime(PlayerbotAI*);
 void AllowExplicitAttack(PlayerbotAI*,Player*,Unit*);bool HasExplicitAttackOrder(PlayerbotAI*,time_t);};
struct{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
bool MoltenCorePackStackRequired(PlayerbotAI*){return false;}bool MoltenCoreImpUnderPressure(PlayerbotAI*){return false;}
__ACCESS__
__METHODS__
int main(){Player bot,owner,other;Group group,foreign;bot.guid=2;owner.guid=1;other.guid=4;bot.group=owner.group=&group;Unit target;
 PlayerbotAI ai(&bot,&owner);ai.units={{3,&target}};WaitForAttackStrategy strategy;ai.strategy=&strategy;
 assert(WaitForAttackStrategy::ShouldWait(&ai));now=108;assert(WaitForAttackStrategy::ShouldWait(&ai));now=110;assert(!WaitForAttackStrategy::ShouldWait(&ai));now=100;
 strategy.AllowExplicitAttack(&ai,&owner,&target);assert(!WaitForAttackStrategy::ShouldWait(&ai)&&ai.context.wait.value==10);
 ai.context.combat.value=101;now=101;assert(WaitForAttackStrategy::ShouldWait(&ai)); // another pull is not authorized
 for(unsigned fault=0;fault<8;++fault){strategy={};ai.context.combat.value=101;ai.owner=&owner;owner.group=&group;target.instance=1;target.friendly=false;target.alive=true;bot.transfer=false;bot.charm=false;ai.security.allowed=true;ai.human=false;
  Player*requester=&owner;
  if(fault==0)requester=&other;if(fault==1)owner.group=&foreign;if(fault==2)target.instance=2;if(fault==3)target.friendly=true;
  if(fault==4)target.alive=false;if(fault==5)bot.transfer=true;if(fault==6)ai.security.allowed=false;if(fault==7)ai.human=true;
  strategy.AllowExplicitAttack(&ai,requester,&target);assert(strategy.orderedTarget==0);
 }
 ai.human=false;ai.security.allowed=true;bot.transfer=false;bot.charm=false;owner.group=&group;target.alive=true;target.friendly=false;target.instance=1;
 strategy={};ai.context.combat.value=0;strategy.AllowExplicitAttack(&ai,&owner,&target);
 ai.context.combat.value=102;now=102;assert(!WaitForAttackStrategy::ShouldWait(&ai));
 ai.context.combat.value=103;now=103;assert(WaitForAttackStrategy::ShouldWait(&ai));
 strategy={};ai.context.combat.value=0;strategy.AllowExplicitAttack(&ai,&owner,&target);ai.context.combat.value=107;now=107;assert(!WaitForAttackStrategy::ShouldWait(&ai)); // approach/hit can start later than three seconds
 strategy={};strategy.AllowExplicitAttack(&ai,&owner,&target);target.entry=11669;assert(WaitForAttackStrategy::ShouldWait(&ai));ai.tank=true;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.tank=false; // imp hold survives an explicit order
 target.entry=1;ai.owner=&other;other.group=&group;assert(WaitForAttackStrategy::ShouldWait(&ai));ai.owner=&owner;
 target.combat=false;assert(!WaitForAttackStrategy::ShouldWait(&ai)); // an explicit Attack authorizes approach before native aggro
 time_t savedNow=now;now=strategy.orderedAt+16;assert(!strategy.HasExplicitAttackOrder(&ai,ai.context.combat.value));now=savedNow;
 target.combat=true;target.alive=false;assert(WaitForAttackStrategy::ShouldWait(&ai));target.alive=true;
 ai.enabled=false;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.enabled=true;ai.context.combat.value=0;assert(!WaitForAttackStrategy::ShouldWait(&ai));
 ai.context.combat.value=now=200;strategy={};bot.map.raid=true;target.entry=12101;target.victim=&owner;owner.roleTank=true;
 assert(!WaitForAttackStrategy::ShouldWait(&ai)); // natural Surger pull already held by a raid tank
 owner.roleTank=false;assert(WaitForAttackStrategy::ShouldWait(&ai));owner.roleTank=true;owner.group=&foreign;assert(WaitForAttackStrategy::ShouldWait(&ai));owner.group=&group;
 target.entry=11669;assert(WaitForAttackStrategy::ShouldWait(&ai)); // requested imp damage hold survives tank control
 ai.healer=true;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.healer=false;ai.tank=true;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.tank=false;
 target.entry=11673;assert(!WaitForAttackStrategy::ShouldWait(&ai));bot.map.raid=false;assert(WaitForAttackStrategy::ShouldWait(&ai));
 std::cout<<"PASS native explicit Attack: timed gate released only for authorized current pull; normal wait, imp wait, native permissions and later pulls preserved\n";
}
'''.replace('__ACCESS__',access).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='attack-wait-') as tmp:
  d=Path(tmp);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
