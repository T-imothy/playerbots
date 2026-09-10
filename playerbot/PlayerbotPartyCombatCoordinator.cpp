#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotPartyCombatCoordinator.h"
#include "playerbot/strategy/values/ItemUsageValue.h"
#include "playerbot/strategy/values/LootValues.h"
#include "playerbot/AiFactory.h"
#include "playerbot/strategy/Action.h"
#include "playerbot/strategy/actions/ChangeTalentsAction.h"
#include "playerbot/strategy/actions/GenericSpellActions.h"
#include "playerbot/RandomPlayerbotMgr.h"

#include "Chat/Chat.h"
#include "Entities/Pet.h"
#include "Entities/Player.h"
#include "Entities/Unit.h"
#include "Globals/ObjectAccessor.h"
#include "Groups/Group.h"
#include "Server/WorldSession.h"
#include "World/World.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>

using namespace ai;

namespace
{
    const int32 kPersistentSpecSeconds = 10 * 365 * 24 * 60 * 60;

    bool ReadBool(const std::string& json, const char* name, bool fallback)
    {
        const std::string needle = std::string("\"") + name + "\"";
        size_t p = json.find(needle);
        if (p == std::string::npos || (p = json.find(':', p)) == std::string::npos) return fallback;
        std::string tail = json.substr(p + 1, 8);
        return tail.find("true") != std::string::npos ? true : tail.find("false") != std::string::npos ? false : fallback;
    }

    uint32 ReadUInt(const std::string& json, const char* name, uint32 fallback)
    {
        const std::string needle = std::string("\"") + name + "\"";
        size_t p = json.find(needle);
        if (p == std::string::npos || (p = json.find(':', p)) == std::string::npos) return fallback;
        while (++p < json.size() && !std::isdigit((unsigned char)json[p])) {}
        return p < json.size() ? (uint32)std::strtoul(json.c_str() + p, NULL, 10) : fallback;
    }

    std::string ReadString(const std::string& json, const char* name, const std::string& fallback)
    {
        const std::string needle = std::string("\"") + name + "\"";
        size_t p = json.find(needle);
        if (p == std::string::npos || (p = json.find(':', p)) == std::string::npos ||
            (p = json.find('"', p)) == std::string::npos) return fallback;
        size_t e = json.find('"', p + 1);
        return e == std::string::npos ? fallback : json.substr(p + 1, e - p - 1);
    }

    bool IsRealPlayer(Player* player) { return player && !player->GetPlayerbotAI(); }
}

PlayerbotPartyCombatCoordinator& PlayerbotPartyCombatCoordinator::instance()
{
    static PlayerbotPartyCombatCoordinator singleton;
    return singleton;
}

PlayerbotPartyCombatCoordinator::PlayerbotPartyCombatCoordinator() {}

const char* PlayerbotPartyCombatCoordinator::RoleName(LivingPartyRole role)
{
    switch (role) { case LivingPartyRole::Tank: return "tank"; case LivingPartyRole::Healer: return "healer";
        case LivingPartyRole::Damage: return "damage"; default: return "auto"; }
}

const char* PlayerbotPartyCombatCoordinator::PhaseName(LivingPartyPhase phase)
{
    switch (phase) { case LivingPartyPhase::Armed: return "armed"; case LivingPartyPhase::Pulling: return "pulling";
        case LivingPartyPhase::Stabilizing: return "stabilizing"; case LivingPartyPhase::Engaged: return "engaged";
        case LivingPartyPhase::Recovering: return "recovering"; default: return "idle"; }
}

void PlayerbotPartyCombatCoordinator::ReloadPolicy() const
{
    time_t now = time(NULL);
    if (now - lastPolicyLoad < 5) return;
    lastPolicyLoad = now;
    const char* configured = std::getenv("LIVING_WOW_PARTY_COMBAT_CONFIG");
    std::ifstream input(configured && *configured ? configured : "/srv/living-wow/config/party-combat.json");
    if (!input.good()) return;
    std::stringstream buffer; buffer << input.rdbuf(); const std::string json = buffer.str();
    policy.mode = ReadString(json, "mode", policy.mode);
    policy.engagementGating = ReadBool(json, "engagementGating", policy.engagementGating);
    policy.threatThrottling = ReadBool(json, "threatThrottling", policy.threatThrottling);
    policy.healerDuty = ReadBool(json, "healingDuty", policy.healerDuty);
    policy.tacticalRules = ReadBool(json, "tacticalRules", policy.tacticalRules);
    policy.addonTelemetry = ReadBool(json, "addonTelemetry", policy.addonTelemetry);
    policy.manaAssistance = ReadBool(json, "manaAssistance", policy.manaAssistance);
    policy.humanFirstLoot = ReadBool(json, "humanFirstLoot", policy.humanFirstLoot);
    policy.roleStrategySync = ReadBool(json, "roleStrategySync", policy.roleStrategySync);
    policy.roleAwareTactics = ReadBool(json, "roleAwareTactics", policy.roleAwareTactics);
    policy.equipmentLootNeed = ReadBool(json, "equipmentUpgradeNeed", policy.equipmentLootNeed);
    policy.professionLootNeed = ReadBool(json, "professionNeed", policy.professionLootNeed);
    policy.questLootNeed = ReadBool(json, "questNeed", policy.questLootNeed);
    policy.announceLootNeed = ReadBool(json, "announceNeedReason", policy.announceLootNeed);
    policy.stabilizeMilliseconds = ReadUInt(json, "stabilizeMilliseconds", policy.stabilizeMilliseconds);
    policy.maximumHoldMilliseconds = ReadUInt(json, "maximumHoldMilliseconds", policy.maximumHoldMilliseconds);
    policy.softThreatPercent = ReadUInt(json, "softThreatPercent", policy.softThreatPercent);
    policy.hardThreatPercent = ReadUInt(json, "hardThreatPercent", policy.hardThreatPercent);
    policy.resumeThreatPercent = ReadUInt(json, "resumeThreatPercent", policy.resumeThreatPercent);
    policy.emergencyHealthPercent = ReadUInt(json, "emergencyHealthPercent", policy.emergencyHealthPercent);
    policy.tankHealPercent = ReadUInt(json, "tankHealPercent", policy.tankHealPercent);
    policy.partyHealPercent = ReadUInt(json, "partyHealPercent", policy.partyHealPercent);
    policy.hotHealthPercent = ReadUInt(json, "hotHealthPercent", policy.hotHealthPercent);
    policy.manaReservePercent = ReadUInt(json, "manaReservePercent", policy.manaReservePercent);
    policy.maximumOverhealPercent = ReadUInt(json, "maximumOverhealPercent", policy.maximumOverhealPercent);
    policy.combatManaRegenPercent = ReadUInt(json, "combatManaRegenPercent", policy.combatManaRegenPercent);
    policy.combatCastingRegenFloorPercent = ReadUInt(json, "combatCastingRegenFloorPercent", policy.combatCastingRegenFloorPercent);
    policy.aoeMinimumTargets = ReadUInt(json, "aoeMinimumTargets", policy.aoeMinimumTargets);
    policy.ccPriorityTargets = ReadUInt(json, "ccPriorityTargets", policy.ccPriorityTargets);
    policy.outOfCombatManaRegenPercent = ReadUInt(json, "outOfCombatManaRegenPercent", policy.outOfCombatManaRegenPercent);
    policy.humanRollSafetySeconds = ReadUInt(json, "humanRollSafetySeconds", policy.humanRollSafetySeconds);
    policy.telemetryMilliseconds = ReadUInt(json, "telemetryMilliseconds", policy.telemetryMilliseconds);
}

