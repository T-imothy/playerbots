"""Execute the actual shared logout method against save-counting sessions."""
from pathlib import Path
import subprocess, tempfile, sys
source=Path(sys.argv[1])
text=(source/'playerbot/PlayerbotMgr.cpp').read_text()
start=text.index('void PlayerbotHolder::LogoutPlayerBot(')
end=text.index('\nvoid PlayerbotHolder::DisablePlayerBot',start)
body=text[start:end]
code=r'''
#include <cassert>
#include <ctime>
#include <map>
#include <memory>
using uint32=unsigned;
enum {CMSG_LOGOUT_REQUEST};
#define BOT_TEXT(x) x
struct WorldPacket { WorldPacket(int=0){} };
struct Player;
struct WorldSession {
 bool due=false,logging=false,save=true; int saves=0,logouts=0,queued=0;
 bool ShouldLogOut(time_t)const{return due;}
 bool isLogingOut()const{return logging;}
 bool ShouldSaveOnLogout()const{return save;}
 void QueuePacket(std::unique_ptr<WorldPacket>){++queued;}
 void LogoutPlayer(){++logouts;if(save)++saves;}
 unsigned GetAccountId()const{return 1;}
};
struct PlayerbotAI {
 Player* GetMaster(){return nullptr;}
 bool HasActivePlayerMaster(){return false;}
 void TellPlayer(Player*,const char*){}
};
struct Group {};
struct Player {
 WorldSession session; PlayerbotAI ai; bool stunned=false;
 PlayerbotAI* GetPlayerbotAI(){return &ai;}
 WorldSession* GetSession(){return &session;}
 Group* GetGroup(){return nullptr;}
 bool InBattleGround(){return false;} bool InBattleGroundQueue(){return false;}
 bool IsStunnedByLogout(){return stunned;}
 const char* GetName(){return "test";}
 void SaveToDB(){++session.saves;}
};
struct Config{bool bExplicitDbStoreSave=true;}sPlayerbotAIConfig;
struct Store{void Save(PlayerbotAI*){}}sPlayerbotDbStore;
struct Log{void outDebug(const char*,const char*){}}sLog;
struct World{bool FindSession(unsigned){return true;}}sWorld;
struct PlayerbotHolder{
 Player* bot=nullptr; std::map<unsigned,Player*> playerBots;
 Player* GetPlayerBot(unsigned){return bot;}
 void LogoutPlayerBot(uint32,bool,bool);
};
'''+body+r'''
int main(){
 // Exhaust all meaningful save policy / logout timing combinations.
 for(bool instant:{false,true})for(bool due:{false,true})
 for(bool logging:{false,true})for(bool save:{false,true})
 for(bool deleting:{false,true})for(bool stunned:{false,true}){
  Player p;p.session.due=due;p.session.logging=logging;
  p.session.save=save;p.stunned=stunned;
  PlayerbotHolder h;h.bot=&p;h.playerBots[1]=&p;
  h.LogoutPlayerBot(1,instant,deleting);
  bool immediate=instant&&(due||!logging);
  int expected=immediate ? (save ? 1 : !deleting) : !deleting;
  assert(p.session.saves==expected);
  assert(p.session.logouts==int(immediate));
  assert(p.session.queued==int(!instant&&!stunned&&!logging));
 }
 PlayerbotHolder empty;empty.LogoutPlayerBot(999,true,false);
}
'''
with tempfile.TemporaryDirectory(prefix='logout-save-') as folder:
 p=Path(folder);f=p/'test.cpp';f.write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(f),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
print('PASS: 64 actual-logout cases; exactly one required save, deferred saves retained, deletion policy preserved')
