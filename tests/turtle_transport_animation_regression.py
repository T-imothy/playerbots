from pathlib import Path
from turtle_cpp_fixture import run
import re
r=Path(__file__).resolve().parents[3]
source=(r/'modules/ManTechPlayerbots/playerbot/TransportAnimation.cpp').read_text(encoding='utf-8')
source=re.sub(r'^#include.*$','',source,flags=re.M)
run(r'''#include <map>
#include <string>
#include <vector>
#include <cstdint>
#include <cmath>
#include <limits>
#include <cassert>
#include <cstdio>
using uint32=uint32_t;
struct TransportAnimationNode{uint32 TimeIndex=0,TimeSeg=0;float X=0,Y=0,Z=0;};
struct TransportAnimation{std::map<uint32,TransportAnimationNode*>Path;uint32 TotalTime=0;};
bool available=true;
template<class T>struct DBCStorage{std::vector<T>rows;
 DBCStorage(const char*f){assert(std::string(f)=="niifffx");rows={{0,8,200,1,2,3},{1,8,0,4,5,6},{2,9,90,-1,-2,-3},{3,8,200,9,9,9},{4,10,0,std::numeric_limits<float>::quiet_NaN(),0,0}};}
 bool Load(const char*){return available;}uint32 GetNumRows(){return rows.size();}T const*LookupEntry(uint32 id){return &rows.at(id);}};
struct {std::string GetDataPath(){return "";}}sWorld;
struct {template<class...T>void outError(T...){}template<class...T>void outString(T...){} }sLog;
'''+source+r'''
int main(){
 auto*a=GetPlayerbotTransportAnimation(8);assert(a&&a->Path.size()==2&&a->TotalTime==200);
 assert(a->Path.begin()->first==0&&a->Path.begin()->second->X==4);
 assert(a->Path.rbegin()->second->X==1);assert(a==GetPlayerbotTransportAnimation(8));
 assert(GetPlayerbotTransportAnimation(9)->Path.begin()->second->Z==-3);
 assert(!GetPlayerbotTransportAnimation(10)&&!GetPlayerbotTransportAnimation(100));
 available=false;AnimationIndex missing;assert(missing.animations.empty());
 puts("PASS actual animation index: entry namespace, ordered time segments, duplicate stability, copied node lifetime, invalid coordinates and missing data");
}
''')
