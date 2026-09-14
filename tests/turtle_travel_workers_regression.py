from pathlib import Path
root=Path(__file__).resolve().parents[1]/'playerbot'
source=(root/'AsyncTravel.cpp').read_text()
source=source.replace('#include "playerbot/playerbot.h"','').replace('#include "AsyncTravel.h"','')
code=r'''
#include <future>
#include <functional>
#include <cassert>
#include <chrono>
#include <vector>
#include <stdexcept>
#include <cstdio>
namespace ai {using PartitionedTravelList=int;void StartPlayerbotTravelWorkers();void StopPlayerbotTravelWorkers();std::future<int> SubmitPlayerbotTravelSearch(std::function<int()>);}
''' + source + r'''
int main(){
 using namespace ai;using namespace std::chrono_literals;
 assert(!SubmitPlayerbotTravelSearch([]{return 1;}).valid());
 StartPlayerbotTravelWorkers();StartPlayerbotTravelWorkers();
 std::promise<void> release;auto gate=release.get_future().share();
 std::atomic<unsigned> running{0},peak{0},finished{0};
 auto work=[&]{unsigned n=++running;unsigned prior=peak.load();while(prior<n&&!peak.compare_exchange_weak(prior,n)){} gate.wait();--running;++finished;return 42;};
 std::vector<std::future<int>> accepted;std::mutex resultsMutex;std::atomic<unsigned> rejected{0};
 std::vector<std::thread> submitters;
 for(int t=0;t<8;++t)submitters.emplace_back([&]{for(int i=0;i<40;++i){auto f=SubmitPlayerbotTravelSearch(work);if(f.valid()){std::lock_guard<std::mutex> lock(resultsMutex);accepted.push_back(std::move(f));}else ++rejected;}});
 for(auto& t:submitters)t.join();
 assert(accepted.size()==128&&rejected==192);
 auto deadline=std::chrono::steady_clock::now()+5s;
 while(running<5&&std::chrono::steady_clock::now()<deadline)std::this_thread::yield();
 assert(running==5&&peak==5);
 // Abandon every future while workers are held. A std::async future would block.
 auto abandoned=std::async(std::launch::async,[&]{accepted.clear();});
 bool nonblocking=abandoned.wait_for(1s)==std::future_status::ready;
 release.set_value();abandoned.get();assert(nonblocking);
 StopPlayerbotTravelWorkers();assert(finished==128&&travelJobs==0&&running==0);
 assert(!SubmitPlayerbotTravelSearch(work).valid());
 StartPlayerbotTravelWorkers();auto failed=SubmitPlayerbotTravelSearch([]()->int{throw std::runtime_error("expected");});
 bool threw=false;try{failed.get();}catch(const std::runtime_error&){threw=true;}assert(threw);
 auto retry=SubmitPlayerbotTravelSearch([]{return 77;});assert(retry.get()==77);
 StopPlayerbotTravelWorkers();StopPlayerbotTravelWorkers();assert(travelJobs==0);
 puts("PASS travel admission under concurrent producers, five-worker bound, nonblocking abandoned futures, shutdown drain, retry and exceptions");
}
'''
import tempfile, subprocess, shutil
with tempfile.TemporaryDirectory(prefix='turtle-integration-') as folder:
    folder=Path(folder)
    cpp=folder/'integration.cpp'; cpp.write_text(code,encoding='utf-8')
    cl=shutil.which('cl')
    if cl:
        exe=folder/'integration.exe'
        command=[cl,'/nologo','/std:c++17','/EHsc','/MD','/O2','/I'+str(Path(__file__).resolve().parents[3]/'src/shared'),str(cpp),'/Fe'+str(exe),'/Fo'+str(folder/'integration.obj')]
    else:
        compiler=shutil.which('c++')
        if not compiler: raise SystemExit('Run in a C++ compiler environment (Visual Studio Developer PowerShell on Windows).')
        exe=folder/'integration'
        command=[compiler,'-std=c++17','-pthread','-I'+str(Path(__file__).resolve().parents[3]/'src/shared'),str(cpp),'-o',str(exe)]
    subprocess.run(command,check=True,cwd=folder)
    subprocess.run([str(exe)],check=True)
