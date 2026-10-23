"""Compile the actual recruitment service with deterministic session/map boundaries.

This exercises production request/eligibility/retry logic, not live pathfinding,
inventory generation, map loading, native packet processing, or an addon client.
Run from a Visual Studio developer shell: python recruitment_regression.py <repo>
"""
from pathlib import Path
import subprocess, tempfile, sys
root=Path(sys.argv[1])
source=(root/'playerbot/BotRecruitment.cpp').read_text()
command=(root/'playerbot/PlayerbotAI.cpp').read_text().split('void PlayerbotAI::HandleCommand(',1)[1].split('void PlayerbotAI::HandleBotOutgoingPacket(',1)[0]
routing=command.index('BotRecruitment::Queue(')
assert command.index('chatFilter.Filter(') < routing < command.index('chatCommands.push(')
assert command.index('PLAYERBOT_SECURITY_ALLOW_ALL') < routing
assert 'type == CHAT_MSG_PARTY || type == CHAT_MSG_RAID' in command[:routing]
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
 uint32 value=0; int kind=0; ObjectGuid()=default; ObjectGuid(int k,uint32 n):value(n),kind(k){}
 bool IsCreature()const{return kind==1;} uint32 GetEntry()const{return value;}
 uint32 GetCounter()const{return value;} explicit operator bool()const{return value!=0;}
 bool operator==(ObjectGuid x)const{return value==x.value;} bool operator!=(ObjectGuid x)const{return value!=x.value;}
};
struct Player; struct Group; struct WorldSession;
std::map<uint32,Player*> players;
std::vector<std::string> messages;
struct ObjectMgr {Player* GetPlayer(const char* name);Player* GetPlayer(ObjectGuid g){auto it=players.find(g.value);return it==players.end()?nullptr:it->second;}} sObjectMgr;
struct WorldPacket {std::string name;ObjectGuid npc{1,14387};unsigned bytes=8;
 unsigned size()const{return bytes;}void rpos(unsigned){}WorldPacket&operator>>(ObjectGuid&g){g=npc;return *this;}
 WorldPacket& operator<<(std::string const& s){name=s;return *this;} WorldPacket& operator<<(uint32){return *this;}};
struct Social {bool ignored=false;bool HasIgnore(ObjectGuid){return ignored;}};
struct Security {bool allow=true;int LevelFor(Player*,void*,bool,bool ignoreQueues){assert(ignoreQueues);return allow?1:-1;}bool CheckLevelFor(int,bool,Player*){return allow;}};
struct AI {Player* master=nullptr; Security security; bool following=true; int changes=0,revivalChecks=0;
 bool HasStrategy(std::string,int){return following;}
 void CompleteSummonRevival(){++revivalChecks;}
 Player* GetMaster(){return master;} void SetMaster(Player* p){master=p;} Security* GetSecurity(){return &security;}
 void ChangeStrategy(std::string const&,int){++changes;} std::string GetDefaultMovementStrategy(){return "follow";}};
using Difficulty=int;
struct PersistentState{};
struct InstanceGroupBind{PersistentState* state=nullptr;};
struct InstanceData{bool active=false;bool IsEncounterInProgress(){return active;}};
struct Map{bool instanced=true,raid=false;PersistentState state;
 bool Instanceable(){return instanced;}bool IsRaid(){return raid;}
 int GetDifficulty(){return 0;}PersistentState* GetPersistentState(){return &state;}};
struct DungeonMap:Map{unsigned count=1,max=40;InstanceData data;
 unsigned GetPlayersCountExceptGMs(){return count;}unsigned GetMaxPlayers(){return max;}
 InstanceData* GetInstanceData(){return &data;}};
struct MapEntry{bool instanced=false;bool Instanceable()const{return instanced;}};
struct MapStore{MapEntry entry;bool missing=false;MapEntry const* LookupEntry(uint32){return missing?nullptr:&entry;}}sMapStore;
struct Log{unsigned diagnostics=0;template<class... T>void outString(const char* format,T...){if(std::string(format)=="PLAYERBOT_RECRUIT_DIAG: %s")++diagnostics;}}sLog;
#define DEBUG_LOG(...) ((void)0)
struct WorldLocation{uint32 mapid=409;float coord_x=0,coord_y=0,coord_z=0;};
struct LfgData {int state=LFG_STATE_NONE;int GetState(){return state;}};
class PlayerbotHolder {public:std::string ProcessBotCommand(std::string,ObjectGuid,ObjectGuid,bool,uint32,uint32);};
struct WorldSession {Player* player=nullptr;uint32 account=1;bool logout=false;struct {bool queued=false;} m_lfgInfo;
 bool isLogingOut(){return logout;} uint32 GetAccountId(){return account;}void SendPacket(WorldPacket const& p){messages.push_back(p.name);}
 void HandleGroupAcceptOpcode(WorldPacket&);void HandleGroupInviteOpcode(WorldPacket&);
};
struct GroupReference{Player*player=nullptr;GroupReference*following=nullptr;
 Player*getSource(){return player;}GroupReference*next(){return following;}};
struct Group {ObjectGuid leader,assistant;unsigned count=1;bool raid=false,bg=false;
 std::vector<GroupReference> members;GroupReference*GetFirstMember(){return members.empty()?nullptr:&members[0];}
 InstanceGroupBind binding;bool bound=true;
 InstanceGroupBind* GetBoundInstance(uint32){return bound?&binding:nullptr;}
 InstanceGroupBind* GetBoundInstance(Map*,Difficulty){return bound?&binding:nullptr;}
 bool IsBattleGroup(){return bg;}ObjectGuid GetLeaderGuid(){return leader;}bool IsLeader(ObjectGuid g){return leader==g;}
 bool IsAssistant(ObjectGuid guid){return assistant==guid;}unsigned GetMembersCount(){return count;}bool IsRaidGroup(){return raid;}};
