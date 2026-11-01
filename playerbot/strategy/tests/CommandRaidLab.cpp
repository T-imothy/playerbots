#include "playerbot/playerbot.h"
#ifdef MANTECH_RAID_LAB
#include "CommandRaidLab.h"
#include "RaidLabRoutes.h"
#include "RaidLabPacks.h"
#include "RaidLabSubgroupPlan.h"
#include "World/RaidLab.h"
#include "Groups/Group.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "Entities/GossipDef.h"
#include "Entities/Item.h"
#include "Spells/Spell.h"
#include "Spells/SpellTargets.h"
#include "Server/DBCStores.h"
#include "AI/ScriptDevAI/include/sc_instance.h"
#include "AI/BaseAI/UnitAI.h"
#include "Movement/MoveSpline.h"
#include "Maps/SpawnManager.h"
#include "MotionGenerators/WaypointMovementGenerator.h"
#include "MotionGenerators/PathFinder.h"
#include "Chat/Chat.h"
#include "GameEvents/GameEventMgr.h"
#include "playerbot/WorldPosition.h"
#include "playerbot/RandomPlayerbotMgr.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include <cmath>
#include <sstream>

using namespace ai;
namespace {
bool RaidLabWarmPreparationGrid(Player* bot, TestContext& ctx, const std::string& operation,
                                float x, float y, std::string& message) {
 // ForceLoadGrid does not run SpawnManager::Update. Native dynamic groups
 // must receive ordinary map updates before we inspect the landing area.
 // One bounded load per command/location, never forced Spawn/Respawn/Update.
 const std::string key=std::to_string(ctx.pc)+":"+operation+":"+
     std::to_string(bot->GetMapId())+":"+std::to_string(int(x/50))+":"+std::to_string(int(y/50));
 const uint32 now=WorldTimer::getMSTime();
 auto found=ctx.raidLabGridWarmups.find(key);
 if(found==ctx.raidLabGridWarmups.end()) {
  for(float dx:{-200.0f,0.0f,200.0f})for(float dy:{-200.0f,0.0f,200.0f})
   bot->GetMap()->ForceLoadGrid(x+dx,y+dy);
  ctx.raidLabGridWarmups.emplace(key,now);
  sLog.outString("RAID_LAB_SETUP: native grid warmup operation=%s map=%u at=%.3f,%.3f",operation.c_str(),bot->GetMapId(),x,y);
  message="Waiting for ordinary native spawn-group updates before preparation admission";
  return false;
 }
 if(uint32(now-found->second)<2000) {
  message="Waiting for native preparation grid updates";return false;
 }
 return true;
}
Player* RaidLabAggroReference(Player* leader) {
 // GM staging changes the leader's faction to 35. Use a real GM-off group
 // member for native faction reaction and level, never the GM immunity flag.
 if(!leader->GetGroup())return nullptr;
 for(auto ref=leader->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  if(member && member!=leader && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() &&
     !member->IsGameMaster() && member->GetTeam()==leader->GetTeam() && member->GetLevel()==leader->GetLevel())return member;
 }
 return nullptr;
}
bool RaidLabBodyPullRisk(Creature* creature, Player* reference, bool preparation = false) {
 // Relation/level checks do not need both units on the same map. Geometry is
 // evaluated separately against points on the creature's own map. Mirror the
 // native MoveInLineOfSight admission without using GM CanAttack immunity.
 return creature && reference && creature->IsInWorld() && creature->IsAlive() &&
     !creature->IsPet() && !creature->IsTotem() && !creature->IsCritter() &&
     !creature->IsNeutralToAll() && (preparation || creature->CanInitiateAttack()) && creature->AI() &&
     creature->AI()->HasReactState(REACT_AGGRESSIVE) && creature->IsEnemy(reference);
}
float RaidLabLandingRadius(float nativeAggro,float followRadius,float leaderRadius) {
 // Fresh mgroup fixtures use the configured follow formation. Validate its
 // footprint, not just the leader point: followers spread after delivery.
 if(!std::isfinite(nativeAggro) || !std::isfinite(followRadius) || !std::isfinite(leaderRadius) ||
    nativeAggro<0 || followRadius<0 || followRadius>30 || leaderRadius<0 || leaderRadius>5)return -1;
 return nativeAggro+followRadius+leaderRadius+2.0f;
}
bool RaidLabPatrolWaitAllowed(uint32 map,uint32 entry,uint32 now,uint32& started) {
 if(!((map==533 && (entry==15931 || entry==16028)) || (map==409 && entry==12056)))return false;
 if(!started)started=now;
 return uint32(now-started)<120000;
}
bool RaidLabNefariusWaveFailed(uint32 map,uint32 entry,const std::string& kind,
    uint32 state,uint32 now,uint32& failedAt) {
 if(map!=469 || entry!=11583 || kind!="gossip" || state!=FAIL) {failedAt=0;return false;}
 // The dragon does not exist when the native first-wave event resets.
 // Keep thirty seconds of real recovery, then report that failure instead
 // of waiting out the fifteen-minute dragon-spawn timeout.
 if(!failedAt)failedAt=now;
 return uint32(now-failedAt)>=30000;
}
bool RaidLabObservePackDeath(TestContext& ctx,ObjectGuid guid,Creature* creature) {
 if(!ctx.raidLabPackMembers.count(guid) || !creature || creature->GetObjectGuid()!=guid)return false;
 if(creature->IsAlive()){ctx.raidLabPackDead.erase(guid);return false;}
 return ctx.raidLabPackDead.insert(guid).second;
}
bool RaidLabEyeLandingSuggestion(uint32 map,uint32 entry,uint32 pathType,size_t count,
    float x,float y,float z,float endX,float endY,float endZ)
{
 if(map!=531 || entry!=15589 || pathType!=PATHFIND_NORMAL || count<2 || count>256)return false;
 for(float value:{x,y,z,endX,endY,endZ})if(!std::isfinite(value))return false;
 return std::hypot(endX-x,endY-y)<=4.0f && std::fabs(endZ-z)<=6.0f;
}
bool RaidLabTrashLandingSuggestion(uint32 map,uint32 entry,bool scopedFixture,uint32 pathType,size_t count,
    float x,float y,float z,float endX,float endY,float endZ)
{
 // Only a new search point for these isolated fixtures, never permission to
 // use an incomplete path. A new floor/aggro/full-route check is mandatory.
 if(!scopedFixture || !((map==409 && entry==11669) || (map==469 && entry==12465) || (map==509 && entry==15327)) ||
    (pathType!=PATHFIND_NORMAL && pathType!=PATHFIND_INCOMPLETE) || count<2 || count>256)return false;
 for(float value:{x,y,z,endX,endY,endZ})if(!std::isfinite(value))return false;
 return std::hypot(endX-x,endY-y)<=20 && std::fabs(endZ-z)<=16;
}
bool RaidLabLandingFloor(Map* map,float x,float y,float hint,float limit,float& height)
{
 if(!map || !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(hint) ||
    !std::isfinite(limit) || limit<=0 || limit>40)return false;
 const auto valid=[&](float value) {
  return std::isfinite(value) && value>INVALID_HEIGHT && std::fabs(value-hint)<=limit;
 };
 height=map->GetHeight(x,y,hint);
 if(valid(height))return true;
 // Broad height searches can select an overlapping floor outside the
 // requested band. Use the native bounded search, with the SAME tolerance.
 float nearby=hint;
 if(!map->GetHeightInRange(x,y,nearby,limit) || !valid(nearby))return false;
 height=nearby;return true;
}
template<class Candidate>
bool RaidLabEyeOuterApproach(uint32 map,uint32 entry,float bossX,float bossY,float bossZ,
    float original,float bearing,Candidate candidate) {
 if(map!=531 || entry!=15589)return false;
 for(float value:{bossX,bossY,bossZ,original,bearing})if(!std::isfinite(value))return false;
 // The Eye sees a raid formation from over 100 yards. A 90-yard fallback
 // cannot find a clear outer waiting point. Only extend this fixture's search;
 // the same callback still requires native floor, clearance and full route.
 for(float radius:{110.0f,120.0f,130.0f})
  for(unsigned sector=0;sector<24;++sector) {
   const float angle=bearing+float(sector)*float(2*M_PI)/24.0f;
   const float x=bossX+radius*std::cos(angle),y=bossY+radius*std::sin(angle);
   if(candidate(x,y,bossZ,8.0f))return true;
   if(std::fabs(original-bossZ)>0.1f && std::fabs(original-bossZ)<=40.0f &&
      candidate(x,y,original,8.0f))return true;
  }
 return false;
}
template<class Candidate>
bool RaidLabNothDoorApproach(uint32 map,uint32 entry,float bossX,float bossY,
    float doorX,float doorY,float doorZ,Candidate candidate) {
 if(map!=533 || entry!=15954 || !std::isfinite(bossX) || !std::isfinite(bossY) ||
    !std::isfinite(doorX) || !std::isfinite(doorY) || !std::isfinite(doorZ))return false;
 const float dx=doorX-bossX,dy=doorY-bossY,length=std::hypot(dx,dy);
 if(length<5 || length>120)return false;
 // The entrance corridor falls between coarse radial samples. Sample only
 // along the corridor outside the native entry door. The native 53-yard
 // detection plus formation/patrol clearance exceeded the former 30-yard
 // search. Each point still uses the ordinary
 // floor, formation/patrol aggro, LOS and complete-path admission callback.
 for(float outward=6;outward<=70;outward+=4)
  for(float side=-6;side<=6;side+=2)
   if(candidate(doorX+(dx*outward-dy*side)/length,
                doorY+(dy*outward+dx*side)/length,doorZ,2.0f))return true;
 return false;
}
bool RaidLabInsideWanderEnvelope(Creature* creature,float x,float y,float z,float clearance) {
 if(!creature || creature->GetDefaultMovementType()!=RANDOM_MOTION_TYPE)return false;
 const float wander=creature->GetRespawnRadius();
 if(!std::isfinite(wander) || wander<0 || !std::isfinite(clearance) || clearance<0)return true;
 if(wander==0)return false;
 float homeX,homeY,homeZ;creature->GetRespawnCoord(homeX,homeY,homeZ);
 const float dx=x-homeX,dy=y-homeY,dz=z-homeZ;
 return !std::isfinite(dx) || !std::isfinite(dy) || !std::isfinite(dz) ||
     dx*dx+dy*dy+dz*dz<(clearance+wander)*(clearance+wander);
}
bool RaidLabInsidePatrolPath(const WaypointPath& path,float x,float y,float z,float clearance) {
 if(path.empty() || path.size()>1024 || !std::isfinite(clearance) || clearance<0)return true;
 auto previous=path.rbegin()->second;
 for(const auto& item:path) {
  const auto& point=item.second;
  const float dx=point.x-previous.x,dy=point.y-previous.y,dz=point.z-previous.z;
  const float length=dx*dx+dy*dy+dz*dz;
  const float projection=length>0?std::max(0.0f,std::min(1.0f,((x-previous.x)*dx+(y-previous.y)*dy+(z-previous.z)*dz)/length)):0;
  const float px=x-previous.x-projection*dx,py=y-previous.y-projection*dy,pz=z-previous.z-projection*dz;
  if(!std::isfinite(length) || !std::isfinite(px) || !std::isfinite(py) || !std::isfinite(pz) ||
     px*px+py*py+pz*pz<clearance*clearance)return true;
  previous=point;
 }
 return false;
}
bool RaidLabInsidePatrolEnvelope(Creature* creature,float x,float y,float z,float clearance) {
 // A formation follower's idle/default movement is not its patrol. Inspect
 // the real master's native waypoint route and reserve the follower offset.
 Creature* master=creature;
 if(auto slot=creature->GetFormationSlot()) {
  Unit* owner=slot->GetMaster();
  if(owner && owner->IsCreature() && owner->IsInMap(creature)) {
   master=static_cast<Creature*>(owner);
   const float offset=std::max(slot->GetDistance(),slot->GetRealDistance());
   if(!std::isfinite(offset) || offset<0 || offset>100)return true;
   clearance+=offset+2;
  }
 }
 const WaypointPath* path=nullptr;
 if(auto movement=dynamic_cast<const WaypointMovementGenerator<Creature>*>(master->GetMotionMaster()->GetCurrent())) {
  uint32 id=0;WaypointPathOrigin origin=PATH_NO_PATH;movement->GetPathInformation(id,origin);
  path=sWaypointMgr.GetPathFromOrigin(master->GetEntry(),master->GetDbGuid(),id,origin);
 } else if(master->GetDefaultMovementType()==WAYPOINT_MOTION_TYPE || master->GetDefaultMovementType()==LINEAR_WP_MOTION_TYPE) {
  WaypointPathOrigin origin=PATH_NO_PATH;
  path=sWaypointMgr.GetDefaultPath(master->GetEntry(),master->GetDbGuid(),&origin);
 } else return false;
 if(!path)return std::hypot(x-master->GetPositionX(),y-master->GetPositionY())<clearance+100;
 return RaidLabInsidePatrolPath(*path,x,y,z,clearance);
}
bool RaidLabFormationVisible(Creature* creature,Player* reference,float x,float y,float z,float footprint) {
 // A leader hidden behind a corner does not imply every follower is hidden.
 // Sample the bounded formation edge as well as the centre using native LOS.
 if(!creature || !reference || !std::isfinite(footprint) || footprint<0 || footprint>35)return true;
 for(unsigned point=0;point<17;++point) {
  const float radius=point?footprint:0.0f;
  const float angle=float(point)*float(2*M_PI)/16.0f;
  if(creature->IsWithinLOS(x+radius*std::cos(angle),y+radius*std::sin(angle),z+reference->GetCollisionHeight(),true))return true;
 }
 return false;
}
bool RaidLabRemovedPrerequisite(uint32 map,uint32 boss,const std::string& scenario,uint32 entry) {
 // Explicit local boss-only companion. Lucifron is normally already defeated
 // before Magmadar; retaining him here confounds fear recovery with a two-boss
 // fight. Neither this removal nor the companion validates Lucifron/progression.
 return map==409 && boss==11982 &&
     (scenario=="raidlab_409_11982_leader_post_lucifron_cleared_room" ||
      scenario=="raidlab_409_11982_leader_mobile_post_lucifron_cleared_room") &&
     (entry==12118 || entry==12119);
}
bool RaidLabRoomTrash(uint32 map,uint32 entry) {
 // Explicit boss-only fixture: native encounter adds are deliberately absent
 // from this list (Firesworn, Core Ragers, protectors, priests, Domo's adds).
 if(map==469)return entry==12458 || entry==12468 || (entry>=14022 && entry<=14025); // Broodlord-only fixture; suppression progression is separate.
 if(map==531)return entry==15233 || entry==15247; // Trio ambient guardians/brainwashers; preserve royalty/brood/clouds.
 if(map==509)return entry==15325 || entry==15327; // Reviewed Kurinnaxx/Ayamiss ambient wasps/stingers, not encounter summons.
 if(map==309) {
  // Explicit Mar'li/Thekal boss fixtures. Keep egg-spawned spiders (15041),
  // zealots (11347/11348) and Thekal's summoned guardians (15068).
  return entry==14880 || entry==14881 || entry==14532 || entry==11388 || entry==11350 || entry==11361;
 }
 if(map==533) {
  // Reviewed native ambient spider-wing packs. Keep Faerlina's six adds,
  // Anub'Rekhan's guards, webs and every native encounter spawn/trigger.
  switch(entry) {
   case 15974:case 15975:case 15976:case 15977:
   case 15978:case 15979:case 15980:case 15981:
   case 16025:case 16056:case 16057:return true; // ambient spewers/maggots; not boss summons or tunnel stalks
   default:return false;
  }
 }
 if(map!=409)return false;
 switch(entry) {
  case 11658:case 11659:case 11665:case 11666:case 11667:case 11668:
  case 11669:case 11671:case 11673:case 12076:case 12100:case 12101:return true;
  default:return false;
 }
}
bool RaidLabClearRoomActor(uint32 map,uint32 boss,const std::string& scenario,uint32 entry,float distance) {
 if(!std::isfinite(distance) || distance<0)return false;
 // Native Jin'do landing was correctly rejected by his uncleared room's
 // slaves/mistresses. This explicitly named companion isolates only the boss;
 // retain sacrificed trolls, totems, shades and all native event actors.
 if(map==309 && boss==11380 && scenario=="raidlab_309_11380_leader_cleared_room" && distance<100 &&
    (entry==14883 || entry==14882 || entry==14825))return true;
 return RaidLabRemovedPrerequisite(map,boss,scenario,entry) ||
     (RaidLabRoomTrash(map,entry) && distance<150.0f);
}
bool RaidLabLocalFloor(Player* member, float& floor) {
 const float x=member->GetPositionX(),y=member->GetPositionY(),z=member->GetPositionZ();
 if(!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z))return false;
 floor=member->GetMap()->GetHeight(x,y,z);
 if(std::isfinite(floor) && floor>INVALID_HEIGHT && std::fabs(floor-z)<=2.0f)return true;
 // The broad terrain query can prefer an overhead surface inside a building.
 // Ask the native bounded-height API for a floor within the SAME two-yard
 // tolerance. Reject missing ground and dynamic surfaces outside that bound.
 const float broad=floor;float nearby=z;
 if(!member->GetMap()->GetHeightInRange(x,y,nearby,2.0f) || !std::isfinite(nearby) ||
    nearby<=INVALID_HEIGHT || std::fabs(nearby-z)>2.0f)return false;
 floor=nearby;
 sLog.outString("RAID_LAB_SETUP: bounded native floor member=%u broad=%.3f nearby=%.3f z=%.3f limit=2",member->GetGUIDLow(),broad,nearby,z);
 return true;
}
bool RaidLabPartyReady(Player* bot, PlayerbotAI* ai, Player*& tank, std::string& message) {
 if(!bot->GetGroup()){message="BLOCKED: no raid group";return false;}
 tank=nullptr;
 for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
  auto p=r->getSource();
  if(!p) {message="BLOCKED: raid member reference has no player";return false;}
  std::string reason;
  if(!p->IsInWorld())reason="not_in_world";
  else if(p->IsBeingTeleported())reason="transferring";
  else if(!p->IsAlive())reason="dead";
  else if(p->GetMap()!=bot->GetMap())reason="different_map_or_instance";
  else if(p->IsGameMaster())reason="gm_mode";
  else if(p->GetDistance(bot)>30.0f)reason="too_far";
#ifdef MANGOSBOT_ZERO
  if(reason.empty() && p!=bot) {
   const uint32 requested=sRandomPlayerbotMgr.GetValue(p->GetGUIDLow(),"raid lab role");
   const uint32 actual=ai->IsTank(p)?BOT_ROLE_TANK:ai->IsHeal(p)?BOT_ROLE_HEALER:BOT_ROLE_DPS;
   if(requested && requested!=actual)
    reason="fixture_role_mismatch_requested_"+std::to_string(requested)+"_actual_"+std::to_string(actual);
  }
#endif
  if(!reason.empty()) {
   std::ostringstream detail;
   detail<<"BLOCKED: raid preparation member="<<p->GetObjectGuid().GetRawValue()<<" reason="<<reason
         <<" map="<<p->GetMapId()<<" instance="<<p->GetInstanceId();
   if(p->IsInWorld() && !p->IsBeingTeleported() && p->GetMap()==bot->GetMap())
    detail<<" distance="<<p->GetDistance(bot)<<" limit=30 position="<<p->GetPositionX()<<","<<p->GetPositionY()<<","<<p->GetPositionZ();
   message=detail.str();
   return false;
  }
  if(p->IsInCombat()) {
   std::ostringstream detail;
   detail<<"BLOCKED: group already fighting before the native boss pull member="<<p->GetObjectGuid().GetRawValue()
         <<" position="<<p->GetPositionX()<<","<<p->GetPositionY()<<","<<p->GetPositionZ()<<" attackers=";
   for(Unit* attacker:p->getAttackers())
    if(attacker)detail<<attacker->GetEntry()<<":"<<attacker->GetObjectGuid().GetRawValue()<<",";
   message=detail.str();
   return false;
  }
  float floor=INVALID_HEIGHT;
  if(!RaidLabLocalFloor(p,floor)) {
   std::ostringstream detail;
   detail<<"BLOCKED: raid preparation member="<<p->GetObjectGuid().GetRawValue()<<" reason=native_floor"
         <<" map="<<p->GetMapId()<<" instance="<<p->GetInstanceId()
         <<" position="<<p->GetPositionX()<<","<<p->GetPositionY()<<","<<p->GetPositionZ()
         <<" floor="<<floor<<" limit=2";
   message=detail.str();
   return false;
  }
  if(p!=bot && p->GetPlayerbotAI() && ai->IsTank(p) && !tank) tank=p;
 }
 if(!tank) {message="BLOCKED: no assigned tank";return false;}
 return true;
}
void RaidLabFollowers(Player* bot, PlayerbotAI* ai, TestContext& ctx) {
 ctx.focusMobPassive=true;
 ai->ChangeStrategy("+test::"+ctx.testName,BotState::BOT_STATE_REACTION);
 RaidLab::Event(bot,(ctx.testName=="raidlab_409_11982_leader_mobile_cleared_room" ||
     ctx.testName=="raidlab_409_11982_leader_mobile_post_lucifron_cleared_room" ||
     ctx.testName=="raidlab_533_15936_leader_mobile_cleared_room")
     ? "leader_policy_native_avoidance_only" : "leader_policy_passive");
 for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
  Player* p=r->getSource();
  // An ordinary player pull does not reset already prepared companions.
  // Preserve their raid/class strategies, caches and decision queue. Initial
  // delivery/settled preparation has already installed the real master.
  if(p && p!=bot && p->GetPlayerbotAI() && p->GetPlayerbotAI()->GetMaster()!=bot) {
   p->GetPlayerbotAI()->SetMaster(bot);p->GetPlayerbotAI()->ResetStrategies(false);
  }
 }
}
bool RaidLabGossip(Player* bot, Creature* npc, unsigned choices) {
 // Use the actual offered menu indices through the same packet handlers as
 // a player. Never call the script's start callback or force encounter state.
 if(!npc || !bot->GetNPCIfCanInteractWith(npc->GetObjectGuid(),UNIT_NPC_FLAG_GOSSIP))return false;
 bot->GetPlayerMenu()->ClearMenus();
 WorldPacket hello(CMSG_GOSSIP_HELLO);hello<<npc->GetObjectGuid();
 bot->GetSession()->HandleGossipHelloOpcode(hello);
 for(unsigned step=1;step<=choices;++step) {
  auto& menu=bot->GetPlayerMenu()->GetGossipMenu();
  bool found=false;
  for(unsigned index=0;index<menu.MenuItemCount();++index) {
   if(menu.MenuItemAction(index)!=1000+step || menu.MenuItemSender(index)!=1 || menu.MenuItemCoded(index))continue;
   RaidLab::Event(bot,"native_gossip_choice",npc->GetObjectGuid().GetRawValue(),1000+step);
   WorldPacket select(CMSG_GOSSIP_SELECT_OPTION);select<<npc->GetObjectGuid()<<uint32(index);
   bot->GetSession()->HandleGossipSelectOptionOpcode(select);found=true;break;
  }
  if(!found)return false;
 }
 return true;
}
TestResult RaidLabLeaderWalk(Player* bot, PlayerbotAI* ai, float x,float y,float z,std::string& message, bool allowCombat=false) {
 // Models player movement only; followers retain their ordinary movement,
 // combat and healing actions. No teleport, forced combat or boss movement.
 if(!bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetTransport() || !ai->CanMove())return TestResult::PENDING;
 if(bot->GetDistance(x,y,z)<=2.5f) {
  if(!bot->IsStopped())bot->StopMoving();
  return TestResult::PASS;
 }
 bool fighting=bot->IsInCombat();
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
  if(Player* member=ref->getSource())fighting|=member->IsInWorld() && member->IsInMap(bot) && member->IsInCombat();
 if(fighting && !allowCombat) {
  if(!bot->IsStopped())bot->StopMoving();
  return TestResult::PENDING;
 }
 if(bot->movespline && !bot->movespline->Finalized()) {
  const auto end=bot->movespline->FinalDestination();
  if(std::hypot(end.x-x,end.y-y)<1.5f && std::fabs(end.z-z)<2)return TestResult::PENDING;
 }
 const float floor=bot->GetMap()->GetHeight(x,y,z);
 if(!std::isfinite(floor) || floor<=INVALID_HEIGHT || std::fabs(floor-z)>3) {
  message="BLOCKED: progression waypoint has no bounded native floor";return TestResult::IMPOSSIBLE;
 }
 WorldPosition destination(bot->GetMapId(),x,y,floor);
 const auto route=destination.getPathStepFrom(WorldPosition(bot),bot,true);
 if(route.size()<2 || route.size()>256 || !destination.isPathTo(route,1.0f,2.0f)) {
  message="BLOCKED: progression waypoint has no complete native walking path";return TestResult::IMPOSSIBLE;
 }
 for(const auto& point:route)
  if(point.getMapId()!=bot->GetMapId() || !std::isfinite(point.getX()) || !std::isfinite(point.getY()) || !std::isfinite(point.getZ())) {
   message="BLOCKED: invalid progression route";return TestResult::IMPOSSIBLE;
  }
 auto points=WorldPosition().toPointsArray(route);
 bot->GetMotionMaster()->Clear(false,true);bot->GetMotionMaster()->MovePath(points,FORCED_MOVEMENT_RUN,false,false);
 RaidLab::Event(bot,"progression_player_walk",uint64(route.size()));
 return TestResult::PENDING;
}
}
TestResult CommandRaidLabCorridor::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                           TestContext& ctx, std::string& message)
{
 const auto* corridor=FindRaidLabCorridor(params);
 if(!corridor){message="BLOCKED: unknown native corridor";return TestResult::IMPOSSIBLE;}
 const bool suppression=params=="suppression";
 const uint32 map=corridor->map, entry=corridor->boss, size=corridor->size;
 if(!RaidLab::Enabled() ||
    ctx.testName!="raidlab_"+std::to_string(map)+"_"+std::to_string(entry)+"_leader_progression" ||
    !bot->IsInWorld() || bot->GetMapId()!=map || bot->IsGameMaster() || bot->IsBeingTeleported() ||
    !bot->GetGroup() || bot->GetGroup()->GetLeaderGuid()!=bot->GetObjectGuid()) {
  message="BLOCKED: corridor requires its isolated GM-off player-led raid fixture";return TestResult::IMPOSSIBLE;
 }
 if(bot->GetGroup()->GetMembersCount()!=size) {message="Corridor raid lost members";return TestResult::FAIL;}
 const uint32 now=WorldTimer::getMSTime();
 if(!ctx.raidLabEventStarted) {
  Player* tank=nullptr;if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::IMPOSSIBLE;
  bot->SetSelectionGuid(ObjectGuid());
  if(!RaidLab::Begin(bot,entry,ctx.testName,true)){message="Corridor trace could not start";return TestResult::IMPOSSIBLE;}
  ctx.raidLabEventStarted=ctx.raidLabStageStarted=now;ctx.focusMobGuid.Clear();ctx.focusMobEntry=entry;
  RaidLabFollowers(bot,ai,ctx);
  RaidLab::Event(bot,"fixture_native_trash_corridor_start",suppression?1:0);
  if(suppression)
   for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
    if(Player* member=ref->getSource())
     if(member!=bot && member->GetPlayerbotAI())member->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"formation melee",*bot);
 }
 if(now-ctx.raidLabEventStarted>1650000){message="Native trash corridor exceeded 27.5-minute bound";return TestResult::FAIL;}
 if(!bot->IsAlive()){message="Player leader died during native corridor";return TestResult::FAIL;}
 Player* tank=nullptr;bool anyCombat=false, regroup=true;unsigned alive=0;
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  if(!member || !member->IsInWorld() || member->IsBeingTeleported() || !bot->IsInMap(member)) {
   message="Native corridor member left its instance";return TestResult::FAIL;
  }
  anyCombat|=member->IsInCombat();alive+=member->IsAlive()?1:0;
  regroup&=member->IsAlive() && member->GetDistance(bot)<18 && member->GetHealthPercent()>=70;
  if(ai->IsHeal(member) && member->GetMaxPower(POWER_MANA)>0)
   regroup&=member->GetPower(POWER_MANA)*100.0f/member->GetMaxPower(POWER_MANA)>=35;
  if(member!=bot && member->IsAlive() && member->GetPlayerbotAI() && ai->IsTank(member) && !tank)tank=member;
 }
 if(!tank){message="Native corridor has no living assigned tank";return TestResult::FAIL;}
 Creature* boss=nullptr;Creature* pullTarget=nullptr;bool majorCombat=false;float nearest=32.0f;
 auto& store=bot->GetMap()->GetObjectsStore();
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;
  if(!c || !c->IsInWorld() || !c->IsAlive() || c->HasCharmer() || c->IsPet() || c->IsTotem())continue;
  if(c->GetEntry()==entry)boss=c;
  const float distance=bot->GetDistance(c);
  if(distance>100)continue;
  Unit* victim=c->GetVictim();if(victim && !victim->IsPlayer())victim=victim->GetMaster();
  Player* player=dynamic_cast<Player*>(victim);
  if(c->IsInCombat() && player && player->GetGroup()==bot->GetGroup() &&
     !(suppression && c->GetEntry()>=14022 && c->GetEntry()<=14025))majorCombat=true;
  if(!c->IsInCombat() && distance<nearest && std::fabs(c->GetPositionZ()-bot->GetPositionZ())<7 &&
     RaidLabBodyPullRisk(c,bot) && c->IsWithinLOSInMap(bot)) {nearest=distance;pullTarget=c;}
 }
 if(boss && ctx.focusMobGuid.IsEmpty()) {
  if(!RaidLab::BindNativeBoss(boss)){message="Native corridor boss binding failed";return TestResult::FAIL;}
  ctx.focusMobGuid=boss->GetObjectGuid();
 }
 if(boss && boss->IsInCombat()) {ctx.combatSeen=true;message="Native trash traversal reached boss combat; mechanics review remains";return TestResult::PASS;}
 // One normal pull per living target. Do not mask a refused pull by injecting
 // repeated attack commands or changing threat, AI state or health.
 if(!ctx.raidLabPullGuid.IsEmpty()) {
  Unit* target=ai->GetUnit(ctx.raidLabPullGuid);
  if(!target || !target->IsInWorld() || !target->IsAlive()) {
   RaidLab::Event(bot,"corridor_pull_finished",ctx.raidLabPullGuid.GetRawValue());
   ctx.raidLabPullGuid.Clear();bot->SetSelectionGuid(ObjectGuid());ctx.raidLabStageStarted=now;
  } else {
   if(!target->IsInCombat() && now-ctx.raidLabPullStarted>45000) {
    message="Native corridor ordinary tank pull failed to engage within 45 seconds";return TestResult::FAIL;
   }
   if(!bot->IsStopped())bot->StopMoving();return TestResult::PENDING;
  }
 }
 if(majorCombat || (anyCombat && !suppression)) {
  ctx.raidLabStageStarted=now;if(!bot->IsStopped())bot->StopMoving();return TestResult::PENDING;
 }
 if(!regroup || alive!=size) {
  if(!bot->IsStopped())bot->StopMoving();
  if(now-ctx.raidLabStageStarted>180000){message="Native corridor failed to heal, resurrect or regroup within three minutes";return TestResult::FAIL;}
  return TestResult::PENDING;
 }
 if(pullTarget && !anyCombat) {
  ctx.raidLabPullGuid=pullTarget->GetObjectGuid();ctx.raidLabPullStarted=now;
  bot->SetSelectionGuid(ctx.raidLabPullGuid);
  RaidLab::Event(bot,"corridor_player_pull",ctx.raidLabPullGuid.GetRawValue(),tank->GetObjectGuid().GetRawValue());
  tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
  return TestResult::PENDING;
 }
 // Advance only six yards per player decision along a complete native path.
 // In suppression, healthy grouped players can advance through minor whelps;
 // native rogues, tanks and followers perform all trap/combat work themselves.
 if(bot->movespline && !bot->movespline->Finalized())return TestResult::PENDING;
 WorldPosition destination(map,corridor->x,corridor->y,corridor->z);
 const auto route=destination.getPathStepFrom(WorldPosition(bot),bot,true);
 if(route.size()<2 || route.size()>1024 || !destination.isPathTo(route,1.0f,2.0f)) {
  message="BLOCKED: native corridor has no complete path to its destination";return TestResult::IMPOSSIBLE;
 }
 WorldPosition next=route.front();float remaining=6;
 for(size_t i=1;i<route.size();++i) {
  const float dx=route[i].getX()-next.getX(),dy=route[i].getY()-next.getY(),dz=route[i].getZ()-next.getZ();
  const float length=std::sqrt(dx*dx+dy*dy+dz*dz);
  if(!std::isfinite(length) || route[i].getMapId()!=map){message="BLOCKED: invalid native corridor path";return TestResult::IMPOSSIBLE;}
  if(length>=remaining && length>0) {next=WorldPosition(map,next.getX()+dx*remaining/length,next.getY()+dy*remaining/length,next.getZ()+dz*remaining/length);break;}
  remaining-=length;next=route[i];
 }
 ctx.raidLabStageStarted=now;
 TestResult result=RaidLabLeaderWalk(bot,ai,next.getX(),next.getY(),next.getZ(),message,suppression && anyCombat && !majorCombat);
 if(result==TestResult::PASS){message="Corridor reached destination without native boss engagement";return TestResult::FAIL;}
 return result;
}
bool RaidLabBalanceSubgroups(Player* leader,PlayerbotAI* ai,std::string& message)
{
 Group* group=leader->GetGroup();
 if(!group || !group->IsRaidGroup() || group->GetLeaderGuid()!=leader->GetObjectGuid() ||
    !RaidLab::Controlled(leader)) {message="BLOCKED: subgroup preparation requires owned local raid";return false;}
 const unsigned size=group->GetMembersCount(),groups=size/5;
 if(size!=20 && size!=40) {message="BLOCKED: unexpected local raid size";return false;}
 std::vector<Player*> members;std::vector<RaidLabMemberRole> roles;
 std::array<unsigned,8> counts{};
 for(auto ref=group->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  if(!member || member->GetGroup()!=group || !member->IsInWorld() || !member->IsAlive() ||
     member->IsBeingTeleported() || !leader->IsInMap(member) || member->IsInCombat() || member->GetSubGroup()>=groups) {
   message="BLOCKED: subgroup preparation requires all members settled out of combat";return false;
  }
  members.push_back(member);++counts[member->GetSubGroup()];
  roles.push_back({member->GetObjectGuid().GetRawValue(),ai->IsTank(member),ai->IsHeal(member),
      member->getClass()==CLASS_SHAMAN || member->getClass()==CLASS_PALADIN});
 }
 const auto planned=RaidLabSubgroups(roles);
 if(members.size()!=size || planned.size()!=size ||
    std::any_of(counts.begin(),counts.begin()+groups,[](unsigned n){return n!=5;})) {
  message="BLOCKED: subgroup identity/count plan invalid";return false;
 }
 for(size_t i=0;i<members.size();++i) {
  const uint8 old=members[i]->GetSubGroup(),target=planned[i];
  if(old==target)continue;
  size_t partner=members.size();
  for(size_t j=i+1;j<members.size();++j)
   if(members[j]->GetSubGroup()==target && planned[j]!=target) {partner=j;break;}
  if(partner==members.size()) {message="BLOCKED: subgroup swap plan inconsistent";return false;}
  // Same native pair of operations as the raid leader's subgroup-swap opcode.
  group->ChangeMembersGroup(members[i],target);
  group->ChangeMembersGroup(members[partner],old);
 }
 for(size_t i=0;i<members.size();++i) {
  if(members[i]->GetSubGroup()!=planned[i]) {message="BLOCKED: native subgroup swap not applied";return false;}
  sLog.outString("RAID_LAB_ROSTER: subgroup member=%u group=%u class=%u tank=%u healer=%u provider=%u",
      members[i]->GetGUIDLow(),planned[i],members[i]->getClass(),roles[i].tank?1u:0u,roles[i].healer?1u:0u,roles[i].provider?1u:0u);
 }
 return true;
}

