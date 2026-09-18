"""Exercise the production transport lookup with deterministic native API fixtures.

Run from a Visual Studio developer prompt with Python. This builds a small test,
not the server. No database or running realm is involved.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/WorldPosition.cpp').read_text()
start = source.index('std::set<GenericTransport*> WorldPosition::getTransports(')
end = source.index('\nvoid WorldPosition::CalculatePassengerPosition', start)
function = source[start:end]
assert 'getGameObjectsNear(' not in function
code = r'''
#include <cassert>
#include <map>
#include <set>
#include <vector>
#include <utility>
using uint32 = unsigned;
constexpr int HIGHGUID_GAMEOBJECT = 1;
struct ObjectGuid {
    unsigned long long value;
    ObjectGuid(int, uint32 entry, uint32 id) : value((1ull*entry<<32)|id) {}
};
struct GameObject { virtual ~GameObject() = default; };
struct GenericTransport : GameObject {
    uint32 entry;
    explicit GenericTransport(uint32 e):entry(e){}
    uint32 GetEntry() const {return entry;}
};
struct Spawn { uint32 id; struct {uint32 mapid;} position; };
using GameObjectDataPair = std::pair<const uint32, Spawn>;
struct Map {
    std::vector<GenericTransport*> boats;
    std::map<unsigned long long, GameObject*> objects;
    auto const& GetTransports() const {return boats;}
    GameObject* GetGameObject(ObjectGuid guid) {
        auto i=objects.find(guid.value);return i==objects.end()?nullptr:i->second;
    }
};
struct ObjectMgr {
    std::map<uint32, Spawn> spawns;
    int scans=0;
    template<class F> void DoGOData(F& f) {
        ++scans;for(auto const& spawn:spawns)if(f(spawn))break;
    }
} sObjectMgr;
struct WorldPosition {
    Map* map; uint32 id; bool valid;
    Map* getMap(uint32) {return map;}
    uint32 getFirstInstanceId() {return 0;}
    uint32 getMapId() {return id;}
    explicit operator bool() const {return valid;}
    std::set<GenericTransport*> getTransports(uint32 entry=0);
};
FUNCTION
int main() {
    GenericTransport boat(10), elevator(20), otherMap(20);
    GameObject ordinary;
    Map map;map.boats={&boat};
    map.objects.emplace(ObjectGuid(1,20,1).value,&elevator);
    map.objects.emplace(ObjectGuid(1,20,2).value,&otherMap);
    map.objects.emplace(ObjectGuid(1,30,3).value,&ordinary);
    sObjectMgr.spawns={{1,{20,{0}}},{2,{20,{1}}},{3,{30,{0}}},{4,{20,{0}}}};
    WorldPosition pos{&map,0,true};
    assert(pos.getTransports(10)==std::set<GenericTransport*>{&boat});
    assert(sObjectMgr.scans==0); // Matched boat needs no fallback scan.
    assert(pos.getTransports(20)==std::set<GenericTransport*>{&elevator});
    assert((pos.getTransports()==std::set<GenericTransport*>{&boat,&elevator}));
    assert(pos.getTransports(30).empty()); // Ordinary GO is not a transport.
    assert(pos.getTransports(999).empty());
    pos.valid=false;
    assert((pos.getTransports(20)==std::set<GenericTransport*>{&elevator,&otherMap}));
    pos.valid=true;
    for(int n=0;n<1000;++n)
        assert(pos.getTransports(20)==std::set<GenericTransport*>{&elevator});
    map.objects.erase(ObjectGuid(1,20,1).value);
    assert(pos.getTransports(20).empty()); // No stale cached live pointers.
    pos.map=nullptr;
    assert(pos.getTransports().empty());
}
'''.replace('FUNCTION', function)
with tempfile.TemporaryDirectory(prefix='turtle-transport-') as directory:
    work = Path(directory)
    (work / 'test.cpp').write_text(code)
    subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', 'test.cpp', '/Fe:test.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'test.exe')], cwd=work, check=True)
print('PASS: production transport lookup filtering, fallback, unload and repeat cases')
