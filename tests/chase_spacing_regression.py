"""Actual chase hazard destination is measured back from the target."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/MovementActions.cpp').read_text()
chase=block(source,'bool MovementAction::ChaseTo(')
start=chase.index('    const Vector3 directionToTarget')
end=chase.index('    WorldPosition endPosition',start)
geometry=chase[start:end]
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
struct Vector3{float x,y,z;Vector3 operator+(Vector3 b)const{return{x+b.x,y+b.y,z+b.z};}
 Vector3 operator-(Vector3 b)const{return{x-b.x,y-b.y,z-b.z};}Vector3 operator*(float f)const{return{x*f,y*f,z*f};}
 float length()const{return std::sqrt(x*x+y*y+z*z);}Vector3 directionOrZero()const{float l=length();return l?*this*(1/l):Vector3{0,0,0};}};
Vector3 destination(Vector3 botPoint,Vector3 targetPoint,float distance){
 float distanceToTarget=(targetPoint-botPoint).length();
 __GEOMETRY__
 return endPoint;
}
int main(){
 auto point=destination({0,0,0},{30,0,0},10);assert(point.x==20);
 point=destination({0,0,0},{5,0,0},10);assert(point.x==0);
 point=destination({0,0,0},{3,4,0},2);assert(std::fabs(point.x-1.8f)<0.001f&&std::fabs(point.y-2.4f)<0.001f);
 point=destination({0,0,0},{3,4,0},0);assert(point.x==3&&point.y==4);
 point=destination({0,0,0},{3,4,0},-2);assert(point.x==3&&point.y==4);
 point=destination({2,2,2},{2,2,2},0);assert(point.x==2&&point.y==2&&point.z==2);
 std::cout<<"PASS: chase offset from target, already-in-range, diagonal, zero-distance and coincident positions\n";
}
'''.replace('__GEOMETRY__',geometry)
with tempfile.TemporaryDirectory(prefix='mantech-chase-spacing-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
