"""Exercise the real short-path result handler with controlled native results."""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
p='playerbot/WorldPosition.cpp'
source=(r/p).read_text()
if '--before' in sys.argv:
 source=subprocess.check_output(['git','-c','safe.directory='+r.as_posix(),'-C',str(r),'show','ae802751:'+p],text=True)
method=block(source,'std::vector<WorldPosition> WorldPosition::getPathStepFrom(const WorldPosition& startPos, std::unique_ptr<PathFinder>&')
code=r'''
#include <cassert>
#include <vector>
#include <memory>
#include <thread>
#include <functional>
#include <cmath>
#include <iostream>
using uint32=unsigned;
struct Point {float x=0,y=0,z=0;};using PointsArray=std::vector<Point>;
enum PathType {PATHFIND_NORMAL=1,PATHFIND_INCOMPLETE=2,PATHFIND_NOPATH=4};
struct Transport {void CalculatePassengerPosition(float& x,float&,float&){x+=1000;}};
struct Unit {Transport* transport=nullptr;unsigned GetMapId()const{return 1;}unsigned GetInstanceId()const{return 7;}
 Transport* GetTransport()const{return transport;}};
struct Travel {bool gethasToGen(){return false;}}sTravelNodeMap;
struct PathFinder {bool result=true;PathType type=PATHFIND_NORMAL;PointsArray points;unsigned calls=0;
 bool calculate(Point,Point,bool force){assert(!force);++calls;return result;}
 PointsArray getPath(){return points;}PathType getPathType(){return type;}};
struct WorldPosition {unsigned map=1;float x=0,y=0,z=0;bool water=true,los=true;
 WorldPosition()=default;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 unsigned getMapId()const{return map;}Point getVector3()const{return{x,y,z};}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}
 void CalculatePassengerOffset(Transport*){x-=1000;}
 bool isUnderWater()const{return water;}bool IsInLineOfSight(const WorldPosition&)const{return los;}
 void loadMapAndVMaps(const WorldPosition&,unsigned)const{}
 std::vector<WorldPosition> fromPointsArray(const PointsArray& points)const{
  std::vector<WorldPosition> result;for(auto p:points)result.emplace_back(map,p.x,p.y,p.z);return result;}
 WorldPosition operator+(const WorldPosition& p)const{return{map,x+p.x,y+p.y,z+p.z};}
 WorldPosition operator-(const WorldPosition& p)const{return{map,x-p.x,y-p.y,z-p.z};}
 WorldPosition operator/(float f)const{return{map,x/f,y/f,z/f};}
 WorldPosition operator*(float f)const{return{map,x*f,y*f,z*f};}
 std::vector<WorldPosition> getPathStepFrom(const WorldPosition&,std::unique_ptr<PathFinder>&,const Unit*,bool)const;
};
__METHOD__
int main(){
 WorldPosition start(1,0,0,0),end(1,10,0,0);Unit bot;
 auto finder=std::make_unique<PathFinder>();finder->points={{0,0,0},{10,0,0}};
 assert(end.getPathStepFrom(start,finder,&bot,false).size()==2);
 // A failed reused native finder can retain an old normal path. Never use it.
 finder->result=false;assert(end.getPathStepFrom(start,finder,&bot,false).empty());finder->result=true;
 // Incomplete need not imply that any points were returned.
 finder->type=PATHFIND_INCOMPLETE;finder->points.clear();
 assert(end.getPathStepFrom(start,finder,&bot,false).empty());
 finder->points={{0,0,0},{8,0,0}};
 assert(end.getPathStepFrom(start,finder,&bot,true).empty());
 auto path=end.getPathStepFrom(start,finder,&bot,false);assert(path.size()==3&&path.back().x==10);
 finder->type=PATHFIND_NOPATH;assert(end.getPathStepFrom(start,finder,&bot,false).empty());
 // Returned transport points have been converted back into world coordinates.
 // Compare/extend against the world destination, not its passenger offset.
 Transport transport;bot.transport=&transport;start.x=1000;end.x=1010;
 finder->type=PATHFIND_INCOMPLETE;path=end.getPathStepFrom(start,finder,&bot,false);
 assert(path.size()==3&&path.back().x==1010);
 std::cout<<"PASS: failed/empty/incomplete native path results, strict normal paths and transport coordinates\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-world-path-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
 subprocess.run([str(tmp/'test.exe')],check=True)
