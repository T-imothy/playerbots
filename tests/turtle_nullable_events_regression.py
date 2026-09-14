from pathlib import Path
root=Path(__file__).resolve().parents[3]
s=(root/'modules/ManTechPlayerbots/playerbot/RandomPlayerbotMgr.cpp').read_text(encoding='utf-8')
methods=s[s.index('void RandomPlayerbotMgr::PrimeEventCache()'):s.index('uint64 RandomPlayerbotMgr::PruneExpiredEventCache')]
f=(root/'src/shared/Database/Field.h').read_text()
getter=f[f.index('        std::string GetCppString() const'):f.index('        float GetFloat()')]
code=r'''
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <map>
#include <mutex>
#include <memory>
#include <string>
#include <unordered_set>
#include <vector>
#include <cstdio>
using uint32=uint32_t;using uint64=uint64_t;
struct Field { const char* mValue; const char* GetString()const{return mValue;}
 uint32 GetUInt32()const{return mValue?uint32(std::strtoul(mValue,nullptr,10)):0;}
''' + getter + r'''};
struct Result {std::vector<std::vector<Field>>rows;size_t i=0;Field*Fetch(){return rows[i].data();}bool NextRow(){return ++i<rows.size();}};
struct Db {std::vector<std::vector<Field>> rows;int reads=0;
 std::unique_ptr<Result> Query(const char*){++reads;if(rows.empty())return {};return std::make_unique<Result>(Result{rows});}
 std::unique_ptr<Result> PQuery(const char*,uint32){return Query("");}
} CharacterDatabase;
struct Diagnostics {void RecordEventCacheLoad(uint32,uint64){}}sPlayerbotDiagnostics;
struct CachedEvent {uint32 value=0,lastChangeTime=0,validIn=0;std::string data;
 CachedEvent()=default;CachedEvent(uint32 v,uint32 t,uint32 ttl,std::string d):value(v),lastChangeTime(t),validIn(ttl),data(d){}
};
struct RandomPlayerbotMgr {std::recursive_mutex eventCacheMutex;std::unordered_set<uint32>loadedEventBots;bool eventCachePrimed=false;std::map<uint32,std::map<std::string,CachedEvent>>eventCache;
 void PrimeEventCache();void EnsureEventCacheLoaded(uint32);
};
''' + methods + r'''
int main(){
 for(const char* payload : {static_cast<const char*>(nullptr),"","talent'\\link"}) {
  CharacterDatabase.rows={{{"login"},{"1"},{"1700000000"},{"90"},{payload}}};
  RandomPlayerbotMgr lazy;lazy.EnsureEventCacheLoaded(42);
  auto e=lazy.eventCache.at(42).at("login");assert(e.value==1&&e.lastChangeTime==1700000000&&e.validIn==90&&e.data==(payload?payload:""));
  int reads=CharacterDatabase.reads;lazy.EnsureEventCacheLoaded(42);assert(CharacterDatabase.reads==reads);
  CharacterDatabase.rows={{{"42"},{"login"},{"1"},{"1700000000"},{"90"},{payload}},{{"43"},{"init"},{"1"},{"1700000001"},{"0"},{nullptr}}};
  RandomPlayerbotMgr bulk;bulk.PrimeEventCache();assert(bulk.eventCachePrimed&&bulk.eventCache.size()==2);
  auto b=bulk.eventCache.at(42).at("login");assert(b.value==e.value&&b.lastChangeTime==e.lastChangeTime&&b.validIn==e.validIn&&b.data==e.data);
  assert(bulk.eventCache.at(43).at("init").data.empty());reads=CharacterDatabase.reads;bulk.EnsureEventCacheLoaded(42);assert(CharacterDatabase.reads==reads);
 }
 CharacterDatabase.rows.clear();RandomPlayerbotMgr empty;empty.PrimeEventCache();assert(!empty.eventCachePrimed&&empty.eventCache.empty());
 puts("PASS actual bulk/lazy event loaders: SQL NULL, empty/nonempty payloads, values/timers preserved, cached rereads and empty store");
}
'''
from turtle_cpp_fixture import run
run(code)
