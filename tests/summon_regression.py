"""Exercise the actual summon command helper with controlled group state."""
import subprocess
import tempfile
from pathlib import Path
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/actions/CastCustomSpellAction.cpp').read_text()
body = block(source, 'bool CastCustomSpellAction::CastSummonPlayer(')
code = r'''
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
using uint8=uint8_t;using uint32=uint32_t;
enum {CLASS_WARLOCK=9, SMSG_SUMMON_REQUEST=1, MAX_PLAYER_SUMMON_DELAY=120, IN_MILLISECONDS=1000};
enum class PlayerbotSecurityLevel {PLAYERBOT_SECURITY_ALLOW_ALL};
#define BOT_TEXT(x) std::string(x)
#define BOT_TEXT2(x,y) std::string(x)
struct ObjectGuid {
    uint32 id=0;explicit operator bool()const{return id!=0;}
    bool IsPlayer()const{return id!=0;}
    bool operator==(ObjectGuid b)const{return id==b.id;}
};
struct WorldPacket {WorldPacket(int,int=0){} template<class T> WorldPacket& operator<<(T){return *this;}};
struct Session {bool logout=false;int packets=0;bool isLogingOut(){return logout;}void SendPacket(WorldPacket*){++packets;}void SendPacket(WorldPacket&){++packets;}};
struct Player;
struct Group {
    struct MemberSlot {ObjectGuid guid;};
    using MemberSlotList=std::vector<MemberSlot>;using member_citerator=MemberSlotList::const_iterator;
    MemberSlotList members;
    const MemberSlotList& GetMemberSlots()const{return members;}
};
struct Map {bool allowed=true;bool CanEnter(Player*){return allowed;}};
struct Player {
    uint32 id=0;std::string name;Group* group=nullptr;int mapId=1;float x=0;
    bool alive=true,world=true,teleporting=false,taxi=false,transport=false,combat=false,real=true,knows=true,los=true,teleportOk=true;
    int summonRequests=0,teleports=0;Session session;Map map;ObjectGuid selection;
    int getClass(){return CLASS_WARLOCK;}bool HasSpell(int){return knows;}
    bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return teleporting;}
    bool IsTaxiFlying(){return taxi;}bool GetTransport(){return transport;}bool IsInCombat(){return combat;}
    Group* GetGroup(){return group;}const char* GetName(){return name.c_str();}
    ObjectGuid GetObjectGuid(){return {id};}ObjectGuid GetSelectionGuid(){return selection;}
    Session* GetSession(){return &session;}Map* GetMap(){return &map;}
    float GetDistance(Player* other){return std::abs(x-other->x);}
    bool IsWithinDistInMap(Player* other,float distance){return mapId==other->mapId && GetDistance(other)<=distance;}
    bool IsWithinLOSInMap(Player* other){return other->los;}
    int GetMapId(){return mapId;}int GetZoneId(){return 1;}
    float GetPositionX(){return x;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}float GetOrientation(){return 0;}
    void GetPosition(float& a,float& b,float& c){a=x;b=0;c=0;}
    bool isRealPlayer(){return real;}
    void SetSummonPoint(int,float,float,float,ObjectGuid){++summonRequests;}
    bool TeleportTo(int,float,float,float,float){if(teleportOk)++teleports;return teleportOk;}
};
struct ObjectMgr {std::map<uint32,Player*> players;Player* GetPlayer(ObjectGuid guid){auto p=players.find(guid.id);return p==players.end()?nullptr:p->second;}} sObjectMgr;
struct Config {float reactDistance=50;int globalCoolDown=1000;} sPlayerbotAIConfig;
struct Facade {bool LookupSpellInfo(int){return true;}} sServerFacade;
struct AI {Player* bot;bool IsSafe(Player* p){return bot->mapId==p->mapId;}template<class... T>void TellPlayerNoFacing(T...){} };
void ltrim(std::string& s){s.erase(s.begin(),std::find_if(s.begin(),s.end(),[](unsigned char c){return !std::isspace(c);}));}
bool normalizePlayerName(std::string& s){if(s.empty())return false;for(char& c:s)c=std::tolower((unsigned char)c);s[0]=std::toupper((unsigned char)s[0]);return true;}
struct CastCustomSpellAction {Player* bot;AI* ai;void SetDuration(int){}bool CastSummonPlayer(Player*,std::string,bool&);};
__BODY__
int main(){
    Group group;Player caster,target,h1,h2;AI ai{&caster};CastCustomSpellAction action{&caster,&ai};
    auto reset=[&](){
        caster=Player{};target=Player{};h1=Player{};h2=Player{};
        caster.id=1;caster.real=false;caster.name="Warlock";
        target.id=2;target.name="Impala";target.mapId=2;target.x=500;
        h1.id=3;h2.id=4;
        group.members={{{1}},{{2}},{{3}},{{4}}};
        caster.group=target.group=h1.group=h2.group=&group;
        sObjectMgr.players={{1,&caster},{2,&target},{3,&h1},{4,&h2}};
    };
    auto reject=[&](){bool handled=false;assert(!action.CastSummonPlayer(&target,"summon Impala",handled));assert(handled);assert(target.summonRequests==0 && target.teleports==0);};
    reset();bool handled=false;assert(action.CastSummonPlayer(&target,"summon impala",handled));assert(handled && target.summonRequests==1 && target.session.packets==1 && target.teleports==0);
    reset();target.selection={2};assert(action.CastSummonPlayer(&target,"summon",handled));assert(target.summonRequests==1);
    reset();h1.alive=false;reject();
    reset();h1.mapId=3;reject(); // same numeric coordinates, wrong map
    reset();h1.x=500;reject();
    reset();h1.combat=true;reject();
    reset();h1.teleporting=true;reject();
    reset();h1.los=false;reject();
    reset();target.alive=false;reject();
    reset();caster.knows=false;reject();
    reset();caster.map.allowed=false;reject();
    reset();target.group=nullptr;reject();
    reset();target.real=false;assert(action.CastSummonPlayer(&h1,"summon Impala",handled));assert(target.teleports==1 && target.summonRequests==0);
    reset();target.real=false;target.teleportOk=false;reject();
    reset();assert(!action.CastSummonPlayer(&target,"summon imp",handled));assert(!handled);
    reset();assert(!action.CastSummonPlayer(&target,"notsummon Impala",handled));assert(!handled);
    std::cout<<"PASS: actual summon command helper, 16 eligibility/direction cases\n";
}
'''.replace('__BODY__', body)
with tempfile.TemporaryDirectory(prefix='mantech-summon-') as tmp:
    tmp=Path(tmp)
    (tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W3','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
