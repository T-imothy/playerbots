"""Native trash fixture uses measured ramp floor; no production/path bypass."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
constexpr float INVALID_HEIGHT=-100000;
struct Map{float native=427.986f,grounded=427.986f;bool found=true;unsigned calls=0;
 float GetHeight(float,float,float hint){++calls;return native;}
 bool GetHeightInRange(float,float,float& z,float limit){assert(limit==2&&z==native);++calls;z=grounded;return found;}};
'''+block(source,'bool RaidLabPackLowerFloor(')+r'''
int main(){Map map;float out=123;
 assert(!RaidLabPackLowerFloor(&map,false,-7568.636,-976.264,440.176,out)&&map.calls==0&&out==123);
 assert(RaidLabPackLowerFloor(&map,true,-7568.636,-976.264,440.176,out)&&out==map.grounded);
 for(float z:{440.176f,435.0f,420.0f,587.567f,INVALID_HEIGHT,NAN}){
  map.native=z;out=123;assert(!RaidLabPackLowerFloor(&map,true,1,2,440.176,out)&&out==123);
 }
 map.native=427.986f;
 for(float z:{430.5f,449.0f,587.567f,INVALID_HEIGHT,NAN}){
  map.grounded=z;out=123;assert(!RaidLabPackLowerFloor(&map,true,1,2,440.176,out)&&out==123);
 }
 map.grounded=map.native;map.found=false;assert(!RaidLabPackLowerFloor(&map,true,1,2,440.176,out));
 assert(!RaidLabPackLowerFloor(nullptr,true,1,2,440.176,out));
 assert(!RaidLabPackLowerFloor(&map,true,NAN,2,440.176,out));
 std::cout<<"PASS native pack ramp floor, bounded search, roof rejection and non-pack isolation\n";
}
'''
landing=block(source,'TestResult CommandRaidLabLanding::Execute(')
for guard in ('RaidLabPackPullCorridor','destination.isPathTo(route,1.0f,2.0f)',
              'RaidLabInsidePatrolEnvelope','RaidLabBodyPullRisk(c,reference,true)',
              'boss->IsWithinLOS','packFloor,2.0f'):
 assert guard in landing
with tempfile.TemporaryDirectory(prefix='raidpack-floor-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
