"""Native doorway search stays bounded and cannot accept a rejected landing."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
using uint32=unsigned;
template<class Candidate>
'''+block(source,'bool RaidLabNothDoorApproach(')+r'''
int main(){
 unsigned calls=0;auto reject=[&](float x,float y,float z,float bound){
  ++calls;assert(x>=66&&x<=130&&y>=-6&&y<=6&&z==262&&bound==2);return false;};
 assert(!RaidLabNothDoorApproach(533,15954,0,0,60,0,262,reject)&&calls==119);
 calls=0;auto admit=[&](float x,float y,float z,float bound){++calls;return x==74&&y==0;};
 assert(RaidLabNothDoorApproach(533,15954,0,0,60,0,262,admit)&&calls==18);
 auto beyondPatrol=[](float x,float y,float,float){return x==110&&y==0;};
 assert(RaidLabNothDoorApproach(533,15954,0,0,60,0,262,beyondPatrol));
 calls=0;assert(!RaidLabNothDoorApproach(469,15954,0,0,60,0,262,reject));
 assert(!RaidLabNothDoorApproach(533,15936,0,0,60,0,262,reject));
 assert(!RaidLabNothDoorApproach(533,15954,0,0,0,0,262,reject));
 assert(!RaidLabNothDoorApproach(533,15954,0,0,121,0,262,reject));
 assert(!RaidLabNothDoorApproach(533,15954,NAN,0,60,0,262,reject)&&calls==0);
 auto rotated=[](float x,float y,float z,float bound){return x==0&&y==66;};
 assert(RaidLabNothDoorApproach(533,15954,0,0,0,60,262,rotated));
 std::cout<<"PASS: Noth entrance search is native-door-relative, bounded, and preserves landing rejection\n";
}
'''
landing=block(source,'TestResult CommandRaidLabLanding::Execute(')
for check in ('RaidLabInsidePatrolEnvelope','RaidLabFormationVisible','destination.isPathTo(route,1.0f,2.0f)',
              'boss->IsWithinLOS','RaidLabNothDoorApproach','GetSingleGameObjectFromStorage(181200)'):
 assert check in landing
with tempfile.TemporaryDirectory(prefix='raid-noth-door-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
