"""Exercise the merged teleport acknowledgement body against controlled map lifetimes."""
from pathlib import Path
import subprocess, tempfile, sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from behavior_regression import block
method=block((root/'playerbot/PlayerbotAI.cpp').read_text(),'void PlayerbotAI::HandleTeleportAck()')
code=r'''
#include <atomic>
#include <cassert>
#include <ctime>
#include <iostream>
#include <string>
using uint32=unsigned;
enum {MSG_MOVE_TELEPORT_ACK,MOVEFLAG_NONE};
struct WorldPacket {WorldPacket(int,int){} template<class T> WorldPacket& operator<<(T){return *this;}};
struct Guid {int WriteAsPacked(){return 0;}};
struct WorldLocation {uint32 mapid=1;};
struct MapEntry {bool bg=false; bool IsBattleGround()const{return bg;}};
struct Maps {MapEntry entry;const MapEntry* LookupEntry(unsigned){return &entry;}}sMapStore;
struct MapMgr {bool exists=true;void* FindMap(unsigned,unsigned){return exists?this:nullptr;}}sMapMgr;
struct Log {template<class... T> void outError(T...){}}sLog;
unsigned urand(unsigned a,unsigned){return a;}
struct Player;
struct MovementGenerator {void Interrupt(Player&){} };
struct Motion {int clears=0,idles=0;MovementGenerator generator;bool empty(){return false;}
 MovementGenerator* top(){return &generator;}void Clear(bool,bool){++clears;}void MoveIdle(){++idles;}};
struct Session {int near=0,far=0;void HandleMoveTeleportAckOpcode(WorldPacket&){++near;}
 void HandleMoveWorldportAckOpcode(){++far;}};
struct MovementInfo {int flags=99;void SetMovementFlags(int n){flags=n;}};
struct Player {bool near=false,far=false,transport=false;unsigned bg=7;WorldLocation dest;Motion motion;Session session;MovementInfo m_movementInfo;int stops=0,hearts=0;
 bool IsBeingTeleportedFar(){return far;}bool IsBeingTeleportedNear(){return near;}
 Motion* GetMotionMaster(){return &motion;}Session* GetSession(){return &session;}
 Guid GetObjectGuid(){return {};}const WorldLocation& GetTeleportDest(){return dest;}
 unsigned GetBattleGroundId(){return bg;}const char* GetName(){return "test";}
 void SetSemaphoreTeleportFar(bool value){far=value;}void SendHeartBeat(){++hearts;}
 void InterruptMoving(bool){++stops;}bool GetTransport(){return transport;}};
struct LastMovement {int clears=0;void clear(){++clears;}};
struct Value {LastMovement movement;LastMovement& Get(){return movement;}};
struct Context {Value movement,trigger;template<class T>Value* GetValue(const char* n){return std::string(n)=="last movement"?&movement:&trigger;}};
struct PlayerbotAI {Player* bot;Context* aiObjectContext;bool real=false;std::atomic<unsigned> transitionGeneration{0};std::atomic<bool>urgentTransitionPending{true};
 int pendingClears=0,stops=0,resets=0,revivals=0,delay=0;
 bool IsRealPlayer(){return real;}void ClearPendingTransition(){++pendingClears;}void StopMoving(){++stops;}
 void SetAIInternalUpdateDelay(unsigned n){delay=n;}void Reset(){++resets;}void CompleteSummonRevival(){++revivals;}
 void HandleTeleportAck();};
__METHOD__
void run(bool bg,bool exists,unsigned bgId,bool near,bool real,bool transport){
 sMapStore.entry.bg=bg;sMapMgr.exists=exists;Player bot;Context ctx;PlayerbotAI ai{&bot,&ctx};
 bot.near=near;bot.far=!near;bot.bg=bgId;bot.transport=transport;ai.real=real;
 ai.HandleTeleportAck();
 if(real&&!near){assert(ai.transitionGeneration==0&&bot.session.far==0&&ai.resets==0);return;}
 assert(ai.transitionGeneration==1&&!ai.urgentTransitionPending&&ai.pendingClears==1);
 if(!near&&bg&&(!exists||!bgId)){
   assert(!bot.far&&bot.session.far==0&&ai.resets==1&&ai.revivals==0);return;
 }
 assert(ai.resets==1&&ai.revivals==1);
 if(near){assert(bot.session.near==1&&bot.session.far==0&&ctx.movement.movement.clears==0);}
 else {assert(bot.session.far==1&&bot.stops==1&&bot.motion.clears==1&&bot.motion.idles==1);
   assert(ctx.movement.movement.clears==1&&ctx.trigger.movement.clears==1);
   assert(bot.m_movementInfo.flags==(transport?99:MOVEFLAG_NONE));}
}
int main(){
 run(true,false,7,false,false,false);run(true,true,0,false,false,false);
 run(true,true,7,false,false,false);run(false,false,0,false,false,false);
 run(false,true,0,true,false,false);run(true,false,7,false,true,false);
 run(false,true,0,false,false,true);
 std::cout<<"PASS: missing/live BG, ordinary worldport, near teleport, real-player acknowledgement, transport movement preservation\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='teleport-merge-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
