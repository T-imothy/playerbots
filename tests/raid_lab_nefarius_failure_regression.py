"""Actual local event failure observation, including recovery interval and clock rollover."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <iostream>
using uint32=uint32_t;constexpr unsigned FAIL=2;
'''+block(s,'bool RaidLabNefariusWaveFailed(')+r'''
int main(){uint32 stamp=0;
 assert(!RaidLabNefariusWaveFailed(469,11583,"gossip",FAIL,1000,stamp)&&stamp==1000);
 assert(!RaidLabNefariusWaveFailed(469,11583,"gossip",FAIL,30999,stamp));
 assert(RaidLabNefariusWaveFailed(469,11583,"gossip",FAIL,31000,stamp));
 assert(RaidLabNefariusWaveFailed(469,11583,"gossip",FAIL,50000,stamp));
 for(unsigned state:{0u,1u,3u,4u}){stamp=1000;assert(!RaidLabNefariusWaveFailed(469,11583,"gossip",state,50000,stamp)&&!stamp);}
 for(unsigned map:{409u,533u,489u}){stamp=1000;assert(!RaidLabNefariusWaveFailed(map,11583,"gossip",FAIL,50000,stamp)&&!stamp);}
 stamp=1000;assert(!RaidLabNefariusWaveFailed(469,12435,"gossip",FAIL,50000,stamp)&&!stamp);
 stamp=1000;assert(!RaidLabNefariusWaveFailed(469,11583,"phase",FAIL,50000,stamp)&&!stamp);
 stamp=0xfffffff0u;assert(!RaidLabNefariusWaveFailed(469,11583,"gossip",FAIL,10,stamp));
 assert(RaidLabNefariusWaveFailed(469,11583,"gossip",FAIL,uint32(stamp+30000),stamp));
 std::cout<<"PASS native Nefarius FAIL only, thirty-second recovery, episode reset, map/event guards and clock rollover\n";
}
'''
body=block(s,'TestResult CommandRaidLabEvent::Execute(')
assert body.index('if(ctx.raidLabEventStarted)')<body.index('RaidLabNefariusWaveFailed')<body.index('if(boss)')
assert 'instance->GetData(7)' in body
assert 'raidLabEventFailureStarted = 0;' in (root/'playerbot/strategy/tests/TestContext.cpp').read_text()
with tempfile.TemporaryDirectory(prefix='raid-nefarius-failure-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
