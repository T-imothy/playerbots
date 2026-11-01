#include "playerbot/playerbot.h"
#include "BattleGroundTactics.h"
#include "BattleGround/BattleGroundAV.h"
#include "playerbot/strategy/values/PvpValues.h"
#include "playerbot/strategy/values/ClassicBattlegroundPolicy.h"

using namespace ai;
namespace policy = ai::ClassicBattlegroundPolicy;

void PlayerbotAI::PrepareForBattlegroundStart()
{
    if (IsRealPlayer() || !bot->IsInWorld() || bot->IsBeingTeleported()) return;
    BattleGround* bg = bot->GetBattleGround();
    const bool active = bg && SupportsBattlegroundObjectiveRecovery(bot) && bg->GetStatus() == STATUS_IN_PROGRESS;
    const bool alive = bot->IsAlive();
    const uint32 instance = bg ? bg->GetInstanceId() : 0;
    const bool resume = active && alive && (instance != observedBattlegroundInstance ||
        !observedBattlegroundActive || !observedBattlegroundAlive);
    observedBattlegroundInstance = instance;
    observedBattlegroundActive = active;
    observedBattlegroundAlive = alive;
    if (!resume || !aiObjectContext || bot->IsNonMeleeSpellCasted(false, false, true)) return;
    // A gate opening / resurrection invalidates waiting-time action sleeps,
    // not an accepted mount/heal/capture cast or ordinary world activity.
    aiInternalUpdateDelay = 0;
    isWaiting = false;
    aiObjectContext->GetValue<PositionMap&>("position")->Get()["bg objective"].Reset();
}

unsigned ai::BattlegroundTeamSlot(Player* bot, unsigned& count)
{
    std::vector<ObjectGuid> roster;
    if (BattleGround* bg = bot->GetBattleGround())
        for (const auto& member : bg->GetPlayers())
        {
            Player* player = bg->GetBgMap()->GetPlayer(member.first);
            if (!player || player->GetBattleGround() != bg || player->GetTeam() != bot->GetTeam() ||
                !player->GetPlayerbotAI()) continue;
            // Dead teammates keep their assignment. No reroll after each death.
            roster.push_back(member.first);
        }
    std::sort(roster.begin(), roster.end());
    count = unsigned(roster.size());
    auto found = std::find(roster.begin(), roster.end(), bot->GetObjectGuid());
    return found == roster.end() ? 0 : unsigned(found - roster.begin());
}

namespace
{
// Classic battleground maps (WSG/AB/AV), shared across all three eras.
// Keep expansion enum differences at this native API boundary.
#ifdef MANGOSBOT_TWO
constexpr auto BG_AV_NODES_FIRSTAID_STATION = BG_AV_NODE_GY_DUN_BALDAR;
constexpr auto BG_AV_NODES_STORMPIKE_GRAVE = BG_AV_NODE_GY_STORMPIKE;
constexpr auto BG_AV_NODES_STONEHEART_GRAVE = BG_AV_NODE_GY_STONEHEARTH;
constexpr auto BG_AV_NODES_ICEBLOOD_GRAVE = BG_AV_NODE_GY_ICEBLOOD;
constexpr auto BG_AV_NODES_FROSTWOLF_GRAVE = BG_AV_NODE_GY_FROSTWOLF;
constexpr auto BG_AV_NODES_FROSTWOLF_HUT = BG_AV_NODE_GY_FROSTWOLF_KEEP;
constexpr auto BG_AV_NODES_FROSTWOLF_ETOWER = BG_AV_NODE_FROSTWOLF_EAST;
constexpr auto BG_AV_NODES_FROSTWOLF_WTOWER = BG_AV_NODE_FROSTWOLF_WEST;
constexpr auto BG_AV_NODES_ICEBLOOD_TOWER = BG_AV_NODE_ICEBLOOD_TOWER;
constexpr auto BG_AV_NODES_TOWER_POINT = BG_AV_NODE_TOWER_POINT;
constexpr auto BG_AV_NODES_STONEHEART_BUNKER = BG_AV_NODE_STONEHEART_BUNKER;
constexpr auto BG_AV_NODES_ICEWING_BUNKER = BG_AV_NODE_ICEWING_BUNKER;
constexpr auto BG_AV_NODES_DUNBALDAR_SOUTH = BG_AV_NODE_DUNBALDAR_SOUTH;
constexpr auto BG_AV_NODES_DUNBALDAR_NORTH = BG_AV_NODE_DUNBALDAR_NORTH;
#endif
    policy::Node AvState(BattleGround* bg, unsigned node, bool alliance, bool enemyTower = false)
    {
        if (bg->IsActiveEvent(node, alliance ? BG_AV_NODE_STATUS_ALLY_OCCUPIED : BG_AV_NODE_STATUS_HORDE_OCCUPIED))
            return enemyTower ? policy::Node::Destroyed : policy::Node::Ours;
        if (bg->IsActiveEvent(node, alliance ? BG_AV_NODE_STATUS_ALLY_CONTESTED : BG_AV_NODE_STATUS_HORDE_CONTESTED))
            return policy::Node::OurAssault;
        if (bg->IsActiveEvent(node, alliance ? BG_AV_NODE_STATUS_HORDE_CONTESTED : BG_AV_NODE_STATUS_ALLY_CONTESTED))
            return policy::Node::EnemyAssault;
        if (bg->IsActiveEvent(node, alliance ? BG_AV_NODE_STATUS_HORDE_OCCUPIED : BG_AV_NODE_STATUS_ALLY_OCCUPIED))
            return policy::Node::Theirs;
        return policy::Node::Neutral;
    }
}