bool PlayerbotPartyCombatCoordinator::IsMixedGroup(Group* group) const
{
    if (!group) return false;
    bool human = false, bot = false;
    Group::MemberSlotList const& slots = group->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid)) (p->GetPlayerbotAI() ? bot : human) = true;
    return human && bot;
}

Player* PlayerbotPartyCombatCoordinator::FindMember(Group* group, ObjectGuid guid) const
{
    return group ? sObjectAccessor.FindPlayer(guid) : NULL;
}

Player* PlayerbotPartyCombatCoordinator::FindMember(Group* group, const std::string& name) const
{
    if (!group) return NULL;
    std::string wanted = name; std::transform(wanted.begin(), wanted.end(), wanted.begin(), ::tolower);
    Group::MemberSlotList const& slots = group->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid)) { std::string n = p->GetName(); std::transform(n.begin(), n.end(), n.begin(), ::tolower); if (n == wanted) return p; }
    return NULL;
}

bool PlayerbotPartyCombatCoordinator::IsLeader(Player* player) const
{
    return player && player->GetGroup() && player->GetGroup()->GetLeaderGuid() == player->GetObjectGuid();
}

bool PlayerbotPartyCombatCoordinator::HasShield(Player* member) const
{
    if (!member) return false;
    Item* item = member->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND);
    return item && item->GetProto() && item->GetProto()->InventoryType == INVTYPE_SHIELD;
}

bool PlayerbotPartyCombatCoordinator::HasHealingSpell(Player* member) const
{
    if (!member) return false;
    PlayerSpellMap const& spells = member->GetSpellMap();
    for (PlayerSpellMap::const_iterator i = spells.begin(); i != spells.end(); ++i)
        if (!i->second.disabled && i->second.state != PLAYERSPELL_REMOVED)
            if (SpellEntry const* entry = sSpellTemplate.LookupEntry<SpellEntry>(i->first))
                if (PlayerbotAI::IsHealSpell(entry)) return true;
    return false;
}

LivingPartyRoleState PlayerbotPartyCombatCoordinator::InferRole(Player* member, const GroupState& state) const
{
    LivingPartyRoleState result;
    std::map<ObjectGuid, LivingPartyRole>::const_iterator forced = state.overrides.find(member->GetObjectGuid());
    if (forced != state.overrides.end() && forced->second != LivingPartyRole::Auto)
    { result.primary = forced->second; result.source = "explicit"; result.locked = true; return result; }
    if ((member->getClass() == CLASS_WARRIOR || member->getClass() == CLASS_PALADIN) && HasShield(member))
    { result.primary = LivingPartyRole::Tank; result.secondary = LivingPartyRole::Damage; result.source = "equipment"; return result; }
    if (member->GetLevel() >= 10)
    {
        BotRoles roles = AiFactory::GetPlayerRoles(member);
        if (roles & BOT_ROLE_TANK) { result.primary = LivingPartyRole::Tank; result.secondary = LivingPartyRole::Damage; result.source = "talents"; return result; }
        if (roles & BOT_ROLE_HEALER) { result.primary = LivingPartyRole::Healer; result.secondary = LivingPartyRole::Damage; result.source = "talents"; return result; }
    }
    if (HasHealingSpell(member) && (member->getClass() == CLASS_DRUID || member->getClass() == CLASS_PRIEST ||
        member->getClass() == CLASS_SHAMAN || member->getClass() == CLASS_PALADIN))
    { result.primary = LivingPartyRole::Healer; result.secondary = LivingPartyRole::Damage; result.source = "abilities"; return result; }
    result.primary = LivingPartyRole::Damage; result.source = "class"; return result;
}

void PlayerbotPartyCombatCoordinator::RefreshRoles(Group* group, GroupState& state) const
{
    state.roles.clear(); state.tank.Clear(); state.healer.Clear();
    Group::MemberSlotList const& slots = group->GetMemberSlots();
    uint32 onlineMembers = 0;
    uint32 lockedHealers = 0;
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid))
        {
            LivingPartyRoleState role = InferRole(p, state);
            state.roles[p->GetObjectGuid()] = role;
            ++onlineMembers;
            if (role.primary == LivingPartyRole::Healer && role.locked) ++lockedHealers;
        }

    // Automatic composition uses one healer per five members. Additional
    // healer-capable characters remain damage/support unless the leader
    // explicitly assigns another healer.
    const uint32 desiredHealers = std::max<uint32>(1, (onlineMembers + 4) / 5);
    uint32 automaticHealers = desiredHealers > lockedHealers ? desiredHealers - lockedHealers : 0;
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid))
        {
            LivingPartyRoleState& role = state.roles[p->GetObjectGuid()];
            if (role.primary == LivingPartyRole::Healer && !role.locked)
            {
                if (automaticHealers) --automaticHealers;
                else
                {
                    role.primary = LivingPartyRole::Damage;
                    role.secondary = LivingPartyRole::Healer;
                    role.source = role.source == "talents" ? "talent_support" : "ability_support";
                }
            }
            if (role.primary == LivingPartyRole::Tank && state.tank.IsEmpty()) state.tank = p->GetObjectGuid();
            if (role.primary == LivingPartyRole::Healer && state.healer.IsEmpty()) state.healer = p->GetObjectGuid();
        }
    if (state.tank.IsEmpty()) state.tank = group->GetLeaderGuid();
    if (state.puller.IsEmpty() || !FindMember(group, state.puller)) state.puller = state.tank;
    state.humanLeader = IsRealPlayer(sObjectAccessor.FindPlayer(group->GetLeaderGuid()));
    ++state.revision;
}

std::string PlayerbotPartyCombatCoordinator::ApplyRoleTalents(Player* member, LivingPartyRole role) const
{
    if (!member || !member->GetPlayerbotAI()) return "completed";
    if (role == LivingPartyRole::Auto || member->GetLevel() < 10) return "completed";
    if (member->IsInCombat() || !member->IsAlive() || member->IsTaxiFlying() || member->InBattleGround() ||
        (member->GetMap() && member->GetMap()->IsDungeon()))
        return "respec_unsafe_now";

    BotRoles desired = role == LivingPartyRole::Tank ? BOT_ROLE_TANK :
        role == LivingPartyRole::Healer ? BOT_ROLE_HEALER : BOT_ROLE_DPS;
    if (!ChangeTalentsAction::HasPremadeRole(member->getClass(), desired))
        return "role_not_supported_by_class";

    // A leader role assignment is an explicit party-scoped preference. Clear
    // the old path before selecting so AutoSelectTalents cannot continue a
    // contradictory build, and reset at no cost as bots do not use trainers.
    sRandomPlayerbotMgr.SetValue(member->GetGUIDLow(), "specNo", 0, "", kPersistentSpecSeconds);
    sRandomPlayerbotMgr.SetValue(member->GetGUIDLow(), "specLink", 0, "", kPersistentSpecSeconds);
    member->resetTalents(true);
    std::ostringstream details;
    ChangeTalentsAction::AutoSelectTalents(member, &details, desired);
    PlayerbotAI* memberAi = member->GetPlayerbotAI();
    memberAi->DoSpecificAction("auto learn spell");
    memberAi->UpdateTalentSpec();

    // Talent assignment alone does not replace the combat engine that was
    // built from the previous specialization.  Rebuild from the newly applied
    // spec so a restoration assignment cannot keep enhancement/feral melee
    // strategies.  Do not reload persisted strategy toggles from the old role.
    if (policy.roleStrategySync)
        memberAi->RequestStrategyReset(false);

    const uint32 freePoints = member->GetFreeTalentPoints();
    const uint32 totalPoints = member->CalculateTalentsPoints();
    const std::string specName = ChangeTalentsAction::GetPremadeSpecName(member);
    sLog.outString("Living WoW role respec bot=%u name=%s role=%s spec=%s used=%u free=%u",
        member->GetGUIDLow(), member->GetName(), RoleName(role), specName.c_str(),
        totalPoints >= freePoints ? totalPoints - freePoints : 0, freePoints);
    if (policy.roleStrategySync)
        sLog.outString("Living WoW role strategy synchronization queued bot=%u name=%s role=%s",
            member->GetGUIDLow(), member->GetName(), RoleName(role));
    return freePoints == 0 ? "completed" : "talent_assignment_incomplete";
}

