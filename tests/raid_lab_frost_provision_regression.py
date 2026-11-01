"""Actual explicit Sapphiron fixture: native inventory refusal, bounded retry and replay."""
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
using uint32=unsigned;using uint16=unsigned short;using uint8=unsigned char;
enum{CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_ROGUE=4,CLASS_PRIEST=5,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
enum{EQUIPMENT_SLOT_HEAD=0,EQUIPMENT_SLOT_CHEST=4,EQUIPMENT_SLOT_WRISTS=8,EQUIPMENT_SLOT_HANDS=9,EQUIPMENT_SLOT_BACK=14,INVENTORY_SLOT_BAG_0=0,NULL_BAG=255,NULL_SLOT=255,CMSG_AUTOEQUIP_ITEM=42,SPELL_SCHOOL_FROST=4};
enum{EQUIP_ERR_OK=0,EQUIP_ERR_CANT_DO_RIGHT_NOW=2};enum class TestResult{PASS,IMPOSSIBLE,PENDING};
namespace WorldTimer{unsigned now=100;unsigned getMSTime(){return now;}}
namespace RaidLab{bool enabled=true;bool Enabled(){return enabled;}}
struct Player;
struct PlayerbotAI{bool real=false;bool IsRealPlayer(){return real;}bool IsHeal(Player*);};
struct Item{unsigned entry,slot;unsigned GetEntry(){return entry;}uint8 GetBagSlot(){return 0;}uint8 GetSlot(){return slot;}};
using ItemPosCountVec=std::vector<unsigned>;
struct WorldPacket{unsigned op;std::vector<unsigned>v;WorldPacket(unsigned op):op(op){}WorldPacket&operator<<(uint8 n){v.push_back(n);return *this;}};
struct Session{Player*p;void HandleAutoEquipItemOpcode(WorldPacket&);};
struct Ref{Player*p;Ref*n=nullptr;Player*getSource(){return p;}Ref*next(){return n;}};
struct Group{Ref*head;Ref*GetFirstMember(){return head;}};
struct TestContext{std::string testName="raidlab_533_15989_leader_event_prepared";unsigned raidLabProvisionStarted=0;};
struct Player{unsigned map=533,level=60,cls=8,created=0,equips=0;bool world=true,tp=false,gm=false,healer=false,space=true,casting=false,equipAllowed=true,equipWorks=true;
 PlayerbotAI ai;Group*group=nullptr;Session session{this};std::map<unsigned,Item>items;std::map<unsigned,unsigned>worn;std::map<unsigned,unsigned>requested;
 unsigned GetMapId(){return map;}unsigned GetLevel(){return level;}uint8 getClass(){return cls;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return tp;}bool IsGameMaster(){return gm;}
 Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return &ai;}bool IsNonMeleeSpellCasted(bool){return casting;}unsigned GetGUIDLow(){return 1;}unsigned GetResistance(unsigned){return 154;}
 unsigned GetItemCount(unsigned e){return items.count(e);}Item*GetItemByEntry(unsigned e){return items.count(e)?&items.at(e):nullptr;}
 Item*GetItemByPos(unsigned,unsigned slot){return worn.count(slot)?GetItemByEntry(worn[slot]):nullptr;}
 unsigned CanStoreNewItem(unsigned,unsigned,ItemPosCountVec&d,unsigned e,unsigned n){assert(n==1);d={e};return space?0:1;}
 Item*StoreNewItem(ItemPosCountVec&d,unsigned e,bool){assert(d[0]==e);++created;items.emplace(e,Item{e,created+20});return &items.at(e);}
 unsigned CanEquipItem(unsigned slot,uint16&,Item*i,bool swap){assert(swap);requested[i->slot]=slot;return !equipAllowed?1:casting?2:0;}
 Session*GetSession(){return &session;}
};
bool PlayerbotAI::IsHeal(Player*p){return p->healer;}
void Session::HandleAutoEquipItemOpcode(WorldPacket&q){assert(q.op==42&&q.v.size()==2&&q.v[0]==0);++p->equips;if(p->equipWorks)for(auto&v:p->items)if(v.second.slot==q.v[1])p->worn[p->requested[q.v[1]]]=v.first;}
bool ready=true;bool RaidLabPartyReady(Player*,PlayerbotAI*,Player*&,std::string&){return ready;}
struct Logger{template<class...T>void outString(const char*,T...){}}sLog;
'''+block(source,'std::vector<std::pair<uint8,uint32>> RaidLabFrostEquipment(')+block(source,'TestResult RaidLabPrepareFrost(')+r'''
int main(){
 for(unsigned c:{1,2,3,4,5,7,8,9,11})for(bool heal:{false,true}){auto gear=RaidLabFrostEquipment(c,heal);assert(gear.size()==5);for(auto v:gear)assert(v.second>=22652&&v.second<=23033);}
 assert(RaidLabFrostEquipment(6,false).empty());assert(RaidLabFrostEquipment(11,true)[0].second==23032);assert(RaidLabFrostEquipment(11,false)[0].second==23020);
 Player p;Ref ref{&p};Group group{&ref};p.group=&group;TestContext ctx;std::string message;
 auto run=[&](){return RaidLabPrepareFrost(&p,&p.ai,ctx,message);};
 RaidLab::enabled=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);RaidLab::enabled=true;
 p.map=469;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.map=533;
 ctx.testName="raidlab_533_15989_leader_event";assert(run()==TestResult::IMPOSSIBLE&&p.created==0);ctx.testName+="_prepared";
 p.gm=true;assert(run()==TestResult::IMPOSSIBLE);p.gm=false;p.tp=true;assert(run()==TestResult::IMPOSSIBLE);p.tp=false;
 p.level=59;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.level=60;p.ai.real=true;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.ai.real=false;
 ready=false;assert(run()==TestResult::IMPOSSIBLE);ready=true;p.space=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==0);p.space=true;
 p.equipAllowed=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==1&&p.equips==0);p.equipAllowed=true;
 p.casting=true;assert(run()==TestResult::PENDING&&p.created==1&&p.equips==0);WorldTimer::now=60100;assert(run()==TestResult::IMPOSSIBLE&&p.created==1);
 p.casting=false;p.equipWorks=false;assert(run()==TestResult::IMPOSSIBLE&&p.created==1);p.equipWorks=true;
 assert(run()==TestResult::PASS&&p.created==5&&p.worn.size()==5);unsigned count=p.equips;
 assert(run()==TestResult::PASS&&p.created==5&&p.equips==count);
 std::cout<<"PASS explicit local frost loadout, native inventory refusal/retry and no duplicate completed equipment\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-frost-fixture-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
