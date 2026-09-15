"""Run the production command coordinator with controlled native collaborators."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/BotPartyCommands.cpp').read_text(encoding='utf-8')
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include "'))
fixture=r'''
#include <string>
#include <array>
#include <vector>
#include <atomic>
#include <cassert>
#include <thread>
#include <chrono>
#include <iostream>
using uint64=unsigned long long;using uint32=unsigned;using uint8=unsigned char;
struct ObjectGuid { uint64 n=0; bool operator==(ObjectGuid o)const{return n==o.n;}
 bool operator!=(ObjectGuid o)const{return n!=o.n;} explicit operator bool()const{return n!=0;} };
const unsigned CHAT_MSG_PARTY=1,CHAT_MSG_RAID=2,CHAT_MSG_WHISPER=3,TYPEID_UNIT=4;
namespace PlayerbotSecurityLevel { const int PLAYERBOT_SECURITY_ALLOW_ALL=0; }
struct Config {bool partyCommandCoordinator=true;std::string commandPrefix;} sPlayerbotAIConfig;
unsigned clockNow=100;
struct WorldTimer { static unsigned getMSTime(){return clockNow;} };
struct Unit { ObjectGuid guid; bool alive=true,world=true,casting=true;unsigned map=0,instance=1;
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsNonMeleeSpellCasted(bool){return casting;}
 unsigned GetTypeId(){return TYPEID_UNIT;} };
struct Player:Unit { bool real=true,teleport=false,charmed=false;void* group=(void*)1;ObjectGuid selection{20};
 bool isRealPlayer(){return real;}void* GetGroup(){return group;}ObjectGuid GetSelectionGuid(){return selection;}
 ObjectGuid GetObjectGuid(){return guid;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit* o){return o->map==map&&o->instance==instance;}
 bool HasCharmer(){return charmed;}const char* GetName(){return "Executor";} };
struct Event {Event(const char*,const char*,Player*){}};
struct Facade { bool IsFriendlyTo(Player*,Unit*){return false;} } sServerFacade;
struct PlayerbotAI {Player* bot;Player* master;Unit* target;bool capable=true,castSuccess=true,authorized=true;
 bool tank=true,slow=false;std::atomic<int> casts{0};std::vector<std::string> replies;
 PlayerbotAI(Player* b,Player* m,Unit* t):bot(b),master(m),target(t){}
 Player* GetBot(){return bot;}Player* GetMaster(){return master;}
 Unit* GetUnit(ObjectGuid g){return g==target->guid?target:nullptr;}
 bool CanCastSpell(const char*,Unit*,int){return capable;}bool HasAura(const char*,Unit*){return false;}
 bool CastSpell(const char*,Unit*){++casts;if(slow)std::this_thread::sleep_for(std::chrono::milliseconds(100));return castSuccess;}
 bool IsTank(Player*){return tank;}bool DoSpecificAction(const char*,Event&,bool){++casts;return castSuccess;}
 void TellPlayerNoFacing(Player*,const std::string& text,int,bool,bool,bool,bool){replies.push_back(text);}
};
namespace ai {enum class PullFailure{None,NoAmmo};
 PullFailure GetPullReadiness(PlayerbotAI* a,Unit*){return a->capable?PullFailure::None:PullFailure::NoAmmo;}
 bool CanManageBotCommands(PlayerbotAI* a,Player*){return a->authorized;}
 class BotPartyCommands {public:static bool Queue(Player*,const std::string&,unsigned);static bool Update(PlayerbotAI*);}; }
'''+source+r'''
int main(){
 Player master,one,two;Unit target;master.guid={10};one.guid={11};two.guid={12};target.guid={20};
 one.real=two.real=false;one.casting=two.casting=false;
 PlayerbotAI a(&one,&master,&target),b(&two,&master,&target);
 assert(!BotPartyCommands::Queue(&master,"pull",CHAT_MSG_PARTY));
 sPlayerbotAIConfig.partyCommandCoordinator=false;
 assert(!BotPartyCommands::Queue(&master,"party interrupt",CHAT_MSG_PARTY));
 sPlayerbotAIConfig.partyCommandCoordinator=true;
 assert(BotPartyCommands::Queue(&master,"party interrupt",CHAT_MSG_PARTY));
 a.capable=false;assert(!BotPartyCommands::Update(&a));
 b.authorized=false;assert(!BotPartyCommands::Update(&b));b.authorized=true;
 assert(BotPartyCommands::Update(&b));assert(b.casts==1&&a.casts==0);
 assert(!BotPartyCommands::Update(&a));
 // A changed selection cannot redirect the queued spell.
 assert(BotPartyCommands::Queue(&master,"party cc",CHAT_MSG_PARTY));
 master.selection={99};assert(BotPartyCommands::Update(&b));master.selection={20};
 // Two ready bots racing still issue exactly one accepted action.
 a.capable=true;a.slow=true;assert(BotPartyCommands::Queue(&master,"party interrupt",CHAT_MSG_PARTY));
 std::thread first([&]{BotPartyCommands::Update(&a);});
 while(a.casts==0)std::this_thread::yield();
 assert(!BotPartyCommands::Update(&b));first.join();assert(a.casts==1&&b.casts==2);
 // A rejected native cast releases the reservation for another capable bot.
 a.slow=false;a.castSuccess=false;assert(BotPartyCommands::Queue(&master,"party cc",CHAT_MSG_PARTY));
 assert(!BotPartyCommands::Update(&a));assert(BotPartyCommands::Update(&b));
 // Do not cast at a creature that stopped casting, or across instances.
 target.casting=false;assert(BotPartyCommands::Queue(&master,"party interrupt",CHAT_MSG_PARTY));
 assert(!BotPartyCommands::Update(&b));target.casting=true;two.instance=2;
 assert(!BotPartyCommands::Update(&b));two.instance=1;
 clockNow+=3000;assert(!BotPartyCommands::Update(&b));assert(b.replies.back().find("no available")!=std::string::npos);
 // Fallback pulling does not bypass ranged readiness in the auto-selector.
 assert(BotPartyCommands::Queue(&master,"party pull",CHAT_MSG_PARTY));b.capable=false;
 assert(!BotPartyCommands::Update(&b));b.capable=true;assert(BotPartyCommands::Update(&b));
 assert(requests.size()==64);
 std::cout<<"PASS: command gates, ownership, target snapshot, one concurrent executor, native rejection, expiry, instance and readiness guards\n";
}
'''
with tempfile.TemporaryDirectory(prefix='reliability-commands-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(fixture,encoding='utf-8')
 for era in ('ZERO','ONE','TWO'):
  result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/UNDEBUG','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],check=True)