bool PlayerbotPartyCombatCoordinator::RoleMatchesTalents(Player* member, LivingPartyRole role) const
{
    if (!member || member->GetLevel() < 10 || role == LivingPartyRole::Auto) return true;
    BotRoles desired = role == LivingPartyRole::Tank ? BOT_ROLE_TANK :
        role == LivingPartyRole::Healer ? BOT_ROLE_HEALER : BOT_ROLE_DPS;
    return (AiFactory::GetPlayerRoles(member) & desired) != 0;
}

void PlayerbotPartyCombatCoordinator::SynchronizeAutomaticRole(Player* bot, GroupState& state) const
{
    if (!bot || !bot->GetPlayerbotAI() || bot->GetLevel() < 10) return;
    std::map<ObjectGuid, LivingPartyRoleState>::const_iterator assigned = state.roles.find(bot->GetObjectGuid());
    if (assigned == state.roles.end() || assigned->second.locked ||
        RoleMatchesTalents(bot, assigned->second.primary))
        return;

    const uint32 now = WorldTimer::getMSTime();
    uint32& lastAttempt = lastAutomaticRoleTalentAttempt[bot->GetGUIDLow()];
    if (lastAttempt && WorldTimer::getMSTimeDiff(lastAttempt, now) < 5000) return;
    lastAttempt = now;

    const LivingPartyRole role = assigned->second.primary;
    const std::string outcome = ApplyRoleTalents(bot, role);
    sLog.outString("Living WoW automatic role sync bot=%u name=%s role=%s result=%s",
        bot->GetGUIDLow(), bot->GetName(), RoleName(role), outcome.c_str());
    if (outcome == "completed")
    {
        state.lastRoleSignature = 0;
        RefreshRoles(bot->GetGroup(), state);
    }
}

void PlayerbotPartyCombatCoordinator::SynchronizeRoleCombatStrategy(Player* bot, const GroupState& state) const
{
    if (!bot || !bot->GetPlayerbotAI()) return;
    std::map<ObjectGuid, LivingPartyRoleState>::const_iterator assigned = state.roles.find(bot->GetObjectGuid());
    const bool shouldUse = policy.mode == "active" && policy.roleAwareTactics &&
        assigned != state.roles.end() && assigned->second.primary == LivingPartyRole::Healer;
    const bool hasStrategy = bot->GetPlayerbotAI()->HasStrategy(
        "living party healer offdps", BotState::BOT_STATE_COMBAT);
    if (shouldUse == hasStrategy) return;

    bot->GetPlayerbotAI()->ChangeStrategy(
        shouldUse ? "+living party healer offdps" : "-living party healer offdps",
        BotState::BOT_STATE_COMBAT);
    sLog.outString("LivingParty healer filler bot=%u name=%s enabled=%u",
        bot->GetGUIDLow(), bot->GetName(), shouldUse ? 1 : 0);
}

void PlayerbotPartyCombatCoordinator::SynchronizeCrowdControlMarker(Player* bot, const GroupState& state) const
{
    if (!bot || !bot->GetPlayerbotAI() || policy.mode != "active" || !policy.roleAwareTactics)
        return;

    // Use the conventional TBC party marker assignments. The value feeds the
    // existing Playerbots RTI crowd-control target selection, so the class AI
    // still validates whether it knows and can use an appropriate CC spell.
    const char* marker = NULL;
    switch (bot->getClass())
    {
        case CLASS_MAGE: marker = "moon"; break;
        case CLASS_HUNTER: marker = "square"; break;
        case CLASS_ROGUE: marker = "triangle"; break;
        case CLASS_WARLOCK:
        case CLASS_PRIEST: marker = "diamond"; break;
        case CLASS_DRUID: marker = "moon"; break;
        default: break;
    }
    if (!marker) return;
    if (bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<std::string>("rti cc")->Get() != marker)
        bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<std::string>("rti cc")->Set(marker);
}

void PlayerbotPartyCombatCoordinator::SynchronizeHunterPetThreat(Player* bot, const GroupState* state) const
{
    if (!bot || bot->getClass() != CLASS_HUNTER) return;
    Pet* pet = bot->GetPet();
    if (!pet) return;

    bool hasTank = false;
    if (state)
        for (std::map<ObjectGuid, LivingPartyRoleState>::const_iterator i = state->roles.begin();
            i != state->roles.end(); ++i)
            if (i->second.primary == LivingPartyRole::Tank && FindMember(bot->GetGroup(), i->first))
            {
                hasTank = true;
                break;
            }

    static const uint32 growlRanks[] = {2649, 14916, 14917, 14918, 14919, 14920, 14921, 27047};
    const bool wasSuppressed = hunterGrowlSuppressed.count(bot->GetGUIDLow()) != 0;
    bool changed = false;
    if (hasTank)
    {
        for (uint32 i = 0; i < sizeof(growlRanks) / sizeof(growlRanks[0]); ++i)
        {
            const uint32 spellId = growlRanks[i];
            if (!pet->HasSpell(spellId)) continue;
            if (std::find(pet->m_autospells.begin(), pet->m_autospells.end(), spellId) != pet->m_autospells.end())
            {
                pet->ToggleAutocast(spellId, false);
                changed = true;
            }
        }
        if (changed) hunterGrowlSuppressed.insert(bot->GetGUIDLow());
    }
    else if (wasSuppressed)
    {
        // Restore only a Growl state that this coordinator disabled. Enable the
        // highest rank the current pet knows rather than overriding an owner or
        // prior Playerbots preference that was already off.
        for (int32 i = (int32)(sizeof(growlRanks) / sizeof(growlRanks[0])) - 1; i >= 0; --i)
            if (pet->HasSpell(growlRanks[i]))
            {
                if (std::find(pet->m_autospells.begin(), pet->m_autospells.end(), growlRanks[i]) == pet->m_autospells.end())
                    pet->ToggleAutocast(growlRanks[i], true);
                changed = true;
                break;
            }
        hunterGrowlSuppressed.erase(bot->GetGUIDLow());
    }

    if (changed)
        sLog.outString("Living WoW hunter pet threat bot=%u name=%s growl=%s tank_present=%u",
            bot->GetGUIDLow(), bot->GetName(), hasTank ? "disabled" : "restored", hasTank ? 1 : 0);
}

bool PlayerbotPartyCombatCoordinator::IsApprovedTarget(const GroupState& state, Unit* target) const
{
    return target && state.approvedTargets.find(target->GetObjectGuid()) != state.approvedTargets.end();
}

void PlayerbotPartyCombatCoordinator::RefreshMarkers(Group* group, GroupState& state) const
{
    ObjectGuid skull = group->GetTargetIcon(7), cross = group->GetTargetIcon(6);
    state.primaryTarget = skull;
    state.secondaryTarget = cross;
    state.crowdControlTargets.clear();
    // Moon, square, diamond, and triangle are protected CC slots. Markers
    // express priority, not permission to pull: only actual combat/threat
    // relationships enter approvedTargets.
    static const uint8 ccIcons[] = {4, 3, 2, 1};
    for (uint32 i = 0; i < sizeof(ccIcons) / sizeof(ccIcons[0]); ++i)
    {
        ObjectGuid target = group->GetTargetIcon(ccIcons[i]);
        if (!target.IsEmpty()) state.crowdControlTargets.insert(target);
    }
}

