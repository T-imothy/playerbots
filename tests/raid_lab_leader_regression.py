"""Execute actual local synthetic-leader preparation and cleanup predicates."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root.parent/'classic/src/game/World/RaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <iostream>
using uint64=uint64_t;using uint32=uint32_t;
struct Guid{uint64 value=1;uint64 GetRawValue(){return value;}};
struct Map{uint32 id=533,instance=1;};
struct Player{bool world=true,teleport=false;Guid guid;Map map;
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return teleport;}Guid GetObjectGuid(){return guid;}
 uint32 GetMapId(){return map.id;}uint32 GetInstanceId(){return map.instance;}Map*GetMap(){return &map;}};
bool enabled=true;bool Enabled(){return enabled;}std::recursive_mutex guard;
std::map<uint64,std::pair<uint32,uint32>>preparedLeaders;
std::map<uint64,uint32>preparationImpacts;
std::map<uint64,uint32>preparationCombats;
struct Attempt{uint64 leader=1;bool controlled=true;};
std::map<std::pair<uint32,uint32>,std::unique_ptr<Attempt>>attempts;
Attempt*Find(Map*m){auto i=attempts.find({m->id,m->instance});return i==attempts.end()?nullptr:i->second.get();}
void FlushCounts(Attempt&){}void Write(Attempt&,std::string){}std::string Quote(std::string s){return s;}
__METHODS__
int main(){
 Player p;assert(!Controlled(&p));assert(PrepareLeader(&p));assert(Controlled(&p)); // before combat Begin
 assert(PrepareLeader(&p)&&preparedLeaders.size()==1); // idempotent fixture setup
 p.map.instance=2;assert(!Controlled(&p));p.map.instance=1;
 p.map.id=469;assert(!Controlled(&p));p.map.id=533;
 p.guid.value=2;assert(!Controlled(&p));p.guid.value=1;
 p.world=false;assert(!Controlled(&p)&&!PrepareLeader(&p));p.world=true;
 enabled=false;assert(!Controlled(&p)&&!PrepareLeader(&p));enabled=true;
 p.teleport=true;assert(!PrepareLeader(&p));p.teleport=false;
 preparationImpacts[1]=10;preparationCombats[1]=10;EndLeader(1,"setup failure");assert(!Controlled(&p)&&preparedLeaders.empty()&&preparationImpacts.empty()&&preparationCombats.empty());
 p.map.id=489;assert(!PrepareLeader(&p));p.map.id=0;assert(!PrepareLeader(&p));p.map.id=533;
 assert(PrepareLeader(&p));attempts[{533,1}]=std::make_unique<Attempt>();
 EndLeader(1,"done");assert(!Controlled(&p)&&attempts.empty());
 assert(PrepareLeader(&p));StopAll();assert(!Controlled(&p));
 assert(!PrepareLeader(nullptr)&&!Controlled(nullptr));
 std::cout<<"PASS local pre-combat leader identity, world/instance scope, setup failure and shutdown cleanup\n";
}
'''
code=code.replace('__METHODS__','\n'.join(block(source,s) for s in ['bool AllowedMap(', 'bool PrepareLeader(', 'bool Controlled(', 'void EndLeader(', 'void StopAll(']))
with tempfile.TemporaryDirectory(prefix='raidlab-leader-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
