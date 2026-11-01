"""Local observed Grobbulus preparation must wait boundedly, never widen pull range."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using uint32=uint32_t;
'''+block(s,'bool RaidLabPatrolWaitAllowed(')+r'''
int main(){uint32 start=0;assert(RaidLabPatrolWaitAllowed(533,15931,1000,start)&&start==1000);
 assert(RaidLabPatrolWaitAllowed(533,15931,120999,start));assert(!RaidLabPatrolWaitAllowed(533,15931,121000,start));
 assert(!RaidLabPatrolWaitAllowed(533,15931,130000,start));
 start=0;assert(RaidLabPatrolWaitAllowed(409,12056,1000,start));
 start=0;assert(RaidLabPatrolWaitAllowed(533,16028,1000,start)&&start==1000);
 assert(RaidLabPatrolWaitAllowed(533,16028,120999,start));
 assert(!RaidLabPatrolWaitAllowed(533,16028,121000,start));
 for(unsigned entry:{15956u,16011u,11988u}){start=0;assert(!RaidLabPatrolWaitAllowed(533,entry,1000,start)&&!start);}
 start=0;assert(!RaidLabPatrolWaitAllowed(489,15931,1000,start)&&!start);
 start=0xfffffff0u;assert(RaidLabPatrolWaitAllowed(533,15931,10,start));
 assert(!RaidLabPatrolWaitAllowed(533,15931,uint32(start+120000),start));
 std::cout<<"PASS exact patrol fixtures, bounded expiry, repeated polls, clock rollover and other-scenario refusal\n";
}
'''
body=block(s,'TestResult CommandRaidLab::Execute(')
assert 'bot->GetDistance(boss)>100.0f' in body and 'boss && !boss->IsInCombat() && RaidLabPatrolWaitAllowed' in body
assert 'RaidLabPartyReady(bot,ai,tank,message)' in body and 'ctx.raidLabPatrolWaitStarted=0;' in body
assert 'raidLabPatrolWaitStarted = 0;' in (root/'playerbot/strategy/tests/TestContext.cpp').read_text()
with tempfile.TemporaryDirectory(prefix='raid-patrol-wait-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