Unit* PlayerbotPartyCombatCoordinator::PreferredEngagedTarget(Player* bot, const GroupState& state) const
{
    if (!bot) return NULL;
    const ObjectGuid order[] = {state.primaryTarget, state.secondaryTarget};
    for (uint32 i = 0; i < sizeof(order) / sizeof(order[0]); ++i)
    {
        if (order[i].IsEmpty() || state.approvedTargets.find(order[i]) == state.approvedTargets.end())
            continue;
        Unit* target = sObjectAccessor.GetUnit(*bot, order[i]);
        if (target && target->IsAlive() && target->IsEnemy(bot)) return target;
    }
    return NULL;
}

void PlayerbotPartyCombatCoordinator::RefreshCombat(Group* group, GroupState& state) const
{
    const uint32 now = WorldTimer::getMSTime();
    bool combat = false;
    state.approvedTargets.clear();
    Group::MemberSlotList const& slots = group->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid))
        {
            if (p->IsInCombat()) combat = true;
            // CMSG_ATTACKSWING assigns a victim as soon as a human right-clicks.
            // Generic combat flags are insufficient: either participant may
            // already be fighting something else. Approve only a direct combat
            // relationship in which the creature has engaged the player, or
            // the player has generated real threat. Merely starting an
            // auto-attack must not authorize bots to pull the selected target.
            if (Unit* victim = p->GetVictim())
            {
                const bool victimAttackingPlayer =
                    p->getAttackers().find(victim) != p->getAttackers().end();
                const bool engaged = victimAttackingPlayer ||
                    victim->getThreatManager().getThreat(p) > 0.0f;
                if (engaged) state.approvedTargets.insert(victim->GetObjectGuid());
            }
            Unit::AttackerSet const& attackers = p->getAttackers();
            for (Unit::AttackerSet::const_iterator a = attackers.begin(); a != attackers.end(); ++a)
                if (*a) state.approvedTargets.insert((*a)->GetObjectGuid());
        }
    RefreshMarkers(group, state);
    if (policy.mode == "active" && policy.botLedAutoMark && !state.humanLeader && state.approvedTargets.size() > 1)
    {
        std::set<ObjectGuid>::const_iterator target = state.approvedTargets.begin();
        if (group->GetTargetIcon(7).IsEmpty()) { group->SetTargetIcon(7, *target); state.primaryTarget = *target; }
        ++target;
        if (target != state.approvedTargets.end() && group->GetTargetIcon(6).IsEmpty())
        { group->SetTargetIcon(6, *target); state.secondaryTarget = *target; }
    }
    LivingPartyPhase old = state.phase;
    if (combat)
    {
        state.lastCombatSeen = now;
        if (old == LivingPartyPhase::Idle || old == LivingPartyPhase::Armed || old == LivingPartyPhase::Recovering)
        { state.phase = LivingPartyPhase::Stabilizing; state.phaseSince = now; state.tankControlSince = 0; }
        else if (old == LivingPartyPhase::Stabilizing)
        {
            Player* tank = FindMember(group, state.tank);
            Unit* controlTarget = tank ? PreferredEngagedTarget(tank, state) : NULL;
            if (!controlTarget && tank && !state.approvedTargets.empty())
                controlTarget = sObjectAccessor.GetUnit(*tank, *state.approvedTargets.begin());
            const bool tankControls = tank && controlTarget &&
                controlTarget->GetVictim() == tank &&
                controlTarget->getThreatManager().getThreat(tank) > 0.0f;
            if (tankControls)
            {
                if (!state.tankControlSince) state.tankControlSince = now;
            }
            else state.tankControlSince = 0;

            const uint32 elapsed = WorldTimer::getMSTimeDiff(state.phaseSince, now);
            const bool stable = state.tankControlSince &&
                WorldTimer::getMSTimeDiff(state.tankControlSince, now) >= policy.stabilizeMilliseconds;
            if (stable || elapsed >= policy.maximumHoldMilliseconds)
                state.phase = LivingPartyPhase::Engaged;
        }
    }
    else if (old != LivingPartyPhase::Idle)
    {
        if (WorldTimer::getMSTimeDiff(state.lastCombatSeen, now) < 3000) state.phase = LivingPartyPhase::Recovering;
        else { state.phase = state.rules.empty() ? LivingPartyPhase::Idle : LivingPartyPhase::Armed; state.primaryTarget.Clear(); state.secondaryTarget.Clear(); }
    }
    if (old != state.phase) ++state.revision;
}

PlayerbotPartyCombatCoordinator::GroupState* PlayerbotPartyCombatCoordinator::EnsureState(Player* member) const
{
    if (!member || !IsMixedGroup(member->GetGroup())) return NULL;
    Group* group = member->GetGroup(); uint32 id = group->GetId(); GroupState& state = groups[id];
    state.groupId = id; state.lastSeen = WorldTimer::getMSTime();
    uint32 signature = group->GetLeaderGuid().GetCounter() ^ (uint32)state.overrides.size() * 2654435761u;
    Group::MemberSlotList const& slots = group->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid))
            signature ^= p->GetGUIDLow() + ((uint32)p->GetLevel() << 16) + ((uint32)p->getClass() << 24) + (HasShield(p) ? 0x40000000u : 0);
    if (state.roles.empty() || state.lastRoleSignature != signature)
    { state.lastRoleSignature = signature; RefreshRoles(group, state); }
    RefreshCombat(group, state); return &state;
}

