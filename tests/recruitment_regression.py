"""Compile the actual recruitment service with deterministic session/map boundaries.

This exercises production request/eligibility/retry logic, not live pathfinding,
inventory generation, map loading, native packet processing, or an addon client.
Run from a Visual Studio developer shell: python recruitment_regression.py <repo>
"""
from pathlib import Path
import subprocess, tempfile, sys
root=Path(sys.argv[1])
source=(root/'playerbot/BotRecruitment.cpp').read_text()
source='\n'.join(x for x in source.splitlines() if not x.startswith('#include "'))
start=source.index('    uint64 Now()'); end=source.index('\n    struct Request',start)
source=source[:start]+'    uint64 Now() { return fakeNow; }\n'+source[end:]
header=(root/'playerbot/BotRecruitment.h').read_text().replace('#include "Common.h"','').replace('#pragma once','')
stubs=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <vector>
#include <functional>
#include <string>
using uint32=uint32_t; using uint64=uint64_t;
uint64 fakeNow=100;
constexpr int POWER_MANA=0;
enum {HIGHGUID_PLAYER, CHAT_MSG_WHISPER, LANG_UNIVERSAL, CHAT_TAG_NONE,
 CONFIG_BOOL_ALLOW_TWO_SIDE_INTERACTION_GROUP, CONFIG_UINT32_MAX_PLAYER_LEVEL,
 PLAYERBOT_SECURITY_ALLOW_ALL, PLAYERBOT_SECURITY_INVITE, BOT_STATE_NON_COMBAT,LFG_STATE_NONE};
struct PlayerbotSecurityLevel {static constexpr int PLAYERBOT_SECURITY_ALLOW_ALL=0,PLAYERBOT_SECURITY_INVITE=1;};
struct BotState {static constexpr int BOT_STATE_NON_COMBAT=0;};
struct ObjectGuid {
 uint32 value=0; ObjectGuid()=default; ObjectGuid(int,uint32 n):value(n){}
 uint32 GetCounter()const{return value;} explicit operator bool()const{return value!=0;}
 bool operator==(ObjectGuid x)const{return value==x.value;} bool operator!=(ObjectGuid x)const{return value!=x.value;}
};
struct Player; struct Group; struct WorldSession;
std::map<uint32,Player*> players;
std::vector<std::string> messages;
struct ObjectMgr {Player* GetPlayer(ObjectGuid g){auto it=players.find(g.value);return it==players.end()?nullptr:it->second;}} sObjectMgr;
struct WorldPacket {std::string name; WorldPacket& operator<<(std::string const& s){name=s;return *this;} WorldPacket& operator<<(uint32){return *this;}};
struct Social {bool ignored=false;bool HasIgnore(ObjectGuid){return ignored;}};
struct Security {bool allow=true;bool CheckLevelFor(int,bool,Player*){return allow;}};
struct AI {Player* master=nullptr; Security security; int changes=0;
 Player* GetMaster(){return master;} void SetMaster(Player* p){master=p;} Security* GetSecurity(){return &security;}
 void ChangeStrategy(std::string const&,int){++changes;} std::string GetDefaultMovementStrategy(){return "follow";}};
struct Map{};
struct LfgData {int state=LFG_STATE_NONE;int GetState(){return state;}};
class PlayerbotHolder {public:std::string ProcessBotCommand(std::string,ObjectGuid,ObjectGuid,bool,uint32,uint32);};
struct WorldSession {Player* player=nullptr;uint32 account=1;bool logout=false;struct {bool queued=false;} m_lfgInfo;
 bool isLogingOut(){return logout;} uint32 GetAccountId(){return account;}void SendPacket(WorldPacket const& p){messages.push_back(p.name);}
 void HandleGroupAcceptOpcode(WorldPacket&);void HandleGroupInviteOpcode(WorldPacket&);
};
struct Group {ObjectGuid leader,assistant;unsigned count=1;bool raid=false,bg=false;
 bool IsBattleGroup(){return bg;}ObjectGuid GetLeaderGuid(){return leader;}bool IsLeader(ObjectGuid g){return leader==g;}
 bool IsAssistant(ObjectGuid guid){return assistant==guid;}unsigned GetMembersCount(){return count;}bool IsRaidGroup(){return raid;}};
