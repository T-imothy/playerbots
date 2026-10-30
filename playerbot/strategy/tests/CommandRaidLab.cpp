#include "playerbot/playerbot.h"
#ifdef MANTECH_RAID_LAB
#include "CommandRaidLab.h"
#include "World/RaidLab.h"
#include "Groups/Group.h"
#include <sstream>

using namespace ai;
bool MonitorRaidLabDeath::IsConditionMet(const std::string&, Player* bot, TestContext& ctx) const {
 return bot->IsInWorld() && ctx.focusMobGuid &&
        RaidLab::BossDied(bot->GetMap(),ctx.focusMobGuid.GetRawValue());
}
TestResult CommandRaidLab::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                  TestContext& ctx, std::string& message)
{
 if (!RaidLab::Enabled() || !bot->IsInWorld() || !RaidLab::AllowedMap(bot->GetMapId())) {
  message="Raid lab requires isolated loopback database and supported raid map";
  return TestResult::IMPOSSIBLE;
 }
 uint32 entry=0; std::string mode; std::istringstream args(params); args >> entry >> mode;
 if (!entry || (mode!="bot" && mode!="leader") || !bot->GetGroup()) {
  message="Expected raidlab <boss entry> <bot|leader> with formed group";
  return TestResult::IMPOSSIBLE;
 }
 Creature* boss=nullptr;
 auto& store=bot->GetMap()->GetObjectsStore();
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  auto c=i->second;
  if(c && c->GetEntry()==entry && c->IsAlive() && c->IsInWorld() &&
     (!boss || bot->GetDistance(c)<bot->GetDistance(boss))) boss=c;
 }
 // Missing/event-gated bosses are a setup limitation, never manufactured here.
 if(!boss || bot->GetDistance(boss)>100.0f) {
  message="BLOCKED: native boss missing or farther than 100 yards";
  return TestResult::IMPOSSIBLE;
 }
 Player* tank=nullptr;
 for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
  auto p=r->getSource();
  if(!p || !p->IsInWorld() || p->IsBeingTeleported() || !p->IsAlive() ||
     p->GetMap()!=bot->GetMap() || p->IsGameMaster() || p->GetDistance(bot)>30.0f) {
   message="BLOCKED: group not alive, settled, nearby and GM-off";
   return TestResult::IMPOSSIBLE;
  }
  if(p->IsInCombat()) {
   message="BLOCKED: group already fighting before the native boss pull";
   return TestResult::IMPOSSIBLE;
  }
  if(p->GetPlayerbotAI() && ai->IsTank(p) && !tank) tank=p;
 }
 if(!tank) {message="BLOCKED: no assigned tank";return TestResult::IMPOSSIBLE;}
 if(boss->IsInCombat()) {message="BLOCKED: boss already in combat before attempt";return TestResult::IMPOSSIBLE;}
 bot->SetSelectionGuid(boss->GetObjectGuid());
 if(!RaidLab::Begin(bot,entry,ctx.testName,mode=="leader")) {
  message="BLOCKED: telemetry could not start";return TestResult::IMPOSSIBLE;
 }
 ctx.focusMobGuid=boss->GetObjectGuid();ctx.focusMobEntry=entry;
 ctx.focusMobPassive=true; // Never run BossFocusManager's spawn/leash/force-attack helpers.
 // A passive synthetic player must not supply damage/heals that wake followers.
 // The test strategy's lab-only multiplier suppresses this leader's ordinary
 // actions; native fear/knockback/damage and all follower decisions still run.
 ai->ChangeStrategy("+test::"+ctx.testName, BotState::BOT_STATE_REACTION);
 RaidLab::Event(bot,"leader_policy_passive");
 for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
  auto p=r->getSource();
  if(p!=bot && p->GetPlayerbotAI()) {
   p->GetPlayerbotAI()->SetMaster(bot);
   // Establish the same follower strategy set a newly controlled companion gets.
   p->GetPlayerbotAI()->ResetStrategies(false);
  }
 }
 RaidLab::Event(bot,"pull_command",boss->GetObjectGuid().GetRawValue(),tank->GetObjectGuid().GetRawValue());
 tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
 // One ordinary pull request. No recurring attack injection or encounter cheats.
 message="Native pull requested; mechanics assertions evaluated separately from outcome";
 return TestResult::PASS;
}
#endif
