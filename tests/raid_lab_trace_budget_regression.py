"""Execute native local trace budgets, preserving bounded files and one-shot coverage gaps."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
s=(root/'classic/src/game/World/RaidLab.cpp').read_text()
methods='\n'.join(block(s,m) for m in ('void SetObservationBudget(','void Write(','bool RecordCombatTransition('))
assert 'SetObservationBudget(*a,name)' in block(s,'bool Begin(')
assert 'if(!RecordCombatTransition(*a))return;' in block(s,'void PreparationCombat(')
code=r'''
#include <cassert>
#include <string>
#include <sstream>
#include <iostream>
using uint64=unsigned long long;
struct Attempt {bool controlled=false,limited=false;unsigned combatTransitions=0,combatTransitionLimit=512;
 uint64 start=0,seq=0,bytes=0,traceLimitBytes=256ull*1024*1024;std::string id="test";std::ostringstream file;};
uint64 Clock(){return 1;}std::string Quote(const std::string&s){return "\""+s+"\"";}
__METHODS__
int main(){Attempt ordinary;SetObservationBudget(ordinary,"raidlab_409_12118_leader_progression");
 assert(ordinary.traceLimitBytes==256ull*1024*1024&&ordinary.combatTransitionLimit==512);
 ordinary.controlled=true;SetObservationBudget(ordinary,"raidlab_409_12118_leader");assert(ordinary.combatTransitionLimit==512);
 SetObservationBudget(ordinary,"other_leader_progression");assert(ordinary.combatTransitionLimit==512);
 for(unsigned i=0;i<512;++i)assert(RecordCombatTransition(ordinary));
 assert(!RecordCombatTransition(ordinary));auto gap=ordinary.file.str();assert(gap.find("coverage_gap")!=std::string::npos);
 for(unsigned i=0;i<100;++i)assert(!RecordCombatTransition(ordinary));assert(gap==ordinary.file.str());
 Attempt route;route.controlled=true;SetObservationBudget(route,"raidlab_409_12118_leader_progression");
 assert(route.traceLimitBytes==512ull*1024*1024&&route.combatTransitionLimit==4096);
 for(unsigned i=0;i<4096;++i)assert(RecordCombatTransition(route));assert(!RecordCombatTransition(route));
 Attempt file;Write(file,"\"type\":\"event\"");assert(file.seq==1&&!file.limited);
 file.bytes=file.traceLimitBytes;Write(file,"\"type\":\"event\"");assert(file.limited);
 auto capped=file.file.str();Write(file,"\"type\":\"event\"");assert(file.file.str()==capped);
 assert(capped.find("256MiB_limit")!=std::string::npos);
 route.bytes=route.traceLimitBytes;Write(route,"\"type\":\"event\"");assert(route.file.str().find("512MiB_limit")!=std::string::npos);
 std::cout<<"PASS actual local progression budgets, unchanged ordinary limits, bounded writes and one-shot gaps\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='raid-trace-budget-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
