"""Execute the actual pending-command branch: poll the local leader, never advance the script."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
s=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/TestAction.cpp').read_text()
branch=block(s,'    else if (commandResult == TestResult::PENDING)').replace('else if','if',1)
code=r'''
#include <cassert>
#include <string>
#include <vector>
#include <iostream>
enum class TestResult{PENDING,PASS};
struct Player{};
namespace RaidLab { bool controlled=true;bool Controlled(Player*){return controlled;} }
struct Context{std::string testName="raidlab_409_12118_leader_progression";std::vector<std::string>script{"raidlab corridor mc_lucifron"};size_t pc=0;};
struct Action { Context ctx;Player player;Player*bot=&player;unsigned duration=1;
 void SetDuration(unsigned value){duration=value;}
 bool Pending(){TestResult commandResult=TestResult::PENDING;__BRANCH__;return true;}
};
int main(){Action a;
#ifdef MANTECH_RAID_LAB
 assert(a.Pending());assert(a.ctx.pc==0&&a.duration==500);
 a.ctx.script[0]="raidlab progression rajaxx";assert(a.Pending());assert(a.ctx.pc==0);
 RaidLab::controlled=false;assert(!a.Pending());RaidLab::controlled=true;
 a.ctx.testName="ordinary_test";assert(!a.Pending());a.ctx.testName="raidlab_409_12118_leader_progression";
 for(const char*s:{"wait 50","pull","raidlab observe","raidlab corridorx","raidlab progressionx"}){a.ctx.script[0]=s;assert(!a.Pending());}
 a.ctx.pc=1;assert(!a.Pending());
#else
 assert(!a.Pending());assert(a.duration==1&&a.ctx.pc==0);
#endif
 std::cout<<"PASS native pending movement polling scope and no script advance\n";
}
'''.replace('__BRANCH__',branch)
with tempfile.TemporaryDirectory(prefix='raid-lab-poll-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 for define in ('/DMANTECH_RAID_LAB','/DORDINARY_BUILD'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',define,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