bool BGTactics::SelectClassicArathiObjective()
{
    BattleGround* bg = bot->GetBattleGround();
    if (!bg || bg->GetStatus() != STATUS_IN_PROGRESS) return false;
    const bool alliance = bot->GetTeam() == ALLIANCE;
    std::array<policy::Node, 5> nodes;
    for (unsigned n = 0; n < nodes.size(); ++n)
    {
        if (bg->IsActiveEvent(n, alliance ? BG_AB_NODE_STATUS_ALLY_OCCUPIED : BG_AB_NODE_STATUS_HORDE_OCCUPIED)) nodes[n] = policy::Node::Ours;
        else if (bg->IsActiveEvent(n, alliance ? BG_AB_NODE_STATUS_ALLY_CONTESTED : BG_AB_NODE_STATUS_HORDE_CONTESTED)) nodes[n] = policy::Node::OurAssault;
        else if (bg->IsActiveEvent(n, alliance ? BG_AB_NODE_STATUS_HORDE_CONTESTED : BG_AB_NODE_STATUS_ALLY_CONTESTED)) nodes[n] = policy::Node::EnemyAssault;
        else if (bg->IsActiveEvent(n, BG_AB_NODE_STATUS_NEUTRAL)) nodes[n] = policy::Node::Neutral;
        else nodes[n] = policy::Node::Theirs;
    }
    unsigned count;
    const unsigned slot = BattlegroundTeamSlot(bot, count);
    // Native GetStartTime includes the two-minute pre-match countdown.
    const unsigned elapsed = bg->GetStartTime() > BG_START_DELAY_2M ? bg->GetStartTime() - BG_START_DELAY_2M : 0;
    const unsigned selected = policy::Arathi(slot, count, alliance, elapsed, nodes);
    // Resolve a registered banner each time; never retain a GameObject pointer
    // across matches or despawn/replacement of a captured flag.
    GameObject* banner = nullptr;
    for (unsigned state = 0; state <= BG_AB_NODE_STATUS_HORDE_OCCUPIED; ++state)
        if (bg->IsActiveEvent(selected, state))
            banner = bot->GetMap()->GetGameObject(bg->GetSingleGameObjectGuid(selected, state));
    if (!banner) banner = bot->GetMap()->GetGameObject(bg->GetSingleGameObjectGuid(selected, BG_AB_NODE_STATUS_NEUTRAL));
    if (!banner) return false;
    AI_VALUE(PositionMap&, "position")["bg objective"].Set(banner->GetPositionX(), banner->GetPositionY(), banner->GetPositionZ(), bot->GetMapId());
    return true;
}

