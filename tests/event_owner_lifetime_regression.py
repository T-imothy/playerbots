"""Compile actual event/command/trigger code; reproduce stale owner access with ASan.

Pass --before to compile the deployed source from Git for the negative control.
Core registry/session/packet interfaces are test doubles, not a live realm.
"""
from pathlib import Path
import os, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[1]
before = '--before' in sys.argv
def source(path):
    if before:
        return subprocess.check_output(['C:/Program Files/Git/cmd/git.exe', '-c',
            'safe.directory='+root.as_posix(), '-C', str(root), 'show',
            '4a72b831:'+path], text=True)
    return (root/path).read_text()
def strip(s):
    return '\n'.join(x for x in s.splitlines() if not x.startswith('#include') and not x.startswith('#pragma'))
def between(s,a,b): return s[s.index(a):s.index(b,s.index(a))]

preamble = r'''
#include <cassert>
#include <cstdint>
#include <ctime>
#include <map>
#include <string>
#include <vector>
#include <iostream>
using uint32 = uint32_t;
constexpr unsigned CHAT_MSG_WHISPER=7;
struct ObjectGuid {
 uint64_t id=0; ObjectGuid(uint64_t id=0):id(id){}
 bool operator<(ObjectGuid rhs)const{return id<rhs.id;}
};
struct WorldPacket {
 std::vector<ObjectGuid> data;
 bool empty()const{return data.empty();} void rpos(int){}
 WorldPacket& operator<<(ObjectGuid g){data.push_back(g);return *this;}
 WorldPacket& operator>>(ObjectGuid& g){g=data.front();return *this;}
};
struct Player;
struct Session { Player* player=nullptr; Player* GetPlayer(){return player;} };
struct Player { ObjectGuid guid; Session* session; Player(uint64_t g,Session* s):guid(g),session(s){s->player=this;}
 ObjectGuid GetObjectGuid(){return guid;} Session* GetSession(){return session;}
};
std::map<ObjectGuid,Player*> online;
struct ObjectAccessor { static Player* FindPlayer(ObjectGuid g,bool){auto i=online.find(g);return i==online.end()?nullptr:i->second;} };
'''
event = strip(source('playerbot/strategy/Event.h'))
event_cpp = strip(source('playerbot/strategy/Event.cpp'))
holder = between(source('playerbot/PlayerbotAI.h'),'class ChatCommandHolder','class PlayerbotAI :')
trigger = r'''
class PlayerbotAI {};
namespace ai {
class Trigger {
public:
 Trigger(PlayerbotAI*,std::string n):name(n){}
 virtual void ExternalEvent(std::string,Player*){}
 virtual void ExternalEvent(WorldPacket&,Player*){}
 virtual Event Check(){return Event();} virtual void Reset(){}
 std::string getName(){return name;}
protected: std::string name,param; bool triggered=false;
 OWNER_TYPE owner;
};
}
'''.replace('OWNER_TYPE', 'Player*' if before else 'EventOwner')
chat = strip(source('playerbot/strategy/triggers/ChatCommandTrigger.h'))
packet = strip(source('playerbot/strategy/triggers/WorldPacketTrigger.h'))
test = r'''
int main(){
 Session s; Player* p=new Player(17,&s); online[p->guid]=p;
 Event query("stance","?",p); Event copied(query); Event assigned; assigned=query;
 ChatCommandHolder delayed("stance ?",p,CHAT_MSG_WHISPER,100);
 ChatCommandHolder delayedCopy(delayed);
 ai::ChatCommandTrigger chat(nullptr,"stance"); chat.ExternalEvent("?",p);
 WorldPacket packet; packet<<ObjectGuid(123);
 ai::WorldPacketTrigger network(nullptr,"proposal"); network.ExternalEvent(packet,p);
 Event packetEvent("packet",packet,p); Event guidEvent("guid",ObjectGuid(123),p);
 Event scheduled=chat.Check();
 assert(query.getOwner()==p && copied.getOwner()==p && assigned.getOwner()==p);
 assert(delayed.GetOwner()==p && delayedCopy.GetOwner()==p);
 assert(chat.Check().getOwner()==p && network.Check().getOwner()==p);
 assert(packetEvent.getObject().id==123 && guidEvent.getObject().id==123);
 Event internal("internal",std::string("?")); assert(!internal.getOwner() && !!internal);
 assert(!Event());
 online.erase(p->guid); s.player=nullptr; delete p;
 // Negative control uses the exact old accessor: ASan detects the dereference.
 if(Player* stale=query.getOwner()) { volatile auto oldGuid=stale->GetObjectGuid().id; (void)oldGuid; }
 assert(!query.getOwner() && !copied.getOwner() && !assigned.getOwner());
 assert(!scheduled.getOwner() && !packetEvent.getOwner() && !guidEvent.getOwner());
 assert(!delayed.GetOwner() && !delayedCopy.GetOwner());
 assert(!chat.Check() && !network.Check());
 assert(!query && !scheduled); // expired user commands cannot become ownerless work
 Session s2; Player replacement(17,&s2); online[replacement.guid]=&replacement;
 assert(!query.getOwner() && !delayed.GetOwner());
 Event fresh("stance","?",&replacement); assert(fresh.getOwner()==&replacement);
 s2.player=nullptr; assert(!fresh.getOwner()); // detached session
 s2.player=&replacement; replacement.session=nullptr; assert(!fresh.getOwner());
 online.clear();
 assert(!!internal); // autonomous bot reactions still work
 std::cout<<"PASS: live, copied, delayed, triggered, queued, packet, GUID, logout, replacement login, detached session, ownerless events\n";
}
'''
with tempfile.TemporaryDirectory(prefix='bot-event-lifetime-') as temp:
    path=Path(temp); cpp=path/'test.cpp'; exe=path/'test.exe'
    cpp.write_text(preamble+event+event_cpp+holder+trigger+chat+packet+test)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/Zi','/fsanitize=address','/Od',str(cpp),'/Fe:'+str(exe),'/link','/INCREMENTAL:NO'],cwd=path,check=True)
    result=subprocess.run([str(exe)],cwd=path,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    print(result.stdout)
    if before:
        assert result.returncode!=0 and 'heap-use-after-free' in result.stdout, 'negative control failed to reproduce stale access'
        print('PASS: deployed code reproduces heap-use-after-free')
    else:
        assert result.returncode==0, result.returncode
        # Ensure every queue-to-execution boundary uses the tested validity rule.
        for name in ('Engine','ReactionEngine'):
            body=source('playerbot/strategy/'+name+'.cpp').split('bool '+name+'::ListenAndExecute(',1)[1]
            assert body.index('!event.IsOwnerAvailable()') < body.index('actionExecutionListeners.Before(')
        commands=source('playerbot/PlayerbotAI.cpp').split('void PlayerbotAI::HandleCommands()',1)[1]
        assert commands.index('!holder.IsOwnerAvailable()') < commands.index('helper.ParseChatCommand(')
