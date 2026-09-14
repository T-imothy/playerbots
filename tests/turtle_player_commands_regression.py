from pathlib import Path
from turtle_cpp_fixture import run
r=Path(__file__).resolve().parents[3]
s=(r/'modules/ManTechPlayerbots/playerbot/PlayerbotMgr.cpp').read_text(encoding='utf-8')
def function(signature):
    begin=s.index(signature);brace=s.index('{',begin);depth=1;i=brace+1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[begin:i]
callback=function('void PlayerbotHolder::HandlePlayerBotLoginCallback(')
register=function('void PlayerbotHolder::RegisterPendingBotLogin(')
destructor=function('PlayerbotHolder::~PlayerbotHolder()')
summon=function('std::string PlayerbotHolder::HandleBotSummon(')
run(r'''#include <map>
#include <mutex>
#include <string>
#include <cassert>
#include <cstdint>
#include <cstdio>
using uint32=uint32_t;using uint64=uint64_t;
constexpr int HIGHGUID_PLAYER=0,LOCALE_enUS=0;
struct ObjectGuid{uint32 n=0;ObjectGuid()=default;ObjectGuid(int,uint32 v):n(v){}uint32 GetCounter()const{return n;}};
struct QueryResult{};
int deleted=0;
struct SqlQueryHolder{virtual ~SqlQueryHolder(){++deleted;}};
struct LoginQueryHolder:SqlQueryHolder{ObjectGuid guid{0,32};ObjectGuid GetGuid(){return guid;}};
struct Player{};Player bot,master;
struct PlayerbotHolder{int logins=0,amount=0;virtual ~PlayerbotHolder();void RegisterPendingBotLogin(SqlQueryHolder*,uint32,uint32);void HandlePlayerBotLoginCallback(QueryResult*,SqlQueryHolder*);uint32 GetPlayerbotsAmount(){return amount;}void OnBotLogin(Player*p){assert(p==&bot);++logins;}std::string HandleBotSummon(Player*,Player*,const std::string);};
struct Random:PlayerbotHolder{int events=0;void SetValue(uint32,const char*,int){++events;}uint32 GetValue(uint32,const char*){return 6000;}}sRandomPlayerbotMgr;
struct PendingBotLogin{ObjectGuid botGuid;uint32 masterAccountId;PlayerbotHolder*owner;uint64 ownerGeneration;};
std::map<SqlQueryHolder*,PendingBotLogin> m_pendingBotLogins;
std::mutex&HolderRegistryLock(){static auto*p=new std::mutex;return *p;}
std::map<PlayerbotHolder*,uint64>&HolderRegistry(){static auto*p=new std::map<PlayerbotHolder*,uint64>;return *p;}
struct{bool asyncBotLogin=false;}sPlayerbotAIConfig;
struct{Player*value=nullptr;Player*GetPlayer(ObjectGuid,bool){return value;}}sObjectMgr;
enum class HeadlessSessionStartResult{Started,Failed};
struct{int calls=0;bool fail=false;HeadlessSessionStartResult StartPreparedHeadlessSession(LoginQueryHolder*h,int,const char*){++calls;delete h;if(fail)return HeadlessSessionStartResult::Failed;sObjectMgr.value=&bot;return HeadlessSessionStartResult::Started;}}sWorld;
struct BotRecruitment{static inline int calls=0;static inline bool accepted=true;static bool Queue(Player*o,Player*b,std::string const&operation){assert(o==&master&&b==&bot&&operation=="summon");++calls;return accepted;}};
'''+register+callback+destructor+summon+r'''
int main(){
  PlayerbotHolder owner;HolderRegistry()[&owner]=1;HolderRegistry()[&sRandomPlayerbotMgr]=2;
  auto request=[&](PlayerbotHolder&recipient){auto*h=new LoginQueryHolder;recipient.RegisterPendingBotLogin(h,32,25);return h;};
  auto*h=request(owner);sRandomPlayerbotMgr.HandlePlayerBotLoginCallback(nullptr,h);assert(owner.logins==1&&sRandomPlayerbotMgr.logins==0&&sWorld.calls==1&&deleted==1);
  // A replacement manager at the same address must not receive an old result.
  sObjectMgr.value=nullptr;h=request(owner);HolderRegistry()[&owner]=3;sRandomPlayerbotMgr.HandlePlayerBotLoginCallback(nullptr,h);assert(owner.logins==1&&sWorld.calls==1&&deleted==2);
  auto*gone=new PlayerbotHolder;HolderRegistry()[gone]=4;h=request(*gone);delete gone;assert(!m_pendingBotLogins.count(h));sRandomPlayerbotMgr.HandlePlayerBotLoginCallback(nullptr,h);assert(sWorld.calls==1&&deleted==3);
  sObjectMgr.value=&bot;h=request(owner);sRandomPlayerbotMgr.HandlePlayerBotLoginCallback(nullptr,h);assert(sWorld.calls==1&&deleted==4);
  sObjectMgr.value=nullptr;sWorld.fail=true;h=request(owner);sRandomPlayerbotMgr.HandlePlayerBotLoginCallback(nullptr,h);assert(owner.logins==1&&sWorld.calls==2&&deleted==5);
  sWorld.fail=false;sRandomPlayerbotMgr.amount=6000;h=request(sRandomPlayerbotMgr);sRandomPlayerbotMgr.HandlePlayerBotLoginCallback(nullptr,h);assert(sWorld.calls==2&&deleted==6&&sRandomPlayerbotMgr.events==1);
  assert(owner.HandleBotSummon(nullptr,&master,"").find("offline")!=std::string::npos);
  assert(owner.HandleBotSummon(&bot,nullptr,"").find("required")!=std::string::npos);assert(BotRecruitment::calls==0);
  assert(owner.HandleBotSummon(&bot,&master,"")=="summon request queued"&&BotRecruitment::calls==1);
  BotRecruitment::accepted=false;assert(owner.HandleBotSummon(&bot,&master,"").find("could not")!=std::string::npos);
  puts("PASS actual login callback: original owner, replaced/destroyed manager, duplicate login, native failure, population cap; summon routing and rejection");
}
''')
