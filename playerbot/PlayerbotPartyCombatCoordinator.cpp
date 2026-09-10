#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotPartyCombatCoordinator.h"
#include "playerbot/strategy/values/ItemUsageValue.h"
#include "playerbot/AiFactory.h"
#include "playerbot/strategy/Action.h"

#include "Chat/Chat.h"
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
    for (Group::MemberSlotList::const_iterator i = slots.begin(); i != slots.end(); ++i)
        if (Player* p = sObjectAccessor.FindPlayer(i->guid))
        {
            LivingPartyRoleState role = InferRole(p, state); state.roles[p->GetObjectGuid()] = role;
            if (role.primary == LivingPartyRole::Tank && state.tank.IsEmpty()) state.tank = p->GetObjectGuid();
            if (role.primary == LivingPartyRole::Healer && state.healer.IsEmpty()) state.healer = p->GetObjectGuid();
        }
    if (state.tank.IsEmpty()) state.tank = group->GetLeaderGuid();
    if (state.puller.IsEmpty() || !FindMember(group, state.puller)) state.puller = state.tank;
    state.humanLeader = IsRealPlayer(sObjectAccessor.FindPlayer(group->GetLeaderGuid()));
    ++state.revision;
}

bool PlayerbotPartyCombatCoordinator::IsApprovedTarget(const GroupState& state, Unit* target) const
{
    return target && state.approvedTargets.find(target->GetObjectGuid()) != state.approvedTargets.end();
}

void PlayerbotPartyCombatCoordinator::RefreshMarkers(Group* group, GroupState& state) const
{
    ObjectGuid skull = group->GetTargetIcon(7), cross = group->GetTargetIcon(6);
    if (!skull.IsEmpty()) { state.primaryTarget = skull; state.approvedTargets.insert(skull); }
    if (!cross.IsEmpty()) { state.secondaryTarget = cross; state.approvedTargets.insert(cross); }
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
            if (Unit* victim = p->GetVictim()) state.approvedTargets.insert(victim->GetObjectGuid());
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
        else if (old == LivingPartyPhase::Stabilizing && WorldTimer::getMSTimeDiff(state.phaseSince, now) >= policy.stabilizeMilliseconds)
            state.phase = LivingPartyPhase::Engaged;
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
    ReloadPolicy(); GroupState* state = EnsureState(bot); if (!state) return;
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
    GroupState* state = EnsureState(bot); if (!state || state->primaryTarget.IsEmpty()) return NULL;
    return sObjectAccessor.GetUnit(*bot, state->primaryTarget);
}

uint8 PlayerbotPartyCombatCoordinator::ThreatPercent(Player* member, Unit* target, Player* tank) const
{
    if (!member || !target || !tank) return 0;
    float tankThreat = target->getThreatManager().getThreat(tank);
    float memberThreat = target->getThreatManager().getThreat(member);
    return tankThreat > 0.0f ? (uint8)std::min(255.0f, memberThreat * 100.0f / tankThreat) : (member == tank && memberThreat > 0.0f ? 100 : 0);
}

bool PlayerbotPartyCombatCoordinator::CanInitiate(Player* bot, Unit* target) const
{
    ReloadPolicy(); if (policy.mode != "active" || !policy.engagementGating) return true;
    GroupState* state = EnsureState(bot); if (!state || !target) return true;
    for (std::vector<LivingPartyTacticalRule>::const_iterator rule = state->rules.begin(); rule != state->rules.end(); ++rule)
        if (rule->selectorType == "target" && rule->selectorId == target->GetGUIDLow() && rule->treatment == "do_not_attack") return false;
    if (IsApprovedTarget(*state, target)) return true;
    if (!state->puller.IsEmpty() && state->puller == bot->GetObjectGuid()) return true;
    return false;
}

float PlayerbotPartyCombatCoordinator::ActionMultiplier(Player* bot, Action* action) const
{
    ReloadPolicy(); if (!action || policy.mode != "active") return 1.0f;
    GroupState* state = EnsureState(bot); if (!state) return 1.0f;
    ActionThreatType threat = action->getThreatType(); if (threat == ActionThreatType::ACTION_THREAT_NONE || threat == ActionThreatType::ACTION_THREAT_LOW) return 1.0f;
    LivingPartyRoleState role = GetRole(bot); if (role.primary == LivingPartyRole::Tank) return 1.0f;
    Unit* target = action->GetTarget();
    // Friendly healing, cleansing, and protection are never subject to hostile
    // pull or DPS threat gates. Existing class strategies remain authoritative
    // for spell choice and emergency-heal timing.
    if (target && bot->CanAssist(target)) return 1.0f;
    if (target && !CanInitiate(bot, target)) return 0.0f;
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
            sLog.outDetail("LivingParty threat hard-hold bot=%s target=%u threat=%u action=%s",
                bot->GetName(), target ? target->GetGUIDLow() : 0, pct, action->getName().c_str());
        return 0.0f;
    }
    if (state->threatHeld.count(bot->GetObjectGuid()))
    {
        if (pct > policy.resumeThreatPercent) return 0.0f;
        state->threatHeld.erase(bot->GetObjectGuid());
        sLog.outDetail("LivingParty threat resume bot=%s target=%u threat=%u",
            bot->GetName(), target ? target->GetGUIDLow() : 0, pct);
    }
    if (pct >= policy.softThreatPercent)
    {
        if (state->threatSoftHeld.insert(bot->GetObjectGuid()).second)
            sLog.outDetail("LivingParty threat soft-throttle bot=%s target=%u threat=%u action=%s",
                bot->GetName(), target ? target->GetGUIDLow() : 0, pct, action->getName().c_str());
        return threat == ActionThreatType::ACTION_THREAT_AOE ? 0.0f : 0.35f;
    }
    if (state->threatSoftHeld.erase(bot->GetObjectGuid()))
        sLog.outDetail("LivingParty threat normal bot=%s target=%u threat=%u",
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
        if (Player* member = FindMember(sender->GetGroup(), f[2])) { LivingPartyRole role = f[3] == "tank" ? LivingPartyRole::Tank : f[3] == "healer" ? LivingPartyRole::Healer : f[3] == "damage" ? LivingPartyRole::Damage : LivingPartyRole::Auto; if (role == LivingPartyRole::Auto) state->overrides.erase(member->GetObjectGuid()); else state->overrides[member->GetObjectGuid()] = role; RefreshRoles(sender->GetGroup(), *state); }
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
        Player* p = FindMember(bot->GetGroup(), ObjectGuid(HIGHGUID_PLAYER, guid)); if (!p) return "member_not_found"; state->puller = p->GetObjectGuid();
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
        else { std::string named = third == std::string::npos ? "damage" : capabilityRef.substr(third + 1); LivingPartyRole role = named == "tank" ? LivingPartyRole::Tank : named == "healer" ? LivingPartyRole::Healer : LivingPartyRole::Damage; state->overrides[p->GetObjectGuid()] = role; }
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
