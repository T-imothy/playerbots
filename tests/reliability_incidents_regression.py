"""Exercise actual episode transitions and JSONL writer in a temporary directory."""
from pathlib import Path
import subprocess,tempfile,json
root=Path(__file__).resolve().parents[1]
header=(root/'playerbot/BotIncidentHistory.h').read_text(encoding='utf-8').replace('#include "Common.h"','')
source=(root/'playerbot/BotIncidentHistory.cpp').read_text(encoding='utf-8')
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include "'))
fixture=r'''
#include <string>
#include <array>
#include <vector>
#include <cassert>
#include <iostream>
#include <ctime>
using uint32=unsigned;using uint64=unsigned long long;using uint8=unsigned char;using int64=long long;
'''+header+r'''
namespace ai { struct BotReliabilityState {BotIncidentState incidents;}; }
struct Value {ai::BotReliabilityState value;ai::BotReliabilityState& Get(){return value;} };
struct Context {Value v;template<class T>Value* GetValue(const char*){return &v;} };
struct Player {bool alive=false,moving=false,casting=false,free=true;unsigned map=0,instance=1;float x=0;
 bool IsInWorld(){return true;}bool IsBeingTeleported(){return false;}unsigned GetGUIDLow(){return 7;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 float GetPositionX(){return x;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}
 bool IsAlive(){return alive;}bool IsStopped(){return !moving;}bool IsNonMeleeSpellCasted(bool){return casting;}
 bool CanFreeMove(){return free;}Player* GetVictim(){return nullptr;}bool CanReachWithMeleeAttack(Player*){return false;}
};
struct PlayerbotAI {Player bot;Context context;Player* GetBot(){return &bot;}Context* GetAiObjectContext(){return &context;} };
struct Config {bool incidentHistory=true;} sPlayerbotAIConfig;
struct GlobalConfig {std::string path;std::string GetStringDefault(const char*){return path;} } sConfig;
unsigned clockNow=1000;struct WorldTimer {static unsigned getMSTime(){return clockNow;} };
'''+source+r'''
int main(int argc,char** argv){
 assert(argc==2);sConfig.path=argv[1];PlayerbotAI ai;
 for(unsigned i=0;i<=300;++i){BotIncidentHistory::Sample(&ai);clockNow+=1000;}
 assert(pending.size()==1&&std::string(pending.back().state)=="opened");
 ai.bot.alive=true;BotIncidentHistory::Sample(&ai);clockNow+=1000;
 assert(pending.size()==2&&std::string(pending.back().state)=="resolved");
 for(int i=0;i<=15;++i){BotIncidentHistory::Sample(&ai);BotIncidentHistory::ActionResult(&ai,"test \"spell\"",false);clockNow+=1000;}
 assert(pending.back().kind==BotIncidentKind::ActionLoop&&std::string(pending.back().state)=="opened");
 BotIncidentHistory::ActionResult(&ai,"other",true);assert(State(&ai).episodes[2].active);
 BotIncidentHistory::ActionResult(&ai,"test \"spell\"",true);assert(!State(&ai).episodes[2].active);
 BotIncidentHistory::Unreachable(&ai);
 for(int i=0;i<32;++i){clockNow+=1000;BotIncidentHistory::Sample(&ai);}
 assert(pending.back().kind==BotIncidentKind::Unreachable&&std::string(pending.back().state)=="observation_ended");
 ai.bot.moving=true;
 for(int i=0;i<32;++i){clockNow+=1000;BotIncidentHistory::Sample(&ai);}
 assert(State(&ai).episodes[1].active);
 ai.bot.x=10;clockNow+=1000;BotIncidentHistory::Sample(&ai);assert(!State(&ai).episodes[1].active);
 BotIncidentHistory::Flush();assert(pending.empty());
 sPlayerbotAIConfig.incidentHistory=false;
 BotIncidentHistory::ActionResult(&ai,"disabled",false);BotIncidentHistory::Unreachable(&ai);assert(pending.empty());
 sPlayerbotAIConfig.incidentHistory=true;
 for(int i=0;i<4100;++i)Emit(State(&ai),BotIncidentKind::Unreachable,"opened",clockNow);
 assert(pending.size()==4096&&dropped==4);clockNow+=10000;BotIncidentHistory::Flush();
 std::cout<<"PASS: thresholds, matching recovery, expiry distinction, disabled bypass, JSONL flush and bounded loss accounting\n";
}
'''
with tempfile.TemporaryDirectory(prefix='reliability-incidents-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(fixture,encoding='utf-8')
 result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/UNDEBUG','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 subprocess.run([str(p/'test.exe'),str(p)],check=True)
 records=[json.loads(line) for line in (p/'PlayerbotIncidents.jsonl').read_text().splitlines()]
 assert any(row.get('action')=='test "spell"' for row in records)
 assert records[-1]['dropped_records']==4
 assert all('started_ms' in row for row in records if 'bot' in row)
