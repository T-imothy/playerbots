from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/RpgSubActions.cpp').read_text(encoding='utf-8')
methods=s[s.index('void RpgAIChatAction::CancelManualChat()'):s.index('bool RpgTradeUsefulAction::IsTradingItem')]
wait=s[s.index('bool RpgAIChatAction::WaitForLines()'):s.index('bool RpgAIChatAction::RequestNewLines()')]
code=r'''
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <future>
#include <map>
#include <memory>
#include <queue>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
#include <cstdio>
using uint32=uint32_t;using int32=int32_t;
constexpr int LANG_UNIVERSAL=0;
struct Unit {bool inWorld=true;uint32 map=0;std::string name="NPC",said;bool IsInWorld()const{return inWorld;}std::string GetName()const{return name;}
template<class B>void MonsterTextEmote(const char* s,B*){said=s;}template<class B>void MonsterSay(const char* s,int,B*){said=s;}} npc;
struct Bot:Unit {bool teleport=false;uint32 instance=0;bool IsBeingTeleported()const{return teleport;}uint32 GetMapId()const{return map;}uint32 GetInstanceId()const{return instance;}uint32 GetGUIDLow()const{return 7;}bool IsInMap(Unit* u)const{return map==u->map;}
void SendMessageToPlayer(const char*){}void TextEmote(std::string s){said=s;}void Say(std::string s,int){said=s;}};
struct GuidPosition {uint32 id=123;Unit* unit=&npc;Unit* GetUnit(uint32)const{return unit;}uint32 GetRawValue()const{return id;}uint32 GetCounter()const{return id;}};
struct AI {bool pending=false;void SetManualRpgChatPending(bool p){pending=p;}};
struct Logger {template<class... T>void outError(const char*,T...){} }sLog;
std::map<std::string,std::string> globals;
using delayedPacket=std::pair<std::string,uint32>;using futurePackets=std::future<std::vector<delayedPacket>>;
struct RpgAIChatAction {
 Bot* bot;AI* ai;GuidPosition target,manualTarget;std::string context;int32 chatLine=0;
 bool manualPending=false;uint32 manualMap=0,manualInstance=0;std::chrono::steady_clock::time_point manualNext{};
 std::queue<delayedPacket> packets;futurePackets futPackets;
 std::vector<std::shared_ptr<std::promise<std::vector<delayedPacket>>>> requests;
 RpgAIChatAction(Bot* b,AI* a):bot(b),ai(a){}
 template<class T>T Get(const char*){if constexpr(std::is_same_v<T,GuidPosition>)return target;else return context;}
 template<class T>void Set(const char*,T v){if constexpr(std::is_same_v<T,GuidPosition>)target=v;else context=v;}
 bool RequestNewLines(){auto p=std::make_shared<std::promise<std::vector<delayedPacket>>>();requests.push_back(p);futPackets=p->get_future();return true;}
 bool SpeakLine(){context+=" "+packets.front().first;packets.pop();return true;}
 bool WaitForLines();void CancelManualChat();void UpdateManualChat();void ManualChat(GuidPosition,const std::string&);
};
#define AI_VALUE(type,name) Get<type>(name)
#define SET_AI_VALUE(type,name,value) Set<type>(name,value)
#define SET_AI_VALUE2(type,name,key,value) (chatLine=(value))
#define GAI_VALUE2(type,name,key) globals[key]
#define SET_GAI_VALUE2(type,name,key,value) (globals[key]=(value))
''' + wait + methods + r'''
int main(){
 Bot bot;bot.name="Bot";AI ai;RpgAIChatAction a(&bot,&ai);GuidPosition target;
 a.ManualChat(target,"hello");assert(ai.pending&&a.manualPending&&bot.said=="hello");
 a.UpdateManualChat();assert(a.manualPending&&a.packets.empty());
 a.requests.back()->set_value({{"NPC: first",10000},{"NPC: second",0}});
 a.UpdateManualChat();assert(a.packets.size()==1&&globals["llmcontext manual123"].find("first")!=std::string::npos);
 a.UpdateManualChat();assert(a.packets.size()==1); // delay without sleeping the owner
 a.manualNext={};a.UpdateManualChat();assert(!ai.pending&&a.packets.empty()&&globals["llmcontext manual123"].find("second")!=std::string::npos);
 a.ManualChat(target,"old");auto old=a.requests.back();a.ManualChat(target,"new");old->set_value({{"STALE",0}});
 a.requests.back()->set_value({{"FRESH",0}});a.UpdateManualChat();assert(a.context.find("STALE")==std::string::npos&&a.context.find("FRESH")!=std::string::npos);
 a.ManualChat(target,"leave");npc.inWorld=false;a.UpdateManualChat();assert(!ai.pending&&!a.futPackets.valid());npc.inWorld=true;
 a.ManualChat(target,"teleport");bot.teleport=true;a.UpdateManualChat();assert(!ai.pending);bot.teleport=false;
 a.ManualChat(target,"switch");a.target.id=444;a.UpdateManualChat();assert(!ai.pending);
 a.ManualChat(target,"exception");a.requests.back()->set_exception(std::make_exception_ptr(std::runtime_error("expected")));a.UpdateManualChat();assert(!ai.pending);
 a.ManualChat(target,"impersonate");assert(!ai.pending);a.ManualChat(target,"impersonate hello");assert(npc.said=="hello"&&globals["llmcontext manual123"].find("NPC:hello")!=std::string::npos);
 globals["llmcontext manual123"]="Bot: only";a.ManualChat(target,"undo");assert(globals["llmcontext manual123"].empty());
 globals["llmcontext manual123"]="NPC: only";a.ManualChat(target,"continue");assert(a.chatLine==12);a.CancelManualChat();
 a.ManualChat(target,"clear");assert(globals["llmcontext manual123"].empty()&&!ai.pending);
 puts("PASS manual chat nonblocking polling/delays, context updates, replacement, target loss, teleport, exceptions, and conversation commands");
}
'''
import tempfile, subprocess, shutil
with tempfile.TemporaryDirectory(prefix='turtle-integration-') as folder:
    folder=Path(folder)
    cpp=folder/'integration.cpp'; cpp.write_text(code,encoding='utf-8')
    cl=shutil.which('cl')
    if cl:
        exe=folder/'integration.exe'
        command=[cl,'/nologo','/std:c++17','/EHsc','/MD','/O2','/I'+str(Path(__file__).resolve().parents[3]/'src/shared'),str(cpp),'/Fe'+str(exe),'/Fo'+str(folder/'integration.obj')]
    else:
        compiler=shutil.which('c++')
        if not compiler: raise SystemExit('Run in a C++ compiler environment (Visual Studio Developer PowerShell on Windows).')
        exe=folder/'integration'
        command=[compiler,'-std=c++17','-pthread','-I'+str(Path(__file__).resolve().parents[3]/'src/shared'),str(cpp),'-o',str(exe)]
    subprocess.run(command,check=True,cwd=folder)
    subprocess.run([str(exe)],check=True)
