#include "playerbot/playerbot.h"
#include "playerbot/RaidLabTrace.h"
#include "BlackwingMovementSafety.h"
#include "MovementPathSafety.h"
#include "BotCommandAccess.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "playerbot/strategy/generic/CombatStrategy.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Combat/ThreatManager.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "MotionGenerators/PathFinder.h"
#include "Movement/MoveSpline.h"
#include "MotionGenerators/MotionMaster.h"
#include "MotionGenerators/MovementGenerator.h"

using namespace ai;
namespace
{
    bool RoomMember(Player* bot, Unit* unit)
    {
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit)) return false;
        if (!unit->IsPlayer()) unit = unit->GetMaster();
        Player* member = dynamic_cast<Player*>(unit);
        return member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            !member->IsBeingTeleported() && !member->HasCharmer() && member->GetGroup() == bot->GetGroup();
    }
    bool RoomEnemyEngaged(PlayerbotAI* ai, Unit* enemy)
    {
        Player* bot = ai->GetBot();
        if (!enemy->IsInCombat()) return false;
        if (RoomMember(bot, enemy->GetVictim())) return true;
        for (Unit* attacker : enemy->getAttackers())
            if (RoomMember(bot, attacker)) return true;
        for (const auto* reference : enemy->getThreatManager().getThreatList())
            if (reference && RoomMember(bot, ai->GetUnit(reference->getUnitGuid()))) return true;
        return false;
    }
    Unit* AuthorizedRoomPull(PlayerbotAI* ai)
    {
        PullStrategy* pull = PullStrategy::Get(ai);
        if (!pull || !pull->IsEncounterPreparationAllowed() || !pull->HasPullStarted()) return nullptr;
        const time_t elapsed = time(nullptr) - pull->GetPullStartTime();
        if (elapsed < 0 || elapsed >= pull->GetMaxPullTime()) return nullptr;
        Player* requester = dynamic_cast<Player*>(ai->GetUnit(pull->GetRequester()));
        Unit* target = pull->GetTarget();
        if (!requester || !requester->isRealPlayer() || !RoomMember(ai->GetBot(), requester) ||
            !CanManageBotCommands(ai, requester) || !target || !target->IsInWorld() || !target->IsAlive() ||
            !ai->GetBot()->IsInMap(target) || target->HasCharmer()) return nullptr;
        return target;
    }
    // A wall or another floor can separate nearby packs. Test visibility at
    // points along the dangerous part of this actual route, not at the bot's
    // current position (which may be safely around a corner).
    bool VisibleAggroCrossing(Player* bot, Unit* enemy, float radius,
        const WorldPosition& from, const WorldPosition& to, const WorldPosition* prediction = nullptr,
        bool nativeStartProjection = false)
    {
        const WorldPosition center = prediction ? *prediction : WorldPosition(enemy);
        std::list<HazardPosition> circle{{center, radius}};
#ifdef MANGOSBOT_ZERO
        // Native BWL paths can begin by projecting the current position down
        // onto the same XY on the navigation floor. A nearby patrol must not
        // pin an already threatened bot there because that vertical correction
        // points slightly toward the patrol. Only the first waypoint qualifies;
        // every subsequent walking segment retains the full aggro check.
        if (nativeStartProjection && from.getMapId() == 469 &&
            IsHazardSafeGroundProjection(from, to, circle)) return false;
#endif
        if (IsHazardSafeSegment(from, to, circle)) return false;
        const double dx = to.getX() - from.getX(), dy = to.getY() - from.getY(), dz = to.getZ() - from.getZ();
        const double ex = from.getX() - center.getX(), ey = from.getY() - center.getY(), ez = from.getZ() - center.getZ();
        const double length = dx*dx + dy*dy + dz*dz;
        const double projection = length > 0 ? std::clamp(-(ex*dx+ey*dy+ez*dz)/length, 0.0, 1.0) : 0;
        const double nearSquared = (ex+projection*dx)*(ex+projection*dx) +
            (ey+projection*dy)*(ey+projection*dy) + (ez+projection*dz)*(ez+projection*dz);
        const double half = length > 0 ? std::sqrt(std::max(0.0, double(radius)*radius-nearSquared)/length) : 0;
        const double first = std::max(0.0, projection-half), last = std::min(1.0, projection+half);
        const unsigned steps = std::max(1u, unsigned(std::ceil((last-first)*std::sqrt(length)/1.0)));
        for (unsigned i=0; i<=steps; ++i)
        {
            const double t = first+(last-first)*i/steps;
            const float x=float(from.getX()+t*dx), y=float(from.getY()+t*dy);
            const float z=float(from.getZ()+t*dz)+bot->GetCollisionHeight();
            if (prediction ? enemy->GetMap()->IsInLineOfSight(center.getX(),center.getY(),
                    center.getZ()+enemy->GetCollisionHeight(),x,y,z,true) : enemy->IsWithinLOS(x,y,z,true)) return true;
        }
        return false;
    }
    bool RaidPatrolLookahead(Unit* enemy, float seconds, std::vector<WorldPosition>& future)
    {
#ifdef MANGOSBOT_ZERO
        // Native spline only, at most five seconds/24yd. An idle mob has no
        // guessed future route, and combat targets are handled by threat rules.
        if (!enemy->movespline || enemy->movespline->Finalized() || enemy->IsInCombat()) return true;
        const float speed=enemy->movespline->Speed();
        if (!std::isfinite(speed) || speed<0 || speed>30 || !std::isfinite(seconds) || seconds<0) return false;
        float remaining=std::min(24.0f,speed*std::min(5.0f,seconds));
        const auto& spline=enemy->movespline->_Spline();
        WorldPosition from(enemy);
        unsigned segments=0;
        for (int32 i=enemy->movespline->_currentSplineIdx()+1; i<=spline.last() && remaining>0.01f; ++i)
        {
            if (++segments>256) return false;
            const auto& p=spline.getPoint(i);
            WorldPosition next(enemy->GetMapId(),p.x,p.y,p.z);
            if (!IsFiniteMovementPoint(next,enemy->GetMapId())) return false;
            const float length=from.distance(next), admitted=std::min(length,remaining);
            if (length>0.01f)
            {
                const unsigned steps=std::max(1u,unsigned(std::ceil(admitted/2.0f)));
                for (unsigned step=1;step<=steps;++step)
                {
                    if (future.size()>=32) return false;
                    const float fraction=admitted*step/steps/length;
                    future.emplace_back(enemy->GetMapId(),from.getX()+(next.getX()-from.getX())*fraction,
                        from.getY()+(next.getY()-from.getY())*fraction,from.getZ()+(next.getZ()-from.getZ())*fraction);
                }
            }
            remaining-=admitted;from=next;
        }
#endif
        return true;
    }
}

