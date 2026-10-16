"""Execute shared WS/AB/AV objective recovery and strategy hooks in all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BattleGroundTactics.cpp').read_text()
body=block(source,'bool BGTactics::resetObjective(')
# EY/IC retain their older native planner; exercise the complete shared branch.
body=body[:body.index('    // sometimes change role')]+'return false;\n}'
execute=block(source,'    if (SupportsBattlegroundObjectiveRecovery(bot))')
pvp=(root/'playerbot/strategy/values/PvpValues.cpp').read_text()
helpers=block(pvp,'BattleGroundTypeId ai::ActualBattlegroundType(')+'\n'+block(pvp,'bool ai::SupportsBattlegroundObjectiveRecovery(')
strategy=(root/'playerbot/strategy/generic/BattlegroundStrategy.cpp').read_text()
hooks='\n'.join(block(strategy,'void BattlegroundStrategy::'+name+'(') for name in ('InitNonCombatTriggers','InitCombatTriggers','InitDeadTriggers'))
factory=(root/'playerbot/AiFactory.cpp').read_text()
assert 'if (ai::SupportsBattlegroundObjectiveRecovery(player))\n            combatEngine->addStrategy("battleground");' in factory
assert 'if (ai::SupportsBattlegroundObjectiveRecovery(player)) deadEngine->addStrategy("battleground");' in factory
code=r'''
#include <cassert>
#include <map>
#include <string>
#include <iostream>
#include <list>
#include <vector>
#include <type_traits>
using uint32=unsigned;using BattleGroundTypeId=unsigned;
constexpr unsigned BATTLEGROUND_TYPE_NONE=0,BATTLEGROUND_WS=1,BATTLEGROUND_AB=2,BATTLEGROUND_AV=3,BATTLEGROUND_EY=4,BATTLEGROUND_IC=5,BATTLEGROUND_RB=6;
constexpr unsigned STATUS_WAIT_JOIN=0,STATUS_IN_PROGRESS=1,STATUS_WAIT_LEAVE=2;
constexpr float ACTION_MOVE=10,ACTION_HIGH=50;
struct BattleGround{unsigned type=2,actual=2,status=STATUS_IN_PROGRESS;
 unsigned GetTypeId(bool real=false){return real?actual:type;}unsigned GetStatus(){return status;}};
struct Player{BattleGround bg;bool inBg=true,world=true,transfer=false,alive=true,cast=false;
 BattleGround*GetBattleGround(){return inBg?&bg:nullptr;}bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool IsNonMeleeSpellCasted(bool){return cast;}};
namespace ai{BattleGroundTypeId ActualBattlegroundType(Player*);bool SupportsBattlegroundObjectiveRecovery(Player*);}
__HELPERS__
using namespace ai;
struct WorldTimer{static unsigned now;static unsigned getMSTime(){return now;}static unsigned getMSTimeDiff(unsigned a,unsigned b){return b-a;}};unsigned WorldTimer::now=1;
namespace ai{struct PositionEntry{bool set=false;unsigned mapId=529;float x=0,y=0,z=0;bool isSet(){return set;}void Reset(){set=false;}};
using PositionMap=std::map<std::string,PositionEntry>;struct WarsongObjective{};}
struct Value{PositionMap map;PositionMap&Get(){return map;}};
struct WarsongValue{unsigned resets=0;void Reset(){++resets;}};
struct Context{Value value;WarsongValue warsong;template<class T>auto*GetValue(const char*){
 if constexpr(std::is_same_v<T,WarsongObjective>)return &warsong;else return &value;}};
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
struct BGTactics{Player*bot;Context*context;unsigned battlegroundObjectiveCheck=0,selected=0,refreshed=0,role=7,nativeActions=0;bool nativeAccepted=true;std::string name="move to objective";
 PositionEntry next{true,529,10,20,30};bool resetObjective();std::string getName(){return name;}
 bool executeProbe(){__EXECUTE__ ++nativeActions;return true;}
 bool refreshWarsongObjective(){++refreshed;return true;}
 bool selectObjective(bool reset){assert(reset);++selected;if(!nativeAccepted)return false;context->value.map["bg objective"]=next;return true;}};
__BODY__
struct PlayerbotAI{Player*bot;Player*GetBot(){return bot;}};
struct NextAction{std::string name;float relevance;NextAction(const char*n,float r):name(n),relevance(r){}
 template<class T>static void add(std::vector<NextAction*>&out,T value){if constexpr(std::is_pointer_v<T>){if(value)out.push_back(value);}}
 template<class...A>static std::vector<NextAction*>array(int,A...items){std::vector<NextAction*>out;(add(out,items),...);return out;}};
struct TriggerNode{std::string name;std::vector<NextAction*>actions;TriggerNode(const char*n,std::vector<NextAction*>a):name(n),actions(a){}};
struct BattlegroundStrategy{PlayerbotAI*ai;void InitNonCombatTriggers(std::list<TriggerNode*>&);void InitCombatTriggers(std::list<TriggerNode*>&);void InitDeadTriggers(std::list<TriggerNode*>&);};
__HOOKS__
float relevance(std::list<TriggerNode*>const&nodes,const char*name){for(auto*n:nodes)for(auto*a:n->actions)if(a->name==name)return a->relevance;return -1;}
void clear(std::list<TriggerNode*>&nodes){for(auto*n:nodes){for(auto*a:n->actions)delete a;delete n;}nodes.clear();}
int main(){
 assert(!SupportsBattlegroundObjectiveRecovery(nullptr));
 for(unsigned type:{BATTLEGROUND_WS,BATTLEGROUND_AB,BATTLEGROUND_AV,BATTLEGROUND_EY,BATTLEGROUND_IC,99u}){
  Player bot;bot.bg.type=type;PlayerbotAI ai{&bot};BattlegroundStrategy strategy{&ai};std::list<TriggerNode*>nodes;
  bool common=type<=BATTLEGROUND_AV;assert(SupportsBattlegroundObjectiveRecovery(&bot)==common);
  strategy.InitNonCombatTriggers(nodes);assert(relevance(nodes,"bg move to objective")== (common?ACTION_MOVE+5:1));clear(nodes);
  strategy.InitCombatTriggers(nodes);assert(nodes.size()==(common?3:0));assert((relevance(nodes,"bg check objective")==10)==common);clear(nodes);
  strategy.InitDeadTriggers(nodes);assert(nodes.size()==(common?2:0));assert((relevance(nodes,"bg reset objective force")==ACTION_HIGH)==common);clear(nodes);
 }
#ifdef MANGOSBOT_TWO
 Player queued;queued.bg.type=BATTLEGROUND_RB;queued.bg.actual=BATTLEGROUND_AV;assert(SupportsBattlegroundObjectiveRecovery(&queued));
 queued.bg.actual=BATTLEGROUND_IC;assert(!SupportsBattlegroundObjectiveRecovery(&queued));
#endif
 for(unsigned type:{BATTLEGROUND_AB,BATTLEGROUND_AV}){
  Player bot;bot.bg.type=type;Context context;BGTactics action{&bot,&context};WorldTimer::now=1;context.value.map["bg objective"]={true,529,1,2,3};
  assert(action.resetObjective()&&action.selected==1&&action.role==7);
  WorldTimer::now=100;assert(!action.resetObjective()&&action.selected==1);
  WorldTimer::now=10001;assert(!action.resetObjective()&&action.selected==2);
  bot.cast=true;WorldTimer::now=20001;assert(!action.resetObjective()&&action.selected==2);
  assert(!action.executeProbe()&&action.nativeActions==0); // no replacement movement during an accepted cast/channel
  bot.cast=false;bot.alive=false;assert(!action.resetObjective());bot.alive=true;
  bot.transfer=true;assert(!action.resetObjective()&&!action.executeProbe());bot.transfer=false;
  bot.world=false;assert(!action.resetObjective()&&!action.executeProbe());bot.world=true;
  bot.bg.status=STATUS_WAIT_JOIN;assert(!action.resetObjective());bot.bg.status=STATUS_WAIT_LEAVE;assert(!action.resetObjective());bot.bg.status=STATUS_IN_PROGRESS;
  action.nativeAccepted=false;assert(!action.resetObjective());auto p=context.value.map["bg objective"];assert(p.isSet()&&p.x==10);
  action.name="reset objective";assert(!action.executeProbe()&&context.value.map["bg objective"].isSet());
  bot.alive=false;assert(action.executeProbe()&&!context.value.map["bg objective"].isSet()&&context.warsong.resets==1&&action.battlegroundObjectiveCheck==0);
  assert(!action.executeProbe()&&context.warsong.resets==1); // death does not rerun the same reset every tick
  bot.alive=true;action.nativeAccepted=true;action.name="move to objective";WorldTimer::now=20002;assert(action.resetObjective());
  bot.inBg=false;assert(!action.resetObjective());bot.inBg=true;bot.bg.type=BATTLEGROUND_WS;
  assert(action.resetObjective()&&action.refreshed==1&&action.role==7);
 }
 std::cout<<"PASS shared WSG/AB/AV activation and movement priority; AB/AV bounded refresh, retained route, loading/phase/death guards and cast preservation; other BGs excluded\n";
}
'''.replace('__HELPERS__',helpers).replace('__BODY__',body).replace('__EXECUTE__',execute).replace('__HOOKS__',hooks)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='shared-bg-recovery-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