void PlayerbotPartyCombatCoordinator::Update(Player* bot)
{
    ReloadPolicy(); GroupState* state = EnsureState(bot);
    if (!state)
    {
        SynchronizeHunterPetThreat(bot, NULL);
        return;
    }
    SynchronizeAutomaticRole(bot, *state);
    SynchronizeRoleCombatStrategy(bot, *state);
    SynchronizeCrowdControlMarker(bot, *state);
    SynchronizeHunterPetThreat(bot, state);

    // Keep every non-CC action on Skull while it is engaged, then Cross. This
    // updates the ordinary Playerbots current-target value; spell rotations,
    // movement, and threat calculation continue through their normal paths.
    if (Unit* priority = PreferredEngagedTarget(bot, *state))
    {
        Unit* current = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<Unit*>("current target")->Get();
        if (current != priority)
        {
            bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<Unit*>("current target")->Set(priority);
            bot->SetSelectionGuid(priority->GetObjectGuid());
        }
    }
    // Human-led bots intentionally do not load Playerbots' broad maintenance
    // strategy. Run the narrowly grounded quest-source action explicitly from
    // the mixed-party coordinator instead of relying on a trigger that does
    // not exist in this engine configuration.
    PlayerbotAI* maintenanceAi = bot->GetPlayerbotAI();
    Player* maintenanceMaster = maintenanceAi ? maintenanceAi->GetMaster() : nullptr;
    bool maintenancePositionStable = !bot->IsBeingTeleported() &&
        (!maintenanceMaster || !maintenanceMaster->IsInWorld() ||
            (bot->GetMapId() == maintenanceMaster->GetMapId() &&
                bot->GetInstanceId() == maintenanceMaster->GetInstanceId() &&
                bot->IsWithinDistInMap(maintenanceMaster, 15.0f)));
    bool pendingLoot = maintenanceAi &&
        (maintenanceAi->GetAiObjectContext()->GetValue<bool>("has available loot")->Get() ||
            !maintenanceAi->GetAiObjectContext()->GetValue<LootObject>("loot target")->Get().IsEmpty());
    uint32 now = WorldTimer::getMSTime();
    uint32& lastLootScan = lastPartyLootScan[bot->GetGUIDLow()];
    bool pendingRolls = maintenanceAi &&
        !maintenanceAi->GetAiObjectContext()->GetValue<LootRollMap>("active rolls")->Get().empty();
    // Resolve group rolls before driving corpse movement. Move-to-loot sets an
    // action duration and can otherwise repeatedly pre-empt the automatic roll
    // until the server timeout. Human-first policy is still enforced inside
    // AutoLootRollAction; a full bot will submit PASS rather than block.
    if (pendingRolls && bot->IsAlive() && !bot->IsInCombat() &&
        !bot->IsNonMeleeSpellCasted(false) &&
        (!lastLootScan || WorldTimer::getMSTimeDiff(lastLootScan, now) >= 250))
    {
        lastLootScan = now;
        bool rolled = maintenanceAi->CanDoSpecificAction("auto loot roll", true, true) &&
            maintenanceAi->DoSpecificAction("auto loot roll",
                Event("living mixed party loot roll"), true);
        pendingRolls = !maintenanceAi->GetAiObjectContext()->
            GetValue<LootRollMap>("active rolls")->Get().empty();
        if (rolled)
            sLog.outDetail("LivingParty loot roll submitted bot=%u name=%s remaining=%u",
                bot->GetGUIDLow(), bot->GetName(), pendingRolls ? 1u : 0u);

        if (pendingRolls)
        {
            LootObject selected = maintenanceAi->GetAiObjectContext()->
                GetValue<LootObject>("loot target")->Get();
            if (!selected.IsEmpty())
            {
                maintenanceAi->StopMoving();
                maintenanceAi->GetAiObjectContext()->GetValue<LootObject>("loot target")->
                    Set(LootObject());
            }
        }
    }
    // Random-bot loot discovery normally runs as a low-priority "often"
    // action. Mixed-party maintenance can starve both discovery and the later
    // select/move/open steps, leaving the human locked out of a corpse assigned
    // to a bot. Drive the existing validated actions in their normal order at
    // a bounded cadence; ownership, distance, movement, and bag checks remain
    // inside those standard Playerbots actions.
    if (maintenanceAi && maintenancePositionStable && !pendingRolls && bot->IsAlive() &&
        !bot->IsInCombat() && !bot->IsNonMeleeSpellCasted(false) &&
        (!lastLootScan || WorldTimer::getMSTimeDiff(lastLootScan, now) >= 1000))
    {
        lastLootScan = now;
        if (!pendingLoot && maintenanceAi->CanDoSpecificAction("add all loot", true, true))
        {
            maintenanceAi->DoSpecificAction("add all loot", Event("living mixed party loot scan"), true);
            pendingLoot =
                maintenanceAi->GetAiObjectContext()->GetValue<bool>("has available loot")->Get() ||
                !maintenanceAi->GetAiObjectContext()->GetValue<LootObject>("loot target")->Get().IsEmpty();
        }
        if (pendingLoot)
        {
            if (maintenanceAi->CanDoSpecificAction("loot", true, true))
                maintenanceAi->DoSpecificAction("loot", Event("living mixed party loot select"), true);

            bool moving = false;
            if (maintenanceAi->CanDoSpecificAction("move to loot", true, true))
                moving = maintenanceAi->DoSpecificAction("move to loot",
                    Event("living mixed party loot approach"), true);
            if (!moving && maintenanceAi->CanDoSpecificAction("open loot", true, true))
                maintenanceAi->DoSpecificAction("open loot",
                    Event("living mixed party loot open"), true);

            sLog.outDetail("LivingParty loot maintenance bot=%u name=%s moving=%s",
                bot->GetGUIDLow(), bot->GetName(), moving ? "yes" : "no");
        }
    }
    uint32& lastAttempt = lastQuestMaintenance[bot->GetGUIDLow()];
    // Loot/follow/combat work must win over opportunistic quest-source item
    // use.  A ten-second floor also prevents an unchanged usable item from
    // monopolising the non-combat engine when its spell reports success but
    // the quest objective cannot advance.
    if (maintenancePositionStable && !pendingLoot && bot->IsAlive() && !bot->IsInCombat() &&
        (!lastAttempt || WorldTimer::getMSTimeDiff(lastAttempt, now) >= 10000))
    {
        lastAttempt = now;
        PlayerbotAI* ai = bot->GetPlayerbotAI();
        if (ai && ai->CanDoSpecificAction("use random quest item", true, true))
        {
            bool used = ai->DoSpecificAction("use random quest item",
                // This is autonomous maintenance, not a direct player command.
                // Keep legacy use/target diagnostics out of party chat.
                Event("living mixed party quest maintenance"), true);
            sLog.outString("Living WoW party maintenance bot=%u name=%s action=quest_source_item result=%s",
                bot->GetGUIDLow(), bot->GetName(), used ? "executed" : "failed");
        }
    }
    if (policy.addonTelemetry && WorldTimer::getMSTimeDiff(state->lastTelemetry, WorldTimer::getMSTime()) >= policy.telemetryMilliseconds)
    { state->lastTelemetry = WorldTimer::getMSTime(); SendSnapshot(bot->GetGroup(), *state); }
}

LivingPartyRoleState PlayerbotPartyCombatCoordinator::GetRole(Player* member) const
{
    GroupState* state = EnsureState(member); if (!state) return LivingPartyRoleState();
    std::map<ObjectGuid, LivingPartyRoleState>::const_iterator i = state->roles.find(member->GetObjectGuid());
    return i == state->roles.end() ? LivingPartyRoleState() : i->second;
}

Unit* PlayerbotPartyCombatCoordinator::GetPreferredTarget(Player* bot) const
{
    GroupState* state = EnsureState(bot);
    return state ? PreferredEngagedTarget(bot, *state) : NULL;
}

uint8 PlayerbotPartyCombatCoordinator::ThreatPercent(Player* member, Unit* target, Player* tank) const
{
    if (!member || !target || !tank) return 0;
    float tankThreat = target->getThreatManager().getThreat(tank);
    float memberThreat = target->getThreatManager().getThreat(member);
    if (Pet* pet = member->GetPet())
        memberThreat += target->getThreatManager().getThreat(pet);
    return tankThreat > 0.0f ? (uint8)std::min(255.0f, memberThreat * 100.0f / tankThreat) : (member == tank && memberThreat > 0.0f ? 100 : 0);
}

bool PlayerbotPartyCombatCoordinator::CanInitiate(Player* bot, Unit* target) const
{
    ReloadPolicy(); if (policy.mode != "active" || !policy.engagementGating) return true;
    GroupState* state = EnsureState(bot); if (!state || !target) return true;
    for (std::vector<LivingPartyTacticalRule>::const_iterator rule = state->rules.begin(); rule != state->rules.end(); ++rule)
        if (rule->selectorType == "target" && rule->selectorId == target->GetGUIDLow() && rule->treatment == "do_not_attack") return false;
    if (IsApprovedTarget(*state, target)) return true;
    if (!state->puller.IsEmpty() && state->puller == bot->GetObjectGuid() &&
        (!state->humanLeader || state->pullerExplicit)) return true;
    return false;
}

