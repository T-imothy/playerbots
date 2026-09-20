"""Exercise the native port of upstream cross-map dispatch without a running realm."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/PlayerbotAI.cpp').read_text(encoding='utf8'),'void PlayerbotAI::RunOnOwningThread(')
code=r'''
#include <cassert>
#include <functional>
#include <map>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;
struct Player {unsigned guid=1,map=0;bool world=true,teleport=false;ObjectGuid GetObjectGuid(){return guid;}unsigned GetGUIDLow(){return guid;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return teleport;}};
struct PlayerbotAI{Player* bot;bool IsSafe(Player* p){return p->map==bot->map&&!p->teleport;}void RunOnOwningThread(Player*,std::function<void(Player*)>);};
struct Accessor{std::map<ObjectGuid,Player*> players;Player* FindPlayer(ObjectGuid g){auto i=players.find(g);return i==players.end()?nullptr:i->second;}}sObjectAccessor;
struct Log{unsigned errors=0;void outError(const char*,unsigned){++errors;}}sLog;
namespace ai {struct Event{};struct WorldActions{static bool mapExecution;bool accept=true;std::function<void(PlayerbotAI&)> task;static bool IsMapExecution(){return mapExecution;}static WorldActions& Instance(){static WorldActions q;return q;}bool Enqueue(Player*,std::string,Event,std::function<void(PlayerbotAI&)> f){if(!accept)return false;task=f;return true;}};bool WorldActions::mapExecution=false;}
__METHOD__
int main(){
 Player actor,target;target.guid=2;target.map=1;PlayerbotAI ai{&actor};sObjectAccessor.players[2]=&target;
 unsigned calls=0;auto action=[&](Player* p){assert(p==&target);++calls;};auto& q=ai::WorldActions::Instance();
 ai.RunOnOwningThread(nullptr,action);ai.RunOnOwningThread(&target,{});assert(calls==0);
 ai.RunOnOwningThread(&target,action);assert(calls==1&&!q.task); // world owner
 ai::WorldActions::mapExecution=true;target.map=0;ai.RunOnOwningThread(&target,action);assert(calls==2&&!q.task); // same map
 target.map=1;ai.RunOnOwningThread(&target,action);assert(calls==2&&q.task);
 ai::WorldActions::mapExecution=false;q.task(ai);assert(calls==3);q.task={};
 ai::WorldActions::mapExecution=true;ai.RunOnOwningThread(&target,action);sObjectAccessor.players.clear();q.task(ai);assert(calls==3);q.task={};
 sObjectAccessor.players[2]=&target;ai.RunOnOwningThread(&target,action);target.teleport=true;q.task(ai);assert(calls==3);q.task={};target.teleport=false;
 q.accept=false;ai.RunOnOwningThread(&target,action);assert(!q.task&&calls==3&&sLog.errors==1);
 std::cout<<"PASS: world/same-map inline; foreign-map deferred; missing/teleporting target skipped; queue rejection logged\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='turtle-owner-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