bool BGTactics::SelectClassicAlteracObjective(WorldLocation& location)
{
    BattleGround* bg = bot->GetBattleGround();
    if (!bg || bg->GetStatus() != STATUS_IN_PROGRESS) return false;
    const bool alliance = bot->GetTeam() == ALLIANCE;
    struct NodeLocation { unsigned node; const char* name; };
    const NodeLocation allianceTowers[] = {
        {BG_AV_NODES_ICEBLOOD_TOWER, "AV_ICEBLOOD_TOWER"}, {BG_AV_NODES_TOWER_POINT, "AV_TOWERPOINT"},
        {BG_AV_NODES_FROSTWOLF_ETOWER, "AV_EAST_FROSTWOLF_TOWER"}, {BG_AV_NODES_FROSTWOLF_WTOWER, "AV_WEST_FROSTWOLF_TOWER"}};
    const NodeLocation hordeTowers[] = {
        {BG_AV_NODES_STONEHEART_BUNKER, "AV_STONEHEART_BUNKER"}, {BG_AV_NODES_ICEWING_BUNKER, "AV_ICEWING_BUNKER"},
        {BG_AV_NODES_DUNBALDAR_SOUTH, "AV_DUNBALDAR_SOUTH"}, {BG_AV_NODES_DUNBALDAR_NORTH, "AV_DUNBALDAR_NORTH"}};
    const NodeLocation allianceGraves[] = {
        {BG_AV_NODES_ICEBLOOD_GRAVE, "AV_ICEBLOOD_GRAVEYARD"}, {BG_AV_NODES_FROSTWOLF_GRAVE, "AV_FROSTWOLF_GRAVEYARD"},
        {BG_AV_NODES_FROSTWOLF_HUT, "AV_FROSTWOLF_RELIEF_HUT"}};
    const NodeLocation hordeGraves[] = {
        {BG_AV_NODES_STONEHEART_GRAVE, "AV_STONEHEART_GRAVEYARD"}, {BG_AV_NODES_STORMPIKE_GRAVE, "AV_STORMPIKE_GRAVEYARD"},
        {BG_AV_NODES_FIRSTAID_STATION, "AV_STORMPIKE_AID_STATION"}};
    const NodeLocation* towers = alliance ? allianceTowers : hordeTowers;
    const NodeLocation* graves = alliance ? allianceGraves : hordeGraves;
    const NodeLocation* homeTowers = alliance ? hordeTowers : allianceTowers;
    const NodeLocation* homeGraves = alliance ? hordeGraves : allianceGraves;
    auto resolve = [&](const NodeLocation& node) {
        // Use the live clickable flag, including its actual floor in bunkers.
        for (unsigned state = 0; state <= BG_AV_NODE_STATUS_NEUTRAL_OCCUPIED; ++state)
            if (bg->IsActiveEvent(node.node, state))
                if (GameObject* go = bot->GetMap()->GetGameObject(bg->GetSingleGameObjectGuid(node.node, state)))
                {
                    // An event can return its decorative roof banner first.
                    // That is not the clickable flag and may be a floor higher.
                    if (go->GetGOInfo()->GetLockId() == 1479)
                    {
                        location = WorldLocation(go->GetMapId(), go->GetPosition());
                        return true;
                    }
                }
        return sRandomPlayerbotMgr.GetNamedLocation(node.name, location);
    };
    unsigned count;
    const unsigned slot = BattlegroundTeamSlot(bot, count);
    const unsigned towerSquad = policy::TowerSquadSize(count);
    const unsigned defenders = count >= 20 ? 3 : (count >= 8 ? 1 : 0);
    std::array<policy::Node, 4> towerStates;
    for (unsigned i = 0; i < 4; ++i) towerStates[i] = AvState(bg, towers[i].node, alliance, true);

    // A small relief group handles counter-captures. Offensive squads don't
    // all turn around when a single home flag is attacked.
    if (slot >= count - defenders)
    {
        std::vector<NodeLocation> threatened;
        for (unsigned i = 0; i < 4; ++i)
            if (AvState(bg, homeTowers[i].node, alliance) == policy::Node::EnemyAssault) threatened.push_back(homeTowers[i]);
        for (unsigned i = 0; i < 3; ++i)
            if (AvState(bg, homeGraves[i].node, alliance) == policy::Node::EnemyAssault) threatened.push_back(homeGraves[i]);
        if (!threatened.empty()) return resolve(threatened[(slot - (count - defenders)) % threatened.size()]);
    }

    if (policy::GeneralReady(towerStates, AvState(bg, graves[2].node, alliance)))
    {
        Creature* general = bot->GetMap()->GetCreature(bg->GetSingleCreatureGuid(alliance ? BG_AV_BOSS_H : BG_AV_BOSS_A, 0));
        if (general && general->IsAlive())
        {
            location = WorldLocation(general->GetMapId(), general->GetPosition());
            return true;
        }
    }

    // Keep the small tower squad together for the assault. Leave one guard
    // at each pending tower while the rest advance; do not begin as fragile
    // three-player teams with no guarantee of a healer in either group.
    if (slot < towerSquad)
    {
        for (unsigned i = 0; i < 4; ++i)
        {
            if (towerStates[i] == policy::Node::Destroyed) continue;
            if (towerStates[i] == policy::Node::OurAssault && slot != i % towerSquad) continue;
            return resolve(towers[i]);
        }
        // Reinforce a pending capture if every tower is already assaulted.
        for (unsigned i = 0; i < 4; ++i)
            if (towerStates[i] != policy::Node::Destroyed) return resolve(towers[i]);
    }

    // Main force progresses down the graveyard chain. Keep a pair at each
    // pending capture instead of parking the entire offensive raid there.
    unsigned pending = 0;
    for (unsigned i = 0; i < 3; ++i)
    {
        const auto state = AvState(bg, graves[i].node, alliance);
        if (state == policy::Node::Ours) continue;
        if (state == policy::Node::OurAssault)
        {
            if (slot >= towerSquad + pending * 2 && slot < towerSquad + pending * 2 + 2) return resolve(graves[i]);
            ++pending;
            continue;
        }
        return resolve(graves[i]);
    }

    // Once the forward resurrection chain is secure, help finish towers;
    // do not divert the army to mines or fight unrelated players on roads.
    std::vector<unsigned> unfinished;
    for (unsigned i = 0; i < 4; ++i)
        if (towerStates[i] != policy::Node::Destroyed) unfinished.push_back(i);
    if (!unfinished.empty()) return resolve(towers[unfinished[(slot / 3) % unfinished.size()]]);
    return resolve(graves[2]);
}