TestResult CommandRaidLabLeader::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                        TestContext& ctx, std::string& message)
{
 if((!params.empty() && params!="settled") || ctx.testName.find("raidlab_"+std::to_string(bot->GetMapId())+"_")!=0 ||
    ctx.testName.find("_leader")==std::string::npos || !bot->GetGroup() ||
    bot->GetGroup()->GetLeaderGuid()!=bot->GetObjectGuid() || !RaidLab::PrepareLeader(bot)) {
  message="BLOCKED: synthetic player leader requires an explicit local leader scenario and its own raid";
  return TestResult::IMPOSSIBLE;
 }
 if(params.empty()) {
  // Prepare on each member's owner thread before delivery. Waiting until the
  // settled command left a window for old autonomous grind/travel actions to
  // run at the landing point. The later reset still selects native raid roles.
  const ObjectGuid leaderGuid=bot->GetObjectGuid();
  for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
   Player* member=ref->getSource();
   if(member && member!=bot)
    ai->RunOnOwningThread(member,[leaderGuid](Player* follower) {
     Player* leader=sObjectMgr.GetPlayer(leaderGuid);
     PlayerbotAI* followerAI=follower->GetPlayerbotAI();
     if(!leader || !RaidLab::Controlled(leader) || !followerAI || followerAI->IsRealPlayer() ||
        !follower->GetGroup() || follower->GetGroup()!=leader->GetGroup() || follower->IsInCombat())return;
     const bool wasGrinding=followerAI->HasStrategy("grind",BotState::BOT_STATE_NON_COMBAT);
     followerAI->SetMaster(leader);followerAI->ResetStrategies(false);
     followerAI->ChangeStrategy("-grind,-travel,-rpg,-group,-guild,-maintenance",BotState::BOT_STATE_NON_COMBAT);
     sLog.outString("RAID_LAB_SETUP: prepared follower=%u leader=%u autonomous_grind_before=%u after=%u",
       follower->GetGUIDLow(),leader->GetGUIDLow(),wasGrinding?1u:0u,
       followerAI->HasStrategy("grind",BotState::BOT_STATE_NON_COMBAT)?1u:0u);
    });
  }
 }
 if(params=="settled") {
  const uint32 expected=bot->GetMapId()==309 || bot->GetMapId()==509?20:40;
  if(bot->GetGroup()->GetMembersCount()!=expected) {
   message="BLOCKED: synthetic player raid lost members during setup";return TestResult::IMPOSSIBLE;
  }
  for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
   Player* member=ref->getSource();
   if(!member || !member->IsInWorld() || member->IsBeingTeleported() || !bot->IsInMap(member)) {
    message="BLOCKED: synthetic player raid delivery not settled";return TestResult::IMPOSSIBLE;
   }
  }
  if(!RaidLabBalanceSubgroups(bot,ai,message))return TestResult::IMPOSSIBLE;
  for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
   Player* member=ref->getSource();
   if(member!=bot && member->GetPlayerbotAI()) {
    member->GetPlayerbotAI()->SetMaster(bot);member->GetPlayerbotAI()->ResetStrategies(false);
   }
  }
 }
 message="Synthetic player leader active for preparation as well as combat";return TestResult::PASS;
}
TestResult CommandRaidLabSeed::Execute(const std::string& params, Player* bot, PlayerbotAI*,
                                      TestContext& ctx, std::string& message)
{
 const bool combat=params=="majordomo" && ctx.testName=="raidlab_409_12018_leader_seeded";
 const bool summon=params=="ragnaros" && ctx.testName=="raidlab_409_11502_leader_seeded_event";
 if(!RaidLab::Enabled() || (!combat && !summon) || !bot->IsInWorld() || bot->GetMapId()!=409 ||
    !bot->IsGameMaster() || bot->IsBeingTeleported() || bot->IsInCombat()) {
  message="BLOCKED: native encounter seed requires explicitly named isolated GM setup";return TestResult::IMPOSSIBLE;
 }
 InstanceData* instance=bot->GetMap()->GetInstanceData();
 if(!instance) {message="BLOCKED: missing native MC instance";return TestResult::IMPOSSIBLE;}
 for(uint32 index=0;index<10;++index)
  if(instance->GetData(index)!=NOT_STARTED) {message="BLOCKED: seed may only initialize an untouched local instance";return TestResult::IMPOSSIBLE;}
 auto& store=bot->GetMap()->GetObjectsStore();
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;
  if(c && c->IsInWorld() && c->IsAlive() && (c->GetEntry()==12018 || c->GetEntry()==11502 || c->GetEntry()==11663 || c->GetEntry()==11664)) {
   message="BLOCKED: native MC encounter actors already exist; seed is not repeated";return TestResult::IMPOSSIBLE;
  }
 }
 // Use the instance's existing diagnostic setup, which creates its normal
 // Majordomo AI and all eight native adds (or its friendly summoning actor).
 // This intentionally skips prerequisites ONLY in named encounter fixtures.
 // It neither sets DONE/SPECIAL nor changes damage, movement or combat rules.
 ChatHandler handler(bot->GetSession());
 char combatCommand[]="spawnmajordomo 0",summonCommand[]="spawnmajordomo 1";
 instance->ExecuteChatCommand(&handler,combat?combatCommand:summonCommand);
 unsigned bosses=0,healers=0,elites=0;
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;if(!c || !c->IsInWorld() || !c->IsAlive())continue;
  bosses+=c->GetEntry()==12018?1:0;healers+=c->GetEntry()==11663?1:0;elites+=c->GetEntry()==11664?1:0;
 }
 if(bosses!=1 || (combat && (healers!=4 || elites!=4))) {
  message="BLOCKED: native Majordomo setup did not create the expected actors";return TestResult::IMPOSSIBLE;
 }
 sLog.outString("RAID_LAB_FIXTURE: native spawnmajordomo mode=%u bosses=%u healers=%u elites=%u; prerequisites NOT validated",combat?0u:1u,bosses,healers,elites);
 message="Explicit native encounter seed; rune and earlier-boss progression NOT validated";return TestResult::PASS;
}
TestResult CommandRaidLabProgression::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                             TestContext& ctx, std::string& message)
{
 if(!RaidLab::Enabled() || params!="rajaxx" || ctx.testName!="raidlab_509_15341_leader_progression" ||
    !bot->IsInWorld() || bot->GetMapId()!=509 || bot->IsBeingTeleported() || bot->IsGameMaster() || !bot->GetGroup()) {
  message="BLOCKED: progression requires the isolated GM-off AQ20 fixture";return TestResult::IMPOSSIBLE;
 }
 InstanceData* instance=bot->GetMap()->GetInstanceData();
 if(!instance) {message="BLOCKED: native AQ20 instance missing";return TestResult::IMPOSSIBLE;}
 if(bot->GetGroup()->GetMembersCount()!=20) {message="AQ20 progression lost its expected 20-player group";return TestResult::FAIL;}
 Creature* kurinnaxx=nullptr;Creature* andorov=nullptr;Creature* rajaxx=nullptr;
 auto& store=bot->GetMap()->GetObjectsStore();
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;if(!c || !c->IsInWorld())continue;
  if(c->GetEntry()==15348)kurinnaxx=c;
  if(c->GetEntry()==15471)andorov=c;
  if(c->GetEntry()==15341)rajaxx=c;
 }
 const uint32 now=WorldTimer::getMSTime();
 const auto stage=[&](uint32 value) {
  ctx.raidLabEventStage=value;ctx.raidLabStageStarted=now;
  RaidLab::Event(bot,"aq20_progression_stage",value);
 };
 if(!ctx.raidLabEventStarted) {
  Player* tank=nullptr;
  if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::IMPOSSIBLE;
  if(!kurinnaxx || !kurinnaxx->IsAlive() || kurinnaxx->IsInCombat() || bot->GetDistance(kurinnaxx)>100 ||
     instance->GetData(0)!=NOT_STARTED || instance->GetData(1)!=NOT_STARTED) {
   message="BLOCKED: progression requires untouched native Kurinnaxx and Rajaxx events";return TestResult::IMPOSSIBLE;
  }
  bot->SetSelectionGuid(ObjectGuid());
  if(!RaidLab::Begin(bot,15341,ctx.testName,true)) {message="BLOCKED: progression telemetry failed";return TestResult::IMPOSSIBLE;}
  ctx.focusMobGuid.Clear();ctx.focusMobEntry=15341;ctx.combatSeen=false;
  ctx.raidLabEventStarted=now;stage(1);RaidLabFollowers(bot,ai,ctx);
  bot->SetSelectionGuid(kurinnaxx->GetObjectGuid());
  RaidLab::Event(bot,"native_prerequisite_pull",kurinnaxx->GetObjectGuid().GetRawValue(),tank->GetObjectGuid().GetRawValue());
  tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
  return TestResult::PENDING;
 }
 bool alive=false;
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
  if(Player* member=ref->getSource())alive|=member->IsInWorld() && member->IsInMap(bot) && member->IsAlive();
 if(!alive) {message="Raid wiped during native AQ20 progression";return TestResult::FAIL;}
 if(now-ctx.raidLabEventStarted>1650000) {message="Native AQ20 progression exceeded its bounded 27.5-minute observation";return TestResult::FAIL;}
 if(rajaxx && rajaxx->IsAlive() && ctx.focusMobGuid.IsEmpty()) {
  if(!RaidLab::BindNativeBoss(rajaxx)){message="Native Rajaxx identity binding failed";return TestResult::FAIL;}
  ctx.focusMobGuid=rajaxx->GetObjectGuid();
 }
 if(ctx.raidLabEventStage==1) {
  if(instance->GetData(0)==FAIL) {message="Native Kurinnaxx prerequisite reset";return TestResult::FAIL;}
  if(instance->GetData(0)==DONE) {stage(2);bot->SetSelectionGuid(ObjectGuid());}
  else if(now-ctx.raidLabStageStarted>900000) {message="Native Kurinnaxx prerequisite timeout";return TestResult::FAIL;}
  return TestResult::PENDING;
 }
 if(ctx.raidLabEventStage==2) {
  if(now-ctx.raidLabStageStarted>180000) {message="Raid failed to recover and regroup after Kurinnaxx";return TestResult::FAIL;}
  Player* tank=nullptr;
  if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::PENDING;
  for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
   Player* member=ref->getSource();
   if(member->GetHealthPercent()<80 || (member->GetMaxPower(POWER_MANA)>0 &&
      member->GetPower(POWER_MANA)*100.0f/member->GetMaxPower(POWER_MANA)<40))return TestResult::PENDING;
  }
  stage(3);
 }
 if(ctx.raidLabEventStage==3) {
  if(now-ctx.raidLabStageStarted>180000) {message="Native Andorov arrival/dialogue timeout";return TestResult::FAIL;}
  if(!andorov || !andorov->IsAlive() || !andorov->HasFlag(UNIT_NPC_FLAGS,UNIT_NPC_FLAG_GOSSIP))return TestResult::PENDING;
  if(bot->GetNPCIfCanInteractWith(andorov->GetObjectGuid(),UNIT_NPC_FLAG_GOSSIP)) {
   if(!RaidLabGossip(bot,andorov,1)){message="Native Andorov did not offer the wave-start dialogue";return TestResult::FAIL;}
   stage(4);
  } else {
   const float angle=andorov->GetOrientation()+float(M_PI);
   TestResult walking=RaidLabLeaderWalk(bot,ai,andorov->GetPositionX()+3*std::cos(angle),andorov->GetPositionY()+3*std::sin(angle),andorov->GetPositionZ(),message);
   return walking==TestResult::PASS?TestResult::PENDING:walking;
  }
 }
 if(ctx.raidLabEventStage==4) {
  if(now-ctx.raidLabStageStarted>180000) {message="Leader/followers did not reach the native Andorov event station";return TestResult::FAIL;}
  // Native POINT_ID_MOVE_ATTACK from ruins_of_ahnqiraj.h; followers must
  // follow this ordinary player walk rather than another group teleport.
  TestResult walking=RaidLabLeaderWalk(bot,ai,-8940.45f,1550.69f,21.616f,message);
  if(walking!=TestResult::PASS)return walking;
  stage(5);
 }
 if(instance->GetData(1)==FAIL) {message="Native Rajaxx wave event reset";return TestResult::FAIL;}
 if((rajaxx && rajaxx->IsInCombat()) || RaidLab::BossDied(bot->GetMap(),ctx.focusMobGuid.GetRawValue())) {
  ctx.combatSeen=true;message="Native prerequisite, Andorov dialogue, player walk and waves reached Rajaxx";return TestResult::PASS;
 }
 return TestResult::PENDING;
}
std::vector<std::pair<uint8,uint32>> RaidLabFrostEquipment(uint8 cls, bool healer)
{
 // Real level-60 Naxxramas resistance equipment only. This is an explicit
 // synthetic test loadout, not automatic production gearing or acquisition.
 uint32 head=0,chest=0,hands=0,wrists=0;
 if(cls==CLASS_MAGE || cls==CLASS_PRIEST || cls==CLASS_WARLOCK ||
    (healer && (cls==CLASS_PALADIN || cls==CLASS_SHAMAN || cls==CLASS_DRUID)))
 {head=23032;chest=22652;hands=22654;wrists=22655;}
 else if(cls==CLASS_WARRIOR || cls==CLASS_PALADIN)
 {head=23019;chest=22669;hands=22670;wrists=22671;}
 else if(cls==CLASS_HUNTER || cls==CLASS_SHAMAN)
 {head=23033;chest=22664;hands=22666;wrists=22665;}
 else if(cls==CLASS_ROGUE || cls==CLASS_DRUID)
 {head=23020;chest=22661;hands=22662;wrists=22663;}
 else return {};
 return {{EQUIPMENT_SLOT_HEAD,head},{EQUIPMENT_SLOT_CHEST,chest},
  {EQUIPMENT_SLOT_HANDS,hands},{EQUIPMENT_SLOT_WRISTS,wrists},{EQUIPMENT_SLOT_BACK,22658}};
}
TestResult RaidLabPrepareFrost(Player* bot, PlayerbotAI* ai, TestContext& ctx, std::string& message)
{
 if(!RaidLab::Enabled() || !bot || bot->GetMapId()!=533 ||
    ctx.testName!="raidlab_533_15989_leader_event_prepared" || !bot->IsInWorld() ||
    bot->IsBeingTeleported() || bot->IsGameMaster()) {
  message="BLOCKED: frost equipment requires the explicit local prepared Sapphiron fixture";return TestResult::IMPOSSIBLE;
 }
 Player* tank=nullptr;if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::IMPOSSIBLE;
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  if(!member || !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer() ||
     member->GetLevel()!=60 || RaidLabFrostEquipment(member->getClass(),ai->IsHeal(member)).empty()) {
   message="BLOCKED: frost fixture may only prepare supported level-60 synthetic members";return TestResult::IMPOSSIBLE;
  }
 }
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  for(const auto& slot:RaidLabFrostEquipment(member->getClass(),ai->IsHeal(member))) {
   Item* worn=member->GetItemByPos(INVENTORY_SLOT_BAG_0,slot.first);
   if(worn && worn->GetEntry()==slot.second)continue;
   if(!member->GetItemCount(slot.second)) {
    ItemPosCountVec destination;
    if(member->CanStoreNewItem(NULL_BAG,NULL_SLOT,destination,slot.second,1)!=EQUIP_ERR_OK ||
       !member->StoreNewItem(destination,slot.second,true)) {
     message="BLOCKED: native storage refused a frost fixture item; combat not started";return TestResult::IMPOSSIBLE;
    }
   }
   Item* item=member->GetItemByEntry(slot.second);uint16 destination=0;
   if(!item){message="BLOCKED: supplied frost fixture item missing";return TestResult::IMPOSSIBLE;}
   const auto admission=member->CanEquipItem(slot.first,destination,item,true);
   if(admission!=EQUIP_ERR_OK) {
    const uint32 now=WorldTimer::getMSTime();if(!ctx.raidLabProvisionStarted)ctx.raidLabProvisionStarted=now;
    std::ostringstream detail;detail<<"Native frost equipment admission member="<<member->GetGUIDLow()<<" item="<<slot.second<<" error="<<uint32(admission);message=detail.str();
    if(admission==EQUIP_ERR_CANT_DO_RIGHT_NOW && member->IsNonMeleeSpellCasted(false) && now-ctx.raidLabProvisionStarted<60000)return TestResult::PENDING;
    message="BLOCKED: "+message;return TestResult::IMPOSSIBLE;
   }
   WorldPacket equip(CMSG_AUTOEQUIP_ITEM);equip<<item->GetBagSlot()<<item->GetSlot();
   member->GetSession()->HandleAutoEquipItemOpcode(equip);
   worn=member->GetItemByPos(INVENTORY_SLOT_BAG_0,slot.first);
   if(!worn || worn->GetEntry()!=slot.second){message="BLOCKED: native frost item equip did not apply";return TestResult::IMPOSSIBLE;}
  }
  sLog.outString("RAID_LAB_SETUP: explicit Sapphiron prepared fixture member=%u native_frost_resistance=%u",member->GetGUIDLow(),member->GetResistance(SPELL_SCHOOL_FROST));
 }
 message="Explicit real frost-resistance loadout equipped through native inventory; acquisition and automatic gearing untested";return TestResult::PASS;
}
TestResult CommandRaidLabProvision::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                           TestContext& ctx, std::string& message)
{
 if(params=="sapphiron")return RaidLabPrepareFrost(bot,ai,ctx,message);
 // Explicit local equipment fixture, never a production gear policy. It does
 // not certify acquisition of these items or the automatic equipment action.
 if(!RaidLab::Enabled() || params!="bwl" || bot->GetMapId()!=469 ||
    ctx.testName.find("raidlab_469_")!=0 || ctx.testName.find("_prepared")==std::string::npos ||
    !bot->IsInWorld() || bot->IsBeingTeleported() || bot->IsGameMaster()) {
  message="BLOCKED: equipment fixture requires explicit local prepared BWL trial";return TestResult::IMPOSSIBLE;
 }
 Player* tank=nullptr;if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::IMPOSSIBLE;
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  if(!member || !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer()) {
   message="BLOCKED: equipment fixture may only modify the local synthetic raid";return TestResult::IMPOSSIBLE;
  }
 }
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  for(uint32 entry:{15138u,19183u}) {
   const uint32 wanted=entry==15138?1:20;
   const uint32 have=member->GetItemCount(entry);
   if(have>=wanted)continue;
   ItemPosCountVec destination;
   if(member->CanStoreNewItem(NULL_BAG,NULL_SLOT,destination,entry,wanted-have)!=EQUIP_ERR_OK ||
      !member->StoreNewItem(destination,entry,true)) {
    message="BLOCKED: native inventory admission failed during local fixture preparation; no combat started";
    return TestResult::IMPOSSIBLE;
   }
  }
  Item* cloak=member->GetItemByEntry(15138);uint16 destination;
  Item* worn=member->GetItemByPos(INVENTORY_SLOT_BAG_0,EQUIPMENT_SLOT_BACK);
  if(!worn || worn->GetEntry()!=15138) {
   if(!cloak) {
    message="BLOCKED: supplied native cloak is missing";return TestResult::IMPOSSIBLE;
   }
   const auto admission=member->CanEquipItem(EQUIPMENT_SLOT_BACK,destination,cloak,true);
   if(admission!=EQUIP_ERR_OK) {
    // Pre-pull buffs/conjuring can temporarily prohibit equipping. Wait for
    // the real cast to finish, without cancelling it or bypassing inventory
    // admission. Item-count checks above make this retry idempotent.
    const uint32 now=WorldTimer::getMSTime();
    if(!ctx.raidLabProvisionStarted)ctx.raidLabProvisionStarted=now;
    std::ostringstream detail;
    detail<<"Native cloak equipment admission member="<<member->GetGUIDLow()<<" error="<<uint32(admission)
          <<" casting="<<member->IsNonMeleeSpellCasted(false);
    message=detail.str();
    if(admission==EQUIP_ERR_CANT_DO_RIGHT_NOW && member->IsNonMeleeSpellCasted(false) &&
       now-ctx.raidLabProvisionStarted<60000)return TestResult::PENDING;
    message="BLOCKED: "+message;return TestResult::IMPOSSIBLE;
   }
   WorldPacket equip(CMSG_AUTOEQUIP_ITEM);equip<<cloak->GetBagSlot()<<cloak->GetSlot();
   member->GetSession()->HandleAutoEquipItemOpcode(equip);
  }
  worn=member->GetItemByPos(INVENTORY_SLOT_BAG_0,EQUIPMENT_SLOT_BACK);
  if(!worn || worn->GetEntry()!=15138 || !member->HasAura(22683)) {
   message="BLOCKED: native cloak equipment/protection did not apply";return TestResult::IMPOSSIBLE;
  }
  sLog.outString("RAID_LAB_SETUP: explicit prepared fixture bot=%u cloak=15138 sand=%u protection=22683",member->GetGUIDLow(),member->GetItemCount(19183));
 }
 message="Explicit local fixture supplied real cloak/sand and equipped through native inventory; acquisition policy untested";
 return TestResult::PASS;
}
bool RaidLabSapphironFixture(uint32 map, uint32 entry, const std::string& scenario) {
 return map==533 && entry==15989 && (scenario=="raidlab_533_15989_leader_event" ||
  scenario=="raidlab_533_15989_leader_event_prepared");
}
GameObject* RaidLabBirthTrap(Player* bot) {
 GameObject* object=nullptr;
 MaNGOS::NearestGameObjectEntryInObjectRangeCheck check(*bot,181356,120.0f);
 MaNGOS::GameObjectLastSearcher<MaNGOS::NearestGameObjectEntryInObjectRangeCheck> searcher(object,check);
 Cell::VisitGridObjects(bot,searcher,120.0f);
 return object && object->IsInWorld() && object->GetGoType()==GAMEOBJECT_TYPE_TRAP ? object : nullptr;
}
TestResult RaidLabStageBirthTrap(Player* bot, TestContext& ctx, std::string& message) {
 // Sapphiron's native GO is a proximity trap, not a clickable activator.
 // Stage the whole formation outside its actual trigger before GM is removed.
 GameObject* object=RaidLabBirthTrap(bot);
 Player* reference=RaidLabAggroReference(bot);
 if(!object || !object->IsSpawned() || !reference) {
  message="BLOCKED: native birth trap or faction reference unavailable";return TestResult::IMPOSSIBLE;
 }
 const float radius=float(object->GetGOInfo()->trap.diameter)/2.0f;
 const float padding=sPlayerbotAIConfig.raidFollowDistance+bot->GetObjectBoundingRadius()+8.0f;
 if(!std::isfinite(radius) || radius<=0 || !std::isfinite(padding) || padding<8 || radius+padding+10>100) {
  message="BLOCKED: native birth trap staging envelope invalid";return TestResult::IMPOSSIBLE;
 }
 WorldPosition origin(object);
 if(!RaidLabWarmPreparationGrid(bot,ctx,"birth-trap",origin.getX(),origin.getY(),message))return TestResult::PENDING;
 for(float extra:{0.0f,5.0f,10.0f})for(unsigned sector=0;sector<24;++sector) {
  const float angle=float(sector)*float(2*M_PI)/24.0f;
  const float x=origin.getX()+(radius+padding+extra)*std::cos(angle);
  const float y=origin.getY()+(radius+padding+extra)*std::sin(angle);
  const float z=bot->GetMap()->GetHeight(x,y,origin.getZ());
  if(!std::isfinite(z) || z<=INVALID_HEIGHT || std::fabs(z-origin.getZ())>8)continue;
  bool risk=false;auto& store=bot->GetMap()->GetObjectsStore();
  for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
   Creature* c=i->second;
   if(c && c->IsInWorld() && c->IsAlive() && c->GetEntry()==15989) {risk=true;break;}
   if(!RaidLabBodyPullRisk(c,reference,true))continue;
   const float limit=RaidLabLandingRadius(c->GetAttackDistance(reference),sPlayerbotAIConfig.raidFollowDistance,bot->GetObjectBoundingRadius());
   if(limit<0 || RaidLabInsideWanderEnvelope(c,x,y,z,limit) || RaidLabInsidePatrolEnvelope(c,x,y,z,limit) ||
      (c->GetDistance(x,y,z)<limit && RaidLabFormationVisible(c,reference,x,y,z,padding))) {risk=true;break;}
  }
  if(risk)continue;
  WorldPosition destination(bot->GetMapId(),x,y,z);
  const auto route=destination.getPathStepFrom(origin,bot,true);
  if(route.size()<2 || route.size()>256 || !destination.isPathTo(route,1.0f,2.0f))continue;
  for(const auto& point:route)
   if(point.getMapId()!=bot->GetMapId() || !std::isfinite(point.getX()) || !std::isfinite(point.getY()) || !std::isfinite(point.getZ()))risk=true;
  if(risk)continue;
  if(!bot->TeleportTo(bot->GetMapId(),x,y,z,bot->GetOrientation())) {
   message="BLOCKED: native birth trap staging teleport refused";return TestResult::IMPOSSIBLE;
  }
  sLog.outString("RAID_LAB_SETUP: native birth trap radius=%.2f formationPadding=%.2f staging=%.3f,%.3f,%.3f",radius,padding,x,y,z);
  message="Staged outside native proximity trap with grounded complete path; no activation yet";return TestResult::PASS;
 }
 message="BLOCKED: no safe grounded formation outside native birth trap";return TestResult::IMPOSSIBLE;
}
TestResult RaidLabApproachBirthTrap(Player* bot,PlayerbotAI* ai,GameObject* trap,std::string& message)
{
 if(!trap || !trap->IsInWorld() || !bot->IsInMap(trap) || trap->GetGoType()!=GAMEOBJECT_TYPE_TRAP ||
    bot->GetMapId()!=533 || trap->GetEntry()!=181356) {
  message="BLOCKED: native birth approach identity invalid";return TestResult::IMPOSSIBLE;
 }
 if(!trap->IsSpawned()) {ai->StopMoving();return TestResult::PASS;}
 const float radius=float(trap->GetGOInfo()->trap.diameter)/2.0f;
 const float dx=bot->GetPositionX()-trap->GetPositionX(),dy=bot->GetPositionY()-trap->GetPositionY();
 const float distance=std::hypot(dx,dy);
 if(!std::isfinite(radius) || radius<=3 || radius>100 || !std::isfinite(distance)) {
  message="BLOCKED: native birth approach geometry invalid";return TestResult::IMPOSSIBLE;
 }
 // Enter only the native trigger's edge. Walking to its center drags every
 // follower underneath the future boss throughout the 22-second birth delay.
 if(distance<=radius-1) {ai->StopMoving();return TestResult::PASS;}
 const float x=trap->GetPositionX()+dx*(radius-2)/distance;
 const float y=trap->GetPositionY()+dy*(radius-2)/distance;
 const float z=bot->GetMap()->GetHeight(x,y,trap->GetPositionZ());
 if(!std::isfinite(z) || z<=INVALID_HEIGHT || std::fabs(z-trap->GetPositionZ())>8) {
  message="BLOCKED: native birth approach floor invalid";return TestResult::IMPOSSIBLE;
 }
 return RaidLabLeaderWalk(bot,ai,x,y,z,message);
}