float PlayerbotPartyCombatCoordinator::ActionMultiplier(Player* bot, Action* action) const
{
    ReloadPolicy(); if (!action || policy.mode != "active") return 1.0f;
    GroupState* state = EnsureState(bot); if (!state) return 1.0f;
    const std::string actionName = action->getName();
    if (!bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<LootRollMap>("active rolls")->Get().empty() &&
        (actionName == "greet" || actionName == "talk" || actionName == "suggest what to do" ||
            actionName == "suggest trade"))
        return 0.0f;
    Unit* target = action->GetTarget();
    // Friendly healing, cleansing, and protection are never subject to hostile
    // pull or DPS threat gates. Existing class strategies remain authoritative
    // for spell choice and emergency-heal timing.
    if (target && bot->CanAssist(target)) return 1.0f;
    // Target gating must precede threat classification. Hunter's Mark and
    // similar hostile setup actions are intentionally low threat, but they
    // still must not begin an unapproved pull in a human-led party.
    if (target && !CanInitiate(bot, target)) return 0.0f;
    const bool crowdControlAction = dynamic_cast<CastCrowdControlSpellAction*>(action) != NULL;
    if (target && !bot->CanAssist(target))
    {
        if (state->crowdControlTargets.count(target->GetObjectGuid()) && !crowdControlAction)
            return 0.0f;
        Unit* priority = PreferredEngagedTarget(bot, *state);
        if (priority && priority != target && !crowdControlAction)
            return 0.0f;
    }
    ActionThreatType threat = action->getThreatType();
    LivingPartyRoleState role = GetRole(bot);

    if (policy.roleAwareTactics)
    {
        // A healer assignment is a combat behavior contract, not just a UI
        // label.  Keep healers at casting range and reserve their action budget
        // whenever the tank or another member needs authoritative healing.
        if (role.primary == LivingPartyRole::Healer)
        {
            bool healingNeeded = false;
            bool emergency = false;
            Group::MemberSlotList const& slots = bot->GetGroup()->GetMemberSlots();
            for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
                if (Player* member = sObjectAccessor.FindPlayer(i->guid))
                {
                    if (!member->IsAlive() || !member->GetMaxHealth()) continue;
                    uint32 health = member->GetHealth() * 100 / member->GetMaxHealth();
                    emergency = emergency || health <= policy.emergencyHealthPercent;
                    const bool isTank = member->GetObjectGuid() == state->tank;
                    healingNeeded = healingNeeded ||
                        health <= (isTank ? policy.tankHealPercent : policy.partyHealPercent);
                }
            if (target && !bot->CanAssist(target) && (emergency || healingNeeded))
                return 0.0f;

            // Druid, shaman, and priest healers cast a cheap ranged filler
            // while the group is healthy. Once they reach the configured
            // healing reserve they stop spending mana and may use a weapon or
            // wand instead. Paladins retain their normal melee support style.
            const bool casterHealer = bot->getClass() == CLASS_DRUID ||
                bot->getClass() == CLASS_SHAMAN || bot->getClass() == CLASS_PRIEST;
            if (casterHealer && target && !bot->CanAssist(target))
            {
                const uint32 maximumMana = bot->GetMaxPower(POWER_MANA);
                const uint32 manaPercent = maximumMana ?
                    bot->GetPower(POWER_MANA) * 100 / maximumMana : 0;
                const bool weaponAction = actionName == "melee" || actionName == "reach melee" ||
                    actionName == "shoot";
                const bool offensiveSpell = dynamic_cast<CastSpellAction*>(action) != NULL;
                if (manaPercent > policy.manaReservePercent && weaponAction)
                    return 0.0f;
                if (manaPercent <= policy.manaReservePercent && offensiveSpell)
                    return 0.0f;
            }
        }

        // Offensive AoE is valuable only on a real multi-target encounter and
        // must never break damage-sensitive crowd control. Friendly AoE heals
        // returned above through the CanAssist path and are unaffected.
        if (threat == ActionThreatType::ACTION_THREAT_AOE &&
            role.primary != LivingPartyRole::Tank)
        {
            if (state->approvedTargets.size() < policy.aoeMinimumTargets)
                return 0.0f;
            for (std::set<ObjectGuid>::const_iterator i = state->crowdControlTargets.begin();
                i != state->crowdControlTargets.end(); ++i)
                if (state->approvedTargets.count(*i))
                    return 0.0f;
            for (std::set<ObjectGuid>::const_iterator i = state->approvedTargets.begin();
                i != state->approvedTargets.end(); ++i)
                if (Unit* engaged = sObjectAccessor.GetUnit(*bot, *i))
                    if (engaged != target && engaged->HasBreakableByDamageCrowdControlAura())
                        return 0.0f;
        }
    }
    if (threat == ActionThreatType::ACTION_THREAT_NONE || threat == ActionThreatType::ACTION_THREAT_LOW)
    {
        if (policy.roleAwareTactics &&
            crowdControlAction &&
            state->approvedTargets.size() >= policy.ccPriorityTargets)
            return 1.35f;
        return 1.0f;
    }
    if (role.primary == LivingPartyRole::Tank) return 1.0f;
    if (!policy.threatThrottling) return 1.0f;
    if (state->hold) return 0.0f;
    uint32 elapsed = WorldTimer::getMSTimeDiff(state->phaseSince, WorldTimer::getMSTime());
    if (state->phase == LivingPartyPhase::Stabilizing && elapsed < policy.maximumHoldMilliseconds)
        return elapsed < policy.stabilizeMilliseconds ? 0.0f : (threat == ActionThreatType::ACTION_THREAT_AOE ? 0.0f : 0.35f);
    Player* tank = FindMember(bot->GetGroup(), state->tank);
    uint8 pct = ThreatPercent(bot, target, tank);
    if (pct >= policy.hardThreatPercent)
    {
        state->threatSoftHeld.erase(bot->GetObjectGuid());
        if (state->threatHeld.insert(bot->GetObjectGuid()).second)
        {
            bot->AttackStop();
            if (Pet* pet = bot->GetPet()) pet->AttackStop();
            sLog.outString("LivingParty threat hard-hold bot=%s target=%u threat=%u action=%s",
                bot->GetName(), target ? target->GetGUIDLow() : 0, pct, action->getName().c_str());
        }
        return 0.0f;
    }
    if (state->threatHeld.count(bot->GetObjectGuid()))
    {
        if (pct > policy.resumeThreatPercent) return 0.0f;
        state->threatHeld.erase(bot->GetObjectGuid());
        sLog.outString("LivingParty threat resume bot=%s target=%u threat=%u",
            bot->GetName(), target ? target->GetGUIDLow() : 0, pct);
    }
    if (pct >= policy.softThreatPercent)
    {
        if (state->threatSoftHeld.insert(bot->GetObjectGuid()).second)
            sLog.outString("LivingParty threat soft-throttle bot=%s target=%u threat=%u action=%s",
                bot->GetName(), target ? target->GetGUIDLow() : 0, pct, action->getName().c_str());
        return threat == ActionThreatType::ACTION_THREAT_AOE ? 0.0f : 0.35f;
    }
    if (state->threatSoftHeld.erase(bot->GetObjectGuid()))
        sLog.outString("LivingParty threat normal bot=%s target=%u threat=%u",
            bot->GetName(), target ? target->GetGUIDLow() : 0, pct);
    return 1.0f;
}

float PlayerbotPartyCombatCoordinator::AdjustManaRegen(Player* member, bool recentCast, float currentRegen, float normalRegen) const
{
    ReloadPolicy();
    if (!member || !member->GetPlayerbotAI() || policy.mode != "active" || !policy.manaAssistance ||
        !IsMixedGroup(member->GetGroup()))
        return currentRegen;

    if (!member->IsInCombat())
        return currentRegen * policy.outOfCombatManaRegenPercent / 100.0f;

    float adjusted = currentRegen * policy.combatManaRegenPercent / 100.0f;
    if (recentCast)
        adjusted = std::max(adjusted, normalRegen * policy.combatCastingRegenFloorPercent / 100.0f);
    return adjusted;
}