bool ai::BlackwingPatrolThreats(PlayerbotAI* ai, EncounterPosition& plan,
    std::vector<encounter::Circle>& threats)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId()!=469 ||
        !bot->IsInCombat() || !bot->GetGroup() || bot->IsBeingTeleported() ||
        bot->HasCharmer() || bot->GetTransport() || ai->IsRealPlayer()) return false;
    struct DragonCheck
    {
        Player* bot;
        WorldObject const& GetFocusObject() const { return *bot; }
        bool operator()(Unit* unit) const
        {
            return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) &&
                !unit->HasCharmer() && (unit->GetEntry()==11981 || unit->GetEntry()==11983 || unit->GetEntry()==14601);
        }
    } check{bot};
    std::list<Unit*> dragons;
    MaNGOS::UnitListSearcher<DragonCheck> searcher(dragons,check);
    Cell::VisitAllObjects(bot,searcher,100.0f);
    Unit* boss=nullptr;
    for (Unit* dragon:dragons)
        if (RoomEnemyEngaged(ai,dragon) && (!boss || dragon->GetObjectGuid()<boss->GetObjectGuid())) boss=dragon;
    if (!boss) return false;
    Unit* pull=AuthorizedRoomPull(ai);
    Unit* ordered=nullptr;
    if (WaitForAttackStrategy* wait=WaitForAttackStrategy::Get(ai)) ordered=wait->GetExplicitAttackTarget(ai);
    const WorldPosition here(bot);
    for (Unit* dragon:dragons)
    {
        // A blocked walking route alone is not an escape order. Only a native
        // moving patrol about to enter this bot's current position qualifies.
        if (dragon==pull || dragon==ordered || dragon->IsInCombat() ||
            !dragon->CanInitiateAttack() || !dragon->CanAttackOnSight(bot) ||
            !dragon->movespline || dragon->movespline->Finalized()) continue;
        const float radius=dragon->GetAttackDistance(bot)+2.0f;
        if (!std::isfinite(radius) || radius<2 || radius>100) continue;
        std::vector<WorldPosition> future;
        if (!RaidPatrolLookahead(dragon,5.0f,future)) continue;
        WorldPosition nearest(dragon);
        bool danger=false;
        for (const WorldPosition& position:future)
            if (here.distance(position)<radius && dragon->GetMap()->IsInLineOfSight(
                position.getX(),position.getY(),position.getZ()+dragon->GetCollisionHeight(),
                here.getX(),here.getY(),here.getZ()+bot->GetCollisionHeight(),true))
            {
                danger=true;
                if (here.distance(position)<here.distance(nearest)) nearest=position;
            }
        if (!danger) continue;
        if (threats.size()>=6) break;
        threats.push_back({{dragon->GetPositionX(),dragon->GetPositionY(),dragon->GetPositionZ()},radius});
        threats.push_back({{nearest.getX(),nearest.getY(),nearest.getZ()},radius});
        if (plan.source==ObjectGuid()) plan.source=dragon->GetObjectGuid();
    }
    if (threats.empty()) return false;
    plan.map=bot->GetMapId(); plan.instance=bot->GetInstanceId();
    plan.boss=boss->GetObjectGuid(); plan.spell=0;
    return true;