SpellCastTargets RaidLabNativeItemTargets(GameObject* object)
{
 SpellCastTargets targets;
 if(object) {
  targets.setGOTarget(object);
  // Classic's setter stores the pointer/GUID only. The packet writer needs
  // this flag to serialize the brazier rather than sending an empty target.
  targets.m_targetMask |= TARGET_FLAG_GAMEOBJECT;
 }
 return targets;
}
TestResult CommandRaidLabEvent::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                       TestContext& ctx, std::string& message)
{
 uint32 entry=0,activator=0;std::string kind;std::istringstream input(params);input>>entry>>kind>>activator;
 const bool allowed=(RaidLabSapphironFixture(bot->GetMapId(),entry,ctx.testName) && kind=="trap" && activator==181356) ||
     (bot->GetMapId()==533 && entry==15990 && kind=="area" && activator==4112 && ctx.testName=="raidlab_533_15990_leader_event") ||
     (bot->GetMapId()==533 && entry==15928 && kind=="phase" && activator==15930 && ctx.testName=="raidlab_533_15928_leader_event") ||
     (bot->GetMapId()==531 && entry==15727 && kind=="phase" && activator==15589 && ctx.testName=="raidlab_531_15727_leader_event") ||
     (bot->GetMapId()==309 && entry==11382 && kind=="phase" && activator==11391 && ctx.testName=="raidlab_309_11382_leader_event") ||
     (bot->GetMapId()==533 && entry==16060 && kind=="gothik" && activator==16060) ||
     (bot->GetMapId()==309 && entry==14515 && kind=="go" && activator==180526) ||
     (bot->GetMapId()==531 && entry==15517 && kind=="approach" && activator==15957) ||
     (bot->GetMapId()==469 && entry==11583 && kind=="gossip" && activator==10162) ||
     (bot->GetMapId()==469 && entry==13020 && kind=="vael" && activator==3626) ||
     (bot->GetMapId()==469 && entry==14020 && kind=="go-existing" && activator==179148) ||
     (bot->GetMapId()==469 && entry==12435 && kind=="razorgore" && activator==12557) ||
     (bot->GetMapId()==309 && entry==15114 && kind=="item" && activator==19974 && ctx.testName=="raidlab_309_15114_leader_event_prepared") ||
     (bot->GetMapId()==309 && entry>=15082 && entry<=15085 && kind=="madness" && activator==19931 &&
      ctx.testName=="raidlab_309_"+std::to_string(entry)+"_leader_event_prepared") ||
     (bot->GetMapId()==409 && entry==11502 && kind=="gossip" && activator==12018 && ctx.testName=="raidlab_409_11502_leader_seeded_event");
 if(!RaidLab::Enabled() || !allowed || !bot->IsInWorld() || bot->IsBeingTeleported() || bot->IsGameMaster()) {
  message="BLOCKED: native event fixture requires isolated, settled GM-off participant";return TestResult::IMPOSSIBLE;
 }
 auto& store=bot->GetMap()->GetObjectsStore();Creature* boss=nullptr;Creature* pullTarget=nullptr;
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;
  if(!c || !c->IsInWorld() || !c->IsAlive() || bot->GetDistance(c)>100) continue;
  if(c->GetEntry()==entry && (!boss || bot->GetDistance(c)<bot->GetDistance(boss))) boss=c;
  if(c->GetEntry()==activator) pullTarget=c;
 }
 // The validated C'Thun corridor can be just beyond the generic 100-yard
 // actor scan. Resolve only its actual registered native eye/body; never
 // spawn a replacement or change encounter state to make the test start.
 if(bot->GetMapId()==531 && entry==15727 && kind=="phase" && activator==15589)
  if(auto* instance=dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData())) {
   auto nativeActor=[&](uint32 id)->Creature* {
    Creature* actor=instance->GetSingleCreatureFromStorage(id,true);
    return actor && actor->GetEntry()==id && actor->IsInWorld() && actor->IsAlive() &&
        bot->IsInMap(actor) && bot->GetDistance(actor)<=150 ? actor : nullptr;
   };
   if(!boss)boss=nativeActor(15727);
   if(!pullTarget)pullTarget=nativeActor(15589);
  }
 if(ctx.raidLabEventStarted) {
  if(InstanceData* instance=bot->GetMap()->GetInstanceData())
   if(RaidLabNefariusWaveFailed(bot->GetMapId(),entry,kind,instance->GetData(7),
       WorldTimer::getMSTime(),ctx.raidLabEventFailureStarted)) {
    message="Native Nefarius wave event reset; thirty-second recovery observed";return TestResult::FAIL;
   }
  bool survivor=false;
  if(bot->GetGroup())for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
   auto member=r->getSource();
   if(member && member->IsAlive() && member->IsInWorld() && bot->IsInMap(member))survivor=true;
  }
  if(!survivor) {message="Raid wiped during native event activation or waves";return TestResult::FAIL;}
  if(kind=="trap" && !boss) {
   // Deactivation is expected once any real participant crosses the radius.
   // Keep observing the native 22-second birth delay without clicking/rearming.
   GameObject* trap=RaidLabBirthTrap(bot);
   if(trap) {
    TestResult walk=RaidLabApproachBirthTrap(bot,ai,trap,message);
    if(walk==TestResult::IMPOSSIBLE || walk==TestResult::FAIL)return walk;
   } else ai->StopMoving();
  }
  if(kind=="approach" && !boss && pullTarget && !pullTarget->IsInCombat()) {
   TestResult walk=RaidLabLeaderWalk(bot,ai,pullTarget->GetPositionX(),pullTarget->GetPositionY(),
       pullTarget->GetPositionZ(),message);
   if(walk==TestResult::IMPOSSIBLE || walk==TestResult::FAIL)return walk;
  }
  // The native lever script opens the door after one second and starts the
  // boss's walk after three. Do not send a pull through its still-closed door.
  if(kind=="go-existing" && WorldTimer::getMSTime()-ctx.raidLabEventStarted<4000)return TestResult::PENDING;
  if(kind=="vael" && boss && ctx.raidLabEventStage<2 && boss->HasFlag(UNIT_NPC_FLAGS,UNIT_NPC_FLAG_GOSSIP)) {
   if(!bot->IsAlive()) {message="Leader died before native Vaelastrasz dialogue";return TestResult::FAIL;}
   if(bot->GetNPCIfCanInteractWith(boss->GetObjectGuid(),UNIT_NPC_FLAG_GOSSIP)) {
    if(!RaidLabGossip(bot,boss,2)) {message="Native Vaelastrasz dialogue unavailable";return TestResult::FAIL;}
    ctx.raidLabEventStage=2;
   } else if(!ctx.raidLabEventStage) {
    const float angle=boss->GetAngle(bot);
    const float x=boss->GetPositionX()+4.0f*std::cos(angle),y=boss->GetPositionY()+4.0f*std::sin(angle);
    const float z=bot->GetMap()->GetHeight(x,y,boss->GetPositionZ());
    if(!std::isfinite(z) || z<=INVALID_HEIGHT || std::fabs(z-boss->GetPositionZ())>3) {
     message="BLOCKED: no grounded native dialogue approach";return TestResult::IMPOSSIBLE;
    }
    WorldPosition destination(bot->GetMapId(),x,y,z);
    const auto path=destination.getPathStepFrom(WorldPosition(bot),bot,true);
    if(path.size()<2 || path.size()>256 || !destination.isPathTo(path,1.0f,2.0f)) {
     message="BLOCKED: native dialogue approach has no complete path";return TestResult::IMPOSSIBLE;
    }
    auto points=WorldPosition().toPointsArray(path);
    bot->GetMotionMaster()->Clear(false,true);
    bot->GetMotionMaster()->MovePath(points,FORCED_MOVEMENT_RUN,false,false);
    ctx.raidLabEventStage=1;
    RaidLab::Event(bot,"native_dialogue_walk",boss->GetObjectGuid().GetRawValue());
   }
  }
  if(boss) {
   if(ctx.focusMobGuid.IsEmpty()) {
    if(!RaidLab::BindNativeBoss(boss)){message="Native event target binding failed";return TestResult::FAIL;}
    ctx.focusMobGuid=boss->GetObjectGuid();ctx.focusMobEntry=entry;
   }
   if(kind=="razorgore" || kind=="area" || kind=="phase") {
    // Grethok's real combat callback starts the egg event. The ordinary bot
    // orb/controller actions must kill him, acquire control and destroy eggs.
    // A protected phase-one dragon is never treated as a direct pull target.
    InstanceData* instance=bot->GetMap()->GetInstanceData();
    const uint32 state=kind=="area"?14:kind=="phase"?(entry==15928?12:entry==15727?8:5):0;
    if(instance && instance->GetData(state)==IN_PROGRESS) {
     ctx.combatSeen=true;message="Native encounter event started; all waves and boss mechanics remain under observation";
     return TestResult::PASS;
    }
   }
   if(boss->IsInCombat()) {ctx.combatSeen=true;message="Native event spawned and engaged its boss";return TestResult::PASS;}
   if(kind!="razorgore" && kind!="gothik" && kind!="area" && kind!="phase" && (kind!="vael" || ctx.raidLabEventStage==2) && bot->CanAttack(boss) && !boss->HasFlag(UNIT_FIELD_FLAGS,
       UNIT_FLAG_NOT_ATTACKABLE_1 | UNIT_FLAG_UNTARGETABLE | UNIT_FLAG_UNINTERACTIBLE)) {
    for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
     Player* tank=r->getSource();
     if(tank && tank!=bot && tank->IsAlive() && tank->IsInWorld() && bot->IsInMap(tank) &&
        tank->GetPlayerbotAI() && ai->IsTank(tank)) {
      bot->SetSelectionGuid(boss->GetObjectGuid());
      RaidLab::Event(bot,"pull_command",boss->GetObjectGuid().GetRawValue(),tank->GetObjectGuid().GetRawValue());
      tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
      message="Native event spawned boss; one ordinary tank pull requested";return TestResult::PASS;
     }
    }
   }
  }
  const uint32 eventLimit=kind=="gossip"?900000:kind=="vael"?180000:90000;
  if(WorldTimer::getMSTime()-ctx.raidLabEventStarted>eventLimit) {
   message="Native activation did not produce an engageable boss within its bounded event window";return TestResult::FAIL;
  }
  return TestResult::PENDING;
 }
 if(boss && kind!="vael" && kind!="go-existing" && kind!="razorgore" && kind!="gothik" && kind!="area" && kind!="phase") {message="BLOCKED: event boss already exists before activation";return TestResult::IMPOSSIBLE;}
 if(kind=="phase" && (!boss || !bot->GetMap()->GetInstanceData() ||
    bot->GetMap()->GetInstanceData()->GetData(entry==15928?12:entry==15727?8:5)!=NOT_STARTED)) {
  message="BLOCKED: phase trial requires untouched native encounter actors";return TestResult::IMPOSSIBLE;
 }
 if(kind=="area" && (!boss || !bot->GetMap()->GetInstanceData() || bot->GetMap()->GetInstanceData()->GetData(14)!=NOT_STARTED)) {
  message="BLOCKED: Kel'Thuzad trial requires untouched native room event";return TestResult::IMPOSSIBLE;
 }
 if(kind=="gothik" && (!boss || boss->IsInCombat())) {
  message="BLOCKED: Gothik room fixture requires the native idle balcony boss";return TestResult::IMPOSSIBLE;
 }
 if(kind=="razorgore" && (!boss || boss->IsInCombat() || !bot->GetMap()->GetInstanceData() ||
    bot->GetMap()->GetInstanceData()->GetData(0)!=NOT_STARTED)) {
  message="BLOCKED: Razorgore trial requires untouched native egg event";return TestResult::IMPOSSIBLE;
 }
 if(kind=="go-existing" && (!boss || boss->IsInCombat())) {
  message="BLOCKED: native lever boss missing or already fighting";return TestResult::IMPOSSIBLE;
 }
 Player* tank=nullptr;if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::IMPOSSIBLE;
 GameObject* object=nullptr;
 if(kind=="vael" || kind=="area") {
  const auto trigger=sAreaTriggerStore.LookupEntry(activator);
  if(!boss || boss->IsInCombat() || !trigger ||
     !IsPointInAreaTriggerZone(trigger,bot->GetMapId(),bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ(),0)) {
   message="BLOCKED: leader must stand inside the native encounter start trigger";return TestResult::IMPOSSIBLE;
  }
 } else if(kind=="trap") {
  object=RaidLabBirthTrap(bot);
  if(!object || !object->IsSpawned()) {
   message="BLOCKED: native birth trap already activated or unavailable";return TestResult::IMPOSSIBLE;
  }
  const float radius=float(object->GetGOInfo()->trap.diameter)/2.0f;
  if(!std::isfinite(radius) || radius<=0) {message="BLOCKED: invalid native trap radius";return TestResult::IMPOSSIBLE;}
  for(auto r=bot->GetGroup()->GetFirstMember();r;r=r->next()) {
   Player* member=r->getSource();
   if(!member || !member->IsInWorld() || !bot->IsInMap(member) || object->GetDistance(member)<=radius+2) {
    message="BLOCKED: group entered native trap before observation";return TestResult::IMPOSSIBLE;
   }
  }
 } else if(kind=="go" || kind=="go-existing") {
  MaNGOS::NearestGameObjectEntryInObjectRangeCheck check(*bot,activator,5.0f);
  MaNGOS::GameObjectLastSearcher<MaNGOS::NearestGameObjectEntryInObjectRangeCheck> searcher(object,check);
  Cell::VisitGridObjects(bot,searcher,5.0f);
  if(!object || !object->IsInWorld() || !object->IsSpawned()) {
   message="BLOCKED: native activator is not within interaction range";return TestResult::IMPOSSIBLE;
  }
 } else if(kind=="item" || kind=="madness") {
  // This explicit local fixture supplies the real lure and its five native
  // reagent fish. Acquisition/fishing is not encounter acceptance. The spell
  // handler must validate location, cooldown, cast and reagent consumption.
  if(bot->IsNonMeleeSpellCasted(false))return TestResult::PENDING;
  if(kind=="madness") {
   unsigned active=0;
   for(uint16 id=29;id<=32;++id)active+=sGameEventMgr.IsActiveEvent(id)?1:0;
   if(active!=1 || !sGameEventMgr.IsActiveEvent(uint16(29+entry-15082))) {
    message="BLOCKED: explicit local calendar fixture does not match requested Madness boss";return TestResult::IMPOSSIBLE;
   }
   MaNGOS::NearestGameObjectEntryInObjectRangeCheck check(*bot,180327,5.0f);
   MaNGOS::GameObjectLastSearcher<MaNGOS::NearestGameObjectEntryInObjectRangeCheck> searcher(object,check);
   Cell::VisitGridObjects(bot,searcher,5.0f);
   if(!object || !object->IsInWorld() || !object->IsSpawned()) {
    message="BLOCKED: native Madness brazier unavailable within item-use range";return TestResult::IMPOSSIBLE;
   }
  }
  const std::vector<std::pair<uint32,uint32>> requirements=kind=="madness"
      ? std::vector<std::pair<uint32,uint32>>{{19931,1}}:std::vector<std::pair<uint32,uint32>>{{19974,1},{19975,5}};
  for(const auto& requirement:requirements) {
   const uint32 count=bot->GetItemCount(requirement.first);
   if(count>=requirement.second)continue;
   ItemPosCountVec positions;
   if(bot->CanStoreNewItem(NULL_BAG,NULL_SLOT,positions,requirement.first,requirement.second-count)!=EQUIP_ERR_OK ||
      !bot->StoreNewItem(positions,requirement.first,true)) {
    message="BLOCKED: native summoning item inventory admission failed";return TestResult::IMPOSSIBLE;
   }
  }
  if(!bot->GetItemByEntry(activator)) {message="BLOCKED: native summoning item unavailable";return TestResult::IMPOSSIBLE;}
 } else if(!pullTarget || pullTarget->IsInCombat()) {
  message="BLOCKED: native event creature unavailable";return TestResult::IMPOSSIBLE;
 } else if(kind=="gossip" && !bot->GetNPCIfCanInteractWith(pullTarget->GetObjectGuid(),UNIT_NPC_FLAG_GOSSIP)) {
  message="BLOCKED: native event dialogue is not interactable";return TestResult::IMPOSSIBLE;
 }
 bot->SetSelectionGuid(ObjectGuid());
 if(!RaidLab::Begin(bot,entry,ctx.testName,true)){message="BLOCKED: telemetry start failed";return TestResult::IMPOSSIBLE;}
 if(ctx.testName.find("_seeded")!=std::string::npos)RaidLab::Event(bot,"fixture_native_encounter_seed_not_progression_validation");
 ctx.focusMobGuid.Clear();ctx.focusMobEntry=entry;ctx.combatSeen=false;
 ctx.raidLabEventStarted=WorldTimer::getMSTime();ctx.raidLabEventStage=0;RaidLabFollowers(bot,ai,ctx);
 if(kind=="vael" || kind=="area") {
  RaidLab::Event(bot,"native_area_trigger",activator);
  WorldPacket packet(CMSG_AREATRIGGER);packet<<activator;
  bot->GetSession()->HandleAreaTriggerOpcode(packet);
 } else if(kind=="trap") {
  RaidLab::Event(bot,"native_proximity_trap_walk",object->GetObjectGuid().GetRawValue(),activator);
  TestResult walk=RaidLabApproachBirthTrap(bot,ai,object,message);
  if(walk==TestResult::IMPOSSIBLE || walk==TestResult::FAIL)return walk;
 } else if(object && kind!="madness") {
  RaidLab::Event(bot,"native_gameobject_use",object->GetObjectGuid().GetRawValue(),activator);
  WorldPacket packet(CMSG_GAMEOBJ_USE);packet<<object->GetObjectGuid();
  bot->GetSession()->HandleGameObjectUseOpcode(packet);
 } else if(kind=="item" || kind=="madness") {
  Item* item=bot->GetItemByEntry(activator);
  if(!item){message="Native summoning item disappeared before use";return TestResult::FAIL;}
  RaidLab::Event(bot,"fixture_native_summoning_items_not_acquisition_validation",activator,kind=="item"?5:0);
  if(kind=="madness") {
   RaidLab::Event(bot,"fixture_calendar_selection_not_schedule_validation",29+entry-15082);
   RaidLab::Event(bot,"fixture_precleared_madness_room_not_trash_validation");
  }
  SpellCastTargets targets=RaidLabNativeItemTargets(object);
  WorldPacket packet(CMSG_USE_ITEM);packet<<uint8(item->GetBagSlot())<<uint8(item->GetSlot())<<uint8(0);
  packet<<targets;
  RaidLab::Event(bot,"native_item_use",activator);
  bot->GetSession()->HandleUseItemOpcode(packet);
 } else if(kind=="approach") {
  // Ouro's native dirt mound is NOT_SELECTABLE. A player walks into its
  // proximity; shooting that hidden actor is correctly refused. Exercise
  // that real activation without changing flags, threat or boss health.
  TestResult walk=RaidLabLeaderWalk(bot,ai,pullTarget->GetPositionX(),pullTarget->GetPositionY(),
      pullTarget->GetPositionZ(),message);
  if(walk==TestResult::IMPOSSIBLE || walk==TestResult::FAIL)return walk;
  RaidLab::Event(bot,"native_proximity_walk",pullTarget->GetObjectGuid().GetRawValue(),activator);
 } else if(kind=="gossip") {
  if(!RaidLabGossip(bot,pullTarget,3)) {
   message="Native event dialogue did not offer the expected next choice";return TestResult::FAIL;
  }
 } else {
  bot->SetSelectionGuid(pullTarget->GetObjectGuid());
  RaidLab::Event(bot,"pull_command",pullTarget->GetObjectGuid().GetRawValue(),tank->GetObjectGuid().GetRawValue());
  tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
 }
 message="Native activation submitted once; awaiting actual spawn";return TestResult::PENDING;
}
bool
RaidLabPackPullCorridor(Creature* target, Player* reference, Player* puller, float range,
    const std::set<ObjectGuid>& pack, const std::vector<WorldPosition>& route);