bool PlayerbotPartyCombatCoordinator::ShouldDeferLootRoll(Player* bot, GroupLootRoll* roll) const
{
    ReloadPolicy();
    if (!bot || !roll || policy.mode != "active" || !policy.humanFirstLoot || !IsMixedGroup(bot->GetGroup()))
        return false;
    if (roll->GetEndTime() <= time(NULL) + policy.humanRollSafetySeconds)
        return false;

    Group::MemberSlotList const& slots = bot->GetGroup()->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* member = sObjectAccessor.FindPlayer(i->guid))
            if (member->isRealPlayer() && roll->GetPlayerVote(member->GetObjectGuid()) == ROLL_NOT_EMITED_YET)
                return true;
    return false;
}

bool PlayerbotPartyCombatCoordinator::HumanNeededLoot(Player* bot, GroupLootRoll* roll) const
{
    ReloadPolicy();
    if (!bot || !roll || !policy.humanFirstLoot || !IsMixedGroup(bot->GetGroup())) return false;
    Group::MemberSlotList const& slots = bot->GetGroup()->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* member = sObjectAccessor.FindPlayer(i->guid))
            if (member->isRealPlayer() && roll->GetPlayerVote(member->GetObjectGuid()) == ROLL_NEED)
                return true;
    return false;
}

bool PlayerbotPartyCombatCoordinator::BotCanNeedForUsage(ItemUsage usage) const
{
    ReloadPolicy();
    if (usage == ItemUsage::ITEM_USAGE_EQUIP) return policy.equipmentLootNeed;
    if (usage == ItemUsage::ITEM_USAGE_SKILL) return policy.professionLootNeed;
    if (usage == ItemUsage::ITEM_USAGE_QUEST) return policy.questLootNeed;
    return usage == ItemUsage::ITEM_USAGE_FORCE_NEED;
}

bool PlayerbotPartyCombatCoordinator::ShouldAnnounceLootNeed() const
{
    ReloadPolicy();
    return policy.mode == "active" && policy.humanFirstLoot && policy.announceLootNeed;
}

bool PlayerbotPartyCombatCoordinator::IsActiveMixedParty(Player* member) const
{
    ReloadPolicy();
    return member && policy.mode == "active" && IsMixedGroup(member->GetGroup());
}

std::vector<std::string> PlayerbotPartyCombatCoordinator::Fields(const std::string& message)
{
    std::vector<std::string> result; std::stringstream in(message); std::string field;
    while (std::getline(in, field, '\t')) result.push_back(field); return result;
}

std::string PlayerbotPartyCombatCoordinator::Escape(const std::string& value)
{
    std::string result; for (std::string::const_iterator i = value.begin(); i != value.end(); ++i)
        result += (*i == '\t' || *i == '\n' || *i == '\r') ? ' ' : *i; return result;
}

void PlayerbotPartyCombatCoordinator::SendAddon(Player* source, Player* target, const std::string& payload) const
{
    if (!source || !target || !target->GetSession()) return;
    WorldPacket data; ChatHandler::BuildChatPacket(data, CHAT_MSG_PARTY, payload.c_str(), LANG_ADDON,
        CHAT_TAG_NONE, source->GetObjectGuid(), source->GetName()); target->GetSession()->SendPacket(data);
}

void PlayerbotPartyCombatCoordinator::SendSnapshot(Group* group, GroupState& state) const
{
    Player* source = NULL; Group::MemberSlotList const& slots = group->GetMemberSlots();
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid)) if (p->GetPlayerbotAI() && (!source || p->GetObjectGuid() < source->GetObjectGuid())) source = p;
    if (!source) return;
    std::ostringstream head; head << "LWOWP1\tS\t" << state.revision << "\t" << PhaseName(state.phase) << "\t" << (state.hold ? 1 : 0);
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* receiver = sObjectAccessor.FindPlayer(i->guid)) if (IsRealPlayer(receiver) && state.addonClients.count(receiver->GetObjectGuid()))
        {
            SendAddon(source, receiver, head.str());
            for (Group::MemberSlotList::const_iterator m = slots.begin(); m != slots.end(); ++m)
                if (Player* member = sObjectAccessor.FindPlayer(m->guid))
                { LivingPartyRoleState r = state.roles[member->GetObjectGuid()]; std::ostringstream row; row << "LWOWP1\tR\t" << state.revision << "\t" << Escape(member->GetName()) << "\t" << RoleName(r.primary) << "\t" << r.source; SendAddon(source, receiver, row.str()); }
            if (state.threatClients.count(receiver->GetObjectGuid()))
                if (Unit* target = sObjectAccessor.GetUnit(*receiver, receiver->GetSelectionGuid())) if (target->IsAlive() && receiver->IsWithinDistInMap(target, 100.0f))
                {
                    Player* tank = FindMember(group, state.tank);
                    for (Group::MemberSlotList::const_iterator m = slots.begin(); m != slots.end(); ++m)
                        if (Player* member = sObjectAccessor.FindPlayer(m->guid)) { std::ostringstream row; row << "LWOWP1\tT\t" << state.revision << "\t" << target->GetObjectGuid().GetCounter() << "\t" << Escape(member->GetName()) << "\t" << (uint32)ThreatPercent(member, target, tank) << "\t" << (target->GetVictim() == member ? 1 : 0); SendAddon(source, receiver, row.str()); }
                }
        }
}

bool PlayerbotPartyCombatCoordinator::HandleAddonMessage(Player* receiverBot, Player* sender, const std::string& message)
{
    if (message.find("LWOWP1\t") != 0 || !receiverBot || !sender || receiverBot->GetGroup() != sender->GetGroup()) return false;
    GroupState* state = EnsureState(receiverBot); if (!state) return true; std::vector<std::string> f = Fields(message); if (f.size() < 2) return true;
    if (f[1] == "HELLO" || f[1] == "GET") { state->addonClients.insert(sender->GetObjectGuid()); ++state->revision; }
    else if (f[1] == "THREAT_ON") { state->addonClients.insert(sender->GetObjectGuid()); state->threatClients.insert(sender->GetObjectGuid()); }
    else if (f[1] == "THREAT_OFF") state->threatClients.erase(sender->GetObjectGuid());
    else if (f[1] == "TAKE_LEAD")
    {
        Group* group = receiverBot->GetGroup();
        // PARTY addon messages are delivered to every bot. Exactly the current
        // bot leader is allowed to act, so one click can never fan out into
        // multiple transfers or legacy chat commands.
        if (!group || !group->IsLeader(receiverBot->GetObjectGuid()) ||
            !group->IsMember(sender->GetObjectGuid()))
            return true;
        group->ChangeLeader(sender->GetObjectGuid());
        ++state->revision;
    }
    else if (!IsLeader(sender)) SendAddon(receiverBot, sender, "LWOWP1\tE\tleader_required");
    else if (f[1] == "HOLD") { state->hold = true; ++state->revision; }
    else if (f[1] == "ASSIST") { state->hold = false; ++state->revision; }
    else if (f[1] == "ROLE" && f.size() >= 4)
    {
        if (Player* member = FindMember(sender->GetGroup(), f[2]))
        {
            // PARTY addon messages fan out to every bot. A bot target handles
            // its own role; a human target is handled by the lowest-guid bot.
            Player* executor = member->GetPlayerbotAI() ? member : NULL;
            if (!executor)
            {
                Group::MemberSlotList const& slots = sender->GetGroup()->GetMemberSlots();
                for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
                    if (Player* candidate = sObjectAccessor.FindPlayer(i->guid))
                        if (candidate->GetPlayerbotAI() && (!executor || candidate->GetObjectGuid() < executor->GetObjectGuid()))
                            executor = candidate;
            }
            if (executor != receiverBot) return true;

            LivingPartyRole role = f[3] == "tank" ? LivingPartyRole::Tank :
                f[3] == "healer" ? LivingPartyRole::Healer :
                f[3] == "damage" ? LivingPartyRole::Damage : LivingPartyRole::Auto;
            std::string outcome = ApplyRoleTalents(member, role);
            if (outcome != "completed")
            {
                SendAddon(receiverBot, sender, "LWOWP1\tE\t" + outcome);
                return true;
            }
            if (role == LivingPartyRole::Auto) state->overrides.erase(member->GetObjectGuid());
            else state->overrides[member->GetObjectGuid()] = role;
            RefreshRoles(sender->GetGroup(), *state);
        }
    }
    SendSnapshot(receiverBot->GetGroup(), *state); return true;
}

