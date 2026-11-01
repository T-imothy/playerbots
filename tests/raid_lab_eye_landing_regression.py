"""Native Eye corridor endpoints are suggestions, never accepted partial paths."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <vector>
constexpr double M_PI=3.14159265358979323846;
using uint32=unsigned;constexpr unsigned PATHFIND_NORMAL=1;
__BODY__
int main(){
 assert(RaidLabEyeLandingSuggestion(531,15589,1,16,-8591.572f,1927.557f,104.475f,-8593.312f,1926.755f,101.888f));
 for(unsigned type:{0u,2u,4u,8u})assert(!RaidLabEyeLandingSuggestion(531,15589,type,16,0,0,0,1,1,1));
 for(size_t count:{0u,1u,257u})assert(!RaidLabEyeLandingSuggestion(531,15589,1,count,0,0,0,1,1,1));
 assert(!RaidLabEyeLandingSuggestion(533,15589,1,16,0,0,0,1,1,1));
 assert(!RaidLabEyeLandingSuggestion(531,15727,1,16,0,0,0,1,1,1));
 assert(!RaidLabEyeLandingSuggestion(531,15589,1,16,0,0,0,5,0,0));
 assert(!RaidLabEyeLandingSuggestion(531,15589,1,16,0,0,0,0,0,7));
 assert(!RaidLabEyeLandingSuggestion(531,15589,1,16,0,0,0,NAN,0,0));
 unsigned calls=0;
 auto reject=[&](float x,float y,float z,float limit){
  ++calls;const float radius=std::hypot(x+8578.790f,y-1986.180f);
  assert(radius>109.99f && radius<130.01f);assert(limit==8);
  assert(z==100.304f || z==103.056f);return false;};
 assert(!RaidLabEyeOuterApproach(531,15589,-8578.790f,1986.180f,100.304f,103.056f,0,reject));
 assert(calls==144);calls=0;
 assert(!RaidLabEyeOuterApproach(533,15589,0,0,0,0,0,reject));
 assert(!RaidLabEyeOuterApproach(531,15727,0,0,0,0,0,reject));
 assert(!RaidLabEyeOuterApproach(531,15589,NAN,0,0,0,0,reject));assert(calls==0);
 assert(RaidLabEyeOuterApproach(531,15589,0,0,0,0,0,[&](float,float,float,float){return ++calls==3;}));
 assert(calls==3); // only the ordinary admission callback can accept a point
 std::cout<<"PASS: native Eye suggestions bounded; wrong era/map/actor, partial paths and invalid endpoints rejected\n";
}
'''.replace('__BODY__',block(source,'bool RaidLabEyeLandingSuggestion(')+'\ntemplate<class Candidate>\n'+block(source,'bool RaidLabEyeOuterApproach('))
landing=block(source,'TestResult CommandRaidLabLanding::Execute(')
for guard in ('eyeLandingSuggestions.size()<16','collectEyeLandings=false',
              'candidate(point.getX(),point.getY(),point.getZ(),2.0f)',
              'destination.isPathTo(route,1.0f,2.0f)','RaidLabEyeEntryRoute',
              'RaidLabFormationVisible','RaidLabInsidePatrolEnvelope'):
 assert guard in landing
with tempfile.TemporaryDirectory(prefix='raid-eye-floor-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