float RaidLabPackApproachRange(float range) {
 // ReachPullAction::isUseful reserves five yards for moving targets. The
 // fixture must validate that same approach, not a farther shooting point.
 return std::isfinite(range) && range>0 && range<=60 ? (range>5?range-5:range) : 0;
}

bool RaidLabCoveredBossPull(uint32 map,uint32 entry,const std::string& scenario) {
 if(map!=533)return false;
 if(entry==16028)return scenario=="raidlab_533_16028_leader" || scenario=="raidlab_533_16028_bot";
 // Noth's safe entry corridor is outside his native patrol envelope but
 // behind the door frame. Validate the tank's full shooting approach, just
 // as for Patchwerk; never demand that the waiting raid already see him.
 return entry==15954 && (scenario=="raidlab_533_15954_leader" || scenario=="raidlab_533_15954_bot");
}

TestResult CommandRaidLabPack::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                      TestContext& ctx, std::string& message)
{
 uint32 id=0;std::string phase,extra;std::istringstream input(params);input>>id>>phase;
 const bool linked=phase=="stage-linked" || phase=="fight-linked";
 if(linked)phase=phase=="stage-linked"?"stage":"fight";
 if(!RaidLab::Enabled() || !id || (phase!="stage" && phase!="fight") || (input>>extra) ||
    !bot->IsInWorld() || !RaidLab::AllowedMap(bot->GetMapId()) || bot->IsBeingTeleported() ||
    bot->HasCharmer() || !bot->GetGroup() || bot->GetGroup()->GetLeaderGuid()!=bot->GetObjectGuid() ||
    ctx.testName!="raidlab_"+std::to_string(bot->GetMapId())+(linked?"_linked_":"_pack_")+std::to_string(id)+"_leader") {
  message="BLOCKED: native pack command requires its explicit isolated local raid fixture";return TestResult::IMPOSSIBLE;
 }
 const unsigned expected=bot->GetMapId()==309 || bot->GetMapId()==509?20:40;
 if(bot->GetGroup()->GetMembersCount()!=expected){message="Pack fixture lost group members";return TestResult::FAIL;}
 if(phase=="stage") {
  if(!bot->IsGameMaster() || bot->IsInCombat() || ctx.raidLabEventStarted) {
   message="BLOCKED: pack staging is preparation only";return TestResult::IMPOSSIBLE;
  }
  SpawnGroup* group=linked?nullptr:bot->GetMap()->GetSpawnManager().GetSpawnGroup(id);
  Player* reference=RaidLabAggroReference(bot);
  if(!reference || (!linked && (!group || !group->GetCreatureGroup() || !group->IsWorldstateConditionSatisfied()))) {
   message="BLOCKED: native creature pack unavailable or event-gated";return TestResult::IMPOSSIBLE;
  }
  std::vector<uint32> dbGuids;
  if(linked) {
   const auto found=RaidLabLinkedPacks().find(id);
   if(found!=RaidLabLinkedPacks().end())dbGuids=found->second;
  } else for(const auto& spawn:group->GetGroupEntry().DbGuids)dbGuids.push_back(spawn.DbGuid);
  if(dbGuids.empty() || dbGuids.size()>64) {
   message="BLOCKED: pack inventory outside bounded fixture size";return TestResult::IMPOSSIBLE;
  }
  if(!RaidLabWarmPreparationGrid(bot,ctx,"pack",bot->GetPositionX(),bot->GetPositionY(),message))return TestResult::PENDING;
  // Load the real database grids. Do not force a group spawn, respawn, selected
  // random entry, event state, or a creature's health/threat/position.
  for(uint32 dbGuid:dbGuids) {
   const CreatureData* data=sObjectMgr.GetCreatureData(dbGuid);
   if(!data || data->mapid!=bot->GetMapId()) {
    message="BLOCKED: native pack GUID belongs to a different map";return TestResult::IMPOSSIBLE;
   }
   if(std::hypot(data->posX-bot->GetPositionX(),data->posY-bot->GetPositionY())>150) {
    message="BLOCKED: pack is not a bounded local cluster";return TestResult::IMPOSSIBLE;
   }
   bot->GetMap()->ForceLoadGrid(data->posX,data->posY);
  }
  std::set<ObjectGuid> members;Creature* target=nullptr;
  for(uint32 dbGuid:dbGuids) {
   Creature* creature=bot->GetMap()->GetCreature(dbGuid);
   const uint32 activeEntry=linked?(creature?creature->GetEntry():0):group->GetGuidEntry(dbGuid);
   if(!linked && !activeEntry)continue; // Native chance/MaxCount alternatives are not all present.
   if(!creature || !creature->IsInWorld() || !creature->IsAlive() || creature->IsInCombat() ||
      creature->GetEntry()!=activeEntry || !creature->IsEnemy(reference) || creature->IsPet() ||
      creature->IsWorldBoss() || creature->GetScriptName().find("boss_")==0) {
    message="BLOCKED: pack contains missing, engaged, friendly or encounter actors";return TestResult::IMPOSSIBLE;
   }
   members.insert(creature->GetObjectGuid());
   if(!target || bot->GetDistance(creature)<bot->GetDistance(target))target=creature;
  }
  if(!target || members.empty()) {message="BLOCKED: no native active trash pack members";return TestResult::IMPOSSIBLE;}
  ctx.raidLabPackId=id;ctx.raidLabPackMembers=std::move(members);ctx.raidLabPackDead.clear();
  ctx.focusMobGuid=target->GetObjectGuid();ctx.focusMobEntry=target->GetEntry();
  CommandRaidLabLanding landing;
  return landing.Execute(std::to_string(ctx.focusMobEntry),bot,ai,ctx,message);
 }
 if(bot->IsGameMaster() || !RaidLab::Controlled(bot) || ctx.raidLabPackId!=id || ctx.raidLabPackMembers.empty()) {
  message="BLOCKED: pack combat requires settled GM-off preparation";return TestResult::IMPOSSIBLE;
 }
 const uint32 now=WorldTimer::getMSTime();
 if(!ctx.raidLabEventStarted) {
  Player* tank=nullptr;if(!RaidLabPartyReady(bot,ai,tank,message))return TestResult::IMPOSSIBLE;
  for(ObjectGuid guid:ctx.raidLabPackMembers) {
   Creature* creature=bot->GetMap()->GetCreature(guid);
   if(!creature || !creature->IsAlive() || creature->IsInCombat()) {
    message="BLOCKED: native pack changed before pull";return TestResult::IMPOSSIBLE;
   }
  }
  if(bot->GetMapId()==309) {
   // A real leader waits for a patrol's safe pull window. The native pack can
   // move far during group preparation; a historical landing check is not
   // permission to chase it through a neighboring pack after preparation.
   Creature* target=bot->GetMap()->GetCreature(ctx.focusMobGuid);
   PullStrategy* pull=PullStrategy::Get(tank->GetPlayerbotAI());
   const float range=pull?RaidLabPackApproachRange(pull->GetRange()):0;
   const WorldPosition waiting(tank);
   const auto route=target?waiting.getPathStepFrom(WorldPosition(target),tank,true):std::vector<WorldPosition>{};
   const bool ready=target && waiting.isPathTo(route,1.0f,2.0f) &&
       RaidLabPackPullCorridor(target,bot,tank,range,ctx.raidLabPackMembers,route);
   const std::string key="pack-pull-window:"+std::to_string(id);
   if(!ready) {
    auto inserted=ctx.raidLabGridWarmups.emplace(key,now);
    if(inserted.second)sLog.outString("RAID_LAB_SETUP: waiting for native ZG patrol pull window pack=%u target=%llu",id,uint64(ctx.focusMobGuid.GetRawValue()));
    if(uint32(now-inserted.first->second)>=180000) {
     message="BLOCKED: native ZG patrol offered no clear ranged pull window within three minutes";return TestResult::IMPOSSIBLE;
    }
    message="Waiting for native patrol to return to a clear ranged pull corridor";return TestResult::PENDING;
   }
  }
  bot->SetSelectionGuid(ctx.focusMobGuid);
  if(!RaidLab::Begin(bot,ctx.focusMobEntry,ctx.testName,true)) {
   message="BLOCKED: pack telemetry could not start";return TestResult::IMPOSSIBLE;
  }
  ctx.raidLabEventStarted=now;ctx.raidLabPostKillStarted=0;ctx.combatSeen=false;
  RaidLabFollowers(bot,ai,ctx);
  RaidLab::Event(bot,linked?"native_linked_pack":"native_pack_group",id,ctx.raidLabPackMembers.size());
  for(ObjectGuid guid:ctx.raidLabPackMembers)RaidLab::Event(bot,"native_pack_member",guid.GetRawValue());
  RaidLab::Event(bot,"pull_command",ctx.focusMobGuid.GetRawValue(),tank->GetObjectGuid().GetRawValue());
  tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
  return TestResult::PENDING;
 }
 if(now-ctx.raidLabEventStarted>900000){message="Native pack observation timed out";return TestResult::FAIL;}
 if(!bot->IsAlive()){message="Player leader died in native pack test";return TestResult::FAIL;}
 bool fighting=false,regroup=true;
 for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
  Player* member=ref->getSource();
  if(!member || !member->IsInWorld() || member->IsBeingTeleported() || !bot->IsInMap(member)) {
   message="Pack group changed map or became unavailable";return TestResult::FAIL;
  }
  fighting|=member->IsInCombat();
  regroup&=member->IsAlive() && member->GetDistance(bot)<=18 && member->GetHealthPercent()>=70 &&
      (member->GetPowerType()!=POWER_MANA || member->GetPowerPercent(POWER_MANA)>=35);
 }
 // Missing actors do not imply kills. Observe death before accepting removal,
 // and revoke that record if a native respawn is seen (e.g. Core Hound packs).
 for(ObjectGuid guid:ctx.raidLabPackMembers) {
  Creature* creature=bot->GetMap()->GetCreature(guid);
  // A member's transient combat flag (including unrelated preparation work)
  // does not prove this pack engaged. Keep the ordinary-pull timeout tied to
  // the actual native pack, not fifteen minutes of unrelated group activity.
  if(creature && creature->GetObjectGuid()==guid && creature->IsInCombat()) ctx.combatSeen=true;
  if(RaidLabObservePackDeath(ctx,guid,creature)) {
   ctx.combatSeen=true;
   RaidLab::Event(bot,"native_pack_member_dead",guid.GetRawValue());
  }
 }
 if(!ctx.combatSeen && now-ctx.raidLabEventStarted>60000) {
  message="Native pack did not engage after the ordinary pull";return TestResult::FAIL;
 }
 if(ctx.raidLabPackDead.size()!=ctx.raidLabPackMembers.size() || fighting) {
  ctx.raidLabPostKillStarted=0;return TestResult::PENDING;
 }
 if(!ctx.raidLabPostKillStarted) {
  ctx.raidLabPostKillStarted=now;RaidLab::Event(bot,"native_pack_cleanup_started",id);
 }
 if(now-ctx.raidLabPostKillStarted>180000 && !regroup) {
  message="Native pack ended but resurrection/healing/regroup failed within three minutes";return TestResult::FAIL;
 }
 if(now-ctx.raidLabPostKillStarted<30000 || !regroup)return TestResult::PENDING;
 message="Observed native pack deaths and recovery; role/mechanic acceptance remains separate";
 return TestResult::PASS;
}

