"""Execute the actual transport-resume method with expired/truncated route state."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/MovementActions.cpp').read_text(), 'bool MovementAction::WaitForTransport(')
code=r'''
#include <cassert>
#include <vector>
#include <iterator>
#include <iostream>
#include <stdexcept>
enum class PathNodeType { NODE_TRANSPORT, NODE_PATH };
struct WorldPosition {int id=0;};
struct PathNodePoint {PathNodeType type=PathNodeType::NODE_TRANSPORT;unsigned entry=7;WorldPosition point;};
struct Points:std::vector<PathNodePoint> {
 PathNodePoint& front(){if(empty())throw std::runtime_error("empty transport route front");return (*this)[0];}
};
struct GenericTransport {unsigned entry=7;unsigned GetEntry(){return entry;}};
struct Player {GenericTransport* transport=nullptr;GenericTransport* GetTransport(){return transport;}};
struct TravelPath {Points points;bool special=true,truncate=false;
 bool empty(){return points.empty();}Points& getPath(){return points;}
 bool UpcommingSpecialMovement(Player*,float,GenericTransport*){if(truncate)points.resize(1);return special;}};
struct LastMovement {unsigned lastTransportEntry=7;TravelPath lastPath;};
struct Config {int transportTeleportType=0;}sPlayerbotAIConfig;
struct MovementAction {Player* bot;void* ai=nullptr;LastMovement last;unsigned calls=0;
 bool used=false;int dock=0,exit=0;
 bool WaitForTransport();
 bool UseTransport(void*,unsigned,WorldPosition a,WorldPosition b,bool){++calls;dock=a.id;exit=b.id;return used;}};
#define AI_VALUE(type,name) last
__METHOD__
int main(){
 Player player;GenericTransport boat;player.transport=&boat;MovementAction action{&player};
 // A previous boarding marker can survive after its route has been cleared.
 assert(!action.WaitForTransport()&&action.calls==0&&action.last.lastTransportEntry==0);
 auto route=[&](){action.last.lastTransportEntry=7;auto& p=action.last.lastPath;
  p.points.clear();p.points.push_back({PathNodeType::NODE_TRANSPORT,7,{10}});
  p.points.push_back({PathNodeType::NODE_PATH,0,{20}});p.special=true;p.truncate=false;};
 route();action.last.lastPath.points.resize(1);assert(!action.WaitForTransport()&&action.calls==0);
 route();action.last.lastPath.truncate=true;assert(!action.WaitForTransport()&&action.calls==0&&action.last.lastTransportEntry==0);
 route();action.last.lastPath.points.front().entry=8;assert(!action.WaitForTransport()&&action.calls==0);
 route();player.transport=nullptr;assert(!action.WaitForTransport()&&action.calls==0);player.transport=&boat;
 route();action.last.lastPath.special=false;assert(!action.WaitForTransport()&&action.calls==0);
 route();assert(action.WaitForTransport()&&action.calls==1&&action.last.lastTransportEntry==7);
 assert(action.dock==10&&action.exit==20); // still waiting for a valid exit
 action.used=true;assert(!action.WaitForTransport()&&action.calls==2&&action.last.lastTransportEntry==0);
 std::cout<<"PASS: actual transport resume with empty, one-point, truncated and valid routes\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-transport-resume-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