#else
    return false;
#endif
}

bool ai::BlackwingSuppressionMovementActive(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId()!=469 || !bot->GetGroup() ||
        bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetTransport() || ai->IsRealPlayer()) return false;
    // Body-pull safety remains active at the Broodlord doorway during and
    // after his fight. Only the separate suppression station plan is retired
    // by the boss state; untouched packs beyond the doorway still exist.
    std::list<GameObject*> devices;
    MaNGOS::GameObjectEntryInPosRangeCheck check(*bot, 179784,
        bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ(), 70.0f);
    MaNGOS::GameObjectListSearcher<MaNGOS::GameObjectEntryInPosRangeCheck> searcher(devices, check);
    Cell::VisitAllObjects(bot, searcher, 70.0f);
    for (GameObject* device : devices)
        if (device && device->IsInWorld() && bot->IsInMap(device) &&
            std::fabs(device->GetPositionZ()-bot->GetPositionZ())<=15.0f) return true;
    return false;
}

bool ai::BlackwingMovementSafetyActive(PlayerbotAI* ai)
{
    if (BlackwingSuppressionMovementActive(ai)) return true;
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    // The dragon rooms have adjacent unpulled bosses too. Apply route
    // admission during combat, without imposing suppression-room stacking
    // or a player-distance leash on those encounters.
    return bot->GetMapId()==469 && bot->IsInWorld() && bot->IsAlive() &&
        bot->IsInCombat() && bot->GetGroup() && !bot->IsBeingTeleported() &&
        !bot->HasCharmer() && !bot->GetTransport() && !ai->IsRealPlayer();
#else
    return false;
#endif
}

bool ai::RaidUnpulledPackMovementActive(PlayerbotAI* ai)
{
    if (BlackwingMovementSafetyActive(ai)) return true;
#ifdef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    // A ZG pull completes as soon as the target engages. Keep admission alive
    // throughout combat: melee and pets must not draw followers into untouched
    // packs after that transition. No BWL stacking/player-distance leash here.
    return bot && bot->GetMapId() == 309 && bot->IsInWorld() && bot->IsAlive() &&
        bot->GetGroup() && !bot->IsBeingTeleported() && !bot->HasCharmer() &&
        !bot->GetTransport() && !ai->IsRealPlayer() &&
        (bot->IsInCombat() || AuthorizedRoomPull(ai));
#else
    return false;
#endif
}

