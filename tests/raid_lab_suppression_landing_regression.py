"""Local suppression starting floor cannot skip packs or snap to an overhead floor."""
from pathlib import Path
import tempfile,subprocess
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
constexpr float INVALID_HEIGHT=-100000;
struct Map{unsigned id=469,calls=0;bool found=true;float native=428.4;
 unsigned GetId(){return id;}bool GetHeightInRange(float,float,float&z,float distance){++calls;assert(z==428.25f&&distance==2);z=native;return found;}};
'''+block(source,'bool RaidLabSuppressionStartFloor(')+r'''
int main(){Map map;float z=0;
 assert(RaidLabSuppressionStartFloor(&map,-7578,-895,z)&&z==map.native);
 for(float floor:{449.25f,587.56f,INVALID_HEIGHT,NAN}){map.native=floor;z=123;assert(!RaidLabSuppressionStartFloor(&map,-7578,-895,z)&&z==123);}
 map.native=428.4;map.found=false;assert(!RaidLabSuppressionStartFloor(&map,-7578,-895,z));map.found=true;
 unsigned calls=map.calls;assert(!RaidLabSuppressionStartFloor(&map,-7578,-930,z)&&map.calls==calls);
 assert(!RaidLabSuppressionStartFloor(&map,NAN,-895,z));map.id=533;assert(!RaidLabSuppressionStartFloor(&map,-7578,-895,z));
 assert(!RaidLabSuppressionStartFloor(nullptr,-7578,-895,z));
 std::cout<<"PASS suppression start uses bounded native lower floor; upper/absent/invalid floors and past-pack landings rejected\n";
}
'''
register=(root/'playerbot/strategy/tests/RegisterInstance.cpp').read_text()
assert 'suppression?"raidlab landing 12465":"wait 1"' in register
for check in ('RaidLabBodyPullRisk(c,reference,true)','RaidLabInsideWanderEnvelope','RaidLabInsidePatrolEnvelope','destination.isPathTo(route,1.0f,2.0f)'):
 assert check in block(source,'TestResult CommandRaidLabLanding::Execute(')
with tempfile.TemporaryDirectory(prefix='suppression-floor-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