std::vector<std::unique_ptr<Group>> groups;
struct Player {
 uint32 id,level=43,cls=1,guild=0,team=0,mapId=1,instance=0;bool real=false,world=true,transfer=false,alive=true,combat=false,
 taxi=false,transport=false,charm=false,bg=false,bgQueue=false,afk=false,los=true,separateMap=false;float distance=0;unsigned distanceChecks=0,losChecks=0;
 std::string name,talents="0-0-10",applyResult="random gear equipped";WorldSession session;AI ai;Social social;Group* group=nullptr;Group* invite=nullptr;
 float landingDistance=0;std::string summonFailure;bool summonRetryable=false;unsigned summonChecks=0;unsigned summons=0,queueCancellations=0,raidPreparations=0;WorldLocation destination;
 bool IsWithinDist3d(float,float,float,float r){return landingDistance<=r;}WorldLocation const& GetTeleportDest(){return destination;}
 DungeonMap map;LfgData lfg;PlayerbotHolder holder;unsigned gear=0;int health=50,maxHealth=100,mana=5,maxMana=100,otherPower=23;
 uint32 homeMap=0;unsigned departures=0;bool homeAccepted=true;
 void GetHomebindLocation(float& x,float& y,float& z,uint32& m){x=y=z=0;m=homeMap;}
 bool TeleportToHomebind(){if(!homeAccepted)return false;transfer=true;++departures;return true;}
 void BreakCharmIncoming(){charm=false;}void BreakCharmOutgoing(){}
 bool TaxiFlightInterrupt(){taxi=false;return true;}void OnTaxiFlightEject(){taxi=false;}
 void InterruptNonMeleeSpells(bool){}
 uint32 GetMaxHealth(){return maxHealth;}void SetHealth(uint32 value){health=value;}
 uint32 GetMaxPower(int power){assert(power==POWER_MANA);return maxMana;}
 void SetPower(int power,uint32 value){assert(power==POWER_MANA);mana=value;}
 Player(uint32 n,bool human=false):id(n),real(human),name("Bot"+std::to_string(n)){session.player=this;session.account=human?n:1000;players[n]=this;}
 WorldSession* GetSession(){return &session;}bool isRealPlayer(){return real;}AI* GetPlayerbotAI(){return real?nullptr:&ai;}
 ObjectGuid GetObjectGuid(){return ObjectGuid(HIGHGUID_PLAYER,id);}uint32 GetGUIDLow(){return id;}uint32 GetGuildId(){return guild;}
 bool IsGameMaster(){return false;}uint32 GetTeam(){return team;}Social* GetSocial(){return &social;}
 Group* GetGroup(){return group;}Group* GetOriginalGroup(){return nullptr;}Group* GetGroupInvite(){return invite;}
 bool InBattleGround(){return bg;}bool InBattleGroundQueue(){return bgQueue;}LfgData& GetLfgData(){return lfg;}
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool IsBeingTeleportedFar(){return transfer;}bool HasCharmer(){return charm;}
 uint32 GetMapId(){return mapId;}uint32 GetInstanceId(){return instance;}void* GetTransport(){return transport?this:nullptr;}
 bool IsTaxiFlying(){return taxi;}bool IsInCombat(){return combat;}bool IsAlive(){return alive;}
 Map* GetMap(){static Map same;return mapId==1&&!separateMap?&same:&map;}float GetDistance(Player* other){++distanceChecks;assert(world&&other->world&&!transfer&&!other->transfer&&alive&&mapId==other->mapId&&instance==other->instance&&GetMap()==other->GetMap());return distance;}
 bool IsWithinLOSInMap(Player* other){++losChecks;assert(world&&other->world&&!transfer&&!other->transfer&&GetMap()==other->GetMap());return los;}const char* GetName(){return name.c_str();}unsigned getClass(){return cls;}
 uint32 GetLevel(){return level;}bool isAFK(){return afk;}void ToggleAFK(){afk=!afk;}
 void UninviteFromGroup(){invite=nullptr;}PlayerbotHolder* GetPlayerbotMgr(){return &holder;}
};
struct Config {float sightDistance=100;bool allowGuildBots=false,recruitmentRevive=true;bool IsInRandomAccountList(uint32 n){return n==1000;}
 bool IsFreeAltBot(Player*){return false;}} sPlayerbotAIConfig;
struct LFGQueue {bool IsPlayerInQueue(ObjectGuid){return false;}LFGQueue& GetMessager(){return *this;}template<class F>void AddMessage(F f){f(this);}};
struct World {bool cross=false;using Queue=LFGQueue;Queue queue;
 bool defer=false;std::vector<std::function<void(World*)>> callbacks;World& GetMessager(){return *this;}
 template<class F>void AddMessage(F f){if(defer)callbacks.push_back(f);else f(this);}
 void Drain(){auto pending=std::move(callbacks);callbacks.clear();for(auto& f:pending)f(this);}
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
struct SummonAction{static void PrepareRaidBinding(Player* owner,Player* p){assert(owner->group&&p->group==owner->group);++p->raidPreparations;}static void CancelAutonomousQueues(Player* p){++p->queueCancellations;p->bgQueue=false;p->session.m_lfgInfo.queued=false;p->lfg.state=0;}AI* ai;std::string failure;bool retry=false;const std::string& GetFailureReason(){return failure;}bool CanRetry(){return retry;}explicit SummonAction(AI* a):ai(a){}bool ExecuteImmediate(Event&){for(auto& x:players)if(&x.second->ai==ai){Player* p=x.second;++p->summonChecks;if(!p->summonFailure.empty()){failure=p->summonFailure;retry=p->summonRetryable;return false;}p->transfer=true;++p->summons;return true;}return false;}};
}
'''
tests=r'''
Player* ObjectMgr::GetPlayer(const char* name){Player* result=nullptr;for(auto const& x:players)if(x.second->name==name)result=x.second;return result;}
void WorldSession::HandleGroupInviteOpcode(WorldPacket& p){
 Player* bot=sObjectMgr.GetPlayer(p.name.c_str());
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
 return ai::BotRecruitment::Prepare(o,b,cmd,"",[&](){++b->gear;return b->applyResult;});
}
void reset(){players.clear();groups.clear();messages.clear();fakeNow+=100;sWorld.defer=false;sWorld.callbacks.clear();
 auto& s=State();s.incoming.clear();s.invites.clear();s.managedInvites.clear();s.summons.clear();s.reservations.clear();s.receipts.clear();s.preparationReceipts.clear();s.preparation.clear();s.preparationTrace=nullptr;s.explicitPreparation=false;sLog.diagnostics=0;s.diagnosticWork=0;s.diagnosticOwnerWork.clear();s.diagnosticSecond=0;s.discoveryTime.clear();s.nextDiscovery=0;s.elapsed=0;sPlayerbotAIConfig.allowGuildBots=false;sPlayerbotAIConfig.recruitmentRevive=true;sWorld.cross=false;sMapStore.missing=false;sMapStore.entry.instanced=false;}