std::vector<std::unique_ptr<Group>> groups;
struct Player {
 uint32 id,level=43,cls=1,guild=0,team=0,mapId=1,instance=0;bool real=false,world=true,transfer=false,alive=true,combat=false,
 taxi=false,transport=false,charm=false,bg=false,bgQueue=false,afk=false,los=true;float distance=0;
 std::string name,talents="0-0-10";WorldSession session;AI ai;Social social;Group* group=nullptr;Group* invite=nullptr;
 Map map;LfgData lfg;PlayerbotHolder holder;unsigned gear=0;int health=50,maxHealth=100,mana=5,maxMana=100,otherPower=23;
 uint32 GetMaxHealth(){return maxHealth;}void SetHealth(uint32 value){health=value;}
 uint32 GetMaxPower(int power){assert(power==POWER_MANA);return maxMana;}
 void SetPower(int power,uint32 value){assert(power==POWER_MANA);mana=value;}
 Player(uint32 n,bool human=false):id(n),real(human),name("Bot"+std::to_string(n)){session.player=this;session.account=human?n:1000;players[n]=this;}
 WorldSession* GetSession(){return &session;}bool isRealPlayer(){return real;}AI* GetPlayerbotAI(){return real?nullptr:&ai;}
 ObjectGuid GetObjectGuid(){return ObjectGuid(HIGHGUID_PLAYER,id);}uint32 GetGUIDLow(){return id;}uint32 GetGuildId(){return guild;}
 bool IsGameMaster(){return false;}uint32 GetTeam(){return team;}Social* GetSocial(){return &social;}
 Group* GetGroup(){return group;}Group* GetOriginalGroup(){return nullptr;}Group* GetGroupInvite(){return invite;}
 bool InBattleGround(){return bg;}bool InBattleGroundQueue(){return bgQueue;}LfgData& GetLfgData(){return lfg;}
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}
 uint32 GetMapId(){return mapId;}uint32 GetInstanceId(){return instance;}void* GetTransport(){return transport?this:nullptr;}
 bool IsTaxiFlying(){return taxi;}bool IsInCombat(){return combat;}bool IsAlive(){return alive;}
 Map* GetMap(){static Map same;return mapId==1?&same:&map;}float GetDistance(Player*){return distance;}
 bool IsWithinLOSInMap(Player*){return los;}const char* GetName(){return name.c_str();}unsigned getClass(){return cls;}
 uint32 GetLevel(){return level;}bool isAFK(){return afk;}void ToggleAFK(){afk=!afk;}
 void UninviteFromGroup(){invite=nullptr;}PlayerbotHolder* GetPlayerbotMgr(){return &holder;}
};
struct Config {bool allowGuildBots=false,recruitmentRevive=true;bool IsInRandomAccountList(uint32 n){return n==1000;}
 bool IsFreeAltBot(Player*){return false;}} sPlayerbotAIConfig;
struct World {bool cross=false;struct Queue {bool IsPlayerInQueue(ObjectGuid){return false;}} queue;
 uint32 getConfig(int which){return which==CONFIG_UINT32_MAX_PLAYER_LEVEL?80:cross;}Queue& GetLFGQueue(){return queue;}}sWorld;
struct RandomMgr:PlayerbotHolder {std::map<uint32,Player*>& GetAllBots(){return players;}}sRandomPlayerbotMgr;
struct RandomItems{bool supported=true;uint32 GetPlayerSpecId(Player*){return supported?1:0;}}sRandomItemMgr;
struct ChatHandler {explicit ChatHandler(WorldSession*){}void PSendSysMessage(const char*,const char* s){messages.push_back(s);}
 static void BuildChatPacket(WorldPacket& p,int,const char* t,int,int,ObjectGuid,const char*){p.name=t;}};
