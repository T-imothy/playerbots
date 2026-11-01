"""Actual local owner-thread preparation callback and its refusal guards."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
command=block(source,'TestResult CommandRaidLabLeader::Execute(')
call=block(command,'ai->RunOnOwningThread(member,')
body=call[call.index('{')+1:-1]
code=r'''
#include <cassert>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;
namespace BotState{enum State{BOT_STATE_NON_COMBAT};}
struct Player;
struct AI{bool real=false,grind=true;unsigned resets=0,changes=0;Player*master=nullptr;
 bool IsRealPlayer(){return real;}bool HasStrategy(const char*s,BotState::State){assert(std::string(s)=="grind");return grind;}
 void SetMaster(Player*p){master=p;}void ResetStrategies(bool load){assert(!load);++resets;grind=true;}
 void ChangeStrategy(const char*s,BotState::State){assert(std::string(s)=="-grind,-travel,-rpg,-group,-guild,-maintenance");++changes;grind=false;}
};
using PlayerbotAI=AI;
struct Player{AI*ai=nullptr;unsigned group=1,guid=1;bool combat=false;
 AI*GetPlayerbotAI(){return ai;}unsigned GetGroup(){return group;}bool IsInCombat(){return combat;}unsigned GetGUIDLow(){return guid;}
};
struct {Player*p=nullptr;Player*GetPlayer(ObjectGuid guid){return p&&p->guid==guid?p:nullptr;}}sObjectMgr;
namespace RaidLab{bool controlled=true;bool Controlled(Player*p){return p&&controlled;}}
struct {template<class...T>void outString(const char*,T...){}}sLog;
void Prepare(Player*follower,ObjectGuid leaderGuid){__BODY__}
int main(){Player leader,follower;AI ai;follower.ai=&ai;follower.guid=2;sObjectMgr.p=&leader;
 Prepare(&follower,1);assert(ai.master==&leader&&ai.resets==1&&ai.changes==1&&!ai.grind);
 // Repeat preparation is harmless; later settled reset chooses the raid's
 // actual player-following strategy defaults on the destination map.
 Prepare(&follower,1);assert(ai.resets==2&&!ai.grind);
 auto refused=[&](){auto before=ai.resets;Prepare(&follower,1);assert(ai.resets==before);};
 RaidLab::controlled=false;refused();RaidLab::controlled=true;
 follower.group=2;refused();follower.group=0;refused();follower.group=1;
 ai.real=true;refused();ai.real=false;follower.combat=true;refused();follower.combat=false;
 follower.ai=nullptr;refused();follower.ai=&ai;sObjectMgr.p=nullptr;refused();sObjectMgr.p=&leader;
 leader.guid=7;refused();
 std::cout<<"PASS local preparation callback: identity/group/real-player/combat guards and pre-delivery autonomous-strategy removal\n";
}
'''.replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='raidlab-follower-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(p/'test.exe')],cwd=p,check=True)
assert command.index('RaidLab::PrepareLeader(bot)')<command.index('ai->RunOnOwningThread(member,')<command.index('if(params=="settled")')
assert 'const ObjectGuid leaderGuid=bot->GetObjectGuid()' in command
assert source.index('#ifdef MANTECH_RAID_LAB')<source.index('CommandRaidLabLeader::Execute(')
print('PASS callback is local-only, GUID-correlated and queued on member owning thread before delivery')
