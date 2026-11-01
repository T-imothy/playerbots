"""Actual local readiness floor: bounded native query, never relaxed tolerance."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
constexpr float INVALID_HEIGHT=-10000;
struct Map{float broad=41.277f,nearby=41.277f;bool found=true;unsigned queries=0;
 float GetHeight(float,float,float){return broad;}
 bool GetHeightInRange(float,float,float&z,float limit){assert(limit==2);++queries;z=nearby;return found;}};
struct Player{float x=-11571.2f,y=-1627.87f,z=41.277f;Map map;Map*GetMap(){return &map;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}unsigned GetGUIDLow(){return 1;}};
struct Log{template<class...T>void outString(const char*,T...){}}sLog;
'''
code+=block((root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text(),'bool RaidLabLocalFloor(')
code+=r'''
int main(){Player p;float floor=INVALID_HEIGHT;
 assert(RaidLabLocalFloor(&p,floor)&&p.map.queries==0);
 p.map.broad=48.57f;assert(RaidLabLocalFloor(&p,floor)&&floor==p.z&&p.map.queries==1);
 p.map.found=false;assert(!RaidLabLocalFloor(&p,floor));p.map.found=true;
 p.map.nearby=48.57f;assert(!RaidLabLocalFloor(&p,floor)); // dynamic overhead rejected too
 p.map.nearby=p.z-2.01f;assert(!RaidLabLocalFloor(&p,floor));
 p.map.nearby=NAN;assert(!RaidLabLocalFloor(&p,floor));
 p.map.nearby=INVALID_HEIGHT;assert(!RaidLabLocalFloor(&p,floor));
 p.map.nearby=p.z;p.x=NAN;const auto before=p.map.queries;
 assert(!RaidLabLocalFloor(&p,floor)&&p.map.queries==before);
 std::cout<<"PASS local readiness preserves2yd tolerance, bounded native ground required, overhead/missing/invalid floor refused\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-local-floor-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