bool PlayerbotPartyCombatCoordinator::SupportsProposal(const std::string& type) const
{
    return type == "set_party_role" || type == "clear_party_role" || type == "set_puller" ||
        type == "hold_attacks" || type == "resume_assist" || type == "set_tactical_rule" ||
        type == "assign_marker_manager" || type == "clear_tactical_rule";
}

std::string PlayerbotPartyCombatCoordinator::ExecuteProposal(Player* bot, Player* requester, const std::string& type,
    const std::string& capabilityRef, const std::string& intent)
{
    GroupState* state = EnsureState(bot); if (!state || !requester || requester->GetGroup() != bot->GetGroup()) return "party_state_changed";
    if (!IsLeader(requester)) return "leader_required";
    if (type == "hold_attacks") state->hold = true;
    else if (type == "resume_assist") state->hold = false;
    else if (type == "set_puller")
    {
        size_t pfx = capabilityRef.rfind(':'); uint32 guid = pfx == std::string::npos ? 0 : std::strtoul(capabilityRef.c_str() + pfx + 1, NULL, 10);
        Player* p = FindMember(bot->GetGroup(), ObjectGuid(HIGHGUID_PLAYER, guid));
        if (!p) return "member_not_found";
        state->puller = p->GetObjectGuid();
        state->pullerExplicit = true;
    }
    else if (type == "clear_tactical_rule") state->rules.clear();
    else if (type == "set_tactical_rule")
    {
        std::vector<std::string> parts; std::stringstream input(capabilityRef); std::string part;
        while (std::getline(input, part, ':')) parts.push_back(part);
        if (parts.size() != 5 || parts[0] != "party" || parts[1] != "rule" || parts[2] != "target") return "invalid_capability";
        uint32 targetGuid = std::strtoul(parts[3].c_str(), NULL, 10); if (!targetGuid) return "invalid_target";
        LivingPartyTacticalRule rule; rule.id = nextRuleId++; rule.selectorType = "target"; rule.selectorId = targetGuid;
        rule.treatment = parts[4]; rule.createdAt = time(NULL); rule.expiresAt = rule.createdAt + policy.ruleArmSeconds;
        state->rules.push_back(rule);
        ObjectGuid target(HIGHGUID_UNIT, targetGuid);
        if (rule.treatment == "primary") bot->GetGroup()->SetTargetIcon(7, target);
        else if (rule.treatment == "secondary") bot->GetGroup()->SetTargetIcon(6, target);
        else if (rule.treatment == "crowd_control") bot->GetGroup()->SetTargetIcon(4, target);
    }
    else if (type == "assign_marker_manager")
    {
        size_t pfx = capabilityRef.rfind(':'); uint32 guid = pfx == std::string::npos ? 0 : std::strtoul(capabilityRef.c_str() + pfx + 1, NULL, 10);
        Player* p = FindMember(bot->GetGroup(), ObjectGuid(HIGHGUID_PLAYER, guid)); if (!p) return "member_not_found";
        for (std::vector<LivingPartyTacticalRule>::iterator rule = state->rules.begin(); rule != state->rules.end(); ++rule) rule->assignee = p->GetObjectGuid();
    }
    else if (type == "set_party_role" || type == "clear_party_role")
    {
        std::vector<std::string> fields = Fields(std::string(capabilityRef.begin(), capabilityRef.end()));
        size_t first = capabilityRef.find(':'); size_t second = first == std::string::npos ? first : capabilityRef.find(':', first + 1);
        size_t third = second == std::string::npos ? second : capabilityRef.find(':', second + 1);
        uint32 guid = second == std::string::npos ? 0 : std::strtoul(capabilityRef.c_str() + second + 1, NULL, 10);
        Player* p = FindMember(bot->GetGroup(), ObjectGuid(HIGHGUID_PLAYER, guid)); if (!p) return "member_not_found";
        if (type == "clear_party_role") state->overrides.erase(p->GetObjectGuid());
        else
        {
            std::string named = third == std::string::npos ? "damage" : capabilityRef.substr(third + 1);
            LivingPartyRole role = named == "tank" ? LivingPartyRole::Tank : named == "healer" ? LivingPartyRole::Healer : LivingPartyRole::Damage;
            std::string outcome = ApplyRoleTalents(p, role);
            if (outcome != "completed") return outcome;
            state->overrides[p->GetObjectGuid()] = role;
        }
        RefreshRoles(bot->GetGroup(), *state);
    }
    ++state->revision; return "completed";
}

std::string PlayerbotPartyCombatCoordinator::GetCandidateJson(Player* bot, Player* speaker) const
{
    GroupState* state = EnsureState(bot); if (!state) return "null"; LivingPartyRoleState role = GetRole(bot);
    std::ostringstream out; out << "{\"mode\":\"" << policy.mode << "\",\"phase\":\"" << PhaseName(state->phase)
        << "\",\"role\":\"" << RoleName(role.primary) << "\",\"role_source\":\"" << role.source
        << "\",\"is_leader\":" << (IsLeader(bot) ? "true" : "false") << ",\"requester_is_leader\":"
        << (IsLeader(speaker) ? "true" : "false") << ",\"hold\":" << (state->hold ? "true" : "false")
        << ",\"capabilities\":[";
    bool first = true;
    if (IsLeader(speaker))
    {
        out << "{\"type\":\"hold_attacks\",\"capability_ref\":\"party:hold\"},"
            << "{\"type\":\"resume_assist\",\"capability_ref\":\"party:assist\"},"
            << "{\"type\":\"clear_tactical_rule\",\"capability_ref\":\"party:rules:clear\"}";
        first = false;
        Group::MemberSlotList const& slots = bot->GetGroup()->GetMemberSlots();
        for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
            if (Player* member = sObjectAccessor.FindPlayer(i->guid))
            {
                const char* roles[] = {"tank", "healer", "damage"};
                for (uint8 r = 0; r < 3; ++r) out << ",{\"type\":\"set_party_role\",\"capability_ref\":\"party:role:"
                    << member->GetGUIDLow() << ':' << roles[r] << "\",\"member\":\"" << Escape(member->GetName()) << "\"}";
                out << ",{\"type\":\"clear_party_role\",\"capability_ref\":\"party:role:" << member->GetGUIDLow()
                    << ":auto\",\"member\":\"" << Escape(member->GetName()) << "\"}"
                    << ",{\"type\":\"set_puller\",\"capability_ref\":\"party:puller:" << member->GetGUIDLow()
                    << "\",\"member\":\"" << Escape(member->GetName()) << "\"}";
            }
        if (speaker && !speaker->GetSelectionGuid().IsEmpty())
            if (Unit* selected = sObjectAccessor.GetUnit(*speaker, speaker->GetSelectionGuid()))
                if (!selected->IsPlayer() && selected->IsAlive())
                {
                    const char* treatments[] = {"primary", "secondary", "crowd_control", "do_not_attack"};
                    for (uint8 t = 0; t < 4; ++t) out << ",{\"type\":\"set_tactical_rule\",\"capability_ref\":\"party:rule:target:"
                        << selected->GetGUIDLow() << ':' << treatments[t] << "\",\"target_name\":\"" << Escape(selected->GetName()) << "\"}";
                }
    }
    out << "]}"; return out.str();
}
