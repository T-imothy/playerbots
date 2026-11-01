"""Exercise the actual lab-only inventory fixture, including replay and refusal.

Does not certify raid mechanics or production acquisition/equipment policy.
"""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <string>
#include <vector>
#include <map>
#include <iostream>
#include <sstream>
using uint32=unsigned;using uint16=unsigned short;
enum class TestResult{PASS,IMPOSSIBLE,PENDING};
constexpr unsigned EQUIP_ERR_CANT_DO_RIGHT_NOW=2;
namespace WorldTimer{unsigned now=100;unsigned getMSTime(){return now;}}
constexpr unsigned NULL_BAG=255,NULL_SLOT=255,EQUIP_ERR_OK=0,EQUIPMENT_SLOT_BACK=14,INVENTORY_SLOT_BAG_0=0,CMSG_AUTOEQUIP_ITEM=42;
using ItemPosCountVec=std::vector<unsigned>;
struct Item{unsigned entry;unsigned GetEntry(){return entry;}unsigned GetBagSlot(){return 0;}unsigned GetSlot(){return 1;}};
struct WorldPacket{unsigned op;std::vector<unsigned> values;WorldPacket(unsigned op):op(op){} WorldPacket&operator<<(unsigned x){values.push_back(x);return *this;}};
struct PlayerbotAI{bool real=false;bool IsRealPlayer(){return real;}};
struct Player;
struct Ref{Player* p;Ref* n=nullptr;Player*getSource(){return p;}Ref*next(){return n;}};
struct Group{Ref*head;Ref*GetFirstMember(){return head;}};
struct Session{Player*p;void HandleAutoEquipItemOpcode(WorldPacket&);};
struct Player{
 unsigned map=469,created=0,equips=0;bool world=true,tp=false,gm=false,space=true,equipAllowed=true,equipWorks=true,aura=false,casting=false;
 bool IsNonMeleeSpellCasted(bool){return casting;}
 PlayerbotAI ai;Group*group=nullptr;std::map<unsigned,unsigned> inventory;Item cloak{15138},old{22960};Item*worn=&old;Session session{this};
 unsigned GetMapId(){return map;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return tp;}bool IsGameMaster(){return gm;}
 Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return &ai;}
 unsigned GetItemCount(unsigned e){return inventory[e];}
 unsigned CanStoreNewItem(unsigned,unsigned,ItemPosCountVec&dest,unsigned e,unsigned n){dest={e,n};return space?0:1;}
 Item*StoreNewItem(ItemPosCountVec&dest,unsigned e,bool update){assert(update&&dest[0]==e);inventory[e]+=dest[1];created+=dest[1];return &cloak;}
 Item*GetItemByEntry(unsigned e){return inventory[e]?&cloak:nullptr;}
 unsigned CanEquipItem(unsigned slot,uint16&,Item*,bool swap){assert(slot==14&&swap);return !equipAllowed?1:casting?EQUIP_ERR_CANT_DO_RIGHT_NOW:0;}
 Item*GetItemByPos(unsigned,unsigned slot){assert(slot==14);return worn;}
 Session*GetSession(){return &session;}bool HasAura(unsigned s){assert(s==22683);return aura;}unsigned GetGUIDLow(){return 1;}
};
void Session::HandleAutoEquipItemOpcode(WorldPacket&pkt){assert(pkt.op==42&&pkt.values==std::vector<unsigned>({0,1}));++p->equips;if(p->equipWorks){p->worn=&p->cloak;p->aura=true;}}
struct TestContext{std::string testName="raidlab_469_14601_leader_prepared";unsigned raidLabProvisionStarted=0;};
namespace RaidLab{bool enabled=true;bool Enabled(){return enabled;}}
bool ready=true;
bool RaidLabPartyReady(Player*,PlayerbotAI*,Player*&,std::string&){return ready;}
struct Logger{template<class...T>void outString(const char*,T...){}}sLog;
struct CommandRaidLabProvision{TestResult Execute(const std::string&,Player*,PlayerbotAI*,TestContext&,std::string&);};
TestResult RaidLabPrepareFrost(Player*,PlayerbotAI*,TestContext&,std::string&){return TestResult::IMPOSSIBLE;}
'''
code+=block(source,'TestResult CommandRaidLabProvision::Execute(')
code+=r'''
int main(){
 Player p;Ref ref{&p};Group group{&ref};p.group=&group;TestContext ctx;std::string message;CommandRaidLabProvision command;
 auto run=[&](){return command.Execute("bwl",&p,&p.ai,ctx,message);};
 RaidLab::enabled=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);RaidLab::enabled=true;
 p.map=409;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.map=469;
 ctx.testName="raidlab_469_14601_leader";assert(run()==TestResult::IMPOSSIBLE&&p.created==0);ctx.testName+="_prepared";
 p.gm=true;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.gm=false;
 p.tp=true;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.tp=false;
 ready=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);ready=true;
 p.ai.real=true;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.ai.real=false;
 p.space=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.space=true;
 p.equipAllowed=false;assert(run()==TestResult::IMPOSSIBLE&&p.equips==0&&p.created==21);p.equipAllowed=true;
 p.casting=true;assert(run()==TestResult::PENDING&&p.equips==0&&p.created==21);
 WorldTimer::now=60100;assert(run()==TestResult::IMPOSSIBLE&&p.equips==0&&p.created==21);
 WorldTimer::now=200;p.casting=false;
 p.equipWorks=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==21&&!p.aura);p.equipWorks=true;
 assert(run()==TestResult::PASS&&p.created==21&&p.aura&&p.worn->entry==15138);
 auto equips=p.equips;assert(run()==TestResult::PASS&&p.created==21&&p.equips==equips);
 std::cout<<"PASS explicit local prepared scope, native inventory/equip refusal, protection verification, bounded replay\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-provision-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
