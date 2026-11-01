"""Actual default invalid-target value re-evaluates immediately; stale-cache hypothesis rejected."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method='bool ClassicRaidTargetAction::Execute(Event& event) {return AttackAction::Execute(event);}'
get=block((root/'playerbot/strategy/Value.h').read_text(),'        virtual T Get() override')
invalid=block((root/'playerbot/strategy/values/InvalidTargetValue.cpp').read_text(),'bool InvalidTargetValue::Calculate(')
code=r'''
#include <algorithm>
#include <cassert>
#include <ctime>
#include <iostream>
#include <list>
#include <string>
#include <type_traits>
using ObjectGuid=unsigned;
enum class BotState{BOT_STATE_COMBAT};
struct Unit{unsigned guid=0,entry=16427;unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}};
struct Player{unsigned map=533,selection=1;unsigned GetMapId(){return map;}unsigned GetSelectionGuid(){return selection;}};
struct PlayerbotAI;
template<class T>struct BaseValue{virtual T Get()=0;};
struct AiNamedObject{static std::string getName(){return "invalid target";}};
struct Monitor{int start(int,std::string,PlayerbotAI*){return 0;}}sPerformanceMonitor;
enum{PERF_MON_VALUE};
#define MANTECH_DIAG_SCOPE(...)
template<class T>struct Cache:BaseValue<T>{time_t lastCheckTime=0;int checkInterval=1;T value{};PlayerbotAI*ai=nullptr;virtual T Calculate()=0;unsigned resets=0;void Reset(){lastCheckTime=0;++resets;}
__GET__
};
Unit oldTarget{1},incoming{2},other{3};Unit*elected=&incoming;unsigned current=1;bool basic=true,protectedCC=false,attackable=false;
struct InvalidTargetValue;
struct Context{InvalidTargetValue*invalid=nullptr;template<class T>Cache<T>*GetValue(const char*,const char*);};
struct PlayerbotAI{Player*bot;Context context;Unit*GetUnit(unsigned guid){return guid==1?&oldTarget:guid==2?&incoming:guid==3?&other:nullptr;}Context*GetAiObjectContext(){return &context;}bool HasStrategy(const char*,BotState){return true;}};
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u&&basic;}};
struct PossibleAttackTargetsValue{static bool IsValid(Unit*,Player*){return attackable;}static bool IsPossibleTarget(Unit*,Player*,float,bool){return false;}};
struct MeleeCcCheck{MeleeCcCheck(PlayerbotAI*){}bool Protected(Unit*){return protectedCC;}};
struct DungeonAddTargetAction{DungeonAddTargetAction(PlayerbotAI*){}Unit*GetTarget(){return nullptr;}};
Unit*RazorgoreDefenseTarget(PlayerbotAI*,bool&defense){defense=false;return nullptr;}
Unit*KelthuzadOpeningTarget(PlayerbotAI*){
#ifdef MANGOSBOT_ZERO
return elected;
#else
return nullptr;
#endif
}
bool RaidLabMovementResult(Player*,const char*,unsigned,bool result){return result;}
struct{float sightDistance=60;}sPlayerbotAIConfig;
template<class T>T Value(const std::string&key){if constexpr(std::is_same_v<T,unsigned>)return key=="duel target"?0:current;else return {};}
#define AI_VALUE(type,key) Value<type>(key)
struct InvalidTargetValue:Cache<bool>{Player*bot;std::string qualifier="current target";bool Calculate()override;};
template<class T>Cache<T>*Context::GetValue(const char*name,const char*qualifier){assert(std::string(name)=="invalid target"&&std::string(qualifier)=="current target");return invalid;}
__INVALID__
struct Event{};
struct AttackAction{PlayerbotAI*ai;Player*bot;bool succeeds=true,commit=true;Unit*chosen=&incoming;bool Execute(Event&){if(!succeeds)return false;if(commit){current=chosen->guid;bot->selection=current;}return true;}};
struct ClassicRaidTargetAction:AttackAction{bool Execute(Event&);};
__METHOD__
void check(bool okay,const char*message){if(!okay){std::cerr<<message<<"\n";std::exit(42);}}
int main(){Player bot;PlayerbotAI brain{&bot};InvalidTargetValue cached;cached.ai=&brain;cached.bot=&bot;brain.context.invalid=&cached;ClassicRaidTargetAction action;action.ai=&brain;action.bot=&bot;Event event;
 // Match native default checkInterval=1 and the actual current timestamp.
 // Setting lastCheckTime in the future would fabricate a cache lifetime.
 auto prime=[&](){current=1;bot.selection=1;cached.Reset();check(cached.Get(),"old generic target should be rejected");};
 prime();check(action.Execute(event),"native attack failed");
#ifdef MANGOSBOT_ZERO
 check(!cached.Get(),"STALE_INVALID_TARGET: newly selected incoming add inherited the previous target's rejection");
 // Recalculate real safety, never replace it with an unconditional valid flag.
 prime();protectedCC=true;check(action.Execute(event),"attack fixture");check(cached.Get(),"protected target incorrectly valid");protectedCC=false;
 prime();action.succeeds=false;auto before=cached.resets;check(!action.Execute(event)&&cached.resets==before,"failed attack modified cache");action.succeeds=true;
 prime();elected=&other;before=cached.resets;check(action.Execute(event)&&cached.resets==before,"unrelated target modified cache");elected=&incoming;
 prime();bot.map=409;before=cached.resets;check(action.Execute(event)&&cached.resets==before,"other map modified cache");bot.map=533;
 prime();action.commit=false;before=cached.resets;check(action.Execute(event)&&cached.resets==before,"accepted attack without target commitment modified cache");
#else
 check(cached.Get(),"later-era behavior changed");
#endif
 std::cout<<"PASS native default invalid-target recalculates after selection; old-cache hypothesis does not reproduce\n";
}
'''.replace('__GET__',get).replace('__INVALID__',invalid).replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='kt-target-cache-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  result=subprocess.run([str(path/'test.exe')],cwd=path,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  print(era+': '+result.stdout.strip())
