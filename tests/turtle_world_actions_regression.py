from pathlib import Path
from turtle_cpp_fixture import run
import re
r=Path(__file__).resolve().parents[3];m=r/'modules/ManTechPlayerbots/playerbot'
def clean(s): return re.sub(r'^#(?:include|pragma).*$', '',s,flags=re.M)
header=clean((m/'WorldActions.h').read_text(encoding='utf-8'))
body=clean((m/'WorldActions.cpp').read_text(encoding='utf-8')).replace('std::chrono::steady_clock','FixtureClock')
engine=(m/'strategy/Engine.cpp').read_text(encoding='utf-8')
continuation=engine[engine.index('bool Engine::ScheduleWorldContinuation('):engine.index('bool Engine::DoNextAction(')]
reaction=(m/'strategy/ReactionEngine.cpp').read_text(encoding='utf-8')
reset=reaction[reaction.index('void ReactionEngine::Reset()'):reaction.index('bool ReactionEngine::CanUpdateAIReaction()')]
run(r'''#include <cstdint>
#include <algorithm>
#include <deque>
#include <functional>
#include <mutex>
#include <unordered_map>
#include <map>
#include <memory>
#include <string>
#include <chrono>
#include <vector>
#include <cassert>
#include <cstdio>
#include <thread>
#include <atomic>
#include "MapWork.h"
struct FixtureClock {using duration=std::chrono::microseconds;using rep=duration::rep;using period=duration::period;using time_point=std::chrono::time_point<FixtureClock>;static constexpr bool is_steady=true;static inline uint64_t us=0;static time_point now(){return time_point(duration(us));}};
using uint32=uint32_t;
struct ObjectGuid { uint32 id;uint32 GetCounter()const{return id;} };
struct BotChatLifetime{};
struct ByteBufferException{};
struct Session{bool headless=true,logging=false;uint32 account=1;bool IsHeadless(){return headless;}bool isLogingOut(){return logging;}uint32 GetAccountId(){return account;}};
class PlayerbotAI;
struct Player{uint32 id=1,map=0,instance=0;uint64_t generation=1;bool world=true,teleport=false;Session session;PlayerbotAI*ai=nullptr;
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return teleport;}Session*GetSession(){return &session;}uint32 GetGUIDLow(){return id;}ObjectGuid GetObjectGuid(){return{id};}
 uint32 GetMapId(){return map;}uint32 GetInstanceId(){return instance;}uint64_t GetMapWorkGeneration(){return generation;}};
namespace ai {struct Event {std::shared_ptr<bool> available=std::make_shared<bool>(true);bool IsOwnerAvailable()const{return *available;}};}
struct PlayerbotAI{Player*bot;std::shared_ptr<BotChatLifetime>life=std::make_shared<BotChatLifetime>();int actions=0;uint32 delay=0;uint32 GetAIInternalUpdateDelay(){return delay;}void SetNextCheckDelay(uint32 value){delay=value;}
 std::weak_ptr<BotChatLifetime>GetChatLifetime(){return life;}Player*GetBot(){return bot;}void DoSpecificAction(std::string const&,ai::Event const&,bool){++actions;}};
PlayerbotAI*GetBotAI(Player*p){return p->ai;}
struct Accessor{std::unordered_map<uint32,Player*>players;Player*FindPlayer(ObjectGuid g){auto p=players.find(g.id);return p==players.end()?nullptr:p->second;}}sObjectAccessor;
struct World{int depth=0,stops=0;bool wantStop=false;void BeginHeadlessStopDeferral(){++depth;}void EndHeadlessStopDeferral(){if(!--depth&&wantStop){++stops;wantStop=false;}}}sWorld;
struct Logger{template<class...T>void outError(const char*,T...){} }sLog;
'''+header+body+r'''
namespace ai {struct QueueMock {struct Node{std::string getName(){return "test";}};struct Basket {Node*getAction(){static Node n;return &n;}};Basket*Peek(){return nullptr;}};struct Engine {PlayerbotAI*ai;QueueMock queue;std::shared_ptr<int>worldContinuationEpoch=std::make_shared<int>(0);std::weak_ptr<int>pendingWorldDecision;
 bool WorldContinuationPending()const{return !pendingWorldDecision.expired();}bool ScheduleWorldContinuation(Event const&,std::function<void(Engine&)>);
};
'''+continuation+r'''
struct ReactionEngine:Engine {using Engine::Engine;struct State{void Reset(){}}ongoingReaction,incomingReaction;uint32 aiReactionUpdateDelay=0;bool decisionPrepared=false;void Reset();};
'''+reset+r'''}
int main(){
 auto&q=ai::WorldActions::Instance();Player p;PlayerbotAI bot{&p};p.ai=&bot;sObjectAccessor.players[p.id]=&p;ai::Event event;
 assert(!ai::WorldActions::IsMapExecution());{ai::WorldActions::MapScope s;assert(ai::WorldActions::IsMapExecution());{ai::WorldActions::MapScope t;}assert(ai::WorldActions::IsMapExecution());}assert(!ai::WorldActions::IsMapExecution());
 for(int i=0;i<8;++i)assert(q.Enqueue(&p,"x",event));assert(!q.Enqueue(&p,"x",event));q.Drain();assert(bot.actions==8);
 q.Enqueue(&p,"x",event);++p.generation;q.Drain();assert(bot.actions==8);
 q.Enqueue(&p,"x",event);++p.instance;q.Drain();assert(bot.actions==8);
 q.Enqueue(&p,"x",event);p.teleport=true;q.Drain();assert(bot.actions==8);p.teleport=false;
 q.Enqueue(&p,"x",event);*event.available=false;q.Drain();assert(bot.actions==8);*event.available=true;
 q.Enqueue(&p,"x",event);bot.life=std::make_shared<BotChatLifetime>();q.Drain();assert(bot.actions==8);
 q.Enqueue(&p,"x",event);p.session.account=2;q.Drain();assert(bot.actions==8);p.session.account=1;
 bool called=false;q.Enqueue(&p,"stop",event,[&](PlayerbotAI&){assert(sWorld.depth==1);assert(ai::WorldActions::IsContinuation());sWorld.wantStop=true;assert(!sWorld.stops);called=true;});q.Drain();assert(called&&sWorld.stops==1&&sWorld.depth==0);assert(!ai::WorldActions::IsContinuation());
 q.Enqueue(&p,"throw",event,[](PlayerbotAI&){throw ByteBufferException();});q.Drain();assert(sWorld.depth==0);
 ai::Engine e{&bot};int resumed=0;assert(e.ScheduleWorldContinuation(event,[&](ai::Engine&){++resumed;}));assert(e.WorldContinuationPending());assert(e.ScheduleWorldContinuation(event,[&](ai::Engine&){resumed+=10;}));q.Drain();assert(resumed==1&&!e.WorldContinuationPending());
 e.ScheduleWorldContinuation(event,[&](ai::Engine&){++resumed;});e.worldContinuationEpoch=std::make_shared<int>(0);q.Drain();assert(resumed==1&&!e.WorldContinuationPending());
 e.ScheduleWorldContinuation(event,[&](ai::Engine&){++resumed;});++p.generation;q.Drain();assert(resumed==1&&!e.WorldContinuationPending());
 e.ScheduleWorldContinuation(event,[&](ai::Engine&){++resumed;});q.Clear();assert(!e.WorldContinuationPending());
 ai::ReactionEngine reaction;reaction.ai=&bot;reaction.ScheduleWorldContinuation(event,[&](ai::Engine&){++resumed;});reaction.Reset();q.Drain();assert(resumed==1&&!reaction.WorldContinuationPending());
 // Concurrent producers never exceed the per-bot bound, and clear releases admission.
 std::atomic<int>accepted{0};std::vector<std::thread>threads;for(int i=0;i<16;++i)threads.emplace_back([&]{for(int n=0;n<10;++n)if(q.Enqueue(&p,"x",event))++accepted;});for(auto&t:threads)t.join();assert(accepted==8);q.Clear();assert(q.Enqueue(&p,"x",event));q.Clear();
 std::vector<Player>players(129);std::vector<PlayerbotAI>ais;ais.reserve(129);int total=0;for(int i=0;i<129;++i){players[i].id=10+i;ais.push_back({&players[i]});players[i].ai=&ais.back();for(int n=0;n<8;++n)if(q.Enqueue(&players[i],"x",event))++total;}assert(total==1024);q.Clear();

 // A deterministic clock tests service capacity and the soft single-callback bound.
 assert(q.DrainBudgetMs(0)==8 && q.DrainBudgetMs(30)==8 && q.DrainBudgetMs(64)==16 && q.DrainBudgetMs(128)==32 && q.DrainBudgetMs(UINT32_MAX)==32);
 for(uint32_t diff=0;diff<10000;++diff)assert(q.DrainBudgetMs(diff)>=8&&q.DrainBudgetMs(diff)<=32);
 for(int i=0;i<8;++i){auto&actor=players[i];sObjectAccessor.players[actor.id]=&actor;for(int j=0;j<8;++j)assert(q.Enqueue(&actor,"timed",event,[](PlayerbotAI&){FixtureClock::us+=1000;}));}
 q.Drain(30);auto stats=q.GetStats();assert(stats.budgetMs==8&&stats.lastDrained==8&&stats.lastDrainUs==8000&&stats.pending==56);
 q.Drain(128);stats=q.GetStats();assert(stats.budgetMs==32&&stats.lastDrained==32&&stats.lastDrainUs==32000&&stats.pending==24);q.Clear();
 for(int j=0;j<8;++j)assert(q.Enqueue(&p,"slow",event,[](PlayerbotAI&){FixtureClock::us+=100000;}));
 q.Drain(128);stats=q.GetStats();assert(stats.lastDrained==1&&stats.lastDrainUs==100000&&stats.pending==7);q.Clear();
 for(int i=0;i<128;++i){auto&actor=players[i];sObjectAccessor.players[actor.id]=&actor;for(int j=0;j<8;++j)assert(q.Enqueue(&actor,"cheap",event,[](PlayerbotAI&){}));}
 q.Drain(UINT32_MAX);stats=q.GetStats();assert(stats.lastDrained==256&&stats.pending==768);q.Clear();
 puts("PASS world drain: 8ms nominal, 32ms maximum, no accumulated credit/overflow, timed drain counts, oversized callback reporting, unchanged 256-callback limit");
 puts("PASS bounded world queue concurrent admission, actor/owner/logout/teleport cancellation, callback guard, engine epoch and retryable continuation cancellation");
}
''',[r/'src/shared'])