bool BGTactics::MoveToClassicAlteracApproach(PositionEntry objective)
{
    BattleGround* bg = bot->GetBattleGround();
    if (!bg || ActualBattlegroundType(bot) != BATTLEGROUND_AV || bg->GetStatus() != STATUS_IN_PROGRESS ||
        !bot->IsAlive() || bot->IsBeingTeleported() || bot->IsNonMeleeSpellCasted(false, false, true) ||
        ai->HasRealPlayerMaster() || !objective.isSet() || objective.mapId != bot->GetMapId()) return false;
    policy::ApproachPoint next;
    if (!policy::AlteracApproach(bot->GetTeam() == ALLIANCE, bg->GetInstanceId(), classicAvCrossingInstance,
        classicAvCrossingStep, bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ(), objective.x, next)) return false;
    // Do not replace the actual objective: targeting/capture decisions must
    // continue to refer to its banner, not to an intermediate travel point.
    return MoveTo(bot->GetMapId(), next.x, next.y, next.z);
}

bool BGTactics::CheckClassicBanner()
{
    BattleGround* bg = bot->GetBattleGround();
    const auto type = ActualBattlegroundType(bot);
    if (!bg || (type != BATTLEGROUND_AB && type != BATTLEGROUND_AV) || bg->GetStatus() != STATUS_IN_PROGRESS ||
        !bot->IsInWorld() || bot->IsBeingTeleported() || !bot->CanUseBattleGroundObject() ||
        bot->IsNonMeleeSpellCasted(false, false, true)) return false;
    GameObject* best = nullptr;
    float bestDistance = 26.0f;
    for (const ObjectGuid& guid : AI_VALUE(std::list<ObjectGuid>, "bg banners"))
    {
        GameObject* go = ai->GetGameObject(guid);
        if (!go || !go->IsSpawned() || go->IsInUse() || go->GetGoState() != GO_STATE_READY) continue;
        // Event nodes also contain visual objects; only the native BG banner
        // lock (1479) accepts the capture spell.
        if (go->GetGOInfo()->GetLockId() != 1479) continue;
        const auto& event = bot->GetMap()->GetMapDataContainer().GetGameObjectEventIndex(go->GetDbGuid());
        const bool alliance = bot->GetTeam() == ALLIANCE;
        bool eligible = false;
        if (type == BATTLEGROUND_AB && event.event1 < BG_AB_MAX_NODES)
            eligible = event.event2 == BG_AB_NODE_STATUS_NEUTRAL || event.event2 == (alliance ? BG_AB_NODE_STATUS_HORDE_OCCUPIED : BG_AB_NODE_STATUS_ALLY_OCCUPIED) ||
                event.event2 == (alliance ? BG_AB_NODE_STATUS_HORDE_CONTESTED : BG_AB_NODE_STATUS_ALLY_CONTESTED);
        if (type == BATTLEGROUND_AV && event.event1 < BG_AV_MAX_NODES)
            eligible = event.event2 == BG_AV_NODE_STATUS_NEUTRAL_OCCUPIED ||
                event.event2 == (alliance ? BG_AV_NODE_STATUS_HORDE_OCCUPIED : BG_AV_NODE_STATUS_ALLY_OCCUPIED) ||
                event.event2 == (alliance ? BG_AV_NODE_STATUS_HORDE_CONTESTED : BG_AV_NODE_STATUS_ALLY_CONTESTED);
        if (!eligible || !bg->IsActiveEvent(event.event1, event.event2)) continue;
        const float distance = bot->GetDistance(go);
        if (distance < bestDistance) { best = go; bestDistance = distance; }
    }
    if (!best) return false;
    // Only defer to a teammate casting on THIS flag; a cast at another node
    // must not suppress capture here. Do not move away while guarding a cast.
    for (const auto& member : bg->GetPlayers())
        if (Player* player = bg->GetBgMap()->GetPlayer(member.first))
            if (player != bot && player->GetTeam() == bot->GetTeam() && player->IsAlive())
                if (Spell* spell = player->GetCurrentSpell(CURRENT_GENERIC_SPELL))
                    if (spell->m_targets.getGOTargetGuid() == best->GetObjectGuid()) return false;
    if (!bot->IsWithinDistInMap(best, INTERACTION_DISTANCE - 1.0f))
    {
        // Do not leave a fight to approach a banner; handle nearby threats.
        if (bot->IsInCombat()) return false;
        return MoveTo(bot->GetMapId(), best->GetPositionX(), best->GetPositionY(), best->GetPositionZ());
    }
    // Match the player's native capture cast. Spell::CheckCast/CheckRange
    // validate this game-object interaction; their unit-target LOS rule does
    // not apply to banners. An extra bot-only LOS gate strands bots beside
    // valid tower flags whose placed model intersects the tower geometry.
    if (bot->IsMounted()) ai->Unmount();
    if (bot->IsInDisallowedMountForm()) ai->RemoveShapeshift();
    // Banner opening is a native BG spell, not a learned lockpicking skill.
    // GetSpellForLock searches the player's spellbook and can reject valid
    // neutral banners. SpellStart still performs normal lock/capture checks.
    const SpellEntry* info = sServerFacade.LookupSpellInfo(SPELL_CAPTURE_BANNER);
    if (!info) return false;
    ai->StopMoving();
    Spell* spell = new Spell(bot, info, false);
    spell->m_targets.setGOTarget(best);
    if (spell->SpellStart(&spell->m_targets) != SPELL_CAST_OK) return false;
    ai->WaitForSpellCast(spell);
    return true;
}

