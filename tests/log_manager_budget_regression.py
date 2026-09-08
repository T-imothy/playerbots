"""Execute production manager loops against deterministic scheduling fixtures."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/RandomPlayerbotMgr.cpp').read_text()
process=s[s.index('    const auto processStart ='):s.index('    uint32 maxLogins =',s.index('    const auto processStart ='))]
memory=s[s.index('    if (!memoryMaintenanceRemaining &&'):s.index('    const uint32 averageWorldDiff',s.index('    if (!memoryMaintenanceRemaining &&'))]
code=r'''
#include <cassert>
#include <cstdint>
#include <vector>
#include <algorithm>
using uint32=uint32_t;using uint64=uint64_t;
namespace std { namespace chrono {
struct milliseconds {long long n;long long count(){return n;}};
static long long clockMs=0;
struct steady_clock {static long long now(){return clockMs;}};
template<class T>T duration_cast(long long n){return {n};}
}}
struct Config {uint32 randomBotManagerScanLimit=512,randomBotManagerBudgetMs=10;} sPlayerbotAIConfig;
struct Logger {template<class... T>void outPerformance(T...){}}sLog;
struct Player {int cleaned=0;Player* GetPlayerbotAI(){return this;}Player* GetAiObjectContext(){return this;}int ClearExpiredValues(){++cleaned;return 1;}};
struct Manager {
 std::vector<uint32> availableBots;std::vector<Player> players;std::vector<int> visits;
 size_t processBotCursor=0,memoryMaintenanceCursor=0,memoryMaintenanceRemaining=0;
 uint64 memoryMaintenanceReleased=0;long long memoryMaintenanceTimer=0;
 int cost=0;bool success=false,online=true;
 Player* GetPlayerBot(uint32 id){return online?&players[id]:nullptr;}
 bool ProcessBot(uint32 id){++visits[id];std::chrono::clockMs+=cost;return success;}
 uint64 PruneExpiredEventCache(long long){return 0;}
 void run(uint32 updateBots=UINT32_MAX){uint32 diagnosticsProcessScans=0,diagnosticsProcessCalls=0;
 PROCESS
 }
 void cleanup(){uint32 memorySoftMb=1,privateMb=2,memoryHardMb=3;long long memoryNow=1000;bool memoryAdmissionPaused=false;
 MEMORY
 }
};
int main(){Manager m;m.players.resize(640);m.visits.resize(640);for(uint32 i=0;i<640;++i)m.availableBots.push_back(i);
 sPlayerbotAIConfig.randomBotManagerScanLimit=8;m.run();assert(m.processBotCursor==8);for(int i=0;i<8;++i)assert(m.visits[i]==1);
 m.cost=20;m.run();assert(m.processBotCursor==9);assert(m.visits[9]==0); // A costly call finishes, then yields.
 m.cost=0;m.success=true;m.run(2);assert(m.processBotCursor==11); // Per-interval quota still honored.
 m.processBotCursor=639;m.run(2);assert(m.processBotCursor==1); // Fair wraparound.
 m.online=false;m.run();assert(m.processBotCursor==9); // Offline scans remain bounded.
 m.online=true;m.cleanup();assert(m.memoryMaintenanceRemaining==512);for(int i=0;i<4;++i)m.cleanup();
 assert(m.memoryMaintenanceRemaining==0&&m.memoryMaintenanceReleased==640);for(auto& p:m.players)assert(p.cleaned==1);
 m.cleanup();for(auto& p:m.players)assert(p.cleaned==1); // No immediate repeat sweep.
 m.availableBots.clear();m.run();m.memoryMaintenanceRemaining=10;m.cleanup();assert(!m.memoryMaintenanceRemaining);
}
'''.replace('PROCESS',process).replace('MEMORY',memory)
with tempfile.TemporaryDirectory(prefix='bot-manager-regression-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('Manager scan/time limits, expensive-call yielding, cursor fairness, incremental cleanup and empty-list cases passed')
