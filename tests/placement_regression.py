"""Run actual relocation scheduling bodies and dense-area occupancy counting."""
import subprocess
import tempfile
from pathlib import Path
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
manager=(root/'playerbot/RandomPlayerbotMgr.cpp').read_text()
rpg=block(manager,'bool RandomPlayerbotMgr::RandomTeleportForRpg(Player* bot, bool activeOnly)')
strategy=block(manager,'bool RandomPlayerbotMgr::ChangeStrategy(Player* player)')
choose=(root/'playerbot/strategy/actions/ChooseRpgTargetAction.cpp').read_text()
crowd=block(choose,'if (!ai->HasRealPlayerMaster())')
assert 'possiblePlayers.size() < 200' not in choose
code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include <unordered_map>
using uint32=uint32_t;
using ObjectGuid=uint32;using GuidPosition=uint32;
enum {ALLIANCE=0, MINUTE=60, IN_MILLISECONDS=1000};
enum class TravelStatus {TRAVEL_STATUS_COOLDOWN};
struct TravelTarget {int statuses=0,expires=0;void SetStatus(TravelStatus){++statuses;}void SetExpireIn(int t){expires=t;}} travelTarget;
struct AiObjectContext {GuidPosition target=12;template<class T> struct Value {T value;T Get(){return value;}};template<class T>Value<T>* GetValue(const char*){static Value<T> v;v.value=target;return &v;}};
struct Player;
struct PlayerbotAI {bool realMaster=false;AiObjectContext context;bool HasRealPlayerMaster(){return realMaster;}bool IsSafe(Player*){return true;}AiObjectContext* GetAiObjectContext(){return &context;}};
struct Player {uint32 id=1;PlayerbotAI ai;uint32 GetGUIDLow(){return id;}int getRace(){return 1;}int GetLevel(){return 60;}int GetTeam(){return 0;}const char* GetName(){return "bot";}PlayerbotAI* GetPlayerbotAI(){return &ai;}};
struct ObjectMgr {std::map<uint32,Player*> players;Player* GetPlayer(uint32 id){return players.at(id);}} sObjectMgr;
struct TravelMgr {int clears=0;void SetNullTravelTarget(TravelTarget*){++clears;}} sTravelMgr;
#define AI_VALUE(type,key) (&::travelTarget)
struct Config {float randomBotRpgChance=0;} sPlayerbotAIConfig;
struct Log {template<class... T>void outDetail(T...){} } sLog;
int roll=100;int urand(int,int){return roll;}
struct RandomPlayerbotMgr {
    std::map<int,std::map<int,std::vector<int>>> rpgLocsCacheLevel;
    std::vector<int> players;
    bool outcome=false;int refreshes=0,schedule=-1;
    bool RandomTeleport(Player*,std::vector<int>&,bool,bool){return outcome;}
    bool RandomTeleportForLevel(Player*,bool){return outcome;}
    void Refresh(Player*){++refreshes;}
    void ScheduleTeleport(uint32,int delay=0){schedule=delay;}
    bool RandomTeleportForRpg(Player*,bool);
    bool ChangeStrategy(Player*);
};
__RPG__
__STRATEGY__
std::unordered_map<ObjectGuid,uint32> countCrowd(Player* bot,std::vector<ObjectGuid>& possiblePlayers){
    PlayerbotAI* ai=bot->GetPlayerbotAI();
    std::unordered_map<ObjectGuid,uint32> rpgOccupancy;
    __CROWD__
    return rpgOccupancy;
}
int main(){
    Player bot;RandomPlayerbotMgr mgr;
    assert(!mgr.RandomTeleportForRpg(nullptr,false));
    assert(!mgr.RandomTeleportForRpg(&bot,false));
    assert(mgr.refreshes==0 && sTravelMgr.clears==0 && travelTarget.statuses==0);
    mgr.outcome=true;assert(mgr.RandomTeleportForRpg(&bot,false));
    assert(mgr.refreshes==1 && sTravelMgr.clears==1 && travelTarget.expires==600000);
    mgr.outcome=false;roll=100;assert(!mgr.ChangeStrategy(&bot));assert(mgr.schedule==60);
    mgr.outcome=true;assert(mgr.ChangeStrategy(&bot));assert(mgr.schedule==0);
    mgr.outcome=false;roll=0;assert(!mgr.ChangeStrategy(&bot));assert(mgr.schedule==60);
    mgr.outcome=true;assert(mgr.ChangeStrategy(&bot));assert(mgr.schedule==0);
    std::vector<Player> players(300);std::vector<ObjectGuid> ids;
    for(uint32 i=0;i<players.size();++i){players[i].id=i+10;sObjectMgr.players[i+10]=&players[i];ids.push_back(i+10);}
    auto counts=countCrowd(&bot,ids);assert(counts[12]==300);
    ids.resize(200);counts=countCrowd(&bot,ids);assert(counts[12]==200);
    ids.resize(199);counts=countCrowd(&bot,ids);assert(counts[12]==199);
    bot.ai.realMaster=true;assert(countCrowd(&bot,ids).empty());
    std::cout<<"PASS: actual relocation outcomes, retry scheduling and crowd counts at 199/200/300\n";
}
'''.replace('__RPG__',rpg).replace('__STRATEGY__',strategy).replace('__CROWD__',crowd)
with tempfile.TemporaryDirectory(prefix='mantech-placement-') as tmp:
    tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W3','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