bool ai::ShouldEngageBattlegroundTarget(PlayerbotAI* ai, Unit* target)
{
    Player* bot = ai->GetBot();
    const auto type = ActualBattlegroundType(bot);
    if ((type != BATTLEGROUND_AB && type != BATTLEGROUND_AV) || ai->HasRealPlayerMaster()) return true;
    if (!target || !target->IsAlive() || !target->IsInMap(bot)) return false;
    AiObjectContext* context = ai->GetAiObjectContext();
    PositionEntry objective = AI_VALUE(PositionMap&, "position")["bg objective"];
    if (!objective.isSet() || objective.mapId != bot->GetMapId()) return true;
    // Defend yourself/nearby teammates and fight through blockers. Do not
    // acquire a distant player solely because the player is visible.
    if (Unit* victim = target->GetVictim())
        if (bot->IsWithinDistInMap(target, 40.0f) && (victim == bot ||
            (victim->IsInMap(bot) && sServerFacade.IsFriendlyTo(victim, bot) && bot->IsWithinDistInMap(victim, 20.0f)))) return true;
    if (bot->IsWithinDistInMap(target, 15.0f)) return true;
    return sqrt(bot->GetDistance(objective.x, objective.y, objective.z, DIST_CALC_NONE)) < 45.0f &&
        sqrt(target->GetDistance(objective.x, objective.y, objective.z, DIST_CALC_NONE)) < 40.0f;
}

bool ai::ShouldAdvanceBattlegroundObjective(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    const auto type = ActualBattlegroundType(bot);
    if ((type != BATTLEGROUND_AB && type != BATTLEGROUND_AV) || ai->HasRealPlayerMaster() || !bot->IsAlive()) return false;
    AiObjectContext* context = ai->GetAiObjectContext();
    PositionEntry objective = AI_VALUE(PositionMap&, "position")["bg objective"];
    if (!objective.isSet() || objective.mapId != bot->GetMapId() || sqrt(bot->GetDistance(objective.x, objective.y, objective.z, DIST_CALC_NONE)) < 4.0f) return false;
    for (const ObjectGuid& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
        if (ShouldEngageBattlegroundTarget(ai, ai->GetUnit(guid))) return false;
    return true;
}
