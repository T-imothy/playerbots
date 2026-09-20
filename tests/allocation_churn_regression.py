"""Compile actual auction-refresh and travel-distance functions with MSVC fixtures.
Run with Python from a Visual Studio developer prompt; no realm or DB required.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
def fragment(file, start, end):
    text = (root / file).read_text()
    begin = text.index(start)
    return text[begin:text.index(end, begin)]

mirror = fragment('playerbot/RandomPlayerbotMgr.cpp', 'void RandomPlayerbotMgr::MirrorAh()', '\ntypedef std::unordered_map <uint32, std::list<float>>')
travel = (root / 'playerbot/TravelMgr.cpp').read_text()
begin = travel.index('float TravelMgr::MapTransDistance(')
depth, end = 0, travel.index('{', begin)
for index in range(end, len(travel)):
    depth += (travel[index] == '{') - (travel[index] == '}')
    if depth == 0:
        end = index + 1
        break
distance = travel[begin:end]
code = r'''
#include <cassert>
#include <cmath>
#include <cfloat>
#include <cstdlib>
#include <new>
#include <map>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <iostream>
#include <limits>
static size_t allocations=0;
void* operator new(size_t n) {++allocations;if(auto p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,size_t) noexcept {std::free(p);}
using uint32=unsigned;
enum AuctionHouseType {H0,H1,H2};
struct AuctionEntry {
    uint32 id,itemTemplate,buyout,itemCount;
    bool operator==(AuctionEntry const& b) const {return id==b.id&&itemTemplate==b.itemTemplate&&buyout==b.buyout&&itemCount==b.itemCount;}
};
struct AuctionHouseEntry {unsigned house;};
struct Store {
    AuctionHouseEntry entries[3]={{0},{1},{2}};
    bool enabled[3]={true,true,true};
    AuctionHouseEntry const* LookupEntry(unsigned i){return enabled[i]?&entries[i]:nullptr;}
} sAuctionHouseStore;
struct AuctionHouseObject {
    using AuctionEntryMap=std::map<unsigned,AuctionEntry*>;
    AuctionEntryMap data;std::recursive_mutex lock;
    auto& GetLock(){return lock;}
    auto GetAuctionsBounds_locked(){return std::make_pair(data.begin(),data.end());}
};
struct AuctionMgr {
    AuctionHouseObject houses[3];
    AuctionHouseObject* GetAuctionsMap(AuctionHouseEntry const* h){return &houses[h->house];}
} sAuctionMgr;
namespace ahbot {struct AhBot {inline static unsigned auctionIds[3]={0,1,2};};}
struct RandomPlayerbotMgr {
    std::mutex m_ahActionMutex;
    std::unordered_map<uint32,std::vector<AuctionEntry>> ahMirror;
    void MirrorAh();
};
MIRROR
auto expectedMirror() {
    std::unordered_map<uint32,std::vector<AuctionEntry>> result;
    for(unsigned h=0;h<3;++h) {
        if(!sAuctionHouseStore.enabled[h])continue;
        for(auto const& a:sAuctionMgr.houses[h].data)
            if(a.second&&a.second->buyout&&a.second->itemCount)
                result[a.second->itemTemplate].push_back(*a.second);
    }
    return result;
}
struct WorldPosition {
    unsigned map;float x,y;
    unsigned getMapId() const {return map;}
    float sqDistance2d(WorldPosition const& b)const{return (x-b.x)*(x-b.x)+(y-b.y)*(y-b.y);}
};
struct Transfer {
    WorldPosition from,to;float length;
    auto GetPointTo()const{return to;}
    float sqDist(WorldPosition const& a,WorldPosition const& b)const{return a.sqDistance2d(from)+length*length+to.sqDistance2d(b);}
};
struct TravelMgr {
    std::map<std::pair<unsigned,unsigned>,std::vector<Transfer>> mapTransfersMap;
    float MapTransDistance(WorldPosition const&,WorldPosition const&,bool)const;
    float reference(WorldPosition const& a,WorldPosition const& b)const {
        std::vector<std::pair<WorldPosition,float>> portals;
        if(a.map==b.map)portals.push_back({a,0.0f});
        else {auto i=mapTransfersMap.find({a.map,b.map});if(i==mapTransfersMap.end())return FLT_MAX;
            for(auto const& t:i->second){auto p=t.GetPointTo();portals.push_back({p,t.sqDist(a,p)});}}
        if(portals.empty())return FLT_MAX;
        float best=FLT_MAX;
        for(auto const& p:portals){float d=p.second+p.first.sqDistance2d(b);if(d<best)best=d;}
        return sqrt(best);
    }
};
DISTANCE
int main() {
    RandomPlayerbotMgr mgr;
    std::vector<AuctionEntry> entries;entries.reserve(600);
    for(unsigned h=0;h<3;++h)for(unsigned i=0;i<200;++i){
        entries.push_back({h*200+i,i%17,i%11?100u:0u,i%13?1u:0u});
        sAuctionMgr.houses[h].data[i]=&entries.back();}
    sAuctionMgr.houses[0].data[300]=nullptr;
    mgr.MirrorAh();assert(mgr.ahMirror==expectedMirror());
    auto before=allocations;
    for(int i=0;i<200;++i)mgr.MirrorAh();
    assert(allocations==before); // Steady refresh requires no allocation.
    entries[5].buyout=999;entries[6].itemCount=0;sAuctionHouseStore.enabled[1]=false;
    sAuctionMgr.houses[2].data.clear();
    mgr.MirrorAh();assert(mgr.ahMirror==expectedMirror());
    for(auto& e:entries)e.itemTemplate=99;
    sAuctionHouseStore.enabled[1]=true;
    mgr.MirrorAh();assert(mgr.ahMirror==expectedMirror());
    sAuctionMgr.houses[0].data.clear();sAuctionMgr.houses[1].data.clear();
    sAuctionMgr.houses[0].data[5]=&entries[5];
    mgr.MirrorAh();assert(mgr.ahMirror==expectedMirror());
    assert(mgr.ahMirror.at(99).capacity()<=64); // Release obsolete peak capacity.
    sAuctionMgr.houses[0].data.clear();mgr.MirrorAh();assert(mgr.ahMirror.empty());
    TravelMgr travel;
    travel.mapTransfersMap[{0,1}]={{{0,1,2},{1,5,6},10},{{0,-2,3},{1,8,9},3}};
    travel.mapTransfersMap[{1,0}]={};
    for(unsigned i=0;i<1000;++i){
        WorldPosition a{i%3,float(i%31)-10,float(i%7)},b{(i/3)%3,float(i%29),-float(i%13)};
        auto want=travel.reference(a,b);before=allocations;
        assert(travel.MapTransDistance(a,b,false)==want);
        assert(travel.MapTransDistance(a,b,true)==want);
        assert(allocations==before);
    }
    WorldPosition a{0,std::numeric_limits<float>::infinity(),0},b{0,0,0};
    assert(travel.MapTransDistance(a,b,false)==travel.reference(a,b));
    a.x=std::numeric_limits<float>::quiet_NaN();
    assert(travel.MapTransDistance(a,b,false)==travel.reference(a,b));
    std::cout<<"PASS: auction contents, changes/removals, bounded capacity, zero-allocation refresh; travel equivalence and zero allocations\n";
}
'''.replace('MIRROR', mirror).replace('DISTANCE', distance)
with tempfile.TemporaryDirectory(prefix='turtle-churn-') as tmp:
    work = Path(tmp)
    (work / 'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=work,check=True)
    subprocess.run([str(work / 'test.exe')],cwd=work,check=True)
