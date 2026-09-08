"""Check production vmap directory/result handling and startup spawn selection."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
def method(path,signature):
    text=(root/path).read_text();a=text.index(signature);b=text.index('{',a);d=1;i=b+1
    while d:d+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[a:i]
code=r'''
#include <cassert>
#include <chrono>
#include <string>
#include <unordered_map>
#include <vector>
#include <cstdint>
using uint32=uint32_t;using int32=int32_t;
#define SIZEFMTD "%zu"
struct World {std::string GetDataPath(){return "fixture/data/";}} sWorld;
namespace VMAP {
 enum Result {VMAP_LOAD_RESULT_ERROR,VMAP_LOAD_RESULT_OK,VMAP_LOAD_RESULT_IGNORED};
 struct Manager {bool loaded=false;int calls=0;Result result=VMAP_LOAD_RESULT_OK;
  Result loadMap(const char* path,uint32,int,int){++calls;assert(std::string(path)=="fixture/data/vmaps");loaded=result==VMAP_LOAD_RESULT_OK;return result;}} manager;
 struct VMapFactory {static Manager* createOrGetVMapManager(){return &manager;}};
}
struct Data {uint32 entry;bool valid,unspawned;};
std::vector<Data*> creatures,objects;
struct WorldPosition {
 static bool isVmapLoaded(uint32,int,int){return VMAP::manager.loaded;}
 static bool loadVMap(uint32,int,int);
 std::vector<Data*> getCreaturesNear(){return creatures;}std::vector<Data*> getGameObjectsNear(){return objects;}
};
int fetched=0;
struct AsyncGuidPosition {Data* data;int area=0;AsyncGuidPosition(Data* d):data(d){}
 bool isValid(){return data->valid;}bool IsEventUnspawned(){return data->unspawned;}
 void FetchArea(){++fetched;area=42;}uint32 GetEntry(){return data->entry;}};
using EntryGuidps=std::unordered_map<int32,std::vector<AsyncGuidPosition>>;
struct EntryGuidpsValue {EntryGuidps Calculate();};
struct Log {template<class... T>void outString(const char*,T...){}} sLog;
'''
code+=method('playerbot/WorldPosition.cpp','bool WorldPosition::loadVMap(uint32 mapId, int x, int y)')+'\n'
code+=method('playerbot/strategy/values/TravelValues.cpp','EntryGuidps EntryGuidpsValue::Calculate()')+'\n'
code+=r'''
int main(){
 assert(WorldPosition::loadVMap(0,1,2));assert(VMAP::manager.calls==1);
 assert(WorldPosition::loadVMap(0,1,2));assert(VMAP::manager.calls==1);
 VMAP::manager.loaded=false;VMAP::manager.result=VMAP::VMAP_LOAD_RESULT_ERROR;assert(!WorldPosition::loadVMap(0,1,2));
 VMAP::manager.result=VMAP::VMAP_LOAD_RESULT_IGNORED;assert(!WorldPosition::loadVMap(0,1,2));
 Data a{10,true,false},b{10,true,false},c{11,false,false},d{12,true,true},e{10,true,false};
 creatures={&a,&b,&c,&d};objects={&e};EntryGuidpsValue value;auto out=value.Calculate();
 assert(out.size()==2&&out.at(10).size()==2&&out.at(-10).size()==1&&fetched==3);
 for(auto const& [entry,points]:out)for(auto const& point:points)assert(point.area==42);
 creatures.clear();objects.clear();assert(value.Calculate().empty());
}
'''
with tempfile.TemporaryDirectory(prefix='object-location-regression-') as temp:
    p=Path(temp);(p/'test.cpp').write_text(code)
    result=subprocess.run(['cl','/nologo','/std:c++20','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('Object-location startup: native vmap path, load results, existing tiles, signed entries and spawn filtering passed')