struct TalentSpec {Player* bot;explicit TalentSpec(Player* b):bot(b){}std::string GetTalentLink(){return bot->talents;}};
namespace ai {
struct EventOwner {Player* p=nullptr;ObjectGuid guid;EventOwner(Player* b=nullptr):p(b),guid(b?b->GetObjectGuid():ObjectGuid()){}
 Player* Get()const{auto it=players.find(guid.value);return it!=players.end()&&it->second==p?p:nullptr;}};
struct Event {Player* owner;Event(std::string,std::string,Player* p):owner(p){}};
struct WhoAction{explicit WhoAction(AI*){}std::string QuerySpec(std::string){return "Warrior (43 lvl), 100 GS (green)";}};
struct SummonAction{AI* ai;explicit SummonAction(AI* a):ai(a){}bool ExecuteImmediate(Event&){for(auto& x:players)if(&x.second->ai==ai){x.second->transfer=true;return true;}return false;}};
}
'''
tests=r'''
void WorldSession::HandleGroupInviteOpcode(WorldPacket& p){
 Player* bot=nullptr;for(auto const& x:players)if(x.second->name==p.name)bot=x.second;
 if(!bot||bot->group||bot->invite||!ai::BotRecruitment::CanInvite(player,bot))return;
 Group* group=player->group?player->group:player->invite;
 if(!group){groups.emplace_back(new Group);group=groups.back().get();group->leader=player->GetObjectGuid();player->invite=group;}
 if(group->count>=(group->raid?40u:5u))return;bot->invite=group;ai::BotRecruitment::OnInvite(player,bot);
}
void WorldSession::HandleGroupAcceptOpcode(WorldPacket&){
 if(!player->invite)return;Group* group=player->invite;player->invite=nullptr;
 if(group->count>=(group->raid?40u:5u))return;Player* owner=sObjectMgr.GetPlayer(group->leader);
 if(owner){owner->group=group;owner->invite=nullptr;}player->group=group;++group->count;
}
std::string PlayerbotHolder::ProcessBotCommand(std::string cmd,ObjectGuid bg,ObjectGuid og,bool,uint32,uint32){
 Player* b=sObjectMgr.GetPlayer(bg);Player* o=sObjectMgr.GetPlayer(og);
 return ai::BotRecruitment::Prepare(o,b,cmd,"",[&](){++b->gear;return "random gear equipped";});
}
void reset(){players.clear();groups.clear();messages.clear();fakeNow+=100;
 auto& s=State();s.incoming.clear();s.invites.clear();s.managedInvites.clear();s.summons.clear();s.reservations.clear();s.receipts.clear();s.preparation.clear();s.discoveryTime.clear();s.nextDiscovery=0;s.elapsed=0;sPlayerbotAIConfig.allowGuildBots=false;sPlayerbotAIConfig.recruitmentRevive=true;sWorld.cross=false;}