void tick(unsigned seconds=0){fakeNow+=seconds;ai::BotRecruitment::Update(250);}
void invite(Player& p,Player& b){WorldPacket packet;packet<<b.name;p.session.HandleGroupInviteOpcode(packet);}
void command(Player& p,std::string args){assert(ai::BotRecruitment::HandleCommand(&p,"recruit v1 "+args));tick();}
bool has(std::string t){for(auto const& m:messages)if(m.find(t)!=std::string::npos)return true;return false;}
int main(){
 // Windia regression: GUID discovery must not invite the lower-level namesake
 // selected by native name lookup. Also test a conflicting real player.
 for(bool human : {false,true}) { reset();Player p(1,true),wanted(2),namesake(3,human);
 wanted.name=namesake.name="Windia";wanted.level=60;namesake.level=30;
 assert(ai::BotRecruitment::Eligibility(&p,&wanted)=="name_identity_conflict");
 command(p,"d discover 1 60 60 0");assert(!has("eligible"));
 command(p,"r reserve 2");assert(has("refused name_identity_conflict")&&State().reservations.empty());
 command(p,"i invite 2 5");assert(!wanted.invite&&!namesake.invite&&!p.invite);
 assert(!wanted.group&&!namesake.group&&!wanted.gear&&!namesake.gear);
 }
 // Names can become ambiguous after reservation; invite must recheck.
 reset();{Player p(1,true),wanted(2);wanted.name="Windia";
 command(p,"r reserve 2");assert(has("reserved"));Player namesake(3);namesake.name="Windia";
 command(p,"i invite 2 5");assert(has("refused name_identity_conflict")&&!namesake.invite&&!wanted.invite);
 namesake.name="Other";command(p,"i2 invite 2 5");tick();assert(wanted.group==p.group&&wanted.group&&!namesake.group);}
 // Actual Lothos entry captures all 39 authorized companions after native acceptance,
 // waits for the human's landing, then uses the existing bounded coordinator.
 reset();{Player p(1,true);Group g;g.raid=true;g.leader=p.GetObjectGuid();p.group=&g;
 p.mapId=0;p.transfer=true;p.world=false;WorldPacket packet;
 std::vector<std::unique_ptr<Player>> bots;g.members.resize(39);
 for(unsigned i=0;i<39;++i){bots.emplace_back(new Player(i+2));auto*b=bots.back().get();
 b->group=&g;b->ai.master=&p;b->mapId=0;
 b->distance=i%2?150:0;b->ai.following=i%3!=0;b->combat=i%5==0;b->alive=i%7!=0;
 if(i%4==0){b->mapId=409;b->instance=25;}
 if(i%6==0)b->mapId=1;
 g.members[i]={b,i+1<39?&g.members[i+1]:nullptr};}
 ai::BotRecruitment::FollowMoltenCoreEntry(&p,packet);assert(State().incoming.size()==39);
 for(int i=0;i<6;++i)tick();for(auto&b:bots)assert(!b->summons);
 p.world=true;p.transfer=false;p.mapId=409;p.instance=55;p.map.raid=true;g.binding.state=&p.map.state;
 for(auto&b:bots){b->map.raid=true;if(b->mapId==409)b->homeMap=0;}
 for(int i=0;i<25;++i){tick();for(auto&b:bots)if(b->transfer){b->transfer=false;if(b->departures&&!b->summons)b->mapId=0;
 else{b->mapId=409;b->instance=55;b->alive=true;}}}
 tick();for(auto&b:bots)assert(b->summons==1&&b->mapId==409&&b->instance==55);
 assert(State().summons.empty());}
 for(unsigned fault=0;fault<13;++fault){reset();Player p(1,true),b(2),other(99,true);Group g;
 g.raid=true;g.leader=p.GetObjectGuid();g.members={{&b,nullptr}};p.group=b.group=&g;
 p.mapId=b.mapId=0;p.transfer=true;p.world=false;b.ai.master=&p;WorldPacket packet;
 if(fault==0)packet.npc={1,123};if(fault==1)packet.bytes=0;if(fault==2)p.destination.mapid=469;
 if(fault==3)b.distance=101;if(fault==4)b.combat=true;if(fault==5)b.ai.following=false;
 if(fault==6)b.real=true;if(fault==7)b.ai.master=&other;if(fault==8)b.alive=false;
 if(fault==9)b.mapId=1;if(fault==10)b.transfer=true;if(fault==11)b.charm=true;
 if(fault==12)g.raid=false;
 ai::BotRecruitment::FollowMoltenCoreEntry(&p,packet);
 bool denied=fault<=2||fault==6||fault==7||fault==12;
 assert(State().incoming.size()==(denied?0u:1u));}
 for(unsigned fault=0;fault<5;++fault){reset();Player p(1,true),b(2);Group g;
 g.raid=true;g.leader=p.GetObjectGuid();g.members={{&b,nullptr}};p.group=b.group=&g;
 p.mapId=b.mapId=0;p.transfer=true;p.world=false;b.ai.master=&p;WorldPacket packet;
 ai::BotRecruitment::FollowMoltenCoreEntry(&p,packet);tick();assert(!b.summons);
 p.world=true;p.transfer=false;p.mapId=409;
 if(fault==0)p.mapId=0;if(fault==1)b.group=nullptr;if(fault==2)b.ai.following=false;
 if(fault==3)b.mapId=1;if(fault==4){b.mapId=409;b.instance=p.instance;}
 tick();if(fault==2||fault==3){assert(b.summons==1);b.transfer=false;b.mapId=409;tick();}
 else assert(!b.summons);assert(State().summons.empty());}
 // Successful legacy gear requests refill current post-equipment maxima,
 // including cached repeats, without rerolling gear or touching other powers.
 reset();{Player p(1,true),b(2);b.ai.master=&p;unsigned calls=0;
 auto apply=[&](){++calls;b.maxHealth=140;b.maxMana=180;return std::string("random gear equipped");};
 ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(calls==1&&b.health==140&&b.mana==180&&b.otherPower==23);
 b.health=1;b.mana=2;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(calls==1&&b.health==140&&b.mana==180);
 b.health=1;b.mana=2;b.combat=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==140&&b.mana==180&&b.combat&&calls==1);
 b.health=1;b.mana=2;b.combat=false;p.combat=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==140&&b.mana==180&&p.combat&&calls==1);
 b.health=1;b.mana=2;p.combat=false;b.alive=false;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2);
 b.alive=true;b.transfer=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2);
 b.transfer=false;b.real=true;ai::BotRecruitment::Prepare(&p,&b,"gear","",apply);assert(b.health==1&&b.mana==2&&calls==1);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.maxMana=0;b.combat=true;p.combat=true;
 auto apply=[](){return std::string("gear upgraded");};
 ai::BotRecruitment::Prepare(&p,&b,"equip","upgrade",apply);assert(b.health==100&&b.mana==5&&b.otherPower==23);
 b.health=1;ai::BotRecruitment::Prepare(&p,&b,"equip","upgrade",apply);assert(b.health==100&&b.otherPower==23);}
 for(auto response:{"unknown gear command","refused: unsupported_spec","refused: busy"}){
 reset();Player p(1,true),b(2);b.ai.master=&p;auto apply=[&](){return std::string(response);};
 ai::BotRecruitment::Prepare(&p,&b,"gear","bad",apply);ai::BotRecruitment::Prepare(&p,&b,"gear","bad",apply);assert(b.health==50&&b.mana==5);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;auto apply=[](){return std::string("food added");};
 ai::BotRecruitment::Prepare(&p,&b,"food","",apply);ai::BotRecruitment::Prepare(&p,&b,"food","",apply);assert(b.health==50&&b.mana==5);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.combat=true;p.combat=true;command(p,"refill prepare 2 gear");assert(b.health==100);
 b.health=7;command(p,"refill prepare 2 gear");assert(b.health==7&&b.gear==1&&b.combat&&p.combat);}
 for(bool requesterCombat:{false,true}){reset();Player p(1,true),b(2);b.ai.master=&p;p.combat=requesterCombat;b.combat=!requesterCombat;
 assert(ai::BotRecruitment::PreparationReason(&p,&b)=="combat");
 for(auto cmd:{"food","drink","potions","pots","consumes","reagents","ammo"}){
 unsigned calls=0;auto apply=[&](){++calls;return std::string("food added");};
 assert(ai::BotRecruitment::Prepare(&p,&b,cmd,"",apply)=="refused: combat"&&calls==0);}
 unsigned calls=0;auto apply=[&](){++calls;return std::string("random gear equipped");};
 assert(ai::BotRecruitment::Prepare(&p,&b,"gear","",apply)=="random gear equipped");assert(calls==1&&b.health==100&&b.mana==100);
 assert(p.combat==requesterCombat&&b.combat!=requesterCombat);}


 reset();{Player p(1,true),b(2);b.combat=true;b.alive=false;b.afk=true;invite(p,b);tick();assert(b.group==p.group&&b.group);assert(!b.alive&&b.combat&&b.health==50&&b.gear==0&&!b.transfer);assert(b.ai.master==&p&&!b.afk);}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);tick();assert(!b.group);tick(15);assert(!b.invite&&!b.group&&has("timed_out"));b.transfer=false;tick();assert(!b.group);}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);tick(10);b.invite=nullptr;invite(p,b);tick(6);assert(b.invite);b.transfer=false;tick();assert(b.group);}
 reset();{Player p(1,true),other(3,true),b(2);command(p,"r reserve 2");invite(other,b);assert(!b.invite&&has("reserved"));invite(p,b);tick();assert(b.ai.master==&p);}
 reset();{Player p(1,true),other(3,true),b(2);invite(p,b);Group external;external.leader=other.GetObjectGuid();b.group=&external;tick();assert(b.group==&external&&!b.invite);}
 reset();{Player p(1,true),human(2,true);command(p,"x summon 2");assert(!human.transfer&&has("not_available_bot"));command(p,"y prepare 2 gear");assert(!human.gear);}
 reset();{Player p(1,true),b(2);b.session.account=999;assert(ai::BotRecruitment::Eligibility(&p,&b)=="not_authorized");b.session.account=1;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());b.session.account=999;p.guild=b.guild=7;sPlayerbotAIConfig.allowGuildBots=true;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());}
 reset();{Player p(1,true),b(2);b.team=1;assert(ai::BotRecruitment::Eligibility(&p,&b)=="wrong_faction");sWorld.cross=true;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());b.bgQueue=true;assert(ai::BotRecruitment::Eligibility(&p,&b).empty());}
 reset();{Player p(1,true),b(2);sWorld.defer=true;b.bgQueue=true;invite(p,b);tick();
 assert(!b.group&&b.invite&&b.queueCancellations==1);tick();assert(!b.group&&b.queueCancellations==1);
 sWorld.Drain();tick();assert(b.group&&b.ai.master==&p&&b.raidPreparations==1);}
 reset();{Player p(1,true),other(3,true),b(2);sWorld.defer=true;invite(p,b);tick();
 Group external;external.leader=other.GetObjectGuid();b.group=&external;sWorld.Drain();tick();
 assert(b.group==&external&&b.ai.master!=&p&&!b.invite);}
 for(unsigned queue=0;queue<4;++queue){reset();Player p(1,true),b(2);
 b.bgQueue=queue==0;b.session.m_lfgInfo.queued=queue==1;b.lfg.state=queue==2?3:0;b.bg=queue==3;
 assert(ai::BotRecruitment::Eligibility(&p,&b).empty());assert(!b.queueCancellations);
 invite(p,b);tick();assert(b.group==p.group&&b.group&&b.ai.master==&p);
 assert(b.queueCancellations==1&&!b.bgQueue&&!b.session.m_lfgInfo.queued&&b.lfg.state==0);}
 reset();{Player p(1,true),other(3,true),b(2);b.bgQueue=true;b.ai.master=&other;
 invite(p,b);tick();assert(!b.group&&b.bgQueue&&!b.queueCancellations&&has("other_controller"));}
 reset();{Player p(1,true),b(2);b.bgQueue=true;b.ai.security.allow=false;
 invite(p,b);tick();assert(!b.group&&b.bgQueue&&!b.queueCancellations&&has("recruitment_policy"));}
 reset();{Player p(1,true),b(2);b.transfer=true;invite(p,b);players.erase(1);tick();assert(!b.invite&&!b.group);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;b.combat=true;p.combat=true;ai::BotRecruitment::Queue(&p,&b,"summon");tick();assert(b.transfer&&!has("arrived"));assert(p.combat);b.transfer=false;b.distance=0;tick();assert(has("arrived"));assert(b.combat&&p.combat);}
 for(unsigned state=0;state<5;++state){reset();Player p(1,true),b(2);b.ai.master=&p;b.distance=100;
 b.taxi=state==0;b.transport=state==1;b.charm=state==2;b.bgQueue=state==3;b.alive=state!=4;
 ai::BotRecruitment::Queue(&p,&b,"summon");tick();assert(b.transfer&&has("teleport_started"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;b.transfer=true;
 command(p,"s summon 2");assert(!has("teleport_started")&&has("bot_transfer"));tick(41);assert(has("timed_out bot_transfer")&&b.summons==0);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;command(p,"s summon 2");
 p.mapId=2;b.distance=1000;b.transfer=false;tick();assert(has("arrived ok")&&b.summons==1);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;b.landingDistance=100;
 command(p,"s summon 2");for(int i=0;i<3;++i){b.transfer=false;tick(3);}assert(b.summons==3&&has("refused arrival_not_confirmed"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;command(p,"s summon 2");
 command(p,"repeat summon 2");assert(b.summons==1&&has("repeat 2 summon_pending existing_request"));ai::BotRecruitment::Queue(&p,&b,"summon");tick();assert(b.summons==1&&has("Bot2: summon_pending (bot_transfer)"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;p.transport=true;
 command(p,"s summon 2");assert(b.summons==0&&has("requester_transport"));p.transport=false;tick();assert(b.summons==1);}

 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=100;p.combat=true;command(p,"combat summon 2");assert(b.transfer&&has("teleport_started"));command(p,"combat summon 2");assert(b.transfer);b.transfer=false;b.distance=0;b.combat=true;tick();assert(has("arrived"));command(p,"prep prepare 2 gear");assert(b.gear==1&&b.combat&&p.combat);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.instance=1;ai::BotRecruitment::Queue(&p,&b,"summon");tick();assert(!b.transfer&&has("different_instance"));}
 // Same-map public companions must leave the old raid before the final summon.
 // Exercise the actual coordinator and departure helper for each core API.
 for(bool dead:{false,true}) {reset();Player p(1,true),b(2);Group g;
 g.leader=p.GetObjectGuid();g.raid=true;p.group=b.group=&g;b.ai.master=&p;
 p.mapId=b.mapId=409;p.instance=29;b.instance=27;p.map.raid=b.map.raid=true;
 g.binding.state=p.map.GetPersistentState();b.alive=!dead;
 ai::BotRecruitment::Queue(&p,&b,"summon");tick();
 assert(b.departures==1&&b.transfer&&b.summons==0&&b.health==50&&b.mana==5);
 assert(!State().summons.at(b.id).started&&has("leaving_previous_instance")&&!has("arrived"));
 tick();assert(b.departures==1&&b.summons==0&&b.ai.revivalChecks==0);
 b.transfer=false;b.mapId=0;b.instance=0;tick();assert(b.summons==1&&b.transfer&&!has("arrived"));
 assert(b.health==50&&b.mana==5&&b.alive==!dead);
 b.transfer=false;b.mapId=409;b.instance=29;b.alive=true;tick();
 assert(has("arrived")&&State().summons.empty()&&b.health==100&&b.mana==100&&b.departures==1);}
 // Genuine entry/ownership denials must not move the bot out of its old raid.
 for(unsigned denied=0;denied<8;++denied){reset();Player p(1,true),b(2);Group g;
 g.leader=p.GetObjectGuid();g.raid=true;p.group=b.group=&g;b.ai.master=&p;
 p.mapId=b.mapId=409;p.instance=29;b.instance=27;p.map.raid=b.map.raid=true;
 g.binding.state=p.map.GetPersistentState();
 if(denied==0){b.session.account=p.session.account;}
 if(denied==1)g.bound=false;
 if(denied==2)g.binding.state=b.map.GetPersistentState();
 if(denied==3)p.map.count=p.map.max;
 if(denied==4)p.map.data.active=true;
 if(denied==5)sMapStore.entry.instanced=true;
 if(denied==6)sMapStore.missing=true;
 if(denied==7)b.homeAccepted=false;
 ai::BotRecruitment::Queue(&p,&b,"summon");tick();
 assert(!b.departures&&!b.summons&&!b.transfer&&has("different_instance")&&b.health==50);}
 // A departure worldport fallback is bounded; it cannot repeatedly eject a bot.
 reset();{Player p(1,true),b(2);Group g;g.leader=p.GetObjectGuid();g.raid=true;
 p.group=b.group=&g;b.ai.master=&p;p.mapId=b.mapId=409;p.instance=29;b.instance=27;
 p.map.raid=b.map.raid=true;g.binding.state=p.map.GetPersistentState();
 ai::BotRecruitment::Queue(&p,&b,"summon");tick();b.transfer=false;tick();
 assert(b.departures==1&&!b.summons&&has("different_instance")&&State().summons.empty());}
 // Session/group changes cancel a staged request after departure as well.
 reset();{Player p(1,true),b(2);Group g;g.leader=p.GetObjectGuid();g.raid=true;
 p.group=b.group=&g;b.ai.master=&p;p.mapId=b.mapId=409;p.instance=29;b.instance=27;
 p.map.raid=b.map.raid=true;g.binding.state=p.map.GetPersistentState();
 ai::BotRecruitment::Queue(&p,&b,"summon");tick();b.transfer=false;b.mapId=0;b.group=nullptr;tick();
 assert(b.departures==1&&!b.summons&&has("membership_changed")&&b.health==50);}
 reset();{Player p(1,true),b(2);Group g;g.leader=p.GetObjectGuid();g.raid=true;
 p.group=b.group=&g;b.ai.master=&p;p.mapId=b.mapId=409;p.instance=29;b.instance=27;
 p.map.raid=b.map.raid=true;g.binding.state=p.map.GetPersistentState();
 ai::BotRecruitment::Queue(&p,&b,"summon");tick();tick(41);
 assert(b.departures==1&&!b.summons&&has("timed_out")&&State().summons.empty()&&b.health==50);}
 // Mixed 40-person raids retain the two-native-transfers-per-tick work bound.
 reset();{Player p(1,true);Group g;g.leader=p.GetObjectGuid();g.raid=true;g.count=40;
 p.group=&g;p.mapId=409;p.instance=29;p.map.raid=true;g.binding.state=p.map.GetPersistentState();
 std::vector<std::unique_ptr<Player>> bots;unsigned arrived=0;
 for(unsigned i=2;i<41;++i){bots.emplace_back(new Player(i));auto& b=*bots.back();
 b.group=&g;b.ai.master=&p;b.mapId=i%3?409:0;b.instance=i%3?27:0;b.map.raid=true;b.alive=i%2;
 assert(ai::BotRecruitment::Queue(&p,&b,"summon"));}
 for(unsigned n=0;n<80;++n){unsigned before=0;for(auto& b:bots)before+=b->departures+b->summons;
 tick();unsigned after=0;for(auto& b:bots){after+=b->departures+b->summons;
 if(b->transfer){b->transfer=false;b->mapId=b->summons?409:0;b->instance=b->summons?29:0;
 if(b->summons)b->alive=true;}}
 assert(after-before<=2);}
 for(auto& b:bots){assert(b->mapId==409&&b->instance==29&&b->summons==1&&b->departures<=1);
 assert(b->alive&&b->health==100&&b->mana==100);++arrived;}
 assert(arrived==39&&State().summons.empty()&&!has("refused")&&!has("timed_out"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.alive=false;sPlayerbotAIConfig.recruitmentRevive=false;command(p,"s summon 2");assert(b.transfer&&has("teleport_started"));}
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
 // A complete raid summon must fit even with normal recruitment traffic queued.
 for(bool dead : {false,true}) { reset(); Player p(1,true); std::vector<std::unique_ptr<Player>> bots;
 for(unsigned i=2;i<42;++i){bots.emplace_back(new Player(i));bots.back()->ai.master=&p;bots.back()->alive=!dead;}
 for(unsigned i=0;i<limits::MaxIncomingPerPlayer;++i) assert(ai::BotRecruitment::Queue(&p,bots[i].get(),"who"));
 for(unsigned i=0;i<39;++i) assert(ai::BotRecruitment::Queue(&p,bots[i].get(),"summon"));
 assert(State().incoming.size()==limits::MaxIncomingPerPlayer+39);
 assert(ai::BotRecruitment::Queue(&p,bots[0].get(),"summon")); // duplicate stays coalesced
 assert(State().incoming.size()==limits::MaxIncomingPerPlayer+39);
 assert(ai::BotRecruitment::Queue(&p,bots[39].get(),"summon"));
 Player extra(42);extra.ai.master=&p;assert(!ai::BotRecruitment::Queue(&p,&extra,"summon"));
 }
 assert(!limits::Arrived(true,false,true,1,2,1,3,0,true));assert(!limits::HasVacancy(25,25,true));
#if defined(MANGOSBOT_ZERO)
 const unsigned cap=60;
#elif defined(MANGOSBOT_ONE)
 const unsigned cap=70;
#else
 const unsigned cap=80;
#endif
 reset();{Player p(1,true);command(p,"cap discover 1 1 "+std::to_string(cap+1)+" 0");assert(has("refused arguments"));}
 reset();{Player p(1,true),b(2);b.level=cap;command(p,"cap discover 1 "+std::to_string(cap)+" "+std::to_string(cap)+" 0");assert(has("eligible"));}
 reset();{Player p(1,true),a(2),b(3),c(4),d(5);a.level=41;b.level=45;c.level=40;d.level=46;
 command(p,"bounds discover 1 41 45 0");assert(has("Bot2")&&has("Bot3")&&!has("Bot4")&&!has("Bot5"));}
 for(auto range:{"45 41","0 40","1x 40","-1 40","1 9999999999999"}){reset();Player p(1,true);command(p,std::string("bad discover 1 ")+range+" 0");assert(has("refused arguments"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.health=4;b.mana=2;
 command(p,"heal summon 2");assert(b.health==4&&b.mana==2);b.transfer=false;tick();
 assert(b.health==100&&b.mana==100&&p.health==50&&p.mana==5&&b.otherPower==23);
 b.health=7;b.mana=3;command(p,"heal summon 2");assert(b.health==7&&b.mana==3);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.maxMana=0;b.mana=0;b.health=4;
 command(p,"warrior summon 2");b.transfer=false;tick();assert(b.health==100&&b.mana==0&&b.otherPower==23);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.health=4;b.mana=2;b.landingDistance=100;
 command(p,"failed summon 2");for(int i=0;i<3;++i){b.transfer=false;tick(3);}assert(b.health==4&&b.mana==2);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.health=4;b.mana=2;b.summonFailure="instance_combat";b.summonRetryable=true;
 command(p,"pending summon 2");assert(has("summon_pending instance_combat")&&b.summonChecks==1&&!b.transfer);
 tick(0);assert(b.summonChecks==1);tick(1);assert(b.summonChecks==1);tick(1);assert(b.summonChecks==2);assert(b.health==4&&b.mana==2);
 b.summonFailure.clear();tick(2);assert(b.summons==1&&b.transfer);b.transfer=false;tick();assert(has("arrived")&&b.health==100&&b.mana==100);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.health=4;b.mana=2;b.summonFailure="lockout";
 command(p,"locked summon 2");assert(has("refused lockout")&&!b.transfer);tick(3);assert(b.summonChecks==1&&b.health==4&&b.mana==2);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.summonFailure="instance_full";b.summonRetryable=true;
 command(p,"full summon 2");assert(has("summon_pending instance_full"));tick(45);assert(has("timed_out instance_full")&&b.summons==0);}

 // Opt-in arrival diagnostics execute the real coordinator and safety guards.
 reset();{Player p(1,true),b(2);b.ai.master=&p;Group g;g.leader=p.GetObjectGuid();p.group=b.group=&g;
 command(p,"caps capabilities 0");assert(has("complete arrival_diag_v1=1;receipt_v1=1;epoch="+State().epoch));
 b.distance=10;command(p,"near status_diag 2 "+State().epoch);assert(has("PBRECRUIT 1 near 2 arrived ok"));assert(has("PBRECRUIT_DIAG 1 near 1 2 status current_readiness ok 10.000000 10.000000 1 0 1 0 none"));
 b.distance=10.01f;command(p,"far prepare_diag 2 gear "+State().epoch);assert(has("PBRECRUIT 1 far 2 refused not_arrived"));assert(has("prepare pre_mutation_refused too_far 10.010000 10.000000"));assert(b.gear==0);
 b.distance=0;command(p,"far prepare_diag 2 gear "+State().epoch);assert(b.gear==0); // A confirmed refusal requires a NEW ID after recovery.
 command(p,"new prepare_diag 2 gear "+State().epoch);assert(b.gear==1&&has("prepare mutation_complete ok 0.000000 10.000000 1 0 1 0 completed"));
 messages.clear();command(p,"new prepare_diag 2 gear "+State().epoch);assert(b.gear==1&&has("complete random gear equipped"));
 tick(limits::ReceiptSeconds+1);messages.clear();command(p,"new prepare_diag 2 gear "+State().epoch);assert(b.gear==1&&has("complete random gear equipped"));
 messages.clear();command(p,"recover receipt 2 new "+State().epoch);assert(b.gear==1&&has("PBRECRUIT 1 new 2 complete random gear equipped")&&has("PBRECRUIT_DIAG 1 new")&&has("PBRECRUIT 1 recover 2 complete receipt_found"));
 messages.clear();command(p,"recover receipt 2 new "+State().epoch);assert(b.gear==1&&has("PBRECRUIT 1 new 2 complete random gear equipped"));
 command(p,"missing receipt 2 never_seen "+State().epoch);assert(has("unknown receipt_missing")&&b.gear==1);
 command(p,"wrong receipt 3 new "+State().epoch);assert(has("refused receipt_bot_mismatch"));
 command(p,"epoch prepare_diag 2 gear 0");assert(has("refused epoch_changed")&&b.gear==1);
 command(p,"new prepare_diag 2 gear 0");command(p,"new prepare_diag 2 gear "+State().epoch);assert(b.gear==1&&has("complete random gear equipped")); // bad epoch cannot overwrite receipt
 }
 for(unsigned fault=0;fault<9;++fault){reset();Player p(1,true),b(2);b.ai.master=&p;Group g;g.leader=p.GetObjectGuid();p.group=b.group=&g;
  const char* expected="";
  if(fault==0){p.world=false;expected="requester_not_in_world";}if(fault==1){b.world=false;expected="bot_not_in_world";}
  if(fault==2){p.transfer=true;expected="requester_transferring";}if(fault==3){b.transfer=true;expected="bot_transferring";}
  if(fault==4){b.alive=false;expected="bot_dead";}if(fault==5){b.mapId=2;expected="different_map";}
  if(fault==6){b.instance=99;expected="different_instance";}if(fault==7){b.los=false;expected="no_line_of_sight";}
  if(fault==8){b.separateMap=true;expected="different_instance";}
  auto arrival=EvaluateArrival(&p,&b);assert(std::string(limits::ArrivalReason(arrival.condition))==expected);
  if(fault!=7)assert(!b.distanceChecks&&!b.losChecks);
  command(p,"denied prepare_diag 2 gear "+State().epoch);assert(b.gear==0&&has("refused not_arrived")&&has(std::string("pre_mutation_refused ")+expected));
  messages.clear();command(p,"check status_diag 2 "+State().epoch);assert(has(std::string("current_readiness ")+expected));
 }
 reset();{Player p(1,true),b(2);b.ai.master=&p;Group g;g.leader=p.GetObjectGuid();p.group=b.group=&g;b.los=false;
 command(p,"legacy prepare 2 gear");assert(has("PBRECRUIT 1 legacy 2 refused not_arrived")&&!has("PBRECRUIT_DIAG")&&!b.gear);
 command(p,"status status 2");assert(has("PBRECRUIT 1 status 2 joined not_nearby")&&!has("PBRECRUIT_DIAG"));
 }
 reset();{Player p(1,true),b(2);b.ai.master=&p;Group g;g.leader=p.GetObjectGuid();p.group=b.group=&g;
 command(p,"landing summon_diag 2 "+State().epoch);b.transfer=false;b.distance=50;b.landingDistance=0;tick();
 assert(has("PBRECRUIT 1 landing 2 arrived ok")&&has("summon accepted_landing ok"));
 command(p,"current status_diag 2 "+State().epoch);assert(has("joined not_nearby")&&has("status current_readiness too_far"));
 command(p,"gear prepare_diag 2 gear "+State().epoch);assert(!b.gear&&has("pre_mutation_refused too_far"));
 }
 reset();{Player p(1,true),other(3,true),b(2);b.ai.master=&other;command(p,"owned prepare_diag 2 gear "+State().epoch);assert(!b.gear&&has("other_controller"));
 b.ai.master=&p;Player conflict(4);conflict.name=b.name;command(p,"identity prepare_diag 2 gear "+State().epoch);assert(!b.gear&&has("name_identity_conflict"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.combat=true;command(p,"supply prepare_diag 2 food "+State().epoch);assert(!b.gear&&has("pre_mutation_refused combat")&&has("1 0 1 0 none"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.applyResult="refused: after_partial_work";command(p,"uncertain prepare_diag 2 gear "+State().epoch);
 assert(b.gear==1&&has("mutation_uncertain after_partial_work")&&has("1 0 1 0 uncertain"));messages.clear();command(p,"uncertain prepare_diag 2 gear "+State().epoch);assert(b.gear==1&&has("mutation_uncertain"));assert(!State().explicitPreparation&&!State().preparationTrace);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;command(p,"finished prepare_diag 2 gear "+State().epoch);messages.clear();command(p,"stop cancel 2");assert(b.gear==1&&has("cancelled completed_work_kept"));command(p,"saved receipt 2 finished "+State().epoch);assert(b.gear==1&&has("PBRECRUIT 1 finished 2 complete random gear equipped"));}
 reset();{Player p(1,true),far(2),near(3);far.ai.master=near.ai.master=&p;far.distance=50;command(p,"failed prepare_diag 2 gear "+State().epoch);command(p,"other prepare_diag 3 gear "+State().epoch);assert(!far.gear&&near.gear==1);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;command(p,"transfer summon_diag 2 "+State().epoch);command(p,"cancel cancel 2");b.transfer=false;tick();assert(has("cancelled transfer_may_complete")&&!b.gear);
 command(p,"old receipt 2 transfer "+State().epoch);assert(has("PBRECRUIT 1 transfer 2 cancelled transfer_may_complete"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;
 for(unsigned i=0;i<40;++i)command(p,"poll"+std::to_string(i)+" status_diag 2 "+State().epoch);
 assert(sLog.diagnostics==0&&has("PBRECRUIT_DIAG 1 poll39"));
 b.distance=50;command(p,"refusal prepare_diag 2 gear "+State().epoch);
 assert(sLog.diagnostics==1&&!b.gear&&has("pre_mutation_refused too_far"));}
 reset();{Player p(1,true),b(2);b.ai.master=&p;b.distance=50;for(unsigned i=0;i<30;++i)command(p,"log"+std::to_string(i)+" prepare 2 gear");assert(sLog.diagnostics==limits::DiagnosticEventsPerPlayerPerSecond&&!b.gear);
 unsigned logs=sLog.diagnostics;for(unsigned i=0;i<20;++i)tick();assert(sLog.diagnostics==logs);}
 reset();{Player p(1,true),b(2);b.ai.master=&p;
 for(unsigned i=0;i<limits::MaxPreparationReceiptsPerPlayer;++i)State().preparationReceipts[{1,"kept"+std::to_string(i)}]={"prepare 2 gear","PBRECRUIT 1 kept 2 complete random gear equipped",0};
 command(p,"bounded prepare_diag 2 gear "+State().epoch);assert(!b.gear&&has("refused receipt_limit")&&has("pre_mutation_refused receipt_limit"));}
 reset();{std::vector<std::unique_ptr<Player>> owners,bots;for(unsigned o=0;o<5;++o){owners.emplace_back(new Player(100+o,true));bots.emplace_back(new Player(200+o));bots.back()->ai.master=owners.back().get();bots.back()->distance=50;
 for(unsigned i=0;i<10;++i)command(*owners.back(),"diag"+std::to_string(i)+" prepare "+std::to_string(200+o)+" gear");}
 assert(sLog.diagnostics==limits::DiagnosticEventsPerSecond);}
 std::cout<<"PASS: actual coordinator permissions, native invitations, summon/arrival separation, structured readiness, pre-mutation refusal, lost ACK recovery, retained replay, cancellation, v1 compatibility and bounded diagnostics\n";
}
'''
policy=(root/'playerbot/RecruitmentPolicy.h').read_text().replace('#pragma once','')
with tempfile.TemporaryDirectory(prefix='pb-recruitment-') as directory:
    folder=Path(directory);cpp=folder/'test.cpp';exe=folder/'test.exe'
    cpp.write_text(stubs+'\n'+policy+'\n'+header+'\n'+source+'\n'+tests)
    for macro in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/D'+macro,str(cpp),'/Fe:'+str(exe),'/Fo:'+str(folder/'test.obj')],check=True)
        subprocess.run([str(exe)],check=True)
