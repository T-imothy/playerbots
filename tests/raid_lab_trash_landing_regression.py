"""Reachable endpoint suggestions must re-enter full fixture admission."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <cstddef>
#include <initializer_list>
using uint32=unsigned;constexpr unsigned PATHFIND_NORMAL=1,PATHFIND_INCOMPLETE=4;
constexpr float INVALID_HEIGHT=-100000;
struct Map {float broad=30.004f,bounded=28.511f;bool found=true;int reads=0;
 float GetHeight(float,float,float){return broad;}
 bool GetHeightInRange(float,float,float& out,float){++reads;out=bounded;return found;}};
__BODY__
int main(){
 Map map;float z=0;
 assert(RaidLabLandingFloor(&map,-9675.626f,1519.297f,21.527f,8,z)&&z==map.bounded&&map.reads==1);
 map.broad=23;assert(RaidLabLandingFloor(&map,0,0,21.527f,8,z)&&z==23&&map.reads==1);
 map.broad=30.004f;map.bounded=30;assert(!RaidLabLandingFloor(&map,0,0,21.527f,8,z));
 map.bounded=28.511f;map.found=false;assert(!RaidLabLandingFloor(&map,0,0,21.527f,8,z));map.found=true;
 map.bounded=NAN;assert(!RaidLabLandingFloor(&map,0,0,21.527f,8,z));
 map.broad=INVALID_HEIGHT;map.bounded=INVALID_HEIGHT;assert(!RaidLabLandingFloor(&map,0,0,21.527f,8,z));
 map.bounded=-21.527f;assert(!RaidLabLandingFloor(&map,0,0,21.527f,8,z));
 assert(!RaidLabLandingFloor(nullptr,0,0,0,8,z));
 for(float bad:{0.f,-1.f,41.f,NAN})assert(!RaidLabLandingFloor(&map,0,0,0,bad,z));
 map.broad=30;assert(RaidLabLandingFloor(&map,0,0,0,40,z)&&z==30);
 assert(!RaidLabLandingFloor(&map,0,0,0,8,z)); // original 8-yard callers stay bounded
 assert(!RaidLabLandingFloor(&map,NAN,0,0,8,z));
 assert(RaidLabTrashLandingSuggestion(509,15327,true,4,4,-9723.033f,1548.856f,24.267f,-9716.955f,1542.778f,22.786f));
 assert(!RaidLabTrashLandingSuggestion(509,15327,false,4,4,0,0,0,1,1,1));
 assert(!RaidLabTrashLandingSuggestion(509,15325,true,4,4,0,0,0,1,1,1));
 assert(RaidLabTrashLandingSuggestion(409,11669,true,4,7,1082.820f,-826.085f,-160.808f,1081.145f,-831.110f,-147.451f));
 assert(RaidLabTrashLandingSuggestion(469,12465,true,4,7,-7568.575f,-892.659f,429.288f,-7565.867f,-899.467f,429.349f));
 for(unsigned type:{0u,2u,8u,16u,32u})assert(!RaidLabTrashLandingSuggestion(409,11669,true,type,7,0,0,0,1,1,1));
 for(size_t size:{0u,1u,257u})assert(!RaidLabTrashLandingSuggestion(409,11669,true,4,size,0,0,0,1,1,1));
 assert(!RaidLabTrashLandingSuggestion(409,11669,false,4,7,0,0,0,1,1,1));
 assert(!RaidLabTrashLandingSuggestion(531,11669,true,4,7,0,0,0,1,1,1));
 assert(!RaidLabTrashLandingSuggestion(409,12056,true,4,7,0,0,0,1,1,1));
 assert(!RaidLabTrashLandingSuggestion(409,11669,true,4,7,0,0,0,21,0,0));
 assert(!RaidLabTrashLandingSuggestion(409,11669,true,4,7,0,0,0,0,0,17));
 assert(!RaidLabTrashLandingSuggestion(409,11669,true,4,7,0,0,0,NAN,0,0));
}
'''.replace('__BODY__',block(source,'bool RaidLabTrashLandingSuggestion(')+'\n'+block(source,'bool RaidLabLandingFloor('))
landing=block(source,'TestResult CommandRaidLabLanding::Execute(')
for text in ('trashLandingSuggestions.size()<16','suppressionStart || ctx.raidLabPackId==4090159',
             'collectEyeLandings=false','candidate(point.getX(),point.getY(),point.getZ(),2.0f)',
             'destination.isPathTo(route,1.0f,2.0f)','RaidLabFormationVisible','RaidLabInsidePatrolEnvelope',
             'ctx.raidLabPackId==5090000','RaidLabLandingFloor(bot->GetMap(),cx,cy,hint,maxDelta,cz)',
             'RaidLabPackPullCorridor','RaidLabSuppressionStartFloor'):
 assert text in landing
with tempfile.TemporaryDirectory(prefix='raid-trash-floor-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: fixture-only bounded endpoint suggestions preserve full landing admission')