bool ai::BlackwingMovementRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path)
{
    if (!RaidUnpulledPackMovementActive(ai)) return true;
    return RaidUnpulledPackRouteSafe(ai, path);
}

bool ai::MadnessFormationRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path, Unit* boss)
{
#ifdef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (bot->GetMapId() == 309 && bot->IsInWorld() && bot->IsAlive() && bot->GetGroup() &&
        !bot->IsBeingTeleported() && !bot->HasCharmer() && !ai->IsRealPlayer() && boss &&
        boss->IsInWorld() && boss->IsAlive() && bot->IsInMap(boss) && !boss->HasCharmer() &&
        boss->GetEntry() >= 15082 && boss->GetEntry() <= 15085 && RoomEnemyEngaged(ai, boss))
        return RaidUnpulledPackRouteSafe(ai, path);
#endif
    return true;
}

bool ai::MajordomoFormationRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path, Unit* boss)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (bot->GetMapId()==409 && bot->IsInWorld() && bot->IsAlive() && bot->GetGroup() &&
        !bot->IsBeingTeleported() && !bot->HasCharmer() && !ai->IsRealPlayer() && boss &&
        boss->IsInWorld() && boss->IsAlive() && bot->IsInMap(boss) && !boss->HasCharmer() &&
        boss->GetEntry()==12018 && RoomEnemyEngaged(ai,boss))
        return RaidUnpulledPackRouteSafe(ai,path);
#endif
    return true;
}

bool ai::MoltenCoreTrashChargeSafe(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (!bot || bot->GetMapId()!=409 || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetTransport() || ai->IsRealPlayer()) return true;
    // CurrentTargetValue is GUID-valued. Resolve it through the owning AI;
    // asking the typed context for Unit* returns null, not a target value.
    auto targetValue=ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target");
    Unit* target=targetValue ? ai->GetUnit(targetValue->Get()) : nullptr;
    // Observed off-tank Intercept on a pulled giant entered an idle Firelord's
    // aggro circle. Limit this admission to these trash targets; Garr, Geddon
    // and other boss control/formation policies remain unchanged.
    if (!target || !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target) ||
        target->HasCharmer() || (target->GetEntry()!=11658 && target->GetEntry()!=11659 && target->GetEntry()!=11668) ||
        !RoomEnemyEngaged(ai,target)) return true;
    // Match Classic MotionMaster::MoveCharge's native contact destination.
    Position contact;
    target->GetFirstCollisionPosition(contact,target->GetCombatReach(),target->GetAngle(bot));
    contact.z+=1.0f;
    WorldPosition destination(bot->GetMapId(),contact.x,contact.y,contact.z);
    if (!IsFiniteMovementPoint(destination,bot->GetMapId()) || WorldPosition(bot).distance(destination)>40) return false;
    PathFinder finder(bot);
    if (!finder.calculate(contact.x,contact.y,contact.z,false) || finder.getPathType()!=PATHFIND_NORMAL ||
        finder.getPath().size()<2 || finder.getPath().size()>256) return false;
    std::vector<WorldPosition> path;
    for (const auto& point:finder.getPath()) path.emplace_back(bot->GetMapId(),point.x,point.y,point.z);
    return destination.isPathTo(path,1.0f,2.0f) && RaidUnpulledPackRouteSafe(ai,path);
#else
    return true;
#endif
}