bool RaidLabPackPullCorridor(Creature* target, Player* reference, Player* puller, float range,
    const std::set<ObjectGuid>& pack, const std::vector<WorldPosition>& route)
{
 if(!target || !reference || !puller || pack.empty() || !pack.count(target->GetObjectGuid()) ||
    !std::isfinite(range) || range<=0 || range>60 || route.size()<2 || route.size()>256)return false;
 std::vector<Creature*> neighbors;
 auto& store=target->GetMap()->GetObjectsStore();
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;
  if(c && !pack.count(c->GetObjectGuid()) && RaidLabBodyPullRisk(c,reference,true))neighbors.push_back(c);
 }
 unsigned samples=0;
 // The admitted navmesh path is boss -> landing. Inspect it in the puller's
 // direction, only until the actual ranged pull can be attempted. A safe
 // landing beyond a neighboring pack is not a valid isolated-pack fixture.
 for(size_t i=route.size()-1;i>0;--i) {
  const auto& from=route[i];const auto& to=route[i-1];
  const float length=std::sqrt(std::pow(to.getX()-from.getX(),2)+std::pow(to.getY()-from.getY(),2)+std::pow(to.getZ()-from.getZ(),2));
  if(!std::isfinite(length) || length>1024)return false;
  const unsigned steps=std::max(1u,unsigned(std::ceil(length/2.0f)));
  if(steps>512 || samples+steps+1>512)return false;
  for(unsigned j=0;j<=steps;++j) {
   ++samples;const float t=float(j)/steps;
   const float x=from.getX()+(to.getX()-from.getX())*t,y=from.getY()+(to.getY()-from.getY())*t,z=from.getZ()+(to.getZ()-from.getZ())*t;
   for(Creature* c:neighbors) {
    const float radius=c->GetAttackDistance(reference)+puller->GetObjectBoundingRadius()+2;
    const float dx=x-c->GetPositionX(),dy=y-c->GetPositionY(),dz=z-c->GetPositionZ();
    if(!std::isfinite(radius) || radius<=0 ||
       RaidLabInsideWanderEnvelope(c,x,y,z,radius) || RaidLabInsidePatrolEnvelope(c,x,y,z,radius) ||
       (dx*dx+dy*dy+dz*dz<radius*radius && c->IsWithinLOS(x,y,z+puller->GetCollisionHeight(),true)))return false;
   }
   const float dx=x-target->GetPositionX(),dy=y-target->GetPositionY(),dz=z-target->GetPositionZ();
   const float reach=range+target->GetCombatReach()+puller->GetCombatReach()-1;
   if(dx*dx+dy*dy+dz*dz<=reach*reach && target->IsWithinLOS(x,y,z+puller->GetCollisionHeight(),true))return true;
  }
 }
 return false;
}

