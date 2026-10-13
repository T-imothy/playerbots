"""Exercise merged native routines at their packet, clock and class boundaries."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

R=Path(__file__).resolve().parents[1]
def source(p): return (R/p).read_text(encoding='utf-8')
mage=source('playerbot/strategy/mage/MageTriggers.cpp')
header=source('playerbot/strategy/mage/MageTriggers.h')
blast=block(header,'class ArcaneBlastTrigger')+';'
full=block(header,'class ArcaneBlastFullTrigger')+';'
methods='#ifdef MANGOSBOT_ONE\n'+block(mage,'bool ArcaneBlastTrigger::IsActive()')+'\n#endif\n'+block(mage,'bool ArcaneBlastFullTrigger::IsActive()')
buy=block(source('playerbot/strategy/actions/BuyFailedAction.cpp'),'bool BuyFailedAction::Execute(')
mgr=source('playerbot/PlayerbotMgr.cpp')
start=mgr.index('    Action* action = nullptr;',mgr.index('std::string PlayerbotHolder::HandleBotDo'))
finish=mgr.index('    ai->RecordMessages(true, true);',start)
resolve=mgr[start:finish]
ai=source('playerbot/PlayerbotAI.cpp')
start=ai.index('        if (!aiObjectContext->GetValue<time_t>("combat start time")->Get())',ai.index('void PlayerbotAI::OnCombatStarted'))
clock_start=ai[start:ai.index('\n\n',start)]
start=ai.index('    if (!sServerFacade.IsInCombat(bot))',ai.index('void PlayerbotAI::Reset(bool full)'))
clock_reset=ai[start:ai.index('\n    bot->SetSelectionGuid',start)]
start=ai.index('    if (currentEngine == engines[(uint8)BotState::BOT_STATE_NON_COMBAT] && !sServerFacade.IsInCombat(bot)')
clock_end=block(ai[start:],'if (currentEngine')
code=r'''
#include <cassert>
#include <cstdint>
#include <ctime>
#include <map>
#include <string>
#include <vector>
#include <iostream>
using uint8=uint8_t;using uint32=uint32_t;
struct Unit{bool alive=true,combat=false;bool IsAlive(){return alive;}};struct Player:Unit{};
struct Aura{unsigned amount=0;unsigned GetStackAmount(){return amount;}};
struct Action{};struct Context{std::map<std::string,Action>actions;Action*GetAction(const std::string&n){auto i=actions.find(n);return i==actions.end()?nullptr:&i->second;}};
struct PlayerbotAI{Unit*bot;Unit*target;bool known=true,stacked=false;unsigned mana=100,stacks=0;Aura aura;Context context;std::string error;
 bool HasSpell(const char*){return known;}bool HasAura(std::string,Unit*t,bool,bool){assert(t==bot);return stacked;}Aura*GetAura(unsigned id,Unit*t){assert(id==36032&&t==bot);aura.amount=stacks;return stacks?&aura:nullptr;}
 Context*GetAiObjectContext(){return &context;}void TellError(Player*,const std::string&e){error=e;}};
struct BuffTrigger{PlayerbotAI*ai;Unit*bot;std::string spell;bool checkIsOwner=false;BuffTrigger(PlayerbotAI*a,const char*n):ai(a),bot(a->bot),spell(n){}virtual bool IsActive(){return false;}Unit*GetTarget(){return ai->target;}};
struct{unsigned mediumMana=40,lowMana=15;}sPlayerbotAIConfig;
#define AI_VALUE2(T,n,q) (ai->mana)
__MAGE__
enum class BuyResult{CANT_FIND_ITEM=0,ITEM_ALREADY_SOLD=1,NOT_ENOUGHT_MONEY=2,SELLER_DONT_LIKE_YOU=3,DISTANCE_TOO_FAR=4,ITEM_SOLD_OUT=5,CANT_CARRY_MORE=6,RANK_REQUIRE=7,REPUTATION_REQUIRE=8,SILENT_ERROR=9};
#define BUY_ERR_CANT_FIND_ITEM BuyResult::CANT_FIND_ITEM
#define BUY_ERR_ITEM_ALREADY_SOLD BuyResult::ITEM_ALREADY_SOLD
#define BUY_ERR_NOT_ENOUGHT_MONEY BuyResult::NOT_ENOUGHT_MONEY
#define BUY_ERR_SELLER_DONT_LIKE_YOU BuyResult::SELLER_DONT_LIKE_YOU
#define BUY_ERR_DISTANCE_TOO_FAR BuyResult::DISTANCE_TOO_FAR
#define BUY_ERR_ITEM_SOLD_OUT BuyResult::ITEM_SOLD_OUT
#define BUY_ERR_CANT_CARRY_MORE BuyResult::CANT_CARRY_MORE
#define BUY_ERR_RANK_REQUIRE BuyResult::RANK_REQUIRE
#define BUY_ERR_REPUTATION_REQUIRE BuyResult::REPUTATION_REQUIRE
struct WorldPacket{std::vector<uint8>bytes;size_t pos=0;size_t size(){return bytes.size();}void rpos(size_t n){assert(n<bytes.size());pos=n;}WorldPacket&operator>>(uint8&v){assert(pos<bytes.size());v=bytes[pos++];return *this;}};
struct Event{WorldPacket packet;Player*owner=nullptr;Player*getOwner(){return owner;}WorldPacket&getPacket(){return packet;}};
struct BuyFailedAction{PlayerbotAI*ai;Player*master;Player*GetMaster(){return master;}bool Execute(Event&);};
__BUY__
std::string resolve(PlayerbotAI*ai,const std::string&param){std::string actionName=param,subparam;__RESOLVE__return actionName+"|"+subparam;}
enum class BotState{BOT_STATE_NON_COMBAT=0,BOT_STATE_COMBAT=1};
struct Value{time_t value=0;time_t Get(){return value;}void Set(time_t v){value=v;}void Reset(){value=0;}};
struct ClockContext{Value clock;template<class T>Value*GetValue(const char*){return &clock;}};
struct Facade{bool IsInCombat(Unit*u){return u->combat;}}sServerFacade;
#define RESET_AI_VALUE(T,n) aiObjectContext->GetValue<T>(n)->Reset()
struct ClockAI{Unit*bot;ClockContext*aiObjectContext;void*engines[2]={(void*)1,(void*)2};void*currentEngine=engines[0];
 void start(){__CLOCK_START__}void reset(){__CLOCK_RESET__}void tick(){__CLOCK_END__}};
int main(){Unit bot;Player master;PlayerbotAI ai{&bot,&bot};ArcaneBlastTrigger blast(&ai);ArcaneBlastFullTrigger full(&ai);
#ifdef MANGOSBOT_ONE
 for(unsigned mana:{20u,40u,41u,100u})for(bool stacked:{false,true}){ai.mana=mana;ai.stacked=stacked;assert(blast.IsActive()==(!stacked||mana>40));assert(full.IsActive()==(stacked&&mana<=40));}
 ai.known=false;assert(!blast.IsActive()&&!full.IsActive());ai.known=true;bot.alive=false;assert(!blast.IsActive()&&!full.IsActive());bot.alive=true;ai.target=nullptr;assert(!blast.IsActive()&&!full.IsActive());ai.target=&bot;
#elif defined(MANGOSBOT_TWO)
 for(unsigned stacks=0;stacks<=4;++stacks){ai.stacks=stacks;assert(blast.IsActive()==(stacks<4));assert(!full.IsActive());}ai.mana=15;assert(!blast.IsActive());ai.mana=100;ai.known=false;assert(!blast.IsActive());ai.known=true;
#else
 assert(!full.IsActive());
#endif
 BuyFailedAction buy{&ai,&master};Event event;for(unsigned size:{13u,17u}){event.packet.bytes.assign(size,0);event.packet.bytes[12]=7;event.packet.bytes.back()=2;ai.error.clear();assert(buy.Execute(event)&&ai.error=="I don't have enough money.");event.packet.bytes.back()=8;assert(buy.Execute(event)&&ai.error=="I don't have enough reputation for this item.");event.packet.bytes.back()=250;assert(!buy.Execute(event));}
 for(unsigned size:{0u,12u,14u,16u,18u}){event.packet.bytes.assign(size,2);assert(!buy.Execute(event));}buy.master=nullptr;assert(!buy.Execute(event));
 ai.context.actions={{"cast",{}},{"cast custom spell",{}},{"attack",{}}};assert(resolve(&ai,"cast custom spell first second")=="cast custom spell|first second");assert(resolve(&ai,"cast 123 target name")=="cast|123 target name");assert(resolve(&ai,"attack")=="attack|");assert(resolve(&ai,"unknown one two")=="action not found");
 ClockContext context;ClockAI clock{&bot,&context};clock.start();time_t initial=context.clock.value;assert(initial>0);bot.combat=true;context.clock.value=initial-20;clock.reset();clock.start();assert(context.clock.value==initial-20);clock.tick();assert(context.clock.value==initial-20);bot.combat=false;clock.tick();assert(context.clock.value==0);clock.start();assert(context.clock.value>=initial);clock.reset();assert(context.clock.value==0);
 std::cout<<"PASS merged native mage/packet/command/combat clock boundaries\n";}
'''
for placeholder,value in [('__MAGE__',blast+'\n'+full+'\n'+methods),('__BUY__',buy),('__RESOLVE__',resolve),('__CLOCK_START__',clock_start),('__CLOCK_RESET__',clock_reset),('__CLOCK_END__',clock_end)]:code=code.replace(placeholder,value)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='upstream-native-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code,encoding='utf-8')
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
    print('PASS upstream sync',era,flush=True)
assert not any(line.strip()=='#define MEMORY_MONITOR' for line in source('playerbot/MemoryMonitor.h').splitlines())
assert 'ShareCreators<' in source('playerbot/strategy/actions/WorldPacketActionContext.h')
assert 'ShareCreators<' in source('playerbot/strategy/mage/MageAiObjectContext.cpp')
print('PASS production instrumentation disabled and creator sharing retained')
