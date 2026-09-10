"""Execute explicit pull diagnostics and read-only status commands in all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
pull=(root/'playerbot/strategy/actions/PullActions.cpp').read_text()
stats=(root/'playerbot/strategy/actions/StatsAction.cpp').read_text()
access=(root/'playerbot/strategy/actions/BotCommandAccess.h').read_text()
diag=(root/'playerbot/strategy/actions/PullDiagnostics.h').read_text()
code=r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
using ObjectGuid=unsigned;
enum {SEC_PLAYER, CLASS_DRUID=11,CLASS_PALADIN=2,INVENTORY_SLOT_BAG_0=0,EQUIPMENT_SLOT_RANGED=17};
enum SpellCastResult{SPELL_CAST_OK,SPELL_FAILED_NEED_AMMO,SPELL_FAILED_NO_AMMO,SPELL_FAILED_EQUIPPED_ITEM,SPELL_FAILED_EQUIPPED_ITEM_CLASS,
 SPELL_FAILED_OUT_OF_RANGE,SPELL_FAILED_TOO_CLOSE,SPELL_FAILED_LINE_OF_SIGHT,SPELL_FAILED_NOT_KNOWN,SPELL_FAILED_NOT_READY,SPELL_FAILED_MOVING};
enum class PlayerbotSecurityLevel{PLAYERBOT_SECURITY_ALLOW_ALL};
struct Session{unsigned GetSecurity(){return 0;}};
struct Unit{bool valid=true;float distance=5;float GetDistance(Unit*){return distance;}};
struct Player:Unit{bool real=true,alive=true,world=true,teleport=false,charm=false,equipped=true,grouped=true;unsigned cls=1;Session session;
 bool isRealPlayer(){return real;}Session*GetSession(){return &session;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charm;}unsigned getClass(){return cls;}
 void*GetItemByPos(int,int){return equipped?this:nullptr;}unsigned GetSelectionGuid(){return 1;}ObjectGuid GetObjectGuid(){return 123;}
 void*GetGroup(){return grouped?this:nullptr;}float GetPositionX(){return 1;}float GetPositionY(){return 2;}float GetPositionZ(){return 3;}unsigned GetMapId(){return 4;}};
struct Security{bool CheckLevelFor(PlayerbotSecurityLevel,bool,Player*){return true;}};
struct PositionEntry{bool set=false;void Set(float,float,float,unsigned){set=true;}};
using PositionMap=std::map<std::string,PositionEntry>;
PositionMap positions;
#define AI_VALUE(type,name) positions
struct Context{bool action=true;void*GetAction(const std::string&){return action?this:nullptr;}};
struct PullStrategy;
struct PlayerbotAI{Player*bot;Player*master;Unit*target;PullStrategy*strategy=nullptr;Context context;Security security;
 SpellCastResult result=SPELL_CAST_OK;unsigned combatStarts=0,castChecks=0;bool tank=false,heal=false,ranged=false;
 std::vector<std::string>messages;Player*GetBot(){return bot;}Player*GetMaster(){return master;}bool HasRealPlayerMaster(){return master&&master->real;}
 Security*GetSecurity(){return &security;}Context*GetAiObjectContext(){return &context;}
 bool CanCastSpell(std::string,Unit*,int,void*,bool,bool,bool,SpellCastResult*out){++castChecks;*out=result;return result==SPELL_CAST_OK;}
 void TellPlayerNoFacing(Player*,const std::string&s,PlayerbotSecurityLevel=PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL,bool priv=true,bool repeat=true,bool ignoreSilent=false,bool forceWhisper=false){if(s.find("Pull failed:")==0)assert(priv&&repeat&&ignoreSilent&&forceWhisper);messages.push_back(s);}void OnCombatStarted(){++combatStarts;}
 Unit*GetUnit(unsigned){return target;}bool IsTank(Player*,bool grouped){assert(grouped==bot->grouped);return tank;}
 bool IsHeal(Player*,bool grouped){assert(grouped==bot->grouped);return heal;}bool IsRanged(Player*,bool grouped){assert(grouped==bot->grouped);return ranged;}};
struct PullStrategy{std::string action="shoot";bool possible=true;Unit*requested=nullptr;unsigned requests=0;ObjectGuid requester=0;void SetRequester(ObjectGuid guid){requester=guid;}
 static PullStrategy*Get(PlayerbotAI*ai){return ai->strategy;}std::string GetPullActionName(){return action;}
 std::string GetSpellName(){return action;}bool CanDoPullAction(Unit*){return possible;}void RequestPull(Unit*u){requested=u;++requests;}};
struct AttackersValue{static bool IsValid(Unit*u,Player*,void*,bool){return u&&u->valid;}};
struct TalentSpec{std::string link="hybrid";TalentSpec()=default;TalentSpec(Player*){}
 std::string GetTalentLink(){return link;}int GetTalentPoints(int tree=-1){return tree==-1?51:tree==0?0:tree==1?32:19;}};
struct Path{std::string name;std::vector<TalentSpec>talentSpec;};
struct Config{float reactDistance=30;struct Specs{std::vector<Path>talentPath;};Specs classSpecs[12];}sPlayerbotAIConfig;
struct ChatHelper{static std::string specName(Player*){return "fury";}};
struct Event{std::string source,param;Player*owner;Player*getOwner(){return owner;}std::string getSource(){return source;}std::string getParam(){return param;}};
namespace ai{
 __ENUM__
 __ACCESS__
 PullFailure GetPullReadiness(PlayerbotAI*,Unit*);const char*PullFailureReason(PullFailure);
 struct PullRequestAction{PlayerbotAI*ai;Player*bot;Player*GetMaster(){return ai->master;}Unit*GetTarget(Event&){return ai->target;}bool Execute(Event&);};
 struct BotStatusAction{PlayerbotAI*ai;Player*bot;Player*GetMaster(){return ai->master;}bool Execute(Event&);};
}
using namespace ai;
__REASON__
__READY__
__PULL__
__FIELD__
__STATUS__
int main(){
 Player bot,owner,stranger;Unit target;PlayerbotAI ai{&bot,&owner,&target};PullStrategy strategy;PullRequestAction pull{&ai,&bot};BotStatusAction status{&ai,&bot};Event event{"pull","",&owner};
 assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: pull strategy is disabled.");ai.messages.clear();
 event.source="attack anything";assert(!pull.Execute(event)&&ai.messages.empty());event.source="pull";ai.strategy=&strategy;
 ai.target=nullptr;assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: no hostile target selected.");ai.target=&target;
 target.distance=100;assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: target is outside pull range.");target.distance=5;
 target.valid=false;assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: target cannot be pulled.");target.valid=true;
 strategy.possible=false;bot.equipped=false;assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: no usable ranged weapon.");bot.equipped=true;
 for(auto result:{SPELL_FAILED_NO_AMMO,SPELL_FAILED_NEED_AMMO}){ai.result=result;assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: ammunition is required.");}
 ai.result=SPELL_FAILED_NOT_READY;assert(!pull.Execute(event)&&ai.messages.back()=="Pull failed: pull spell is on cooldown.");
 ai.messages.clear();event.source="attack anything";assert(!pull.Execute(event)&&ai.messages.empty());event.source="pull";
 // Existing accepted requests still approach range/LOS; the diagnostic is not a new execution gate.
 strategy.possible=true;for(auto result:{SPELL_FAILED_OUT_OF_RANGE,SPELL_FAILED_LINE_OF_SIGHT,SPELL_FAILED_MOVING}){ai.result=result;assert(pull.Execute(event));}
 assert(strategy.requests==3&&ai.combatStarts==3&&positions["pull"].set&&strategy.requester==owner.GetObjectGuid());auto requests=strategy.requests;
 event={"status","pull",&owner};ai.result=SPELL_FAILED_LINE_OF_SIGHT;assert(status.Execute(event));
 assert(ai.messages.back()=="PullAction: shoot; Ready: no; Reason: no line of sight; Scope: immediate_cast");
 assert(strategy.requests==requests&&strategy.requested==&target&&ai.combatStarts==3);
 ai.result=SPELL_CAST_OK;assert(status.Execute(event)&&ai.messages.back().find("Ready: yes")!=std::string::npos);
 ai.strategy=nullptr;assert(status.Execute(event)&&ai.messages.back().find("pull strategy is disabled")!=std::string::npos);ai.strategy=&strategy;
 ai.context.action=false;assert(GetPullReadiness(&ai,&target)==PullFailure::NoAction);ai.context.action=true;
 bot.alive=false;assert(GetPullReadiness(&ai,&target)==PullFailure::InvalidState);bot.alive=true;
 event.param="role";ai.tank=true;assert(status.Execute(event)&&ai.messages.back().find("Role: tank;")==0);
 ai.heal=true;assert(status.Execute(event)&&ai.messages.back().find("Role: tank+healer;")==0);
 ai.tank=ai.heal=false;ai.ranged=true;bot.grouped=false;assert(status.Execute(event)&&ai.messages.back().find("Role: dps; Range: ranged;")==0);
 event.param="build";assert(status.Execute(event)&&ai.messages.back()=="Build: unknown; Layout: 0/32/19; SuggestedRole: unknown");
 sPlayerbotAIConfig.classSpecs[1].talentPath={{"fury;prot",{TalentSpec{}}}};
 assert(status.Execute(event)&&ai.messages.back()=="Build: fury%3Bprot; Layout: 0/32/19; SuggestedRole: unknown");
 sPlayerbotAIConfig.classSpecs[1].talentPath.push_back({"another",{TalentSpec{}}});assert(status.Execute(event)&&ai.messages.back().find("Build: unknown;")==0);
 auto messageCount=ai.messages.size();event.owner=&stranger;assert(!status.Execute(event)&&ai.messages.size()==messageCount);
 assert(strategy.requests==requests&&ai.combatStarts==3);
 std::cout<<"PASS: explicit pull reasons, autonomous silence, unchanged accepted pulls, authorized read-only role/build/pull status and hybrid ambiguity\n";
}
'''
for marker,text,signature in [('__ENUM__',diag,'    enum class PullFailure'),('__ACCESS__',access,'    inline bool CanManageBotCommands('),
 ('__REASON__',pull,'const char* ai::PullFailureReason('),('__READY__',pull,'PullFailure ai::GetPullReadiness('),('__PULL__',pull,'bool PullRequestAction::Execute('),
 ('__FIELD__',stats,'    std::string StatusField('),('__STATUS__',stats,'bool BotStatusAction::Execute(')]:
 code=code.replace(marker,block(text,signature)+(';' if marker=='__ENUM__' else ''))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bot-status-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
body=block(stats,'bool BotStatusAction::Execute(')
for mutator in ('ApplyTalents','ChangeStrategy','RequestPull','SetTarget','OnCombatStarted','PExecute'):
 assert mutator not in body
for file in ('actions/ChatActionContext.h','triggers/ChatTriggerContext.h','generic/ChatCommandHandlerStrategy.cpp'):
 assert '"status"' in (root/'playerbot/strategy'/file).read_text()
