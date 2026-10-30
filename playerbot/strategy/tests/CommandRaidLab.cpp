#include "playerbot/playerbot.h"
#ifdef MANTECH_RAID_LAB
#include "CommandRaidLab.h"
#include "World/RaidLab.h"
#include "Groups/Group.h"
#include "playerbot/WorldPosition.h"
#include <cmath>
#include <sstream>

using namespace ai;
TestResult CommandRaidLabStaging::Execute(const std::string& params, Player* bot, PlayerbotAI*,
                                         TestContext& ctx, std::string& message)
{
 // This direct encounter fixture is deliberately limited to Magmadar. It does
 // not alter native trash, combat logic, or any production placement policy.
 if (!RaidLab::Enabled() || !bot->IsInWorld() || bot->IsBeingTeleported() ||
     !bot->IsGameMaster() || bot->GetMapId()!=409 ||
     (params!="11982" && params!="11982 cleared-room")) {
  message="BLOCKED: Magmadar staging requires settled local setup observer";
  return TestResult::IMPOSSIBLE;
 }
 auto& store=bot->GetMap()->GetObjectsStore();
 Creature* boss=nullptr;
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  auto c=i->second;
  if(c && c->GetEntry()==11982 && c->IsAlive() && c->IsInWorld() &&
     bot->GetDistance(c)<100.0f) {boss=c;break;}
 }
 if(!boss || boss->IsInCombat()) {
  message="BLOCKED: native Magmadar unavailable for staging";return TestResult::IMPOSSIBLE;
 }
 if(params=="11982 cleared-room") {
  if(ctx.testName.find("_cleared_room")==std::string::npos) {
   message="BLOCKED: cleared-room fixture requires an explicitly named scenario";
   return TestResult::IMPOSSIBLE;
  }
  std::vector<Creature*> trash;
  for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
   auto c=i->second;
   if(c && c->GetEntry()==11671 && c->IsAlive() && c->IsInWorld() && boss->GetDistance(c)<100.0f)
    trash.push_back(c);
  }
  for(auto c:trash) {
   sLog.outString("RAID_LAB_FIXTURE: cleared_room despawn entry=%u guid=%s; NOT trash validation",
       c->GetEntry(),c->GetObjectGuid().GetString().c_str());
   c->SetRespawnDelay(3600,true);
   c->ForcedDespawn();
  }
 }
 unsigned floorRejected=0, losRejected=0, pathRejected=0, trashRejected=0;
 for(float radius : {30.0f,35.0f,40.0f,45.0f,50.0f}) for(unsigned sector=0;sector<24;++sector) {
  if(radius<boss->GetAttackDistance(bot)+2.0f) continue;
  float angle=float(sector)*float(2*M_PI)/24.0f;
  float x=boss->GetPositionX()+radius*std::cos(angle);
  float y=boss->GetPositionY()+radius*std::sin(angle), z=boss->GetPositionZ();
  bot->UpdateAllowedPositionZ(x,y,z);
  if(!std::isfinite(z) || std::abs(z-boss->GetPositionZ())>8.0f) {++floorRejected;continue;}
  if(!boss->IsWithinLOS(x,y,z+bot->GetCollisionHeight(),true)) {++losRejected;continue;}
  WorldPosition destination(bot->GetMapId(),x,y,z);
  auto path=destination.getPathStepFrom(WorldPosition(boss),bot,true);
  if(!destination.isPathTo(path,1.0f,2.0f)) {++pathRejected;continue;}
  bool clear=true;
  for(auto i=store.begin<Creature>();i!=store.end<Creature>() && clear;++i) {
   auto c=i->second;
   if(!c || c==boss || !c->IsInWorld() || !c->IsAlive() || c->IsPet() || c->IsTotem()) continue;
   // Conservative native-trash clearance along the pull corridor as well as
   // landing point. Setup GM state makes faction-based aggro tests unsuitable.
   for(const auto& point : path) {
    float dx=c->GetPositionX()-point.coord_x, dy=c->GetPositionY()-point.coord_y;
    float dz=c->GetPositionZ()-point.coord_z;
    // Native DetectOrAttack compares center distance (DIST_CALC_NONE).
    // Match its level/aura-adjusted radius, with two yards of fixture margin.
    float clearance=c->GetAttackDistance(bot)+2.0f;
    if(dx*dx+dy*dy+dz*dz<clearance*clearance) {
     if(trashRejected<4) sLog.outString("RAID_LAB_SETUP: rejected radius=%.1f sector=%u trash=%u distance=%.2f limit=%.2f",
         radius,sector,c->GetEntry(),std::sqrt(dx*dx+dy*dy+dz*dz),clearance);
     clear=false;break;
    }
   }
  }
  if(!clear) {++trashRejected;continue;}
  if(!bot->TeleportTo(bot->GetMapId(),x,y,z,angle+float(M_PI))) {
   message="BLOCKED: native staging teleport refused";return TestResult::IMPOSSIBLE;
  }
  std::ostringstream details;
  details<<"Validated Magmadar staging "<<x<<","<<y<<","<<z<<" radius="<<radius
         <<" rejected floor="<<floorRejected<<" los="<<losRejected
         <<" path="<<pathRejected<<" trash="<<trashRejected;
  message=details.str();sLog.outString("RAID_LAB_SETUP: %s",message.c_str());
  return TestResult::PASS;
 }
 std::ostringstream details;
 details<<"BLOCKED: no clear Magmadar staging; floor="<<floorRejected<<" los="<<losRejected
        <<" path="<<pathRejected<<" trash="<<trashRejected;
 message=details.str();sLog.outString("RAID_LAB_SETUP: %s",message.c_str());
 return TestResult::IMPOSSIBLE;
}
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
 if(ctx.testName.find("_cleared_room")!=std::string::npos)
  RaidLab::Event(bot,"fixture_precleared_room_not_trash_validation");
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