bool RaidLabSuppressionStartFloor(Map* map, float x, float y, float& floor)
{
 // Setup only, before the first lower-room packs. Never land on the upper
 // suppression floor or beyond the first row merely to obtain a valid path.
 if(!map || map->GetId()!=469 || !std::isfinite(x) || !std::isfinite(y) ||
    x < -7605 || x > -7510 || y < -912 || y > -870) return false;
 float nearby=428.25f;
 if(!map->GetHeightInRange(x,y,nearby,2.0f) || !std::isfinite(nearby) ||
    nearby<=INVALID_HEIGHT || std::fabs(nearby-428.25f)>2.0f) return false;
 floor=nearby;return true;
}
bool RaidLabEyeEntrySeparated(float waitingDistance, float pullerDistance, float fromWaiting, float formation, float jump)
{
 return std::isfinite(waitingDistance) && std::isfinite(pullerDistance) && std::isfinite(fromWaiting) &&
     std::isfinite(formation) && std::isfinite(jump) && formation>=0 && jump>0 && jump<=20 &&
     pullerDistance+formation+2<waitingDistance && fromWaiting>formation+jump+2;
}
bool RaidLabEyeEntryRoute(Creature* eye, Player* reference, const std::vector<WorldPosition>& route, float formation)
{
 if(!eye || eye->GetEntry()!=15589 || eye->GetMapId()!=531 || !reference || route.size()<2 || route.size()>256)return false;
 const auto waiting=route.back();
 const auto distance=[&](const WorldPosition& p) {
  return std::sqrt(std::pow(p.getX()-eye->GetPositionX(),2)+std::pow(p.getY()-eye->GetPositionY(),2)+std::pow(p.getZ()-eye->GetPositionZ(),2));
 };
 const float waitingDistance=distance(waiting),jump=SpellTargetMgr::GetJumpRadius(32950);
 unsigned checked=0;
 // The route was validated from the boss to the waiting point. Walk it in
 // reverse to inspect the first native-LOS body pull, including segment interiors.
 for(size_t i=route.size()-1;i>0;--i) {
  const auto& from=route[i];const auto& to=route[i-1];
  const unsigned steps=std::max(1u,unsigned(std::ceil(from.distance(to)/2.0f)));
  if(steps>256)return false;
  for(unsigned n=0;n<=steps;++n) {
   if(++checked>512)return false;
   const float t=float(n)/steps;
   WorldPosition point(531,from.getX()+(to.getX()-from.getX())*t,
       from.getY()+(to.getY()-from.getY())*t,from.getZ()+(to.getZ()-from.getZ())*t);
   const float range=distance(point);
   if(range>100 || !eye->IsWithinLOS(point.getX(),point.getY(),point.getZ()+reference->GetCollisionHeight(),true))continue;
   // AttackClosestEnemy must select the isolated entrant, not a caster behind
   // the wall who happens to be nearer in straight-line distance.
   return RaidLabEyeEntrySeparated(waitingDistance,range,point.distance(waiting),formation,jump);
  }
 }
 return false;
}
bool RaidLabPackLowerFloor(Map* map,bool nativePack,float x,float y,float hint,float& floor)
{
 if(!nativePack || !map || !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(hint))return false;
 const float native=map->GetHeight(x,y,hint);
 // A native patrol can stand halfway up a ramp. Its approach can be on
 // the lower floor, beyond the ordinary eight-yard boss-height query.
 // Only use an actual nearby lower floor, never a roof or invented Z.
 if(!std::isfinite(native) || native<=INVALID_HEIGHT || hint-native<=8 || hint-native>18)return false;
 float grounded=native;
 if(!map->GetHeightInRange(x,y,grounded,2.0f) || !std::isfinite(grounded) ||
    grounded<=INVALID_HEIGHT || std::fabs(grounded-native)>2)return false;
 floor=grounded;return true;
}

