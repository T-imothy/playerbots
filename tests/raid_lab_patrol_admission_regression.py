"""Reproduce AQ20 landing inside a native stinger patrol rather than its current aggro circle."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <algorithm>
#include <map>
struct WaypointNode {float x,y,z;};using WaypointPath=std::map<unsigned,WaypointNode>;
'''+block(source,'bool RaidLabInsidePatrolPath(')+r'''
int main(){
 // Native creature_movement 5090094, not an invented encounter route.
 WaypointPath stinger{{1,{-8761.08f,1573.96f,24.669f}},
 {2,{-8754.32f,1573.61f,23.1307f}},{3,{-8749.5f,1583.89f,21.5113f}},
 {4,{-8749.61f,1598.33f,22.0267f}},{5,{-8744.07f,1615.72f,21.6868f}},
 {6,{-8738.8f,1626.02f,22.6612f}}};
 float x=-8755.230f,y=1619.709f,z=21.495f;
 assert(std::hypot(x-stinger.begin()->second.x,y-stinger.begin()->second.y)>40);
 assert(RaidLabInsidePatrolPath(stinger,x,y,z,25));
 assert(!RaidLabInsidePatrolPath(stinger,-8830,1550,21,25));
 WaypointPath segment{{1,{0,0,0}},{2,{100,0,0}}};
 assert(RaidLabInsidePatrolPath(segment,50,3,0,4)); // Between nodes.
 assert(!RaidLabInsidePatrolPath(segment,50,3,10,4)); // Separate floor.
 assert(!RaidLabInsidePatrolPath(segment,50,8,0,4));
 assert(RaidLabInsidePatrolPath(segment,50,8,0,10)); // Formation offset.
 segment[2]={0,0,0};assert(RaidLabInsidePatrolPath(segment,0,0,0,1));
 assert(!RaidLabInsidePatrolPath(segment,3,0,0,1));
 segment[2].x=NAN;assert(RaidLabInsidePatrolPath(segment,3,0,0,1));
 assert(RaidLabInsidePatrolPath({},0,0,0,1));
 assert(RaidLabInsidePatrolPath(stinger,x,y,z,NAN));
}
'''
wrapper=block(source,'bool RaidLabInsidePatrolEnvelope(')
for required in ('GetFormationSlot','slot->GetMaster()','slot->GetRealDistance()','GetPathInformation','GetPathFromOrigin','GetDefaultPath'):
    assert required in wrapper
assert 'RaidLabInsidePatrolEnvelope(c,cx,cy,cz,radius)' in block(source,'TestResult CommandRaidLabLanding::Execute(')
with tempfile.TemporaryDirectory(prefix='raid-native-patrol-') as folder:
    path=Path(folder);(path/'test.cpp').write_text(code)
    result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
    if result.returncode:print(result.stdout,result.stderr)
    result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
print('PASS native AQ20 patrol admission: current position is insufficient; segment/floor/formation/invalid path cases covered')