void tick(unsigned seconds=0){fakeNow+=seconds;ai::BotRecruitment::Update(250);}
void invite(Player& p,Player& b){WorldPacket packet;packet<<b.name;p.session.HandleGroupInviteOpcode(packet);}
void command(Player& p,std::string args){assert(ai::BotRecruitment::HandleCommand(&p,"recruit v1 "+args));tick();}
bool has(std::string t){for(auto const& m:messages)if(m.find(t)!=std::string::npos)return true;return false;}
int main(){
 // Successful legacy gear requests refill current post-equipment maxima,
 // including cached repeats, without rerolling gear or touching other powers.
 reset();{Player p(1,true),b(2);b.ai.master=&p;unsigned calls=0;
 auto apply=[&](){++calls;b.maxHealth=140;b.maxMana=180;return std::string("random gear equipped");};
 ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(calls==1&&b.health==140&&b.mana==180&&b.otherPower==23);
 b.health=1;b.mana=2;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(calls==1&&b.health==140&&b.mana==180);
 b.health=1;b.mana=2;b.combat=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2);
 b.combat=false;p.combat=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2);
 p.combat=false;b.alive=false;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2);
 b.alive=true;b.transfer=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2);
 b.transfer=false;b.real=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2&&calls==1);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.maxMana=0;
 auto apply=[](){return std::string("gear upgraded");};
 ai::BotRecruitment::Prepare(&p,&b,"equip","upgrade",apply);assert(b.health==100&&b.mana==5&&b.otherPower==23);
 b.health=1;ai::BotRecruitment::Prepare(&p,&b,"equip","upgrade",apply);assert(b.health==100&&b.otherPower==23);}
 for(auto response:{"unknown gear command","refused: unsupported_spec","refused: busy"}){
 reset();Player p(1,true),b(2);b.ai.master=&p;auto apply=[&](){return std::string(response);};
 ai::BotRecruitment::Prepare(&p,&b,"gear","bad",apply);ai::BotRecruitment::Prepare(&p,&b,"gear","bad",apply);assert(b.health==50&&b.mana==5);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;auto apply=[](){return std::string("food added");};
 ai::BotRecruitment::Prepare(&p,&b,"food","",apply);ai::BotRecruitment::Prepare(&p,&b,"food","",apply);assert(b.health==50&&b.mana==5);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;command(p,"refill prepare 2 gear");assert(b.health==100);
 b.health=7;command(p,"refill prepare 2 gear");assert(b.health==7&&b.gear==1);}

 reset();{Player p(1,true),b(2);b.combat=true;b.alive=false;b.afk=true;invite(p,b);tick();assert(b.group==p.group&&b.group);assert(!b.alive&&b.combat&&b.health==50&&b.gear==0&&!b.transfer);assert(b.ai.master==&p&&!b.afk);}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);tick();assert(!b.group);tick(15);assert(!b.invite&&!b.group&&has("timed_out"));b.transfer=false;tick();assert(!b.group);}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);tick(10);b.invite=nullptr;invite(p,b);tick(6);assert(b.invite);b.transfer=false;tick();assert(b.group);}
 reset();{Player p(1,true),other(3,true),b(2);command(p,"r reserve 2");invite(other,b);assert(!b.invite&&has("reserved"));invite(p,b);tick();assert(b.ai.master==&p);}
 reset();{Player p(1,true),other(3,true),b(2);invite(p,b);Group external;external.leader=other.GetObjectGuid();b.group=&external;tick();assert(b.group==&external&&!b.invite);}
 reset();{Player p(1,true),human(2,true);command(p,"x summon 2");assert(!human.transfer&&has("not_available_bot"));command(p,"y prepare 2 gear");assert(!human.gear);}
 reset();{Player p(1,true),b(2);b.session.account=999;assert(ai::BotRecruitment::Eligibility(&p,&b)=="not_authorized");b.session.account=1;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());b.session.account=999;p.guild=b.guild=7;sPlayerbotAIConfig.allowGuildBots=true;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());}
 reset();{Player p(1,true),b(2);b.team=1;assert(ai::BotRecruitment::Eligibility(&p,&b)=="wrong_faction");sWorld.cross=true;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());b.bgQueue=true;assert(ai::BotRecruitment::Eligibility(&p,&b)=="queued_activity");}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);players.erase(1);tick();assert(!b.invite&&!b.group);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;b.combat=true;ai::BotRecruitment::Queue(&p,&b,"summon");tick();assert(!b.transfer);b.combat=false;b.taxi=true;tick();assert(!b.transfer);b.taxi=false;tick();assert(b.transfer&&!has("arrived"));b.transfer=false;b.distance=0;tick();assert(has("arrived"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.instance=1;ai::BotRecruitment::Queue(&p,&b,"summon");tick();assert(!b.transfer&&has("different_instance"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.alive=false;sPlayerbotAIConfig.recruitmentRevive=false;command(p,"s summon 2");assert(!b.transfer&&has("revival_disabled"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;command(p,"g prepare 2 gear");assert(b.gear==1);command(p,"g prepare 2 gear");assert(b.gear==1);command(p,"g summon 2");assert(has("id_conflict"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;unsigned count=0;auto apply=[&](){++count;return std::string("random gear equipped");};assert(ai::BotRecruitment::Prepare(&p,&b,"gear","",apply)=="random gear equipped");ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(count==1);b.talents="10-0-0";tick(1);ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(count==2);b.real=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(count==2);}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);command(p,"c cancel 2");b.transfer=false;tick();assert(!b.group&&!b.invite);}
 reset();{Player p(1,true),b(2);Group g;g.leader=p.GetObjectGuid();g.count=4;p.group=&g;invite(p,b);g.count=5;tick();assert(!b.group&&!b.invite&&g.count==5);}
 reset();{Player p(1,true),b(2);Group g;g.leader=p.GetObjectGuid();p.group=&g;invite(p,b);g.leader=ObjectGuid(HIGHGUID_PLAYER,3);tick();assert(!b.group&&!b.invite);}
 reset();{Player p(1,true);Group g;g.leader=p.GetObjectGuid();g.count=10;g.raid=true;p.group=&g;std::vector<std::unique_ptr<Player>> bots;for(unsigned i=2;i<32;++i){bots.emplace_back(new Player(i));invite(p,*bots.back());}for(int n=0;n<5;++n)tick();assert(g.count==40);for(auto const& b:bots)assert(b->group==&g&&!b->gear);}
 reset();{Player p(1,true);std::vector<std::unique_ptr<Player>> bots;for(unsigned i=2;i<1002;++i)bots.emplace_back(new Player(i));command(p,"d discover 1 41 45 0");assert(has("cursor=")&&has("eligible"));assert(messages.size()<=9);}
 reset();{Player p(1,true),b(2);ai::BotRecruitment::Queue(&p,&b,"who");tick();assert(has("(43 lvl)")&&has("GS ("));}
 reset();{Player p(1,true);std::vector<std::unique_ptr<Player>> bots;for(unsigned i=2;i<42;++i){bots.emplace_back(new Player(i));ai::BotRecruitment::Queue(&p,bots.back().get(),"who");}assert(State().incoming.size()==limits::MaxIncomingPerPlayer);tick();assert(State().incoming.size()==limits::MaxIncomingPerPlayer-limits::CommandsPerTick);}
 reset();{Player p(1,true),b(2),leader(3);Group g;g.leader=leader.GetObjectGuid();g.assistant=p.GetObjectGuid();p.group=leader.group=&g;invite(p,b);assert(ai::BotRecruitment::HasPendingInvite(&b));tick();assert(b.group==&g&&b.ai.master==&p&&!ai::BotRecruitment::HasPendingInvite(&b));}
 reset();{std::vector<std::unique_ptr<Player>> owners,bots;for(unsigned n=1;n<=32;++n){owners.emplace_back(new Player(n,true));for(unsigned j=1;j<=16;++j){bots.emplace_back(new Player(100+n*16+j));ai::BotRecruitment::Queue(owners.back().get(),bots.back().get(),"who");}}assert(State().incoming.size()==256);tick();assert(State().incoming.size()==248);}
 reset();{Player p(1,true),b(2);command(p,"bad accept 2");assert(has("unsupported_operation")&&!b.group);}
 assert(!limits::Arrived(true,false,true,false,1,2,1,3,0,true));assert(!limits::HasVacancy(25,25,true));
 std::cout<<"PASS: actual coordinator permissions, native-invite scheduling, stale/replaced invites, ownership, combat/death, session loss, transports, arrival, replay, cancellation, mixed 40-member capacity, bounded discovery/work\n";
}
'''
policy=(root/'playerbot/RecruitmentPolicy.h').read_text().replace('#pragma once','')
with tempfile.TemporaryDirectory(prefix='pb-recruitment-') as directory:
    folder=Path(directory);cpp=folder/'test.cpp';exe=folder/'test.exe'
    cpp.write_text(stubs+'\n'+policy+'\n'+header+'\n'+source+'\n'+tests)
    for macro in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/D'+macro,str(cpp),'/Fe:'+str(exe),'/Fo:'+str(folder/'test.obj')],check=True)
        subprocess.run([str(exe)],check=True)
