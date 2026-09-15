"""Compile actual native-facing pursuit hooks, exercising their exemptions."""
from pathlib import Path
from turtle_cpp_fixture import run
p=Path(__file__).resolve().parents[1]/'playerbot'
s=(p/'BotProgress.cpp').read_text(encoding='utf-8')
body=s[s.index('bool PlayerbotAI::IgnoreUnreachableTarget'):s.index('void PlayerbotAI::RecordBotActionFailure')]
run(r'''
#include "BotProgress.h"
#include <cassert>
#include <cstdio>
using namespace ai;using uint64=uint64_t;using uint32=uint32_t;
constexpr int TYPEID_UNIT=3;
struct Guid {uint64 n=5;uint64 GetRawValue(){return n;}};
struct Unit {int type=TYPEID_UNIT;Guid guid;Unit*victim=nullptr;int GetTypeId(){return type;}Unit*GetVictim(){return victim;}Guid GetObjectGuid(){return guid;}};
struct Player:Unit {bool alive=true,valid=true,transfer=false,taxi=false,transport=false,charm=false,casting=false;uint32 map=0,instance=0;float x=0,y=0;
 uint32 GetMapId(){return map;}uint32 GetInstanceId(){return instance;}uint32 GetGUIDLow(){return 10;}uint32 GetZoneId(){return 12;}
 bool IsAlive(){return alive;}bool IsValidAttackTarget(Unit*){return valid;}bool IsBeingTeleported(){return transfer;}bool IsTaxiFlying(){return taxi;}bool GetTransport(){return transport;}bool HasCharmer(){return charm;}bool IsNonMeleeSpellCasted(bool){return casting;}float GetPositionX(){return x;}float GetPositionY(){return y;}};
struct Config{uint32 unreachableTargetTimeout=15,unreachableTargetRetry=300;}sPlayerbotAIConfig;
struct WorldTimer{static inline uint32 now=0;static uint32 getMSTime(){return now;}};
struct Diagnostics {int events=0;bool enabled=true;bool IncidentsEnabled(){return enabled;}void RecordBotIncident(uint32,BotIncidentKind,bool,uint64,uint32,uint32,uint32,const char*){++events;}}sPlayerbotDiagnostics;
class PlayerbotAI {public:Player*bot;bool master=false;UnreachableTargetMemory unreachableTargets;BotIncidentTracker incidentTracker;uint32 incidentBotGuid=0;bool HasActivePlayerMaster(){return master;}bool IgnoreUnreachableTarget(Unit*);bool ObserveTargetProgress(Unit*,float,bool);};
'''+body+r'''
int main(){Player bot;Unit target;PlayerbotAI ai{&bot};
 for(int reason=0;reason<10;++reason){
  ai.unreachableTargets.Reset();ai.master=reason==0;target.type=reason==1?4:TYPEID_UNIT;target.victim=reason==2?&bot:nullptr;
  bot.alive=reason!=3;bot.valid=reason!=4;bot.transfer=reason==5;bot.taxi=reason==6;bot.transport=reason==7;bot.charm=reason==8;bot.casting=reason==9;
  WorldTimer::now=0;assert(!ai.ObserveTargetProgress(&target,20,false));WorldTimer::now=100;assert(!ai.ObserveTargetProgress(&target,20,false));assert(!ai.IgnoreUnreachableTarget(&target));
 }
 ai.master=false;target.type=TYPEID_UNIT;target.victim=nullptr;bot.alive=bot.valid=true;bot.transfer=bot.taxi=bot.transport=bot.charm=bot.casting=false;
 WorldTimer::now=0;assert(!ai.ObserveTargetProgress(&target,20,false));WorldTimer::now=14;assert(!ai.ObserveTargetProgress(&target,20,true));WorldTimer::now=15;assert(!ai.ObserveTargetProgress(&target,20,false));WorldTimer::now=30;assert(ai.ObserveTargetProgress(&target,20,false));assert(ai.IgnoreUnreachableTarget(&target));assert(sPlayerbotDiagnostics.events==1);
 target.victim=&bot;assert(!ai.IgnoreUnreachableTarget(&target));target.victim=nullptr;ai.master=true;assert(!ai.IgnoreUnreachableTarget(&target));ai.master=false;assert(ai.IgnoreUnreachableTarget(&target));
 ++bot.instance;assert(!ai.IgnoreUnreachableTarget(&target));sPlayerbotDiagnostics.enabled=false;WorldTimer::now=40;assert(!ai.ObserveTargetProgress(&target,20,false));WorldTimer::now=55;assert(ai.ObserveTargetProgress(&target,20,false));assert(sPlayerbotDiagnostics.events==1);
 WorldTimer::now=355;assert(!ai.IgnoreUnreachableTarget(&target));
 puts("PASS actual pursuit hooks: player masters, PvP, self-defense, friendly/dead/controlled/transfer/casting exemptions, LOS reset, map reset and independent diagnostic toggle");
}
''',includes=[p])
