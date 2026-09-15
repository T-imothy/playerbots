"""Execute the production pursuit policy, including timer wrap and bounded expiry."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
fixture = r'''
#include "playerbot/BotReliabilityPolicy.h"
#include <cassert>
#include <iostream>
#include <limits>
int main() {
    ai::PursuitProgress pursuit;
    for (unsigned t=0;t<15000;t+=1000) assert(!pursuit.Observe(1,0,0,t,50,0,0,0,true));
    assert(pursuit.Observe(1,0,0,15000,50,0,0,0,true));
    assert(!pursuit.Observe(1,0,0,16000,47,0,0,0,true)); // real progress
    assert(!pursuit.Observe(1,0,0,17000,47,9,0,0,true)); // navigation detour
    assert(!pursuit.Observe(1,0,0,18000,47,9,0,0,false)); // party/LOS exemption
    assert(!pursuit.Observe(1,0,0,19000,47,9,0,0,true));
    assert(!pursuit.Observe(2,0,0,20000,47,9,0,0,true)); // new target
    assert(!pursuit.Observe(2,0,1,21000,47,9,0,0,true)); // instance transfer
    assert(!pursuit.Observe(2,0,1,28000,47,9,0,0,true)); // missed samples
    assert(!pursuit.Observe(2,0,1,29000,std::numeric_limits<float>::quiet_NaN(),9,0,0,true));
    pursuit.Reset();
    unsigned start=0xffffe000u;
    for(unsigned t=0;t<15000;t+=1000) assert(!pursuit.Observe(3,1,2,start+t,50,0,0,0,true));
    assert(pursuit.Observe(3,1,2,start+15000,50,0,0,0,true));
    ai::UnreachableTargets targets;
    targets.Add(1,0,4,start);
    assert(targets.Contains(1,0,4,start+29999));
    assert(!targets.Contains(1,0,5,start+29999));
    assert(!targets.Contains(1,0,4,start+30000));
    for(unsigned i=1;i<=9;++i) targets.Add(i,0,4,100);
    assert(!targets.Contains(1,0,4,100));
    for(unsigned i=2;i<=9;++i) assert(targets.Contains(i,0,4,100));
    static_assert(sizeof(ai::UnreachableTargets)<256,"Exclusion memory must stay bounded");
    std::cout << "PASS: pursuit progress, exemptions, invalid data, transfers, wraparound, expiry and bounded eviction\n";
}
'''
with tempfile.TemporaryDirectory(prefix='bot-reliability-') as temp:
    d=Path(temp); source=d/'test.cpp'; source.write_text(fixture)
    subprocess.run(['cl','/nologo','/std:c++20','/EHsc','/UNDEBUG','/I'+str(root),str(source),
        '/Fe:'+str(d/'test.exe'),'/Fo:'+str(d/'test.obj')],check=True)
    subprocess.run([str(d/'test.exe')],check=True)
