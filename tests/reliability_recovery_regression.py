"""Execute the actual new corpse-entry and explicit body-pull decision blocks."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
corpse=(root/'playerbot/strategy/actions/ReviveFromCorpseAction.cpp').read_text(encoding='utf-8')
helper=corpse[corpse.index('#ifdef MANGOSBOT_TWO'):corpse.index('bool ReviveFromCorpseAction::Execute')]
start=corpse.index('bool FindCorpseAction::Execute(Event& event)')
end=corpse.index('    Player* master = ai->GetGroupMaster();',start)
corpse=corpse[start:end]+'    fallback = true; return false;\n}\n'
pull=(root/'playerbot/strategy/actions/PullActions.cpp').read_text(encoding='utf-8')
start=pull.index('    strategy->SetBodyPull(false);');end=pull.index('    //Set position to return',start)
pull=pull[start:end]
fixture=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <iostream>
#include <string>
using uint32=unsigned;
struct Config{bool dungeonCorpseRecovery=true,explicitBodyPull=true;unsigned reactDelay=250;float sightDistance=50;}sPlayerbotAIConfig;
struct MapEntry{bool dungeon=true;bool IsDungeon()const{return dungeon;}};
struct MapStore{MapEntry entry;bool present=true;const MapEntry* LookupEntry(unsigned){return present?&entry:nullptr;}}sMapStore;
struct Corpse{unsigned map=70;unsigned GetMapId(){return map;}};
struct Player{Corpse corpse;bool hasCorpse=true,bg=false,alive=false,charmed=false,teleport=false;unsigned map=0;float distance=25;
 bool InBattleGround(){return bg;}Corpse* GetCorpse(){return hasCorpse?&corpse:nullptr;}
 bool IsAlive(){return alive;}unsigned GetMapId(){return map;}float GetDistance(float,float,float){return distance;}
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}};
struct AreaTrigger{unsigned entry=1;};struct AreaTriggerEntry{unsigned mapid=0;float x=1,y=2,z=3;};
struct ObjectMgr{AreaTrigger entry;bool present=true;int lookups=0,idLookups=0;const AreaTrigger* GetMapEntranceTrigger(unsigned){++lookups;return present?&entry:nullptr;}
 const AreaTrigger* GetAreaTrigger(unsigned id){++idLookups;return present&&id==1?&entry:nullptr;}}sObjectMgr;
struct TriggerStore{AreaTriggerEntry entry;const AreaTriggerEntry* LookupEntry(unsigned id){return id==1?&entry:nullptr;}
 unsigned GetNumRows(){return 6;}}sAreaTriggerStore;
const int CMSG_AREATRIGGER=1;
struct WorldPacket{unsigned id=0;WorldPacket(int){}void operator<<(unsigned value){id=value;}};
struct Event{std::string source="pull";Event(){}Event(const char*,WorldPacket&){}std::string getSource(){return source;}};
struct AI{bool authorized=true;int notified=0;void TellPlayerNoFacing(Player*,const char*){++notified;}};
struct ReachAreaTriggerAction{AI* ai;static bool accepted;static int calls;ReachAreaTriggerAction(AI* a):ai(a){}
 bool Execute(Event&){++calls;return accepted;}unsigned GetDuration(){return 3000;}};
bool ReachAreaTriggerAction::accepted=true;int ReachAreaTriggerAction::calls=0;
struct FindCorpseAction{Player* bot;AI* ai;bool fallback=false;int moved=0;unsigned duration=0;
 bool MoveTo(unsigned,float,float,float){++moved;return true;}void SetDuration(unsigned value){duration=value;}bool Execute(Event&);};
'''+helper+corpse+r'''
enum class PullFailure{None,Unavailable,NoRangedWeapon,NoAmmo,NotKnown,NotReady,NoLineOfSight,OutOfRange,InvalidState};
struct Strategy{bool body=true,can=false;void SetBodyPull(bool value){body=value;}bool CanDoPullAction(Player*){return can;}};
PullFailure reason=PullFailure::NoAmmo;PullFailure GetPullReadiness(AI*,Player*){return reason;}
bool CanManageBotCommands(AI* ai,Player*){return ai->authorized;}
bool Attempt(Strategy* strategy,AI* ai,Player* bot,Player* requester,Player* target,Event event){
 auto fail=[](PullFailure){return false;};
'''+pull+r'''
 return true;
}
int main(){
 Player bot,requester,target;AI ai;Event event;FindCorpseAction action{&bot,&ai};
 assert(action.Execute(event));assert(ReachAreaTriggerAction::calls==1&&action.duration==3000);
#ifdef MANGOSBOT_TWO
 int searches=sObjectMgr.idLookups;assert(searches>=1);
 assert(action.Execute(event));assert(sObjectMgr.idLookups==searches+1); // validated cached ID
#endif
 int beforeDistance=ReachAreaTriggerAction::calls;
 bot.distance=100;assert(action.Execute(event));assert(action.moved==1&&ReachAreaTriggerAction::calls==beforeDistance);
 bot.distance=25;ReachAreaTriggerAction::accepted=false;assert(!action.Execute(event));assert(!action.fallback);
 sObjectMgr.present=false;assert(!action.Execute(event));assert(!action.fallback);sObjectMgr.present=true;
 bot.bg=true;int before=sObjectMgr.lookups;assert(!action.Execute(event));assert(sObjectMgr.lookups==before);bot.bg=false;
 sPlayerbotAIConfig.dungeonCorpseRecovery=false;assert(!action.Execute(event));assert(action.fallback);
 sPlayerbotAIConfig.dungeonCorpseRecovery=true;action.fallback=false;bot.map=70;assert(!action.Execute(event));assert(action.fallback);
 Strategy strategy;bot.alive=true;
 for(auto failure:{PullFailure::NoAmmo,PullFailure::NoRangedWeapon,PullFailure::NotKnown}){
  reason=failure;assert(Attempt(&strategy,&ai,&bot,&requester,&target,event)&&strategy.body);
 }
 for(auto failure:{PullFailure::NotReady,PullFailure::NoLineOfSight,PullFailure::OutOfRange,PullFailure::InvalidState}){
  reason=failure;assert(!Attempt(&strategy,&ai,&bot,&requester,&target,event)&&!strategy.body);
 }
 reason=PullFailure::NoAmmo;event.source="attack anything";assert(!Attempt(&strategy,&ai,&bot,&requester,&target,event));
 event.source="pull";ai.authorized=false;assert(!Attempt(&strategy,&ai,&bot,&requester,&target,event));ai.authorized=true;
 sPlayerbotAIConfig.explicitBodyPull=false;assert(!Attempt(&strategy,&ai,&bot,&requester,&target,event));sPlayerbotAIConfig.explicitBodyPull=true;
 bot.charmed=true;assert(!Attempt(&strategy,&ai,&bot,&requester,&target,event));bot.charmed=false;
 strategy.body=true;strategy.can=true;assert(Attempt(&strategy,&ai,&bot,&requester,&target,event)&&!strategy.body);
 std::cout<<"PASS: native portal delegation/denial/duration, same-map and battleground guards, explicit-only fallback and native failure exclusions\n";
}
'''
with tempfile.TemporaryDirectory(prefix='reliability-recovery-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(fixture,encoding='utf-8')
 for era in ('ZERO','ONE','TWO'):
  result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/UNDEBUG','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],check=True)