bool ai::RaidUnpulledPackRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path)
{
    Player* bot = ai->GetBot();
    if (path.empty() || path.size()>256) return false;
    WorldPosition previous(bot);
    float total=0, extent=0;
    for (const WorldPosition& point:path)
    {
        if (!IsFiniteMovementPoint(point,bot->GetMapId())) return false;
        total+=previous.distance(point);
        if (total>120) return false;
        extent=std::max(extent,WorldPosition(bot).distance(point));
        previous=point;
    }
    struct FreshEnemy
    {
        Player* bot;
        WorldObject const& GetFocusObject() const { return *bot; }
        bool operator()(Unit* unit) const
        {
            return unit && unit->GetTypeId()==TYPEID_UNIT && unit->IsInWorld() && unit->IsAlive() &&
                bot->IsInMap(unit) && !unit->HasCharmer() && unit->CanInitiateAttack() && unit->CanAttackOnSight(bot);
        }
    } check{bot};
    std::list<Unit*> enemies;
    MaNGOS::UnitListSearcher<FreshEnemy> searcher(enemies, check);
    // Only scan the actual route extent plus the maximum admitted native
    // attack radius. Short combat adjustments do not scan the whole room.
    Cell::VisitAllObjects(bot, searcher, extent+100.0f);
    Unit* pull = AuthorizedRoomPull(ai);
    Unit* ordered = nullptr;
    if (WaitForAttackStrategy* wait = WaitForAttackStrategy::Get(ai))
        ordered = wait->GetExplicitAttackTarget(ai);
    struct ProtectedPack { Unit* enemy; float radius; std::vector<WorldPosition> future; };
    std::vector<ProtectedPack> protectedPacks;
    for (Unit* enemy : enemies)
    {
        if (enemy==pull || enemy==ordered || RoomEnemyEngaged(ai, enemy)) continue;
        // Classic DetectOrAttack uses squared centre distance (DIST_CALC_NONE),
        // not melee reaches. Adding dragon reach here blocked otherwise legal
        // routes before the native aggro boundary was reached.
        float radius=enemy->GetAttackDistance(bot);
#ifndef MANGOSBOT_ZERO
        radius+=enemy->GetCombatReach()+bot->GetCombatReach();
#endif
        bool stealth=bot->HasAuraType(SPELL_AURA_MOD_STEALTH) && bot->getAttackers().empty() &&
            !bot->HasAuraTypeWithCaster(SPELL_AURA_MOD_STALKED, enemy->GetObjectGuid());
#ifdef MANGOSBOT_ZERO
        // A ZG combat opener removes stealth at the destination. Native trace:
        // Cheap Shot at an admitted stealth position body-pulled two Axe
        // Throwers. Use visible clearance for these offensive approaches;
        // retain stealth-aware BWL trap disarming and ordinary travel.
        if (bot->GetMapId()==309 && (bot->IsInCombat() || pull || ordered)) stealth=false;
#endif
#ifndef MANGOSBOT_ZERO
        stealth=stealth && !enemy->HasAuraType(SPELL_AURA_DETECT_STEALTH);
#endif
        if (stealth)
        {
            const float hidden=bot->GetVisibilityData().GetStealthVisibilityDistance(enemy,
                bot->HasFlag(UNIT_FIELD_FLAGS, UNIT_FLAG_PLAYER_CONTROLLED));
            if (std::isfinite(hidden)) radius=std::min(radius,std::max(0.0f,hidden));
        }
        if (!std::isfinite(radius) || radius<0 || radius>98.0f) return false;
        ProtectedPack pack{enemy,radius+2.0f,{}};
        // This is a route-time safety margin, not an increase to native aggro.
        // Slow/suppressed players need the full bounded lookahead.
        const float speed=bot->GetSpeed(MOVE_RUN);
        const float seconds=std::isfinite(speed)&&speed>0.1f?std::min(5.0f,total/speed+1.0f):5.0f;
        if (!RaidPatrolLookahead(enemy,seconds,pack.future)) return false;
        protectedPacks.push_back(std::move(pack));
    }
    previous=WorldPosition(bot);
    bool firstWaypoint = true;
    for (const WorldPosition& point : path)
    {
        for (const auto& pack : protectedPacks)
        {
            const bool projection = firstWaypoint && path.size() > 1;
            bool crossing=VisibleAggroCrossing(bot,pack.enemy,pack.radius,previous,point,nullptr,projection);
            for (const auto& predicted : pack.future)
                if (!crossing && VisibleAggroCrossing(bot,pack.enemy,pack.radius,previous,point,&predicted,projection)) crossing=true;
            if (crossing)
            {
#ifdef MANTECH_RAID_LAB
                RaidLab::Count(bot,bot->GetMapId()==469?"bwl_route_fresh_enemy":bot->GetMapId()==409?"mc_charge_fresh_enemy":"madness_route_fresh_enemy",pack.enemy->GetEntry(),0,pack.enemy->GetObjectGuid().GetRawValue());
                RaidLab::RouteRejected(bot,previous.getX(),previous.getY(),previous.getZ(),
                    point.getX(),point.getY(),point.getZ(),pack.enemy->GetPositionX(),
                    pack.enemy->GetPositionY(),pack.enemy->GetPositionZ(),pack.radius);
#endif
                return false;
            }
        }
        previous=point;
        firstWaypoint = false;
    }
    return true;
}

