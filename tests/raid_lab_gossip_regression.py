"""Native-menu fixture contract; this does not certify Nefarian mechanics."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <vector>
#include <iostream>
using uint32=unsigned;
struct Guid{unsigned id=10162;unsigned GetRawValue(){return id;}};
struct Creature{Guid GetObjectGuid(){return {};}};
constexpr unsigned UNIT_NPC_FLAG_GOSSIP=1,CMSG_GOSSIP_HELLO=2,CMSG_GOSSIP_SELECT_OPTION=3;
struct WorldPacket{unsigned opcode;std::vector<unsigned> data;WorldPacket(unsigned op):opcode(op){}
 WorldPacket&operator<<(Guid g){data.push_back(g.id);return *this;}
 WorldPacket&operator<<(unsigned v){data.push_back(v);return *this;}};
struct Menu{unsigned expected=1001;bool missing=false,coded=false,wrongSender=false;
 unsigned MenuItemCount(){return 2;}unsigned MenuItemAction(unsigned i){return i==0||missing?999:expected;}
 unsigned MenuItemSender(unsigned){return wrongSender?2:1;}bool MenuItemCoded(unsigned){return coded;}};
struct PlayerMenu{Menu menu;unsigned clears=0;void ClearMenus(){++clears;}Menu&GetGossipMenu(){return menu;}};
struct Session{PlayerMenu*p;unsigned hello=0,select=0;bool stopAtSecond=false;
 void HandleGossipHelloOpcode(WorldPacket&pck){assert(pck.opcode==CMSG_GOSSIP_HELLO&&pck.data==std::vector<unsigned>{10162});++hello;}
 void HandleGossipSelectOptionOpcode(WorldPacket&pck){assert(pck.opcode==CMSG_GOSSIP_SELECT_OPTION);assert((pck.data==std::vector<unsigned>{10162,1}));++select;++p->menu.expected;if(stopAtSecond&&select==1)p->menu.missing=true;}};
struct Player{bool interact=true;PlayerMenu menu;Session session{&menu};
 Creature*GetNPCIfCanInteractWith(Guid,unsigned flag){assert(flag==UNIT_NPC_FLAG_GOSSIP);static Creature npc;return interact?&npc:nullptr;}
 PlayerMenu*GetPlayerMenu(){return &menu;}Session*GetSession(){return &session;}};
namespace RaidLab{unsigned events=0;void Event(Player*,const char*,unsigned,unsigned){++events;}}
'''
code+=block(source,'bool RaidLabGossip(')
code+=block(source,'bool RaidLabRoomTrash(')
code+=r'''
int main(){
 for(unsigned entry:{12458,12468,14022,14023,14024,14025})assert(RaidLabRoomTrash(469,entry));
 for(unsigned entry:{12017,12435,13020,11983,14601,11981,14020,11583,10162,12459})assert(!RaidLabRoomTrash(469,entry));
 for(unsigned entry:{15325,15327})assert(RaidLabRoomTrash(509,entry));
 for(unsigned entry:{15369,15555,15546,15934,15370,15514})assert(!RaidLabRoomTrash(509,entry));
 for(unsigned entry:{14880,14881,14532,11388,11350,11361})assert(RaidLabRoomTrash(309,entry));
 for(unsigned entry:{14510,15041,14509,11347,11348,15068,11391,11382,15117})assert(!RaidLabRoomTrash(309,entry));
 for(unsigned entry:{15974,15975,15976,15977,15978,15979,15980,15981,16025,16056,16057}) {
  assert(RaidLabRoomTrash(533,entry));assert(!RaidLabRoomTrash(409,entry));
 }
 for(unsigned entry:{15956,15953,15952,15931,15936,16290,16363,16236,16505,16506,16573,16486,17055,15384,16803,16218,17293})
  assert(!RaidLabRoomTrash(533,entry)); // encounter adds and native hazard/phase triggers retained
 for(unsigned entry:{11658,11659,11665,11666,11667,11668,11669,11671,11673,12076,12100,12101}) {
  assert(RaidLabRoomTrash(409,entry));assert(!RaidLabRoomTrash(469,entry));
 }
 for(unsigned entry:{12057,12056,11982,11988,12099,11672,12119,11661,11662,11663,11664,11502,12018})
  assert(!RaidLabRoomTrash(409,entry)); // every boss and native encounter add retained
 for(unsigned entry:{15233,15247})assert(RaidLabRoomTrash(531,entry));
 for(unsigned entry:{15511,15543,15544,15621,15933,15263,15510,15509})assert(!RaidLabRoomTrash(531,entry));
 Creature npc;Player p;
 assert(!RaidLabGossip(&p,nullptr,3));p.interact=false;assert(!RaidLabGossip(&p,&npc,3));assert(p.session.hello==0);
 p.interact=true;p.menu.menu.missing=true;assert(!RaidLabGossip(&p,&npc,3));assert(p.session.select==0);
 p.menu.menu.missing=false;p.menu.menu.coded=true;assert(!RaidLabGossip(&p,&npc,3));assert(p.session.select==0);
 p.menu.menu.coded=false;p.menu.menu.wrongSender=true;assert(!RaidLabGossip(&p,&npc,3));assert(p.session.select==0);
 p.menu.menu.wrongSender=false;p.session.stopAtSecond=true;
 assert(!RaidLabGossip(&p,&npc,3)&&p.session.select==1); // never invent a missing next choice
 Player good;assert(RaidLabGossip(&good,&npc,3));assert(good.session.hello==1&&good.session.select==3);
 assert(good.menu.clears==1&&good.menu.menu.expected==1004);
 std::cout<<"PASS native gossip menu indices, interaction/sender/code guards and missing-step refusal\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-gossip-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode()
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
