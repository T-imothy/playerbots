"""Execute the actual admin action dispatcher, including parameter parsing and recording cleanup."""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/PlayerbotMgr.cpp').read_text()
if '--before' in sys.argv:
    source=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show',
        'c016ca372ed6e16773164e1086d44ceb64b1663a:playerbot/PlayerbotMgr.cpp'],text=True)
method=block(source,'std::string PlayerbotHolder::HandleBotDo(')
code=r'''
#include <cassert>
#include <string>
#include <vector>
#include <set>
#include <iostream>
struct Player;
struct Event {std::string source,param;Player* owner;Event(std::string s,std::string p,Player*o):source(s),param(p),owner(o){}};
struct Action {};
struct Context {std::set<std::string> names{"debug","move to","attack","move"};Action action;
 Action* GetAction(std::string n){return names.count(n)?&action:nullptr;}};
struct PlayerbotAI {Context context;bool recording=false,result=true;unsigned calls=0;
 std::string action,param;Player* owner=nullptr;std::vector<std::string> messages,output;
 Context* GetAiObjectContext(){return &context;}void RecordMessages(bool value,bool=false){recording=value;if(!value)messages.clear();}
 bool DoSpecificAction(std::string name,Event event,bool forced){assert(forced&&event.source==".bot");++calls;action=name;param=event.param;owner=event.owner;messages=output;return result;}
 std::vector<std::string> GetRecordedMessages(){recording=false;auto copy=messages;messages.clear();return copy;}
};
struct Player {PlayerbotAI* ai=nullptr;PlayerbotAI* GetPlayerbotAI(){return ai;}std::string GetName(){return "Testbot";}};
struct PlayerbotHolder {std::vector<std::string> errors;std::vector<std::string> GetBotErrors(std::string){return errors;}
 std::string HandleBotDo(Player*,Player*,const std::string);};
__METHOD__
int main(){
 PlayerbotAI ai;Player bot{&ai},master;PlayerbotHolder holder;
 assert(holder.HandleBotDo(nullptr,nullptr,"attack")=="do requires a bot");
 assert(holder.HandleBotDo(&master,nullptr,"attack")=="Bot has no AI");
 assert(holder.HandleBotDo(&bot,nullptr,"attack")=="(no output)"&&ai.action=="attack"&&ai.param.empty()&&ai.owner==&bot&&!ai.recording);
 ai.output={"position"};assert(holder.HandleBotDo(&bot,&master,"debug position ground")=="position\n");
 assert(ai.action=="debug"&&ai.param=="position ground"&&ai.owner==&master&&!ai.recording);
 assert(holder.HandleBotDo(&bot,nullptr,"move to 1 2 3")=="position\n"&&ai.action=="move to"&&ai.param=="1 2 3");
 unsigned calls=ai.calls;assert(holder.HandleBotDo(&bot,nullptr,"missing action parameter")=="action not found"&&ai.calls==calls);
 ai.result=false;assert(holder.HandleBotDo(&bot,nullptr,"attack")=="action failed"&&!ai.recording&&ai.messages.empty());
 holder.errors={"cannot reach","blocked"};assert(holder.HandleBotDo(&bot,nullptr,"move to 1 2 3")=="cannot reach\nblocked\n"&&!ai.recording);
 std::cout<<"PASS: actual bot action command, longest action prefix, parameters and failed-action recording cleanup\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-bot-do-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