TestResult CommandRaidLabLanding::Execute(const std::string& params, Player* bot, PlayerbotAI* ai,
                                         TestContext& ctx, std::string& message)
{
 // Travel-node interpolation is only an approach estimate, not a floor query.
 // Correct the isolated GM setup position before copying it to the group.
 if (!RaidLab::Enabled() || !bot->IsInWorld() || !RaidLab::AllowedMap(bot->GetMapId()) ||
     !bot->IsGameMaster() || bot->IsBeingTeleported() || bot->IsInCombat()) {
  message="BLOCKED: landing validation requires settled local GM setup";return TestResult::IMPOSSIBLE;
 }
 uint32 entry=0;std::istringstream input(params);input>>entry;
 if(RaidLabSapphironFixture(bot->GetMapId(),entry,ctx.testName))return RaidLabStageBirthTrap(bot,ctx,message);
 Player* reference=RaidLabAggroReference(bot);
 if(!reference) {message="BLOCKED: no settled GM-off faction reference for landing aggro validation";return TestResult::IMPOSSIBLE;}
 Creature* boss=nullptr;auto& store=bot->GetMap()->GetObjectsStore();
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;
  if(c && c->GetEntry()==entry && c->IsAlive() && c->IsInWorld() &&
     (!boss || bot->GetDistance(c)<bot->GetDistance(boss))) boss=c;
 }
 // Explicit pack fixtures bind the selected native GUID, not the nearest
 // creature with the same entry in a neighboring pack.
 if(ctx.raidLabPackId) {
  boss=bot->GetMap()->GetCreature(ctx.focusMobGuid);
  if(boss && (boss->GetEntry()!=entry || !ctx.raidLabPackMembers.count(boss->GetObjectGuid())))boss=nullptr;
 }
 const bool patrollingGeddon=bot->GetMapId()==409 && entry==12056;
 if(!boss || boss->IsInCombat() || bot->GetDistance(boss)>(patrollingGeddon?300.0f:100.0f)) {
  sLog.outString("RAID_LAB_SETUP: landing boss entry=%u found=%u combat=%u distance=%.2f",entry,
      boss?1u:0u,boss&&boss->IsInCombat()?1u:0u,boss?bot->GetDistance(boss):-1.0f);
  message="BLOCKED: native boss unavailable for landing validation";return TestResult::IMPOSSIBLE;
 }
 // The travel graph is only an estimate. Prefer it, then examine a bounded
 // ring on the native floor. Never make a bad fixture pass by accepting a
 // partial path, an airborne landing, or an initial trash aggro position.
 sLog.outString("RAID_LAB_SETUP: landing admission entry=%u guid=%u reference=%u referenceMap=%u referenceFaction=%u bossFaction=%u nativeAggro=%.2f risk=%u neutral=%u initiate=%u canAggro=%u aggressive=%u enemy=%u bossPosition=%.3f,%.3f,%.3f",
     boss->GetEntry(),boss->GetGUIDLow(),reference->GetGUIDLow(),reference->GetMapId(),reference->GetFaction(),boss->GetFaction(),
     boss->GetAttackDistance(reference),RaidLabBodyPullRisk(boss,reference)?1u:0u,boss->IsNeutralToAll()?1u:0u,
     boss->CanInitiateAttack()?1u:0u,boss->CanAggro()?1u:0u,
     boss->AI()&&boss->AI()->HasReactState(REACT_AGGRESSIVE)?1u:0u,boss->IsEnemy(reference)?1u:0u,
     boss->GetPositionX(),boss->GetPositionY(),boss->GetPositionZ());
 const float original=bot->GetPositionZ();
 float x=0,y=0,z=0;std::vector<WorldPosition> path;
 const bool ledgePull=entry==14517 && bot->GetMapId()==309;
 WorldPosition origin(boss);
 if(ledgePull) {
  const float floor=bot->GetMap()->GetHeight(-12281.58f,-1392.84f,146.1f);
  if(!std::isfinite(floor) || floor<=INVALID_HEIGHT) {
   message="BLOCKED: native flight landing has no floor";return TestResult::IMPOSSIBLE;
  }
  origin=WorldPosition(bot->GetMapId(),-12281.58f,-1392.84f,floor);
 }
 unsigned floorRejected=0,aggroRejected=0,pathRejected=0,losRejected=0;
 uint32 rejectedActorEntry=0,rejectedActorDbGuid=0;
 std::vector<WorldPosition> eyeLandingSuggestions;
 std::vector<WorldPosition> trashLandingSuggestions;
 bool collectEyeLandings=true;
 const bool suppressionStart=bot->GetMapId()==469 && entry==12465 &&
     ctx.testName=="raidlab_469_12017_leader_progression";
 const bool coveredBossPull=RaidLabCoveredBossPull(bot->GetMapId(),entry,ctx.testName);
 std::set<ObjectGuid> pullMembers=ctx.raidLabPackMembers;
 if(coveredBossPull)pullMembers.insert(boss->GetObjectGuid());
 Player* packPuller=nullptr;float packRange=0;
 if(ctx.raidLabPackId || coveredBossPull) {
  for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
   Player* member=ref->getSource();
   if(member && member!=bot && member->GetPlayerbotAI() && ai->IsTank(member)) {
    packPuller=member;
    if(auto* pull=PullStrategy::Get(member->GetPlayerbotAI()))packRange=RaidLabPackApproachRange(pull->GetRange());
    break;
   }
  }
  if(!packPuller || !std::isfinite(packRange) || packRange<=0 || packRange>60) {
   message="BLOCKED: native pack puller has no bounded ranged approach";return TestResult::IMPOSSIBLE;
  }
 }
 if(!RaidLabWarmPreparationGrid(bot,ctx,"landing",origin.getX(),origin.getY(),message))return TestResult::PENDING;
 const auto candidate=[&](float cx,float cy,float hint,float maxDelta) {
  bot->GetMap()->ForceLoadGrid(cx,cy);
  // A patrol may have moved far from its database spawn/travel node during
  // setup. Stage near its current native position without moving the boss.
  if(patrollingGeddon && std::hypot(cx-boss->GetPositionX(),cy-boss->GetPositionY())>60.0f)return false;
  rejectedActorEntry=0;rejectedActorDbGuid=0;
  float cz=INVALID_HEIGHT;
  if(suppressionStart) {
   if(!RaidLabSuppressionStartFloor(bot->GetMap(),cx,cy,cz)) {++floorRejected;return false;}
  } else if(!RaidLabLandingFloor(bot->GetMap(),cx,cy,hint,maxDelta,cz)) {
   ++floorRejected;return false;
  }
  if(!std::isfinite(cz) || cz<=INVALID_HEIGHT || std::fabs(cz-hint)>maxDelta) {
   if(floorRejected<4) {
    float bounded=hint;
    const bool found=bot->GetMap()->GetHeightInRange(cx,cy,bounded,maxDelta);
    sLog.outString("RAID_LAB_SETUP: landing floor rejected entry=%u x=%.3f y=%.3f hint=%.3f raw=%.3f limit=%.3f boundedFound=%u bounded=%.3f",
        entry,cx,cy,hint,cz,maxDelta,found?1u:0u,bounded);
   }
   ++floorRejected;return false;
  }
  // The Eye can body-pull from 100 yards. Its native pull starts by entering
  // LOS from the corridor, so a safe preparation point must be behind cover.
  // Keep the complete native walking path; no combat/visibility bypass.
  const bool coveredEyePull=bot->GetMapId()==531 && entry==15589;
  // A native trash pull may start with the party waiting behind cover. Its
  // tank still needs the complete corridor below to an actual ranged/LOS
  // pull point without crossing an unrelated pack. Requiring party LOS here
  // excluded those legitimate approaches before that stronger check ran.
  // The suppression progression fixture starts before the first pack and
  // walks the human-leader corridor below. A sheltered entrance is valid;
  // it need not already see the first Wyrmguard. Keep all native landing
  // aggro, floor and complete-path checks, and let progression earn LOS.
  // Patchwerk's narrow hall does not provide a full-raid waiting footprint
  // outside his native aggro radius that also sees him. A covered wait still
  // needs a complete, clear tank approach to a real shooting position below.
  if(!coveredEyePull && !ctx.raidLabPackId && !suppressionStart && !coveredBossPull &&
     !boss->IsWithinLOS(cx,cy,cz+bot->GetCollisionHeight(),true)) {++losRejected;return false;}
  for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
   Creature* c=i->second;
   // A GM-only loaded grid can still have its native spawn aggro delay. That
   // temporary inability to attack must not make a future party landing safe.
   if(!RaidLabBodyPullRisk(c,reference,true))continue;
   const float dx=cx-c->GetPositionX(),dy=cy-c->GetPositionY(),dz=cz-c->GetPositionZ();
   const float radius=RaidLabLandingRadius(c->GetAttackDistance(reference),sPlayerbotAIConfig.raidFollowDistance,bot->GetObjectBoundingRadius());
   if(radius<0){++aggroRejected;return false;}
   // A random wanderer can enter the formation during preparation. Reserve
   // its native home/wander envelope instead of freezing or moving the actor.
   if(RaidLabInsideWanderEnvelope(c,cx,cy,cz,radius) || RaidLabInsidePatrolEnvelope(c,cx,cy,cz,radius)) {
    rejectedActorEntry=c->GetEntry();rejectedActorDbGuid=c->GetDbGuid();
    if(aggroRejected<4)sLog.outString("RAID_LAB_SETUP: landing movement envelope entry=%u dbguid=%u radius=%.2f",c->GetEntry(),c->GetDbGuid(),radius);
    ++aggroRejected;return false;
   }
   if(dx*dx+dy*dy+dz*dz<radius*radius &&
      RaidLabFormationVisible(c,reference,cx,cy,cz,sPlayerbotAIConfig.raidFollowDistance+bot->GetObjectBoundingRadius())) {
    rejectedActorEntry=c->GetEntry();rejectedActorDbGuid=c->GetDbGuid();
    if(aggroRejected<4)sLog.outString("RAID_LAB_SETUP: landing aggro entry=%u distance=%.2f limit=%.2f",c->GetEntry(),std::sqrt(dx*dx+dy*dy+dz*dz),radius);
    ++aggroRejected;return false;
   }
  }
  WorldPosition destination(bot->GetMapId(),cx,cy,cz);
  auto finder=std::make_unique<PathFinder>(bot);
  auto route=destination.getPathStepFrom(origin,finder,bot,true);
  if(route.size()<2 || route.size()>256 || !destination.isPathTo(route,1.0f,2.0f)) {
   const auto nativeEnd=finder->getActualEndPosition();
   if(collectEyeLandings && eyeLandingSuggestions.size()<16 &&
      RaidLabEyeLandingSuggestion(bot->GetMapId(),entry,uint32(finder->getPathType()),
          finder->getPath().size(),cx,cy,cz,nativeEnd.x,nativeEnd.y,nativeEnd.z))
    eyeLandingSuggestions.emplace_back(bot->GetMapId(),nativeEnd.x,nativeEnd.y,nativeEnd.z);
   if(collectEyeLandings && trashLandingSuggestions.size()<16 &&
      RaidLabTrashLandingSuggestion(bot->GetMapId(),entry,suppressionStart || ctx.raidLabPackId==4090159 || ctx.raidLabPackId==5090000,
          uint32(finder->getPathType()),finder->getPath().size(),cx,cy,cz,nativeEnd.x,nativeEnd.y,nativeEnd.z))
    trashLandingSuggestions.emplace_back(bot->GetMapId(),nativeEnd.x,nativeEnd.y,nativeEnd.z);
   if(pathRejected<4)sLog.outString("RAID_LAB_SETUP: landing path rejected origin=%.3f,%.3f,%.3f destination=%.3f,%.3f,%.3f points=%u last=%.3f,%.3f,%.3f nativeType=%u nativePoints=%u nativeEnd=%.3f,%.3f,%.3f",
       origin.getX(),origin.getY(),origin.getZ(),cx,cy,cz,uint32(route.size()),
       route.empty()?0.0f:route.back().getX(),route.empty()?0.0f:route.back().getY(),route.empty()?0.0f:route.back().getZ(),
       uint32(finder->getPathType()),uint32(finder->getPath().size()),
       finder->getActualEndPosition().x,finder->getActualEndPosition().y,finder->getActualEndPosition().z);
   ++pathRejected;return false;
  }
  for(const auto& point:route)
   if(!std::isfinite(point.getX()) || !std::isfinite(point.getY()) || !std::isfinite(point.getZ()) ||
      point.getMapId()!=bot->GetMapId()) {++pathRejected;return false;}
  if((ctx.raidLabPackId || coveredBossPull) && !RaidLabPackPullCorridor(boss,reference,packPuller,packRange,pullMembers,route)) {
   ++aggroRejected;return false;
  }
  if(coveredEyePull && !RaidLabEyeEntryRoute(boss,reference,route,
      sPlayerbotAIConfig.raidFollowDistance+reference->GetObjectBoundingRadius())) {
   ++aggroRejected;return false;
  }
  x=cx;y=cy;z=cz;path=std::move(route);return true;
 };
 bool found=candidate(bot->GetPositionX(),bot->GetPositionY(),original,40.0f);
 const float bearing=std::atan2(bot->GetPositionY()-origin.getY(),bot->GetPositionX()-origin.getX());
 for(float radius:{30.0f,35.0f,40.0f,45.0f,50.0f,60.0f,70.0f,80.0f,90.0f}) {
  if(found)break;
  for(unsigned sector=0;sector<24;++sector) {
   const float angle=bearing+float(sector)*float(2*M_PI)/24.0f;
   if(candidate(origin.getX()+radius*std::cos(angle),origin.getY()+radius*std::sin(angle),origin.getZ(),8.0f)) {
    found=true;break;
   }
   float packFloor=0;
   if(RaidLabPackLowerFloor(bot->GetMap(),ctx.raidLabPackId!=0,
       origin.getX()+radius*std::cos(angle),origin.getY()+radius*std::sin(angle),origin.getZ(),packFloor) &&
      candidate(origin.getX()+radius*std::cos(angle),origin.getY()+radius*std::sin(angle),packFloor,2.0f)) {
    found=true;break;
   }
   // Golemagg stands below the entrance ledge (~16yd vertically). Keep the
   // same eight-yard floor search bound, but also query near the actual
   // approach elevation; a boss-height-only query misses that valid floor.
   // C'Thun's rising entrance corridor likewise uses its actual approach hint.
   // The candidate still needs native LOS, a complete walking path and the
   // full party/patrol clearance. Never move or remove his Core Ragers.
   if(((bot->GetMapId()==409 && entry==11988) || (bot->GetMapId()==531 && entry==15589)) && std::isfinite(original) &&
      std::fabs(original-origin.getZ())>((bot->GetMapId()==531 && entry==15589)?0.1f:8.0f) && std::fabs(original-origin.getZ())<=40.0f &&
      candidate(origin.getX()+radius*std::cos(angle),origin.getY()+radius*std::sin(angle),original,8.0f)) {
    found=true;break;
   }
  }
 }
 if(!found)found=RaidLabEyeOuterApproach(bot->GetMapId(),entry,origin.getX(),origin.getY(),
     origin.getZ(),original,bearing,candidate);
 // A narrow entrance can fall between the 15-degree radial samples. Search
 // the same bounded lower-room staging rectangle before declaring it blocked;
 // candidate still enforces native floor, LOS, aggro and complete path checks.
 if(!found && suppressionStart) {
  for(float cx=-7605.0f;cx<=-7510.0f && !found;cx+=5.0f)
   for(float cy=-870.0f;cy>=-912.0f;cy-=3.0f)
    if(candidate(cx,cy,428.25f,2.0f)) {found=true;break;}
 }
 if(!found && bot->GetMapId()==533 && entry==15954) {
  if(auto* instance=dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData()))
   if(GameObject* door=instance->GetSingleGameObjectFromStorage(181200))
    if(door->IsInWorld() && bot->IsInMap(door))
     found=RaidLabNothDoorApproach(bot->GetMapId(),entry,boss->GetPositionX(),boss->GetPositionY(),
         door->GetPositionX(),door->GetPositionY(),door->GetPositionZ(),candidate);
 }
 // A complete native path may end on the adjacent step of the rising Eye
 // corridor. Try that as a new floor candidate, never as an accepted partial
 // route: the same callback rechecks floor, formation aggro, entry LOS and a
 // newly calculated complete path with the original endpoint tolerances.
 collectEyeLandings=false;
 if(!found)for(const auto& point:eyeLandingSuggestions) {
  const unsigned beforeFloor=floorRejected,beforeAggro=aggroRejected,beforePath=pathRejected,beforeLos=losRejected;
  found=candidate(point.getX(),point.getY(),point.getZ(),2.0f);
  sLog.outString("RAID_LAB_SETUP: Eye endpoint x=%.3f y=%.3f z=%.3f accepted=%u rejectedFloor=%u rejectedAggro=%u rejectedPath=%u rejectedLos=%u",
      point.getX(),point.getY(),point.getZ(),found?1u:0u,floorRejected-beforeFloor,
      aggroRejected-beforeAggro,pathRejected-beforePath,losRejected-beforeLos);
  if(found)break;
 }
 // Coarse ground samples can fall below the imp cavern's walkable ramp or
 // outside the lower suppression entrance's navigation boundary. Re-probe
 // the native reachable endpoint as a distinct candidate; the original
 // complete-path test, formation footprint and pack pull corridor still apply.
 if(!found)for(const auto& point:trashLandingSuggestions) {
  const unsigned beforeFloor=floorRejected,beforeAggro=aggroRejected,beforePath=pathRejected,beforeLos=losRejected;
  found=candidate(point.getX(),point.getY(),point.getZ(),2.0f);
  float bounded=point.getZ();
  const bool boundedFound=bot->GetMap()->GetHeightInRange(point.getX(),point.getY(),bounded,2.0f);
  sLog.outString("RAID_LAB_SETUP: trash endpoint entry=%u x=%.3f y=%.3f z=%.3f accepted=%u rejectedFloor=%u rejectedAggro=%u rejectedPath=%u rejectedLos=%u rawHeight=%.3f boundedFound=%u boundedHeight=%.3f actorEntry=%u actorDbGuid=%u",
      entry,point.getX(),point.getY(),point.getZ(),found?1u:0u,floorRejected-beforeFloor,
      aggroRejected-beforeAggro,pathRejected-beforePath,losRejected-beforeLos,
      bot->GetMap()->GetHeight(point.getX(),point.getY(),point.getZ()),boundedFound?1u:0u,bounded,
      rejectedActorEntry,rejectedActorDbGuid);
  if(found)break;
 }
 sLog.outString("RAID_LAB_SETUP: approach entry=%u candidates rejected floor=%u aggro=%u path=%u los=%u",
     entry,floorRejected,aggroRejected,pathRejected,losRejected);
 if(!found) {
  message="BLOCKED: no grounded clear approach with complete native path and LOS";return TestResult::IMPOSSIBLE;
 }
 unsigned nearby=0;
 for(auto i=store.begin<Creature>();i!=store.end<Creature>() && nearby<16;++i) {
  Creature* c=i->second;
  if(!c || !c->IsInWorld() || !c->IsAlive() || std::hypot(x-c->GetPositionX(),y-c->GetPositionY())>45)continue;
  ++nearby;
  sLog.outString("RAID_LAB_SETUP: landing neighbor entry=%u guid=%u risk=%u nativeAggro=%.2f position=%.3f,%.3f,%.3f",
      c->GetEntry(),c->GetGUIDLow(),RaidLabBodyPullRisk(c,reference,true)?1u:0u,c->GetAttackDistance(reference),
      c->GetPositionX(),c->GetPositionY(),c->GetPositionZ());
 }
 if(!bot->TeleportTo(bot->GetMapId(),x,y,z,bot->GetOrientation())) {
  message="BLOCKED: native grounded setup teleport refused";return TestResult::IMPOSSIBLE;
 }
 sLog.outString("RAID_LAB_SETUP: grounded approach entry=%u at %.3f,%.3f originalZ=%.3f nativeZ=%.3f; native path points=%u",
     entry,x,y,original,z,uint32(path.size()));
 message="Native floor and complete walking path validated before group placement";
 return TestResult::PASS;
}
bool RaidLabMadnessRoomActor(uint32 entry,float distance) {
 return std::isfinite(distance) && distance>=0 && distance<65 &&
     (entry==15111 || entry==15146 || entry==11340);
}
TestResult RaidLabStageMadnessRoom(Player* bot,TestContext& ctx,uint32 entry,std::string& message) {
 if(!RaidLab::Enabled() || !bot->IsInWorld() || bot->IsBeingTeleported() ||
    !bot->IsGameMaster() || bot->IsInCombat() || bot->GetMapId()!=309 || entry<15082 || entry>15085 ||
    ctx.testName!="raidlab_309_"+std::to_string(entry)+"_leader_event_prepared") {
  message="BLOCKED: Madness boss-only room requires its explicit local prepared fixture";return TestResult::IMPOSSIBLE;
 }
 if(!RaidLabWarmPreparationGrid(bot,ctx,"madness-room",bot->GetPositionX(),bot->GetPositionY(),message))return TestResult::PENDING;
 GameObject* brazier=nullptr;
 MaNGOS::NearestGameObjectEntryInObjectRangeCheck check(*bot,180327,5.0f);
 MaNGOS::GameObjectLastSearcher<MaNGOS::NearestGameObjectEntryInObjectRangeCheck> searcher(brazier,check);
 Cell::VisitGridObjects(bot,searcher,5.0f);
 if(!brazier || !brazier->IsInWorld() || !brazier->IsSpawned()) {
  message="BLOCKED: native Madness brazier unavailable for room fixture";return TestResult::IMPOSSIBLE;
 }
 auto& store=bot->GetMap()->GetObjectsStore();std::vector<Creature*> trash;
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  Creature* c=i->second;
  if(!c || !c->IsInWorld() || !c->IsAlive())continue;
  if(c->GetEntry()>=15082 && c->GetEntry()<=15085) {
   message="BLOCKED: Madness boss already spawned before room preparation";return TestResult::IMPOSSIBLE;
  }
  if(!RaidLabMadnessRoomActor(c->GetEntry(),brazier->GetDistance(c)))continue;
  if(c->IsInCombat()) {message="BLOCKED: Madness ambient trash already fighting";return TestResult::IMPOSSIBLE;}
  trash.push_back(c);
 }
 if(trash.size()>48) {message="BLOCKED: unexpected Madness ambient room population";return TestResult::IMPOSSIBLE;}
 for(Creature* c:trash) {
  sLog.outString("RAID_LAB_FIXTURE: prepared Madness boss-only room despawn entry=%u guid=%s; NOT trash progression validation",
      c->GetEntry(),c->GetObjectGuid().GetString().c_str());
  c->SetRespawnDelay(3600,true);c->ForcedDespawn();
 }
 message="Explicit Madness boss-only room; native brazier/calendar/summon retained; trash progression NOT tested";
 return TestResult::PASS;
}
bool RaidLabStagingAllowed(uint32 map,uint32 entry,const std::string& fixture) {
 const bool clearedRoom=fixture=="cleared-room";
 const bool mcBoss=entry==12118 || entry==11982 || entry==12259 || entry==12057 || entry==12056 ||
     entry==12264 || entry==12098 || entry==11988 || entry==12018 || entry==11502;
 const bool naxxRoomBoss=entry==15956 || entry==15953 || entry==15952 || entry==15931 || entry==15936;
 return (map==409 && mcBoss && (clearedRoom || (entry==11982 && fixture.empty()))) ||
       (map==533 && naxxRoomBoss && clearedRoom) ||
       (map==469 && entry==12017 && clearedRoom) ||
       (map==309 && (entry==14510 || entry==14509 || entry==11380) && clearedRoom) ||
       (map==509 && (entry==15369 || entry==15348) && clearedRoom) ||
       (map==531 && (entry==15511 || entry==15543 || entry==15544) && clearedRoom) ||
       (map==309 && entry==14517 && fixture.empty());
}
TestResult CommandRaidLabStaging::Execute(const std::string& params, Player* bot, PlayerbotAI*,
                                         TestContext& ctx, std::string& message)
{
 // Explicit local boss-only fixtures retain native encounter adds; their
 // cleared ambient trash is never counted as trash-progression validation.
 uint32 entry=0;std::string fixture;std::istringstream input(params);input>>entry>>fixture;
 if(fixture=="madness-room")return RaidLabStageMadnessRoom(bot,ctx,entry,message);
 const bool clearedRoom=fixture=="cleared-room";
 if (!RaidLab::Enabled() || !bot->IsInWorld() || bot->IsBeingTeleported() ||
     !bot->IsGameMaster() || !RaidLabStagingAllowed(bot->GetMapId(),entry,fixture)) {
  message="BLOCKED: reviewed raid staging requires settled local setup observer";
  return TestResult::IMPOSSIBLE;
 }
 Player* reference=RaidLabAggroReference(bot);
 if(!reference) {message="BLOCKED: no settled GM-off faction reference for staging aggro validation";return TestResult::IMPOSSIBLE;}
 auto& store=bot->GetMap()->GetObjectsStore();
 Creature* boss=nullptr;
 for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
  auto c=i->second;
  if(c && c->GetEntry()==entry && c->IsAlive() && c->IsInWorld() &&
     bot->GetDistance(c)<(bot->GetMapId()==409 && entry==12056?300.0f:100.0f)) {boss=c;break;}
 }
 if(!boss || boss->IsInCombat()) {
  sLog.outString("RAID_LAB_SETUP: staging boss entry=%u found=%u combat=%u",entry,boss?1u:0u,boss&&boss->IsInCombat()?1u:0u);
  message="BLOCKED: native raid boss unavailable for staging";return TestResult::IMPOSSIBLE;
 }
 if(!RaidLabWarmPreparationGrid(bot,ctx,"staging",boss->GetPositionX(),boss->GetPositionY(),message))return TestResult::PENDING;
 if(clearedRoom) {
  if(ctx.testName.find("_cleared_room")==std::string::npos) {
   message="BLOCKED: cleared-room fixture requires an explicitly named scenario";
   return TestResult::IMPOSSIBLE;
  }
  std::vector<Creature*> trash;
  for(auto i=store.begin<Creature>();i!=store.end<Creature>();++i) {
   auto c=i->second;
   if(c && c->IsAlive() && c->IsInWorld() &&
      RaidLabClearRoomActor(bot->GetMapId(),entry,ctx.testName,c->GetEntry(),boss->GetDistance(c)))
    trash.push_back(c);
  }
  if(RaidLabRemovedPrerequisite(bot->GetMapId(),entry,ctx.testName,12118)) {
   unsigned lucifron=0,protectors=0;
   for(Creature* c:trash) {
    lucifron+=c->GetEntry()==12118?1:0;
    protectors+=c->GetEntry()==12119?1:0;
   }
   // Lucifron's native spawn is ~158yd from Magmadar, outside the ambient
   // trash radius. This named prerequisite fixture must account for all
   // three loaded actors, otherwise the observation is not isolated.
   if(lucifron!=1 || protectors!=2) {
    message="BLOCKED: post-Lucifron fixture did not find one boss and two protectors";
    return TestResult::IMPOSSIBLE;
   }
  }
  for(auto c:trash) {
   if(RaidLabRemovedPrerequisite(bot->GetMapId(),entry,ctx.testName,c->GetEntry()))
    sLog.outString("RAID_LAB_FIXTURE: post_lucifron prerequisite removed entry=%u; NOT Lucifron or progression validation",c->GetEntry());
   sLog.outString("RAID_LAB_FIXTURE: cleared_room despawn entry=%u guid=%s; NOT trash validation",
       c->GetEntry(),c->GetObjectGuid().GetString().c_str());
   c->SetRespawnDelay(3600,true);
   c->ForcedDespawn();
  }
  if(entry!=11982) {
   message="Explicit boss-only room fixture; native encounter adds retained; trash progression NOT tested";
   return TestResult::PASS;
  }
 }
 unsigned floorRejected=0, losRejected=0, pathRejected=0, trashRejected=0;
 for(float radius : {30.0f,35.0f,40.0f,45.0f,50.0f}) for(unsigned sector=0;sector<24;++sector) {
  if(radius<boss->GetAttackDistance(bot)+2.0f) continue;
  float angle=float(sector)*float(2*M_PI)/24.0f;
  float x=boss->GetPositionX()+radius*std::cos(angle);
  float y=boss->GetPositionY()+radius*std::sin(angle), z=boss->GetPositionZ();
  bot->UpdateAllowedPositionZ(x,y,z);
  if(!std::isfinite(z) || std::abs(z-boss->GetPositionZ())>(entry==14517?40.0f:8.0f)) {++floorRejected;continue;}
  if(!boss->IsWithinLOS(x,y,z+bot->GetCollisionHeight(),true)) {++losRejected;continue;}
  WorldPosition destination(bot->GetMapId(),x,y,z);
  WorldPosition origin(boss);
  if(entry==14517) {
   // The script's native flight landing is the ground arena. The estimated
   // travel-node approach can itself lie on a disconnected ledge.
   const float originX=-12281.58f,originY=-1392.84f;
   const float originZ=bot->GetMap()->GetHeight(originX,originY,146.1f);
   if(!std::isfinite(originZ) || originZ<=INVALID_HEIGHT) {++floorRejected;continue;}
   origin=WorldPosition(bot->GetMapId(),originX,originY,originZ);
  }
  auto path=destination.getPathStepFrom(origin,bot,true);
  if(!destination.isPathTo(path,1.0f,2.0f)) {++pathRejected;continue;}
  bool clear=true;
  for(auto i=store.begin<Creature>();i!=store.end<Creature>() && clear;++i) {
   auto c=i->second;
   if(c==boss || !RaidLabBodyPullRisk(c,reference,true)) continue;
   // Check actual aggressive enemies along the pull corridor and landing.
   for(const auto& point : path) {
    float dx=c->GetPositionX()-point.coord_x, dy=c->GetPositionY()-point.coord_y;
    float dz=c->GetPositionZ()-point.coord_z;
    // Native DetectOrAttack compares center distance (DIST_CALC_NONE).
    // Match its level/aura-adjusted radius, with two yards of fixture margin.
    float clearance=c->GetAttackDistance(reference)+2.0f;
    if(dx*dx+dy*dy+dz*dz<clearance*clearance &&
       c->IsWithinLOS(point.coord_x,point.coord_y,point.coord_z+reference->GetCollisionHeight(),true)) {
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
  details<<"Validated raid staging entry="<<entry<<" "<<x<<","<<y<<","<<z<<" radius="<<radius
         <<" rejected floor="<<floorRejected<<" los="<<losRejected
         <<" path="<<pathRejected<<" trash="<<trashRejected;
  message=details.str();sLog.outString("RAID_LAB_SETUP: %s",message.c_str());
  return TestResult::PASS;
 }
 std::ostringstream details;
 details<<"BLOCKED: no clear raid staging entry="<<entry<<" floor="<<floorRejected<<" los="<<losRejected
        <<" path="<<pathRejected<<" trash="<<trashRejected;
 message=details.str();sLog.outString("RAID_LAB_SETUP: %s",message.c_str());
 return TestResult::IMPOSSIBLE;
}
bool MonitorRaidLabDeath::IsConditionMet(const std::string&, Player* bot, TestContext& ctx) const {
 if(!bot->IsInWorld() || !ctx.focusMobGuid || !RaidLab::BossDied(bot->GetMap(),ctx.focusMobGuid.GetRawValue()))return false;
 if(!ctx.raidLabPostKillStarted) {
  ctx.raidLabPostKillStarted=WorldTimer::getMSTime();RaidLab::Event(bot,"post_kill_observation_started");
 }
 // Observe native add cleanup, resurrection and regroup for thirty seconds;
 // a boss death alone still does not certify those behaviors.
 return WorldTimer::getMSTime()-ctx.raidLabPostKillStarted>=30000;
}
bool MonitorRaidLabCompletion::IsConditionMet(const std::string&, Player* bot, TestContext& ctx) const {
 // Majordomo concedes after his adds die. A boss-death assertion would never
 // complete this native encounter and could conceal its actual outcome.
 if(!RaidLab::Enabled() || !bot->IsInWorld() || bot->GetMapId()!=409 || ctx.focusMobEntry!=12018 || !ctx.focusMobGuid)return false;
 InstanceData* instance=bot->GetMap()->GetInstanceData();
 if(!instance || instance->GetData(8)!=DONE)return false;
 if(!ctx.raidLabPostKillStarted) {
  ctx.raidLabPostKillStarted=WorldTimer::getMSTime();RaidLab::Event(bot,"native_encounter_complete_observation_started",12018);
 }
 return WorldTimer::getMSTime()-ctx.raidLabPostKillStarted>=30000;
}
bool MonitorRaidLabNoEngagement::IsConditionMet(const std::string&, Player* bot, TestContext& ctx) const
{
 Creature* boss=bot->GetMap()->GetCreature(ctx.focusMobGuid);
 if(boss && boss->IsInCombat()) ctx.combatSeen=true;
 return !ctx.combatSeen && ctx.monitorTime && WorldTimer::getMSTime()-ctx.monitorTime>60000;
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
  if(!ctx.raidLabPatrolWaitStarted)
   sLog.outString("RAID_LAB_SETUP: pull acquisition entry=%u found=%u distance=%.2f combat=%u boss=%.3f,%.3f,%.3f",
       entry,boss?1u:0u,boss?bot->GetDistance(boss):-1.0f,boss&&boss->IsInCombat()?1u:0u,
       boss?boss->GetPositionX():0,boss?boss->GetPositionY():0,boss?boss->GetPositionZ():0);
  if(boss && !boss->IsInCombat() && RaidLabPatrolWaitAllowed(bot->GetMapId(),entry,
      WorldTimer::getMSTime(),ctx.raidLabPatrolWaitStarted)) {
   message="Waiting at validated preparation point for native patrol to return within pull search range";
   return TestResult::PENDING;
  }
  message="BLOCKED: native boss missing or farther than 100 yards";
  return TestResult::IMPOSSIBLE;
 }
 ctx.raidLabPatrolWaitStarted=0;
 Player* tank=nullptr;
 if(!RaidLabPartyReady(bot,ai,tank,message)) return TestResult::IMPOSSIBLE;
 if(bot->GetMapId()==531 && entry==15276) {
  // Vek'lor is physically immune: the native warrior shoot correctly refuses
  // it. Model a player requesting a ranged magical pull, not a forced engage.
  std::vector<Player*> casters;
  for(auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next()) {
   Player* member=ref->getSource();
   if(!member || member==bot || !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer() ||
      ai->IsHeal(member) || member->getClass()!=CLASS_WARLOCK)continue;
   Item* weapon=member->GetItemByPos(INVENTORY_SLOT_BAG_0,EQUIPMENT_SLOT_RANGED);
   if(weapon && weapon->GetProto()->SubClass==ITEM_SUBCLASS_WEAPON_WAND)casters.push_back(member);
  }
  std::sort(casters.begin(),casters.end(),[](Player* a,Player* b){return a->GetObjectGuid()<b->GetObjectGuid();});
  if(casters.empty()) {message="BLOCKED: Vek'lor fixture requires a warlock with a native wand";return TestResult::IMPOSSIBLE;}
  tank=casters[std::min<size_t>(1,casters.size()-1)];
 }
 if(boss->IsInCombat()) {message="BLOCKED: boss already in combat before attempt";return TestResult::IMPOSSIBLE;}
 bot->SetSelectionGuid(boss->GetObjectGuid());
 if(!RaidLab::Begin(bot,entry,ctx.testName,mode=="leader")) {
  message="BLOCKED: telemetry could not start";return TestResult::IMPOSSIBLE;
 }
 ctx.focusMobGuid=boss->GetObjectGuid();ctx.focusMobEntry=entry;ctx.combatSeen=false;
 if(ctx.testName.find("_cleared_room")!=std::string::npos)
  RaidLab::Event(bot,"fixture_precleared_room_not_trash_validation");
 if(ctx.testName.find("_seeded")!=std::string::npos)
  RaidLab::Event(bot,"fixture_native_encounter_seed_not_progression_validation");
 RaidLabFollowers(bot,ai,ctx);
 if(bot->GetMapId()==531 && entry==15276) {
  tank->GetPlayerbotAI()->ChangeStrategy("+pull",BotState::BOT_STATE_NON_COMBAT);
  tank->GetPlayerbotAI()->ChangeStrategy("+pull",BotState::BOT_STATE_COMBAT);
  RaidLab::Event(bot,"fixture_magical_puller",tank->GetObjectGuid().GetRawValue());
 }
 RaidLab::Event(bot,"pull_command",boss->GetObjectGuid().GetRawValue(),tank->GetObjectGuid().GetRawValue());
 tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot);
 // One ordinary pull request. No recurring attack injection or encounter cheats.
 message="Native pull requested; mechanics assertions evaluated separately from outcome";
 return TestResult::PASS;
}
#endif
