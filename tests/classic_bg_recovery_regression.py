"""Execute the actual Classic objective refresh branch with native-shaped state."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
body=block((root/'playerbot/strategy/actions/BattleGroundTactics.cpp').read_text(),'bool BGTactics::resetObjective(')
# The preserved older-era random-job branch is outside this Classic fixture.
body=body[:body.index('    // sometimes change role')]+'return false;\n}'
code=r'''
#include <cassert>
#include <map>
#include <string>
#include <iostream>
using uint32=unsigned;
constexpr unsigned BATTLEGROUND_WS=1,BATTLEGROUND_AB=2,BATTLEGROUND_AV=3;
struct BattleGround{};
struct Player{BattleGround bg;bool inBg=true,alive=true,cast=false;unsigned type=2;
 BattleGround*GetBattleGround(){return inBg?&bg:nullptr;}bool IsAlive(){return alive;}bool IsNonMeleeSpellCasted(bool){return cast;}};
unsigned ActualBattlegroundType(Player*p){return p->type;}
struct WorldTimer{static unsigned now;static unsigned getMSTime(){return now;}static unsigned getMSTimeDiff(unsigned a,unsigned b){return b-a;}};unsigned WorldTimer::now=1;
namespace ai{struct PositionEntry{bool set=false;unsigned mapId=529;float x=0,y=0,z=0;bool isSet(){return set;}void Reset(){set=false;}};
using PositionMap=std::map<std::string,PositionEntry>;}
using namespace ai;
struct Value{PositionMap map;PositionMap&Get(){return map;}};
struct Context{Value value;template<class T>Value*GetValue(const char*){return &value;}};
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
struct BGTactics{Player*bot;Context*context;unsigned classicObjectiveCheck=0,selected=0,refreshed=0,role=7;bool nativeAccepted=true;
 PositionEntry next{true,529,10,20,30};bool resetObjective();bool refreshWarsongObjective(){++refreshed;return true;}
 bool selectObjective(bool reset){assert(reset);++selected;if(!nativeAccepted)return false;context->value.map["bg objective"]=next;return true;}};
__BODY__
int main(){Player bot;Context context;BGTactics action{&bot,&context};context.value.map["bg objective"]={true,529,1,2,3};
 assert(action.resetObjective()&&action.selected==1&&action.role==7); // changed node ownership, preserve job
 WorldTimer::now=100;assert(!action.resetObjective()&&action.selected==1); // bounded work
 WorldTimer::now=10001;assert(!action.resetObjective()&&action.selected==2); // same accepted objective is not new movement
 bot.cast=true;WorldTimer::now=20001;assert(!action.resetObjective()&&action.selected==2); // preserve banner channel/heal/damage cast
 bot.cast=false;bot.alive=false;assert(!action.resetObjective());bot.alive=true;
 action.nativeAccepted=false;assert(!action.resetObjective());auto p=context.value.map["bg objective"];assert(p.isSet()&&p.x==10); // failed native election retains valid route
 bot.inBg=false;assert(!action.resetObjective());bot.inBg=true;bot.type=BATTLEGROUND_WS;
 assert(action.resetObjective()&&action.refreshed==1&&action.role==7); // existing deterministic WSG planner kept
 std::cout<<"PASS actual Classic AB/AV bounded refresh, no random job churn, native rejection and cast/channel preservation\n";
}
'''.replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='classic-bg-recovery-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_ZERO','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
