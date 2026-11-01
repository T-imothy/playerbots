"""The local pull handoff must not erase a settled follower's prepared strategies."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <string>
#include <iostream>
struct Player;enum class BotState{BOT_STATE_REACTION};
struct PlayerbotAI{Player*master=nullptr;unsigned resets=0,changes=0;bool prepared=true;
 Player*GetMaster(){return master;}void SetMaster(Player*p){master=p;}
 void ResetStrategies(bool load){assert(!load);++resets;prepared=false;}
 void ChangeStrategy(std::string,BotState){++changes;}};
struct Ref{Player*player;Ref*nextRef;Player*getSource(){return player;}Ref*next(){return nextRef;}};
struct Group{Ref*head;Ref*GetFirstMember(){return head;}};
struct Player{Group*group;PlayerbotAI*ai;Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}};
struct TestContext{bool focusMobPassive=false;std::string testName="raidlab_533_15936_leader_cleared_room";};
namespace RaidLab{unsigned events=0;void Event(Player*,const char*){++events;}}
'''+block(source,'void RaidLabFollowers(')+r'''
int main(){
 PlayerbotAI leaderAI,settledAI,newAI;Group group;
 Player leader{&group,&leaderAI},settled{&group,&settledAI},fresh{&group,&newAI};
 Ref c{&fresh,nullptr},b{&settled,&c},a{&leader,&b};group.head=&a;
 settledAI.master=&leader;TestContext ctx;
 RaidLabFollowers(&leader,&leaderAI,ctx);
 assert(settledAI.resets==0&&settledAI.prepared);assert(newAI.resets==1&&newAI.master==&leader);
 newAI.prepared=true;RaidLabFollowers(&leader,&leaderAI,ctx);
 assert(settledAI.resets==0&&settledAI.prepared&&newAI.resets==1&&newAI.prepared);
 assert(ctx.focusMobPassive&&leaderAI.changes==2&&RaidLab::events==2);
 std::cout<<"PASS native pull handoff preserves settled follower strategies and attaches only new followers\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-pull-state-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
