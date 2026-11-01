"""Execute the production scheduling and opening-route bodies, without a realm."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
ai=(root/'playerbot/PlayerbotAI.cpp').read_text()
cadence=ai.split('        bool min = minimal;',1)[1].split('        YieldAIInternalThread(min);',1)[0]
yield_body=block((root/'playerbot/PlayerbotAIBase.cpp').read_text(),'void PlayerbotAIBase::YieldAIInternalThread(')
common=r'''
#include <cassert>
#include <algorithm>
#include <iostream>
#include "playerbot/strategy/values/ClassicBattlegroundPolicy.h"
using uint32=unsigned;
enum {STATUS_WAIT_JOIN=2,STATUS_IN_PROGRESS=3,STATUS_WAIT_LEAVE=4};
struct Config {unsigned reactDelay=100,passiveDelay=10000;}sPlayerbotAIConfig;
struct BattleGround{unsigned status=2;unsigned GetStatus(){return status;}};
struct Player{BattleGround bg;bool supported=true;BattleGround*GetBattleGround(){return &bg;}};
namespace ai {bool SupportsBattlegroundObjectiveRecovery(Player*p){return p&&p->supported;}}
struct PlayerbotAIBase{unsigned aiInternalUpdateDelay=0;void YieldAIInternalThread(bool minimal);};
__YIELD__
struct TestAI:PlayerbotAIBase{Player*bot;bool inCombat=false,human=false;
 bool HasRealPlayerMaster(){return human;}
 void tick(bool minimal){bool min=minimal;__CADENCE__ YieldAIInternalThread(min);}};
int main(){
 Player p;TestAI a;a.bot=&p;
 for(unsigned status:{STATUS_WAIT_JOIN,STATUS_IN_PROGRESS}) {
  p.bg.status=status;a.aiInternalUpdateDelay=0;a.tick(false);
#ifdef MANGOSBOT_ZERO
  assert(a.aiInternalUpdateDelay==100); // regression: the old path scheduled 10000
  a.aiInternalUpdateDelay=2500;a.tick(false);assert(a.aiInternalUpdateDelay==2500); // cast duration retained
#else
  assert(a.aiInternalUpdateDelay==10000); // other builds are intentionally unchanged
#endif
 }
 p.supported=false;a.aiInternalUpdateDelay=0;a.tick(false);assert(a.aiInternalUpdateDelay==10000); // world/raid/other BG
 p.supported=true;p.bg.status=STATUS_WAIT_LEAVE;a.aiInternalUpdateDelay=0;a.tick(false);assert(a.aiInternalUpdateDelay==10000);
 a.human=true;a.aiInternalUpdateDelay=0;a.tick(false);assert(a.aiInternalUpdateDelay==100);
 std::cout<<"PASS native cadence: active Classic WS/AB/AV, preserved casts, world/dungeons/other eras unchanged\n";
}
'''.replace('__YIELD__',yield_body).replace('__CADENCE__',cadence)
opening=block((root/'playerbot/strategy/actions/ClassicBattlegroundActions.cpp').read_text(),'bool BGTactics::MoveToClassicWarsongOpening(')
routes=r'''
#include <cassert>
#include <iostream>
#include <cmath>
#include <type_traits>
#include "playerbot/strategy/values/ClassicBattlegroundPolicy.h"
using uint32=unsigned;
const unsigned BATTLEGROUND_WS=2,STATUS_IN_PROGRESS=3,BG_START_DELAY_2M=120000,ALLIANCE=469;
enum class WarsongGoal{None,Fetch,Capture,Intercept,Escort,Return,Recover,Hold};
struct WarsongObjective{WarsongGoal goal=WarsongGoal::Fetch;bool carrying=false;};
struct BattleGround{unsigned type=2,status=3,instance=17,time=120000;
 unsigned GetTypeId(){return type;}unsigned GetStatus(){return status;}unsigned GetInstanceId(){return instance;}unsigned GetStartTime(){return time;}};
struct Player{BattleGround bg;unsigned slot=0,team=ALLIANCE;bool alive=true,teleport=false,combat=false;float x=1519.53f,y=1481.87f,z=352.024f;
 BattleGround*GetBattleGround(){return &bg;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}
 bool IsInCombat(){return combat;}unsigned GetTeam(){return team;}unsigned GetMapId(){return 489;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
struct AI{bool human=false;bool HasRealPlayerMaster(){return human;}};
struct Value{WarsongObjective obj;WarsongObjective Get(){return obj;}};
struct Context{Value v;template<class T>Value*GetValue(const char*){return &v;}};
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
namespace policy=ai::ClassicBattlegroundPolicy;
unsigned BattlegroundTeamSlot(Player*p,unsigned&count){count=10;return p->slot;}
struct BGTactics{Player*bot;AI*ai;Context*context;unsigned classicWsOpeningInstance=0,classicWsOpeningLane=0,classicWsOpeningStep=0,moves=0;
 bool accepted=true;policy::ApproachPoint dest{};bool MoveTo(unsigned map,float x,float y,float z){assert(map==489);++moves;dest={x,y,z};return accepted;}
 bool MoveToClassicWarsongOpening();};
__OPENING__
int main(){
 for(bool alliance:{true,false}) {
  unsigned lanes[2]={};
  for(unsigned slot=0;slot<10;++slot) {
   Player bot;bot.slot=slot;bot.team=alliance?ALLIANCE:67;
   if(!alliance){bot.x=933.331f;bot.y=1433.72f;bot.z=345.536f;}
   AI ai;Context ctx;BGTactics a{&bot,&ai,&ctx};
   assert(a.MoveToClassicWarsongOpening());++lanes[a.classicWsOpeningLane];
   auto first=a.dest;bot.slot+=1; // roster changes cannot reroll an in-progress lane
   assert(a.MoveToClassicWarsongOpening()&&a.dest.x==first.x&&a.dest.y==first.y);
   unsigned steps=0;while(a.MoveToClassicWarsongOpening()) {bot.x=a.dest.x;bot.y=a.dest.y;bot.z=a.dest.z;assert(++steps<=3);}
   assert(a.classicWsOpeningStep==3&&!a.MoveToClassicWarsongOpening());
   bot.x=alliance?1410:1040;bot.z=343;assert(!a.MoveToClassicWarsongOpening()); // death/return cannot reverse completed lane
   bot.bg.instance++;assert(a.MoveToClassicWarsongOpening());
  }
  assert(lanes[0]==5&&lanes[1]==5);
 }
 for(WarsongGoal goal:{WarsongGoal::Capture,WarsongGoal::Intercept,WarsongGoal::Escort,WarsongGoal::Return,WarsongGoal::Recover,WarsongGoal::Hold}) {
  Player bot;AI ai;Context ctx;ctx.v.obj.goal=goal;BGTactics a{&bot,&ai,&ctx};
  assert(!a.MoveToClassicWarsongOpening()&&a.moves==0);
 }
 {Player bot;AI ai;Context ctx;BGTactics a{&bot,&ai,&ctx};ctx.v.obj.carrying=true;assert(!a.MoveToClassicWarsongOpening());}
 {Player bot;AI ai;Context ctx;BGTactics a{&bot,&ai,&ctx};a.accepted=false;assert(!a.MoveToClassicWarsongOpening()&&a.moves==1);assert(!a.MoveToClassicWarsongOpening()&&a.moves==1);}
 {Player bot;AI ai;Context ctx;BGTactics a{&bot,&ai,&ctx};bot.bg.time=210001;assert(!a.MoveToClassicWarsongOpening()&&a.moves==0);}
 {Player bot;AI ai;Context ctx;BGTactics a{&bot,&ai,&ctx};ai.human=true;assert(!a.MoveToClassicWarsongOpening());ai.human=false;
  bot.combat=true;assert(!a.MoveToClassicWarsongOpening());bot.combat=false;assert(a.MoveToClassicWarsongOpening());}
 {Player bot;AI ai;Context ctx;BGTactics a{&bot,&ai,&ctx};bot.bg.type=3;assert(!a.MoveToClassicWarsongOpening());}
 std::cout<<"PASS native opening action: mirrored lane split, monotonic steps, other objectives/master/combat preserved, rejected native path falls back\n";
}
'''.replace('__OPENING__',opening)
def run(code,label,era):
 with tempfile.TemporaryDirectory(prefix='bg-opening-') as tmp:
  p=Path(tmp);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'/I'+str(root),'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  assert r.returncode==0,label+'\n'+r.stdout+r.stderr
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
for era in ('ZERO','ONE','TWO'):run(common,'cadence',era)
run(routes,'opening','ZERO')
