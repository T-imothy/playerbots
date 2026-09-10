"""Compile the actual convenience teleport and post-ACK revival bodies against controlled state."""
import subprocess
import tempfile
from pathlib import Path
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/actions/UseMeetingStoneAction.cpp').read_text()
inn = block(source, 'bool SummonAction::SummonUsingNpcs(')
for forbidden in ('SendSpellCooldown', 'IsSpellReady', 'HasItemCount', '8690', '6948'):
    assert forbidden not in inn, forbidden
assert 'player->isRealPlayer()' in inn
ai_source = (root / 'playerbot/PlayerbotAI.cpp').read_text()
code = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <string>
#include <iostream>
using uint32=uint32_t;
constexpr double M_PI=3.141592653589793;
enum class BotState {BOT_STATE_NON_COMBAT};
struct Session {bool logout=false;bool isLogingOut(){return logout;}};
struct Motion {int clears=0;void Clear(){++clears;}void MovementExpired(){}};
struct Player;
struct Map {bool allowed=true,instanceable=true;bool CanEnter(Player*){return allowed;}bool Instanceable(){return instanceable;}};
struct Player {
 bool world=true,real=false,teleporting=false,transport=false,taxi=false,combat=false,charmed=false,alive=true;
 bool accepted=true,los=true;uint32 mapId=0,instanceId=0;float x=0,y=0,z=0;int teleports=0,resurrections=0,bones=0;
 Session session;Motion motion;Map* map=nullptr;
 bool isRealPlayer(){return real;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return teleporting;}
 Session* GetSession(){return &session;}bool GetTransport(){return transport;}bool IsTaxiFlying(){return taxi;}
 bool InBattleGround(){return false;}
 bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}bool IsAlive(){return alive;}
 uint32 GetMapId(){return mapId;}uint32 GetInstanceId(){return instanceId;}Map* GetMap(){return map;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return 0.4f;}
 void UpdateGroundPositionZ(float,float,float&){}float GetCollisionHeight(){return 2;}
 bool IsWithinLOS(float,float,float,bool){return los;}void ResurrectPlayer(float,bool){++resurrections;alive=true;}
 void SpawnCorpseBones(){++bones;}bool TaxiFlightInterrupt(){bool was=taxi;taxi=false;return was;}
 void OnTaxiFlightEject(){taxi=false;}void BreakCharmIncoming(){charmed=false;}void BreakCharmOutgoing(){}
 void InterruptNonMeleeSpells(bool){}Motion* GetMotionMaster(){return &motion;}
 bool TeleportTo(uint32,float,float,float,float){++teleports;teleporting=accepted;return accepted;}
 bool IsWithinDist3d(float a,float b,float c,float r){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c))<=r;}
};
struct PositionEntry {PositionEntry(float,float,float,uint32){}};
int positionWrites=0;
#define SET_AI_VALUE2(type,name,key,value) (++positionWrites)
struct PlayerbotAI {
 Player* bot;bool safe=true,stay=true;
 struct PendingSummonRevival {bool active=false;uint32 mapId=0,instanceId=0;float x=0,y=0,z=0;time_t expires=0;} pendingSummonRevival;
 bool IsRealPlayer(){return bot->real;}bool IsSafe(Player*){return safe;}float GetRange(const char*){return 0;}
 void ChangeStrategy(const char*,BotState){}
 template<class... Args> void TellPlayerNoFacing(Args...){}
 bool HasStrategy(const char*,BotState){return stay;}
 void QueueSummonRevival(uint32,float,float,float,uint32=0);void CompleteSummonRevival();
};
struct Config {bool recruitmentRevive=true;} sPlayerbotAIConfig;
struct Facade {bool UnitIsDead(Player* p){return !p->alive;}bool IsAlive(Player* p){return p->alive;}} sServerFacade;
struct SummonAction {Player* bot;PlayerbotAI* ai;float GetFollowAngle(){return 0;}bool Teleport(Player*,Player*,Player*);static void CancelAutonomousQueues(Player*){};};
__TELEPORT__
__QUEUE__
__COMPLETE__
int main(){
 Map from,to;Player bot,leader;PlayerbotAI ai{&bot};SummonAction action{&bot,&ai};
 auto reset=[&](){from={};to={};bot=Player{};leader=Player{};bot.map=&from;leader.map=&to;leader.mapId=1;leader.real=true;ai.safe=true;ai.pendingSummonRevival={};positionWrites=0;sPlayerbotAIConfig.recruitmentRevive=true;};
 auto reject=[&](){assert(!action.Teleport(&leader,&leader,&bot));assert(bot.motion.clears==0 && positionWrites==0 && bot.resurrections==0);};
 reset();assert(action.Teleport(&leader,&leader,&bot));assert(bot.teleports==1 && bot.motion.clears==1 && positionWrites==2);
 reset();bot.accepted=false;reject();assert(bot.teleports==1);
 reset();bot.alive=false;bot.accepted=false;reject();assert(!ai.pendingSummonRevival.active);
 reset();bot.real=true;reject();
 reset();bot.teleporting=true;reject();
 reset();leader.teleporting=true;reject();
 reset();bot.combat=true;assert(action.Teleport(&leader,&leader,&bot));assert(bot.teleports==1);
 reset();leader.combat=true;assert(action.Teleport(&leader,&leader,&bot));assert(leader.combat);
 reset();bot.combat=true;leader.combat=true;leader.mapId=0;leader.map=&from;
 assert(action.Teleport(&leader,&leader,&bot));assert(bot.teleports==1&&leader.combat);
 reset();bot.combat=true;bot.accepted=false;reject();assert(bot.teleports==1);
 reset();bot.charmed=true;assert(action.Teleport(&leader,&leader,&bot)&&!bot.charmed);
 reset();bot.transport=true;assert(action.Teleport(&leader,&leader,&bot));
 reset();leader.transport=true;reject();
 reset();bot.taxi=true;assert(action.Teleport(&leader,&leader,&bot)&&!bot.taxi);
 reset();bot.session.logout=true;reject();
 reset();leader.world=false;reject();
 reset();to.allowed=false;reject();
 reset();leader.mapId=0;reject(); // Same numeric map, different instance.
 reset();leader.mapId=0;to.instanceable=false;assert(action.Teleport(&leader,&leader,&bot)); // Internal continent partitions.
 reset();leader.mapId=0;leader.map=&from;from.allowed=false;
 assert(action.Teleport(&leader,&leader,&bot)); // Already admitted to this map.
 reset();leader.los=false;reject();
 reset();bot.alive=false;ai.safe=false;assert(action.Teleport(&leader,&leader,&bot)); // Different source map does not prevent summon/revival request.
 reset();bot.alive=false;assert(action.Teleport(&leader,&leader,&bot));
 assert(bot.resurrections==0 && ai.pendingSummonRevival.active);
 bot.teleporting=false;bot.mapId=1;ai.CompleteSummonRevival();
 assert(bot.resurrections==1 && bot.bones==1 && !ai.pendingSummonRevival.active);
 ai.CompleteSummonRevival();assert(bot.resurrections==1);
 reset();bot.alive=false;ai.QueueSummonRevival(1,0,0,0);ai.CompleteSummonRevival();assert(bot.resurrections==0);
 reset();bot.alive=false;ai.QueueSummonRevival(0,0,0,0);ai.pendingSummonRevival.expires=0;
 ai.CompleteSummonRevival();assert(bot.resurrections==0);
 reset();bot.alive=false;ai.QueueSummonRevival(0,0,0,0);bot.x=50;ai.CompleteSummonRevival();assert(bot.resurrections==0);
 reset();bot.alive=false;ai.QueueSummonRevival(0,0,0,0);bot.teleporting=true;ai.CompleteSummonRevival();assert(bot.resurrections==0);
 reset();bot.alive=false;sPlayerbotAIConfig.recruitmentRevive=false;assert(action.Teleport(&leader,&leader,&bot)&&ai.pendingSummonRevival.active);
 reset();bot.alive=false;ai.QueueSummonRevival(0,0,0,0,7);ai.CompleteSummonRevival();assert(bot.resurrections==0);
 reset();bot.alive=false;from.instanceable=false;ai.QueueSummonRevival(0,0,0,0,7);ai.CompleteSummonRevival();assert(ai.pendingSummonRevival.active&&!bot.alive);bot.instanceId=7;ai.CompleteSummonRevival();assert(bot.alive&&!ai.pendingSummonRevival.active);
 reset();bot.alive=false;bot.instanceId=7;ai.QueueSummonRevival(0,0,0,0,7);ai.CompleteSummonRevival();assert(bot.resurrections==1);
 std::cout<<"PASS: convenience summon and post-ACK revival, combat and controlled scenarios; inn hearth independence\n";
}
'''.replace('__TELEPORT__', block(source, 'bool SummonAction::Teleport(')).replace(
    '__QUEUE__', block(ai_source, 'void PlayerbotAI::QueueSummonRevival(')).replace(
    '__COMPLETE__', block(ai_source, 'void PlayerbotAI::CompleteSummonRevival('))
with tempfile.TemporaryDirectory(prefix='mantech-convenience-summon-') as tmp:
    tmp = Path(tmp)
    (tmp / 'test.cpp').write_text(code)
    subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/W3', 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
    subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
