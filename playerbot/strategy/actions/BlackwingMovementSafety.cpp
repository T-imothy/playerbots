#include "playerbot/playerbot.h"
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
        const WorldPosition& from, const WorldPosition& to)
    {
        std::list<HazardPosition> circle{{WorldPosition(enemy), radius}};
        if (IsHazardSafeSegment(from, to, circle)) return false;
        const double dx = to.getX() - from.getX(), dy = to.getY() - from.getY(), dz = to.getZ() - from.getZ();
        const double ex = from.getX() - enemy->GetPositionX(), ey = from.getY() - enemy->GetPositionY(), ez = from.getZ() - enemy->GetPositionZ();
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
            if (enemy->IsWithinLOS(float(from.getX()+t*dx), float(from.getY()+t*dy),
                float(from.getZ()+t*dz)+bot->GetCollisionHeight(), true)) return true;
        }
        return false;
    }
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

bool ai::BlackwingMovementRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path)
{
    if (!BlackwingSuppressionMovementActive(ai)) return true;
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
    std::vector<std::pair<Unit*,float>> protectedPacks;
    for (Unit* enemy : enemies)
    {
        if (enemy==pull || enemy==ordered || RoomEnemyEngaged(ai, enemy)) continue;
        // Native IsWithinDistInMap compares centre distance after adding both
        // combat reaches. Large dragons must retain that same admission area.
        float radius=enemy->GetAttackDistance(bot)+enemy->GetCombatReach()+bot->GetCombatReach();
        bool stealth=bot->HasAuraType(SPELL_AURA_MOD_STEALTH) && bot->getAttackers().empty() &&
            !bot->HasAuraTypeWithCaster(SPELL_AURA_MOD_STALKED, enemy->GetObjectGuid());
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
        protectedPacks.emplace_back(enemy,radius+2.0f);
    }
    previous=WorldPosition(bot);
    for (const WorldPosition& point : path)
    {
        for (const auto& pack : protectedPacks)
            if (VisibleAggroCrossing(bot,pack.first,pack.second,previous,point)) return false;
        previous=point;
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
    if (!IsFiniteMovementPoint(destination,bot->GetMapId()) || WorldPosition(bot).distance(destination)>70) return false;
    PathFinder finder(bot);
    if (!finder.calculate(destination.getX(),destination.getY(),destination.getZ(),false) ||
        finder.getPathType()!=PATHFIND_NORMAL || finder.getPath().size()<2 || finder.getPath().size()>256) return false;
    for (const auto& point : finder.getPath()) path.emplace_back(bot->GetMapId(),point.x,point.y,point.z);
    if (!destination.isPathTo(path,1.0f,2.0f) || !BlackwingMovementRouteSafe(ai,path)) return false;
    auto hazards=ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Get();
    AppendBlackwingGroundHazards(ai,hazards);
    WorldPosition previous(bot);
    for (const auto& point:path)
    {
        if (!IsHazardSafeSegment(previous,point,hazards)) return false;
        previous=point;
    }
    return true;
}

bool ai::BlackwingActiveMovementUnsafe(PlayerbotAI* ai)
{
    Player* bot=ai->GetBot();
    // A boss knockback/fear is authoritative native movement, not a bot route.
    if (!ai->CanMove() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType()==EFFECT_MOTION_TYPE ||
        !bot->movespline || bot->movespline->Finalized() || !BlackwingSuppressionMovementActive(ai)) return false;
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
