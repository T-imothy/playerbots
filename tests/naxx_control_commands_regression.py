"""Execute the Naxx command bridge, real chat mappings, queue and pull-end bodies.

Native world/session outcomes are mocked; this tests dispatch/lifecycle sequencing,
not a live possession spell, pathfinding or raid completion.
"""
from pathlib import Path
import re, subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
helper = (root/'playerbot/strategy/actions/NaxxramasControlCommands.cpp').read_text()
helper = '\n'.join(line for line in helper.splitlines() if not line.startswith('#include'))
ai_source = (root/'playerbot/PlayerbotAI.cpp').read_text()
chat_source = (root/'playerbot/strategy/generic/ChatCommandHandlerStrategy.cpp').read_text()
pull_source = (root/'playerbot/strategy/actions/PullActions.cpp').read_text()
supported = re.findall(r'supported.push_back\("([^"]+)"\)', chat_source)
assert 'naxxControlScopeActive' in ai_source
assert '(bot->GetMapId() == 533 || naxxControlScopeActive)' in ai_source
assert ai_source.index('ProcessNaxxramasControlCommands(this') < ai_source.index('controller->UpdateControl()', ai_source.index('ProcessNaxxramasControlCommands(this'))
assert 'if (!NaxxramasControlAllowed(ai)) return nullptr;' in (root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()

code = r'''
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <queue>
#include <string>
#include <type_traits>
#include <vector>
using int32=int;using uint32=unsigned;
long long clockNow=100;
long long testTime(void*){return clockNow;}
#define time testTime
constexpr unsigned CHAT_MSG_WHISPER=1,REACT_PASSIVE=0;
struct Player;struct PlayerbotAI;struct Unit;
using ObjectGuid=Unit*;
namespace ai {
enum BotState{BOT_STATE_REACTION};
struct Event{std::string source,param;Player*owner=nullptr;Event(std::string s="",std::string p="",Player*o=nullptr):source(s),param(p),owner(o){}
 std::string getSource()const{return source;}Player*getOwner()const{return owner;}};
bool NaxxramasControlAllowed(PlayerbotAI*);
void ProcessNaxxramasControlCommands(PlayerbotAI*,bool);
}
using namespace ai;
struct Unit{unsigned entry=16803;bool world=true,alive=true,combat=false,sameMap=true;ObjectGuid owner=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool IsPlayer(){return false;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return this;}bool HasCharmer(ObjectGuid p){return owner==p;}};
struct UnitAI{void SetReactState(unsigned){}unsigned GetReactState(){return 0;}void AttackStart(Unit*){}};
struct Creature:Unit{UnitAI brain;UnitAI*AI(){return &brain;}};
using Pet=Creature;
struct Player:Unit{unsigned map=533,instance=7;bool transfer=false,charmed=false,real=false,authorized=true;
 Unit*charm=nullptr;unsigned breaks=0;bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charmed;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}bool IsInMap(Unit*u){return u&&u->sameMap;}
 Unit*GetCharm(){return charm;}bool isRealPlayer(){return real;}Pet*GetPet(){return nullptr;}
 void BreakCharmOutgoing(Unit*u){assert(u==charm&&u->owner==this);u->owner=nullptr;charm=nullptr;++breaks;}};
struct Trigger{Event event;Event Check(){return event;}void Reset(){event=Event();}};
struct NextAction{std::string name;NextAction(std::string s,float):name(s){}std::string getName(){return name;}
 static NextAction**array(int first,...){std::vector<NextAction*>v;va_list args;va_start(args,first);while(auto*a=va_arg(args,NextAction*))v.push_back(a);va_end(args);
 auto*r=new NextAction*[v.size()+1]{};for(unsigned i=0;i<v.size();++i)r[i]=v[i];return r;}
 static void destroy(NextAction**a){if(a){for(unsigned i=0;a[i];++i)delete a[i];delete[]a;}}};
struct TriggerNode{std::string name;NextAction**handlers;Trigger*trigger=nullptr;
 TriggerNode(std::string s,NextAction**h):name(s),handlers(h){}~TriggerNode(){NextAction::destroy(handlers);}
 std::string getName(){return name;}void setTrigger(Trigger*t){trigger=t;}NextAction**getHandlers(){assert(trigger);unsigned n=0;while(handlers[n])++n;
 auto*r=new NextAction*[n+1]{};for(unsigned i=0;i<n;++i)r[i]=new NextAction(handlers[i]->name,1);return r;}};
template<class T>struct Value{T value{};T Get(){return value;}void Set(T v){value=v;}};
struct Context{Value<bool>blocked;Value<int32>instance;std::map<std::string,Trigger>triggers;
 template<class T>Value<T>*GetValue(const char*,const char*){if constexpr(std::is_same_v<T,bool>)return &blocked;else return &instance;}
 Trigger*GetTrigger(std::string s){return &triggers[s];}};
using AiObjectContext=Context;
struct PositionEntry{bool isSet(){return false;}};using PositionMap=std::map<std::string,PositionEntry>;
struct ChatCommandHolder{std::string command;Player*owner;long long due=0;bool available=true;
 bool IsOwnerAvailable(){return available;}long long GetTime(){return due;}std::string GetCommand(){return command;}
 Player*GetOwner(){return owner;}unsigned GetType(){return CHAT_MSG_WHISPER;}};
struct PullStrategy;
struct PlayerbotAI{Player bot;Context storage;Context*aiObjectContext=&storage;std::queue<ChatCommandHolder>chatCommands;
 PullStrategy*pull=nullptr;bool real=false,melee=true;unsigned handled=0,combatStarts=0,meleeCalls=0;PositionMap positions;Unit*target=nullptr;
 std::vector<std::string>actions;PlayerbotAI(){bot.combat=true;}
 Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return aiObjectContext;}bool IsRealPlayer(){return real;}
 void HandleCommands();bool DoSpecificAction(const std::string&,Event=Event(),bool=false);
 Unit*GetUnit(ObjectGuid p){return p;}bool IsMelee(Player*){return melee;}void OnCombatStarted(){++combatStarts;}
 void TellPlayerNoFacing(Player*,const char*){} };
struct ExternalEventHelper{Context*context;ExternalEventHelper(Context*c):context(c){}
 bool ParseChatCommand(std::string s,Player*p){context->triggers[s].event=Event(s,"",p);return true;}};
bool CanManageBotCommands(PlayerbotAI*,Player*p){return p&&p->authorized;}
bool NaxxramasEncounterEngaged(Player*,Unit*u){return u&&u->combat;}
struct PullStrategy{Unit*target=nullptr;bool allowed=false,started=false;long long start=100;unsigned ended=0;
 static PullStrategy*Get(PlayerbotAI*a){return a->pull;}bool IsEncounterPreparationAllowed(){return allowed;}
 bool HasPullStarted(){return started;}Unit*GetTarget(){return target;}long long GetPullStartTime(){return start;}
 unsigned GetMaxPullTime(){return 15;}void OnPullEnded(){allowed=false;started=false;++ended;target=nullptr;}
 ObjectGuid GetRequester(){return nullptr;}bool HasSavedPetReactState(){return false;}unsigned GetPetReactState(){return 0;}};
struct PassTroughStrategy{std::vector<std::string>supported;float relevance=100;
 void InitNonCombatTriggers(std::list<TriggerNode*>&nodes){for(auto&s:supported)nodes.push_back(new TriggerNode(s,NextAction::array(0,new NextAction(s,relevance),nullptr)));}};
struct ChatCommandHandlerStrategy:PassTroughStrategy{ChatCommandHandlerStrategy(PlayerbotAI*){supported={__SUPPORTED__};}
 void InitTriggers(std::list<TriggerNode*>&nodes,BotState){InitReactionTriggers(nodes);}void InitReactionTriggers(std::list<TriggerNode*>&);};
struct PullEndAction{PlayerbotAI*ai;Player*bot;bool Execute(Event&);};
#define AI_VALUE(T,N) ([&]()->T {if constexpr(std::is_same_v<T,PositionMap&>)return ai->positions;else return ai->target;}())
#define SET_AI_VALUE(T,N,V) ai->target=V
__CHAT__
__QUEUE__
__END__
bool PlayerbotAI::DoSpecificAction(const std::string&name,Event event,bool){actions.push_back(name);
 if(name=="pull end"){PullEndAction action{this,&bot};return action.Execute(event);}
 if(name=="melee"){++meleeCalls;}
 // Follow/reset rebuild ordinary contexts in production. The helper must write
 // its explicit override after the handler, then still accept a later attack.
 if(name=="follow chat shortcut"||name=="stay chat shortcut"||name=="reset ai")storage.blocked.Set(false);
 return true;}
__HELPER__
void issue(PlayerbotAI&a,Player&owner,const char*command,long long due=0){a.chatCommands.push({command,&owner,due});ProcessNaxxramasControlCommands(&a,true);}
void own(PlayerbotAI&a,Unit&student){a.bot.charm=&student;student.owner=&a.bot;}
int main(){
 PlayerbotAI a;Player human;human.real=true;Unit student;own(a,student);
 ProcessNaxxramasControlCommands(&a,false);assert(a.bot.charm==&student&&a.actions.empty()&&a.bot.breaks==0);
 issue(a,human,"status");assert(a.actions.back()=="status"&&a.bot.charm==&student);
 auto n=a.actions.size();ProcessNaxxramasControlCommands(&a,true);assert(a.actions.size()==n); // consumed once
 human.authorized=false;issue(a,human,"follow");assert(a.bot.charm==&student&&a.actions.size()==n);
 human.authorized=true;human.real=false;issue(a,human,"follow");assert(a.bot.charm==&student);human.real=true;
 issue(a,human,"follow",110);assert(a.bot.charm==&student&&!a.chatCommands.empty());clockNow=110;
 ProcessNaxxramasControlCommands(&a,true);assert(a.bot.charm==nullptr&&a.actions.back()=="follow chat shortcut"&&!NaxxramasControlAllowed(&a));
 ProcessNaxxramasControlCommands(&a,false);assert(!NaxxramasControlAllowed(&a)&&a.bot.breaks==1); // no reacquisition
 issue(a,human,"attack");assert(a.actions.back()=="attack my target"&&NaxxramasControlAllowed(&a));
 own(a,student);issue(a,human,"stay");assert(!NaxxramasControlAllowed(&a));issue(a,human,"pull");assert(a.actions.back()=="pull my target"&&NaxxramasControlAllowed(&a));
 own(a,student);issue(a,human,"follow");a.bot.combat=false;assert(NaxxramasControlAllowed(&a));a.bot.combat=true;
 own(a,student);issue(a,human,"follow");a.bot.instance=8;ProcessNaxxramasControlCommands(&a,false);assert(NaxxramasControlAllowed(&a));
 own(a,student);issue(a,human,"follow");a.bot.map=409;ProcessNaxxramasControlCommands(&a,false);a.bot.map=533;assert(NaxxramasControlAllowed(&a));
 // Loading/map/real-character/foreign charms do not dispatch or cancel control.
 own(a,student);a.bot.transfer=true;n=a.actions.size();issue(a,human,"status");assert(a.actions.size()==n);a.bot.transfer=false;
 ProcessNaxxramasControlCommands(&a,true);assert(a.actions.size()==n+1);
 a.real=true;issue(a,human,"follow");assert(a.bot.charm==&student);a.real=false;a.chatCommands={};
 student.owner=&human;n=a.actions.size();issue(a,human,"follow");assert(a.actions.size()==n&&a.bot.charm==&student);a.chatCommands={};own(a,student);
 // Accepted native pull retires once, adopts actual combat, and never starts
 // owner's melee (which would cancel possession). Ordinary pulls are unchanged.
 PullStrategy pull;Unit boss;boss.entry=16061;boss.combat=true;a.pull=&pull;
 pull.target=&boss;pull.allowed=pull.started=true;pull.start=clockNow;
 ProcessNaxxramasControlCommands(&a,false);assert(pull.ended==1&&!pull.started&&a.combatStarts==1&&a.meleeCalls==0&&a.bot.charm==&student);
 ProcessNaxxramasControlCommands(&a,false);assert(pull.ended==1);
 boss.combat=false;pull.target=&boss;pull.allowed=pull.started=true;pull.start=clockNow-15;
 ProcessNaxxramasControlCommands(&a,false);assert(pull.ended==2&&a.meleeCalls==0&&a.bot.charm==&student);
 pull.target=&boss;pull.allowed=pull.started=true;pull.start=clockNow;boss.alive=false;
 ProcessNaxxramasControlCommands(&a,false);assert(pull.ended==3);boss.alive=true;
 pull.target=&boss;pull.allowed=pull.started=true;student.owner=&human;
 ProcessNaxxramasControlCommands(&a,false);assert(pull.ended==3);own(a,student);
 boss.combat=true;Event ordinary("pull end");PullEndAction end{&a,&a.bot};assert(end.Execute(ordinary));assert(a.meleeCalls==1);
 std::cout<<"PASS actual Naxx command dispatch, delayed ownership checks, suspension scope and native pull cleanup\n";
}
'''
# A type-directed helper keeps the actual AI_VALUE expressions intact.
code=code.replace('#define AI_VALUE(T,N) ([&]()->T {if constexpr(std::is_same_v<T,PositionMap&>)return ai->positions;else return ai->target;}())',
                  'template<class T>T fixtureValue(PlayerbotAI*a){if constexpr(std::is_same_v<T,PositionMap&>)return a->positions;else return a->target;}\n#define AI_VALUE(T,N) fixtureValue<T>(ai)')
code=code.replace('__SUPPORTED__',','.join('"'+s+'"' for s in supported))
code=code.replace('__CHAT__',block(chat_source,'void ChatCommandHandlerStrategy::InitReactionTriggers('))
code=code.replace('__QUEUE__',block(ai_source,'void PlayerbotAI::HandleCommands('))
code=code.replace('__END__',block(pull_source,'bool PullEndAction::Execute(')).replace('__HELPER__',helper)
with tempfile.TemporaryDirectory(prefix='naxx-control-commands-') as folder:
    p=Path(folder);(p/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