bool ai::BuildBlackwingMovementPath(PlayerbotAI* ai, const WorldPosition& destination,
    std::vector<WorldPosition>& path)
{
    Player* bot=ai->GetBot();
    path.clear();
    if (Player* owner=ai->GetMaster())
        if (owner->GetMapId()==bot->GetMapId() && !bot->IsInMap(owner)) return false;
    if (!IsFiniteMovementPoint(destination,bot->GetMapId()) || WorldPosition(bot).distance(destination)>70)
    {
#ifdef MANTECH_RAID_LAB
        RaidLab::Count(bot,"bwl_path_destination",0);
#endif
        return false;
    }
    PathFinder finder(bot);
    if (!finder.calculate(destination.getX(),destination.getY(),destination.getZ(),false) ||
        finder.getPathType()!=PATHFIND_NORMAL || finder.getPath().size()<2 || finder.getPath().size()>256)
    {
#ifdef MANTECH_RAID_LAB
        RaidLab::Count(bot,"bwl_path_native",finder.getPathType());
#endif
        return false;
    }
    for (const auto& point : finder.getPath()) path.emplace_back(bot->GetMapId(),point.x,point.y,point.z);
    if (!destination.isPathTo(path,1.0f,2.0f))
    {
#ifdef MANTECH_RAID_LAB
        RaidLab::Count(bot,"bwl_path_endpoint",0);
#endif
        return false;
    }
    if (!BlackwingMovementRouteSafe(ai,path)) return false;
    auto hazards=ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Get();
    AppendBlackwingGroundHazards(ai,hazards);
    WorldPosition previous(bot);
    for (const auto& point:path)
    {
        if (!IsHazardSafeSegment(previous,point,hazards))
        {
#ifdef MANTECH_RAID_LAB
            RaidLab::Count(bot,"bwl_path_ground_hazard",0);
            for(const auto& hazard:hazards)
                if(!IsHazardSafeSegment(previous,point,{hazard})) {
                    RaidLab::RouteRejected(bot,previous.getX(),previous.getY(),previous.getZ(),
                        point.getX(),point.getY(),point.getZ(),hazard.first.getX(),
                        hazard.first.getY(),hazard.first.getZ(),hazard.second);
                    break;
                }
#endif
            return false;
        }
        previous=point;
    }
    return true;
}

bool ai::BlackwingActiveMovementUnsafe(PlayerbotAI* ai)
{
    Player* bot=ai->GetBot();
    // A boss knockback/fear is authoritative native movement, not a bot route.
    if (!ai->CanMove() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType()==EFFECT_MOTION_TYPE ||
        !bot->movespline || bot->movespline->Finalized() || !RaidUnpulledPackMovementActive(ai)) return false;
    const auto& spline=bot->movespline->_Spline();
    std::vector<WorldPosition> path;
    for (int32 i=bot->movespline->_currentSplineIdx()+1; i<=spline.last() && path.size()<=256; ++i)
    {
        const auto& p=spline.getPoint(i);
        path.emplace_back(bot->GetMapId(),p.x,p.y,p.z);
    }
    return !BlackwingMovementRouteSafe(ai,path);
}

bool ai::StopUnsafeBlackwingMovement(PlayerbotAI* ai)
{
    if (!BlackwingActiveMovementUnsafe(ai)) return false;
    ai->StopMoving();
    return true;
}
