"""Exercise the actual security policy, with queue override only for recruitment."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
header=(root/'playerbot/PlayerbotSecurity.h').read_text()
body=block((root/'playerbot/PlayerbotSecurity.cpp').read_text(),'PlayerbotSecurityLevel PlayerbotSecurity::LevelFor(')
code=r'''
#include <cassert>
#include <cstdint>
#include <ctime>
#include <map>
#include <string>
using uint8=uint8_t;using uint32=uint32_t;using uint64=uint64_t;
constexpr int SEC_GAMEMASTER=2,CONFIG_BOOL_ALLOW_TWO_SIDE_INTERACTION_GROUP=0,CONFIG_UINT32_MAX_PLAYER_LEVEL=1;
struct Player;
__HEADER__
struct GroupReference{Player* getSource(){return nullptr;}GroupReference* next(){return nullptr;}};
struct Group{bool bg=false;uint32 leader=0;GroupReference* GetFirstMember(){return nullptr;}
 bool IsFull(){return false;}bool IsBattleGroup(){return bg;}uint32 GetLeaderGuid(){return leader;}};
struct Session{int security=0;uint32 account=2;struct{bool queued=false;}m_lfgInfo;
 int GetSecurity(){return security;}uint32 GetAccountId(){return account;}};
struct AI{bool opposing=false,master=false;bool IsOpposing(Player*){return opposing;}
 bool HasRealPlayerMaster(){return master;}uint32 GetEquipGearScore(Player*,bool,bool){return 100;}};
struct Player{Session session;AI ai;Group* group=nullptr;Group* original=nullptr;uint32 guild=0,level=37;bool bgQueue=false;
 Session* GetSession(){return &session;}AI* GetPlayerbotAI(){return &ai;}Group* GetGroup(){return group;}
 Group* GetOriginalGroup(){return original;}uint32 GetObjectGuid(){return 42;}uint32 GetGuildId(){return guild;}
 uint32 GetLevel(){return level;}bool InBattleGroundQueue(){return bgQueue;}};
struct Config{int levelCheck=10;bool gearscorecheck=false;}sPlayerbotAIConfig;
struct World{struct Queue{bool queued=false;bool IsPlayerInQueue(uint32){return queued;}}queue;
 Queue& GetLFGQueue(){return queue;}unsigned getConfig(int key){return key==CONFIG_UINT32_MAX_PLAYER_LEVEL?80:0;}}sWorld;
PlayerbotSecurity::PlayerbotSecurity(Player* const b):bot(b),account(1){}
__BODY__
int main(){Player human,bot;PlayerbotSecurity security(&bot);
 assert(security.LevelFor(&human)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE);
 bot.bgQueue=true;assert(security.LevelFor(&human)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_TALK);
 assert(security.LevelFor(&human,nullptr,false,true)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE);
 bot.bgQueue=false;sWorld.queue.queued=true;bot.ai.master=true;bot.session.m_lfgInfo.queued=true;
#if !defined(MANGOSBOT_TWO)
 assert(security.LevelFor(&human)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_TALK);
#endif
 assert(security.LevelFor(&human,nullptr,false,true)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE);
 bot.ai.opposing=true;assert(security.LevelFor(&human,nullptr,false,true)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_DENY_ALL);
 bot.ai.opposing=false;bot.level=60;assert(security.LevelFor(&human,nullptr,false,true)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_TALK);
 bot.level=37;Group bg;bg.bg=true;bot.group=&bg;
 assert(security.LevelFor(&human,nullptr,false,true)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE);
 Group party;bot.original=&party;
 assert(security.LevelFor(&human,nullptr,false,true)==PlayerbotSecurityLevel::PLAYERBOT_SECURITY_GUILD);
}
'''.replace('__HEADER__',header).replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='pb-recruit-security-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 for macro in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/D'+macro,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
  print('PASS:',macro,'actual security policy: recruitment queue override, faction/level/group protections')
