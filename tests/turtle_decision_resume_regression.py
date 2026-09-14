from pathlib import Path
from turtle_cpp_fixture import run
r=Path(__file__).resolve().parents[3];m=r/'modules/ManTechPlayerbots/playerbot/strategy'
s=(m/'Engine.cpp').read_text(encoding='utf-8');walk=s[s.index('bool Engine::DoNextAction('):s.index('ActionNode* Engine::CreateActionNode(')]
run(r'''#define MANTECH_DIAG_SCOPE(...)
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <functional>
#include <iomanip>
#include <list>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include <cassert>
#include <cstdio>
using uint32=uint32_t;using uint64=uint64_t;
constexpr int ACTION_RESULT_FAILED=1,ACTION_RESULT_IMPOSSIBLE=2,CLASS_WARRIOR=1,ACTION_MOVE=20,PERF_MON_ACTION=0;
struct Unit{};struct Player:Unit{int getClass(){return 2;}bool IsTaxiFlying(){return false;}};
struct Event{std::string source="retained event";auto getSource()const{return source;}};
struct NextAction{};
struct Action {std::string name;bool world=false,useful=true;int calls=0;virtual ~Action()=default;Unit*GetTarget(){return nullptr;}bool RequiresWorldOwner(){return world;}auto getName(){return name;}bool isUsefulWhenStunned(){return true;}bool isUseful(){return useful;}bool isPossible(){return true;}void setRelevance(float){}float getRelevance(){return 1;}bool ShouldTryAlternativesWhenUseless(){return false;}};
struct CastSpellAction:Action{int GetDecisionSpellId(){return 0;}Unit*GetTarget(){return nullptr;}};
struct ActionNode{Action*action;auto getName(){return action->name;}NextAction**getPrerequisites(){return nullptr;}NextAction**getAlternatives(){return nullptr;}NextAction**getContinuers(){return nullptr;}};
struct ActionBasket{ActionNode*node;Event event;ActionNode*getAction(){return node;}float getRelevance(){return 120;}bool isSkipPrerequisites(){return true;}Event getEvent(){return event;}};
struct Queue{std::list<ActionBasket*> items;~Queue(){while(!items.empty())delete Pop();}void Add(Action*a){items.push_back(new ActionBasket{new ActionNode{a},{}});}ActionBasket*Peek(){return items.empty()?nullptr:items.front();}ActionNode*Pop(){auto*b=Peek();if(!b)return nullptr;items.pop_front();auto*n=b->node;delete b;return n;}size_t Size(){return items.size();}void RemoveExpired(){}};
class Engine;
struct AI{Player bot;Engine*engine=nullptr;Player*GetBot(){return &bot;}Engine*GetCurrentEngine(){return engine;}Player*GetMaster(){return nullptr;}template<class...T>void TellPlayerNoFacing(T&&...){} };
struct WorldActions{static inline bool map=true,continuation=false;static bool IsMapExecution(){return map;}static bool IsContinuation(){return continuation;}};
struct Context{int updates=0;void Update(){++updates;}};
struct Multiplier{float GetValue(Action*){return 1;}std::string getName(){return "test";}};
struct PlayerbotEngineSample{bool minimal=false,actionExecuted=false;uint32 queueStart=0,queueEnd=0,evaluations=0,unknown=0,suppressedImpossible=0,suppressedFailed=0,ok=0,failed=0,impossible=0,useless=0;uint64 durationUs=0;};
struct {bool ShouldSampleEngineTick(){return false;}void RecordEngineSample(PlayerbotEngineSample const&){}template<class...T>void RecordFailure(T&&...){} }sPlayerbotDiagnostics;
enum class PlayerbotDiagnosticOutcome{Failed,Impossible};enum class PlayerbotSecurityLevel{PLAYERBOT_SECURITY_ALLOW_ALL};
struct {bool logValuesPerTick=false;uint32 iterationsPerTick=10;template<class...T>bool CanLogAction(T&&...){return false;}}sPlayerbotAIConfig;
struct {template<class...T>std::unique_ptr<int>start(T&&...){return {};}}sPerformanceMonitor;
struct CombatActionContext{CombatActionContext(std::string const&){} };struct CombatDiagnostics{static bool Select(AI*){return false;}template<class...T>static void Record(T&&...){} };
struct {int LookupSpellInfo(int){return 0;}}sServerFacade;
bool CanPlanWarriorSpell(AI*,std::string,Unit*){return false;}std::string WarriorStancePrerequisite(AI*,int){return "";}
struct WorldTimer{static uint32 getMSTime(){return 1;}};
struct Counter{void fetch_add(int,std::memory_order){} };
class Engine{public:
AI*ai;Queue queue;Context context;Context*aiObjectContext=&context;std::list<Multiplier*>multipliers;float lastRelevance=0;
bool decisionPrepared=false,pending=false;int triggers=0,defaults=0;std::function<void(Engine&)> callback;
Counter suppressedImpossibleActions,suppressedFailedActions;
Engine(AI*a):ai(a){a->engine=this;}
bool WorldContinuationPending(){return pending;}void PruneActionFailures(uint32){}template<class...T>void LogAction(T&&...){}void LogValues(){}
void ProcessTriggers(bool){++triggers;}void PushDefaultActions(){++defaults;}Action*InitializeAction(ActionNode*n){return n->action;}
bool ScheduleWorldContinuation(Event const&e,std::function<void(Engine&)>f){assert(e.source=="retained event");pending=true;callback=std::move(f);return true;}
void Resume(){pending=false;WorldActions::map=false;WorldActions::continuation=true;callback(*this);WorldActions::continuation=false;WorldActions::map=true;}
bool IsFailureBackedOff(Action*,Event const&,int){return false;}void ClearFailures(Action*,Event const&){}void RecordFailure(Action*,Event const&,int){}
bool MultiplyAndPush(NextAction**,float,bool,Event const&,const char*){return false;}void PushAgain(ActionNode*n,float,Event const&,bool=true){delete n;}
bool ListenAndExecute(Action*a,Event&e){assert(e.source=="retained event");assert(!a->world||!WorldActions::IsMapExecution());++a->calls;return true;}
bool DoNextAction(Unit* =nullptr,int=0,bool=false,bool=false);
};
'''+walk+r'''
int main(){
 AI ai;Engine e(&ai);Action global;global.name="global";global.world=true;global.useful=false;Action local;local.name="local";
 e.queue.Add(&global);e.queue.Add(&local);
 assert(!e.DoNextAction());assert(e.pending&&e.triggers==1&&e.context.updates==1&&e.queue.Size()==2);
 assert(!e.DoNextAction());assert(e.triggers==1);e.Resume();
 assert(e.queue.Size()==1&&e.decisionPrepared&&e.triggers==1&&local.calls==0);
 assert(e.DoNextAction());assert(local.calls==1&&!e.decisionPrepared&&e.triggers==1&&e.defaults==1);
 // A completed decision permits fresh stimuli on the following tick.
 assert(!e.DoNextAction());assert(e.triggers==2);
 global.useful=true;e.queue.Add(&global);assert(!e.DoNextAction());e.Resume();assert(global.calls==1&&!e.decisionPrepared);
 // Multiple required global checks remain in the same decision, without re-triggering.
 global.useful=false;e.queue.Add(&global);e.queue.Add(&global);e.queue.Add(&local);int before=e.triggers;
 assert(!e.DoNextAction());e.Resume();assert(e.triggers==before+1&&e.queue.Size()==1);assert(e.DoNextAction());assert(local.calls==2);
 puts("PASS actual decision walk: one trigger pass across map/world/map, retained events, pending deduplication, local continuation and next-tick refresh");
}
''')
