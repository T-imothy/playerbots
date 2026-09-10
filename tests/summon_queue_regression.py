"""Compile the actual summon queue cleanup for all expansion APIs."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
body=block((root/'playerbot/strategy/actions/UseMeetingStoneAction.cpp').read_text(),'void SummonAction::CancelAutonomousQueues(')
code=r'''
#include <cassert>
#include <cstdint>
#include <vector>
using uint32=uint32_t;using uint8=uint8_t;using uint16=uint16_t;
using ObjectGuid=uint32;using BattleGroundQueueTypeId=int;using BattleGroundTypeId=int;
constexpr int PLAYER_CLIENT_LEAVE=1,LFG_STATE_NONE=0,PLAYER_MAX_BATTLEGROUND_QUEUES=3,BATTLEGROUND_QUEUE_NONE=0,CMSG_BATTLEFIELD_PORT=1;
struct WorldPacket{std::vector<unsigned> values;WorldPacket(int,int){}template<class T>WorldPacket& operator<<(T x){values.push_back(x);return *this;}};
struct LFGQueue{unsigned removed=0,leader=0;void RemovePlayerFromQueue(ObjectGuid g,int){removed=g;}void StopLookingForGroup(ObjectGuid l,ObjectGuid p){leader=l;removed=p;}
 void RemoveFromQueue(ObjectGuid g){removed=g;}LFGQueue& GetMessager(){return *this;}template<class F>void AddMessage(F f){f(this);}};
struct World{LFGQueue queue;LFGQueue& GetLFGQueue(){return queue;}}sWorld;
struct BattleGround{unsigned GetMapId(){return 489;}};
struct Mgr{BattleGround bg;bool available=true;int BgTemplateId(int q){return q;}int BgArenaType(int){return 3;}BattleGround* GetBattleGroundTemplate(int){return available?&bg:nullptr;}}sBattleGroundMgr;
struct Session{std::vector<std::vector<unsigned>> packets;void HandleBattlefieldPortOpcode(WorldPacket& p){packets.push_back(p.values);}};
struct Lfg{int state=5;void SetState(int s){state=s;}};
struct Player{bool grouped=true,inbg=true;int queues[3]={1,2,0};Session session;Lfg lfg;ObjectGuid GetObjectGuid(){return 42;}
 void* GetGroup(){return grouped?this:nullptr;}Lfg& GetLfgData(){return lfg;}int GetBattleGroundQueueTypeId(int s){return queues[s];}
 bool InBattleGround(){return inbg;}int GetBattleGroundTypeId(){return 1;}Session* GetSession(){return &session;}};
struct SummonAction{Player* bot;void CancelAutonomousQueues();};
__BODY__
int main(){Player p;SummonAction action{&p};action.CancelAutonomousQueues();assert(sWorld.queue.removed==42&&p.grouped&&p.lfg.state==5);
 assert(p.session.packets.size()==1);auto const& packet=p.session.packets[0];
#ifdef MANGOSBOT_ZERO
 assert(packet.size()==2&&packet[0]==489&&packet[1]==0);
#elif defined(MANGOSBOT_ONE)
 assert(sWorld.queue.leader==42);assert(packet.size()==5&&packet[0]==3&&packet[2]==2&&packet.back()==0);
#else
 assert(packet.size()==5&&packet[0]==3&&packet[2]==2&&packet.back()==0);p.grouped=false;action.CancelAutonomousQueues();assert(p.lfg.state==0);
#endif
 p.session.packets.clear();p.queues[1]=0;action.CancelAutonomousQueues();assert(p.session.packets.empty());
}
'''.replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='mantech-summon-queues-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 for macro in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/D'+macro,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
  print('PASS:',macro,'native cleanup body: own queue only, active BG preserved, correct leave packet')
