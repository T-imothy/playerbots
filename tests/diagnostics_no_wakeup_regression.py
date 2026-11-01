"""Execute the actual console probe handler and preserve the pending action wait."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
body=block((root/'playerbot/PlayerbotMgr.cpp').read_text(),'std::string PlayerbotHolder::HandleBotDebug(')
code=r'''
#include <cassert>
#include <iostream>
#include <string>
#include <vector>
struct PlayerbotAI;
struct Player {PlayerbotAI*ai=nullptr;bool available=true;PlayerbotAI*GetPlayerbotAI(){return ai;}};
struct Event {std::string param;Player*owner;Event(const char*,std::string p,Player*o):param(p),owner(o){}bool IsOwnerAvailable(){return owner&&owner->available;}};
struct Action {unsigned direct=0;bool ok=true;bool Execute(Event&){++direct;return ok;}};
struct Context {Action action;bool present=true;Action*GetAction(const char*){return present?&action:nullptr;}};
struct PlayerbotAI {Context context;unsigned delay=10000,engineCalls=0;std::string last="cast frostbolt";std::vector<std::string>messages={"snapshot"};
 void RecordMessages(bool,bool){}Context*GetAiObjectContext(){return &context;}
 bool DoSpecificAction(const char*,Event,bool){++engineCalls;delay=100;last="debug";return true;}
 auto GetRecordedMessages(){return messages;}};
struct PlayerbotHolder {std::string HandleBotDebug(Player*,Player*,const std::string);};
__BODY__
int main(){
 PlayerbotHolder holder;PlayerbotAI ai;Player bot{&ai},master{&ai};
 assert(holder.HandleBotDebug(nullptr,nullptr,"why")=="debug requires a bot");
 Player plain;assert(holder.HandleBotDebug(&plain,nullptr,"why")=="Bot has no AI");
 for(unsigned wait:{0u,100u,2500u,10000u,30000u})for(const char*probe:{"why","engine","history","position"}){
  ai.delay=wait;ai.last="cast frostbolt";auto before=ai.engineCalls;
  assert(holder.HandleBotDebug(&bot,nullptr,probe)=="snapshot\n");
  assert(ai.delay==wait&&ai.last=="cast frostbolt"&&ai.engineCalls==before);
 }
 auto before=ai.context.action.direct;master.available=false;
 assert(holder.HandleBotDebug(&bot,&master,"why")=="debug failed"&&ai.context.action.direct==before);
 master.available=true;ai.context.present=false;assert(holder.HandleBotDebug(&bot,nullptr,"why")=="debug failed");ai.context.present=true;
 ai.context.action.ok=false;assert(holder.HandleBotDebug(&bot,nullptr,"why")=="debug failed");ai.context.action.ok=true;
 for(const char*command:{"position teleport","setvalueuin32 bg type,2","mount","unmount","history clear"}){
  auto n=ai.engineCalls;holder.HandleBotDebug(&bot,nullptr,command);assert(ai.engineCalls==n+1);
 }
 std::cout<<"PASS actual console diagnostics preserve idle/cast waits and last action; mutation dispatch and owner safety preserved\n";
}
'''.replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='bot-probe-no-wakeup-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
