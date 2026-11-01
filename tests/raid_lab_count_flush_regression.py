"""Exercise actual bounded AI counter flushing; a lossless flush is not a gap."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'classic/src/game/World/RaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <mutex>
#include <string>
#include <tuple>
#include <vector>
#include <iostream>
using uint32=uint32_t;using uint64=uint64_t;
struct Map{};struct Guid{uint64 GetRawValue(){return 1;}};
struct Unit{bool world=true;Map map;bool IsInWorld(){return world;}uint32 GetMapId(){return 409;}Map*GetMap(){return &map;}Guid GetObjectGuid(){return {};}uint32 GetEntry(){return 0;}};
struct Bucket{uint64 count=0,first=0,last=0;};
struct Attempt{std::map<std::tuple<uint64,uint32,std::string,uint32,uint32,uint64>,Bucket>counts;uint64 start=0;};
Attempt attempt;std::recursive_mutex guard;std::vector<std::string> rows;
bool Enabled(){return true;}bool AllowedMap(uint32 m){return m==409;}
Attempt*Find(Map*){return &attempt;}uint64 Clock(){static uint64 tick=0;return ++tick;}
std::string Quote(const std::string&s){return '"'+s+'"';}
void Write(Attempt&,const std::string&s){rows.push_back(s);}
__FLUSH__
__COUNT__
int main(){Unit unit;
 for(unsigned id=0;id<4096;++id)Count(&unit,"action",id,1,0);
 assert(attempt.counts.size()==4096&&rows.empty());
 for(unsigned i=0;i<4;++i)Count(&unit,"action",99,1,0);
 assert(attempt.counts.size()==1);FlushCounts(attempt);
 uint64 total=0;unsigned flushes=0;
 for(const auto&row:rows){
  assert(row.find("coverage_gap")==std::string::npos);
  if(row.find("ai_bucket_flush")!=std::string::npos){++flushes;continue;}
  const auto count=row.find("\"count\":");assert(count!=std::string::npos);
  total+=std::stoull(row.substr(count+8));
 }
 assert(total==4100&&flushes==1&&attempt.counts.empty());
 std::cout<<"PASS bounded counter flush preserves every count and distinguishes pressure from data loss\n";
}
'''.replace('__FLUSH__',block(source,'void FlushCounts(')).replace('__COUNT__',block(source,'void Count('))
with tempfile.TemporaryDirectory(prefix='raid-count-flush-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
