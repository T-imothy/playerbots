from pathlib import Path
source=(Path(__file__).resolve().parents[1]/'playerbot/RandomPlayerbotFactory.cpp').read_text(encoding='utf-8')
a=source.index('RandomPlayerbotFactory::RandomPlayerbotFactory(')
b=source.index('bool RandomPlayerbotFactory::isAvailableRole(',a)
code='''#include <map>
#include <vector>
#include <algorithm>
#include <cassert>
#include <thread>
#include <cstdio>
#include <cstdint>
using uint8=uint8_t; using uint32=uint32_t;
constexpr int MAX_CLASSES=12, MAX_RACES=11;
struct ObjectMgr {
 std::map<std::pair<int,int>,int> valid;
 const int* GetPlayerInfo(int race,int cls) const {
  auto i=valid.find({race,cls});return i==valid.end()?nullptr:&i->second;
 }
} sObjectMgr;
class RandomPlayerbotFactory {
 uint32 accountId;
public:
 static std::map<uint8,std::vector<uint8>> availableRaces;
 RandomPlayerbotFactory(uint32);
 static bool isAvailableRace(uint8,uint8);
};
std::map<uint8,std::vector<uint8>> RandomPlayerbotFactory::availableRaces;
'''+source[a:b]+'''
int main(){
 const std::vector<std::pair<int,int>> native={{1,1},{6,5},{3,8},{2,8},{5,3},{7,3},{3,9},{8,9},{9,1},{10,2}};
 for(auto pair:native)sObjectMgr.valid[pair]=1;
 std::vector<std::thread> threads;
 for(int i=0;i<8;++i)threads.emplace_back([](){for(int n=0;n<600;++n){
  RandomPlayerbotFactory factory(n);
  assert(RandomPlayerbotFactory::isAvailableRace(8,2));
  assert(!RandomPlayerbotFactory::isAvailableRace(6,1));
 }});
 for(auto& thread:threads)thread.join();
 size_t count=0;for(auto& entry:RandomPlayerbotFactory::availableRaces)count+=entry.second.size();
 assert(count==native.size());
 for(auto pair:native)assert(RandomPlayerbotFactory::isAvailableRace(pair.second,pair.first));
 assert(!RandomPlayerbotFactory::isAvailableRace(255,255));
 assert(!RandomPlayerbotFactory::isAvailableRace(0,0));
 puts("PASS: native Turtle combinations, rejected unsupported pairs, repeated and concurrent factory construction without roster duplication.");
}
'''
import tempfile, subprocess, shutil
with tempfile.TemporaryDirectory(prefix='turtle-race-pool-') as folder:
    folder=Path(folder)
    cpp=folder/'race-pool.cpp'; cpp.write_text(code,encoding='utf-8')
    cl=shutil.which('cl')
    if cl:
        exe=folder/'race-pool.exe'
        command=[cl,'/nologo','/std:c++17','/EHsc','/MD','/O2',str(cpp),'/Fe'+str(exe),'/Fo'+str(folder/'race-pool.obj')]
    else:
        compiler=shutil.which('c++')
        if not compiler: raise SystemExit('Run in a C++ compiler environment (Visual Studio Developer PowerShell on Windows).')
        exe=folder/'race-pool'
        command=[compiler,'-std=c++17','-pthread',str(cpp),'-o',str(exe)]
    subprocess.run(command,check=True,cwd=folder)
    subprocess.run([str(exe)],check=True)
