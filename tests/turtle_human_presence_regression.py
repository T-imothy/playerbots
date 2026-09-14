from pathlib import Path
from turtle_cpp_fixture import run
m=Path(__file__).resolve().parents[1]/'playerbot'
run(r'''#include "HumanPresence.h"
#include <cassert>
#include <cstdio>
using namespace ai;
int main(){
 std::vector<HumanPresence> humans={{true,{{0,0,3,4,0,false},{0,0,0,0,0,true}}}, {false,{{0,0,0,0,0,false}}}, {true,{{0,1,0,0,0,false}}}, {true,{{1,0,0,0,0,false}}}};
 assert(CountHumansNear(humans,0,0,0,0,0,5,false,true)==0);
 assert(CountHumansNear(humans,0,0,0,0,0,5.1f,false,true)==1);
 assert(CountHumansNear(humans,0,0,0,0,0,1,true,true)==1);
 assert(CountHumansNear(humans,0,0,0,0,0,20,true,true)==1); // camera/body count once
 assert(CountHumansNear(humans,0,1,0,0,0,1,false,true)==1);
 assert(CountHumansNear(humans,0,0,0,0,20,6,false,true)==0);
 assert(CountHumansNear(humans,0,0,0,0,20,6,false,false)==1);
 assert(CountHumansNear(humans,0,0,0,0,0,0,true,true)==0);
 assert(CountHumansNear(humans,0,0,0,0,0,-1,true,true)==0);
 puts("PASS human presence instance/map/visibility boundaries, camera union, linear radius, and 2D/3D semantics");
}
''',[m])
